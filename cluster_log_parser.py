from datetime import datetime, timezone, timedelta
import time
from collections import defaultdict
from datetime import datetime
import os
import re
import sys
import logging
import argparse
import gzip
import lzma

# Define relevant keywords for log files
TARGET_KEYWORDS = ['messages', 'journal', 'crm_mon', 'analysis', 'ha-log', 'corosync', 'pacemaker']

# Define a global constant for the number of days
DAYS_TO_ANALYZE = 60  # Number of days to look back for log analysis

# Global pattern definitions
LOG_PATTERNS = [
    (r'^(\w{3} \d{2} \d{2}:\d{2}:\d{2})(?:\.\d+)? \[\d+\] (\S+)', 1),
    (r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}) (\S+)', 2),
    (r'^(\w{3} \d{2} \d{2}:\d{2}:\d{2}) (\S+)', 3),
    (r'^(\w{3} \d{2} \d{2}:\d{2}:\d{2}) \[\d+\] (\S+)', 4)
]

def compile_patterns(pattern_file='err_pattern.txt'):
    if not os.path.isfile(pattern_file):
        logging.error(f"Pattern file '{pattern_file}' not found.")
        sys.exit(1)

    with open(pattern_file, 'r') as f:
        raw_patterns = [line.strip() for line in f if line.strip()]

    processed_patterns = [
        fr'\b{pattern}\b' if not pattern.startswith('^') and not pattern.endswith('$') else pattern
        for pattern in raw_patterns
    ]

    return [re.compile(pattern, re.IGNORECASE) for pattern in processed_patterns]

def is_text_file(file_path, block_size=512):
    if file_path.endswith(('.tar', '.zip', '.gz', '.bz2', '.xz', '.7z')):
        return False

    try:
        with open(file_path, 'rb') as file:
            block = file.read(block_size)
            block.decode('utf-8')
            return True
    except (UnicodeDecodeError, FileNotFoundError):
        return False

def is_target_file(file_name):
    return any(keyword in file_name for keyword in TARGET_KEYWORDS)
    
def extract_date_from_filename(filename):
    # Define regex patterns for various date formats in filenames
    patterns = [
        r'(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})',    # YYYYMMDD
        r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})',  # YYYY-MM-DD
        r'(?P<year>\d{4})_(?P<month>\d{2})_(?P<day>\d{2})',  # YYYY_MM_DD
        r'(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})'     # YYMMDD
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            year = int(match.group('year'))
            month = int(match.group('month'))
            day = int(match.group('day'))

            # Handle two-digit year (e.g., "YYMMDD")
            if year < 100:
                current_year = datetime.now().year
                current_century = current_year // 100 * 100
                year += current_century

            try:
                return datetime(year, month, day)
            except ValueError:
                # Log a warning if the date is invalid
                logging.warning(f"Invalid date extracted from filename: {filename}")
                continue

    # Log a warning if no date pattern matches
    logging.warning(f"No valid date found in filename: {filename}")
    return None
    
def should_parse_file(filename):
    file_date = extract_date_from_filename(filename)
    if file_date:
        # Calculate the cutoff date based on the global constant
        cutoff_date = datetime.now() - timedelta(days=DAYS_TO_ANALYZE)
        return file_date >= cutoff_date
    return True  # If no date is found, assume it's a recent log

def parse_and_format_timestamp(timestamp, current_year):
    formats = [
        # Pattern order matter here
        "%b %d %H:%M:%S",     # Pattern for "Jan 07 00:19:21"
        "%b %d %H:%M:%S.%f",  # Pattern for "Feb 16 03:20:34.165"
        "%Y-%m-%dT%H:%M:%S.%f%z"  # Pattern for "2025-03-07T01:45:59.817699+00:00"
    ]
    
    current_month = datetime.now().month

    for fmt in formats:
        try:
            parsed_date = datetime.strptime(timestamp, fmt)
            # print(f"DEBUG: Parsed date (initial): {parsed_date}")  # Debugging output for initial parsed date
            
            # If the year is missing, parsed_date.year will be 1900
            if parsed_date.year == 1900:
                # Assign last year if the month is greater than the current month
                if parsed_date.month > current_month:
                    parsed_date = parsed_date.replace(year=current_year - 1)
                    # print(f"DEBUG: Parsed date (initial): {parsed_date}")  # Debugging output for initial parsed date
                else:
                    parsed_date = parsed_date.replace(year=current_year)
                    # print(f"DEBUG: Adjusted year (current year): {parsed_date}")  # Debugging output for adjusted date
                    
            # Make current time aware by using the parsed_date's timezone
            now_aware = datetime.now(parsed_date.tzinfo)
            
            # Check if the parsed date is within the last days
            if parsed_date < now_aware - timedelta(days=DAYS_TO_ANALYZE):
                # print(f"DEBUG: Parsed date is older than {DAYS_TO_ANALYZE} days: {parsed_date}")  # Debugging output for date check
                return None

            return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            # Debugging output for timestamp parsing failures, this is normal that if one previous format gives exception then it will continue
            # print(f"DEBUG exception: Failed to parse timestamp: {timestamp} using format {fmt}. Error: {e}")
            continue
            
    return None

def extract_timestamp_hostname(line):
    current_year = datetime.now().year

    for pattern, _ in LOG_PATTERNS:
        match = re.match(pattern, line)
        if match:
            timestamp, hostname = match.groups()
            hostname = hostname.lower()  # Normalize to lowercase
            formatted_timestamp = parse_and_format_timestamp(timestamp, current_year)
            if formatted_timestamp is None:
                # print(f"DEBUG: Failed to format timestamp: {timestamp}")
                continue
            return formatted_timestamp, hostname

    # print(f"DEBUG: Failed to extract timestamp/hostname from line: {line.strip()}")
    return None, None

def decompress_file(file_path):
    decompressed_content = None
    decompressed_file_path = None
    
    if file_path.endswith('.gz'):
        decompressed_file_path = file_path[:-3]  # Remove '.gz' extension
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            decompressed_content = f.read()
    elif file_path.endswith('.xz'):
        decompressed_file_path = file_path[:-3]  # Remove '.xz' extension
        with lzma.open(file_path, 'rt', encoding='utf-8') as f:
            decompressed_content = f.read()

    if decompressed_content is not None and decompressed_file_path is not None:
        # Write the decompressed content to a file
        with open(decompressed_file_path, 'w', encoding='utf-8') as decompressed_file:
            decompressed_file.write(decompressed_content)
    
    return decompressed_content
        
def parse_log(file_path, patterns, error_hourly_counts, output_file=None):
    if not should_parse_file(os.path.basename(file_path)):
        logging.info(f"Skipping file {file_path} as it is older than {DAYS_TO_ANALYZE} days.")
        return
    
    if not file_path or (not is_text_file(file_path) and not file_path.endswith(('.gz', '.xz'))):
        logging.warning(f"Skipping non-text or unreadable file: {file_path}")
        return

    encodings = ['utf-8', 'latin-1']  # Add more encodings if needed
    
    file_content = None
    if file_path.endswith(('.gz', '.xz')):
        try:
            file_content = decompress_file(file_path)
            if file_content is None:
                logging.error(f"Failed to decompress {file_path}")
                return
            # Print header only once when file content is successfully decompressed
            header = f"======= {file_path} ======="
            if output_file:
                output_file.write(header + '\n')
            print(header)
        except Exception as e:
            logging.error(f"Failed to decompress {file_path}: {e}")
            return

    encoding_failed = False  # Flag to indicate if decoding has failed for this file
    for encoding in encodings:
        try:
            if file_content is not None:
                # Use the decompressed content
                lines = file_content.splitlines()
            else:
                # Open and read file directly
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                    # Print header only for non-compressed files
                    header = f"======= {file_path} ======="
                    if output_file:
                        output_file.write(header + '\n')
                    print(header)

            # logging.info(f"Start parsing {file_path} with encoding {encoding}")
                
            for line in lines:
                for pattern in patterns:
                    if pattern.search(line):
                        # Debug print(f"Pattern matched: {pattern.pattern} in {file_path}")
                        timestamp, hostname = extract_timestamp_hostname(line)
                        
                        if timestamp is None or hostname is None:
                            # Debugging output for lines with missing information
                            # print(f"DEBUG: Skipping line due to missing timestamp or hostname: {line.strip()}")
                            break  # Skip this line if timestamp or hostname is missing
                        
                        # Debug print(f"Extracted Timestamp: {timestamp}, Hostname: {hostname}")
                        
                        if timestamp and hostname:
                            date_hour = timestamp[:13]  # Extract date and hour part
                            error_hourly_counts[hostname][pattern.pattern][date_hour]['total'] += 1
                            error_hourly_counts[hostname][pattern.pattern][date_hour]['files'][file_path] += 1
                        
                        # Debug print(f"Updated error_hourly_counts for {hostname}: {error_hourly_counts[hostname]}")
                        if output_file:
                            output_file.write(line.strip() + '\n')
                        else:
                            print(line.strip())
                        break  # Stop checking other patterns if one matches
            if output_file:
                output_file.write('\n')
            print('\n')
            break  # Exit the loop if the file was successfully read
        except UnicodeDecodeError:
            if not encoding_failed:
                # logging.warning(f"Failed to decode {file_path} using {encoding}, trying next encoding...")
                encoding_failed = True  # Set the flag to avoid repeated messages
            continue
        except FileNotFoundError:
            logging.error(f"File {file_path} not found.")
            sys.exit(1)
        except Exception as e:
            logging.error(f"An unexpected error occurred while processing {file_path}: {e}")
            sys.exit(1)
    else:
        logging.error(f"Unable to decode {file_path} with the specified encodings.")

def extract_and_format_logs(log_lines):
    current_year = datetime.now().year
    grouped_logs = defaultdict(list)

    for line in log_lines:
        for pattern, _ in LOG_PATTERNS:
            match = re.match(pattern, line)
            if match:
                timestamp, hostname = match.groups()
                hostname = hostname.lower()  # Normalize to lowercase
                formatted_timestamp = parse_and_format_timestamp(timestamp, current_year)
                if formatted_timestamp is None:
                    # print(f"DEBUG: Failed to format timestamp: {timestamp}")
                    break

                remaining_line = line[len(match.group(0)):].strip()
                grouped_logs[hostname].append((formatted_timestamp, remaining_line))
                break
        else:
            print(f"DEBUG: Failed to extract timestamp/hostname from line: {line.strip()}")

    for hostname in grouped_logs:
        grouped_logs[hostname].sort(key=lambda x: x[0])

    return grouped_logs

def print_error_statistics(error_counts, error_hourly_counts, output_file=None):
    
    title = """
##########################################
#                                        #
#       Pacemaker Log Analysis           #
#       From Azure Linux Team            #
#                                        #
##########################################
"""

    # Print the title
    print(title)
    if output_file:
        output_file.write(title + '\n')
        
    # Get the local time and timezone
    local_time = time.localtime()
    local_timezone = time.strftime('%Z', local_time)
    local_utc_offset = time.strftime('%z', local_time)

    # Get and print the current local timestamp with timezone
    current_timestamp = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S {local_timezone}{local_utc_offset}")
    timestamp_line = f"Report generated on: {current_timestamp}\n"
    print(timestamp_line)
    if output_file:
        output_file.write(timestamp_line + '\n')
        
    separator = "=" * 80  # Define a separator line for clarity
    print("\n" + separator)
    print("Error Statistics Report")
    print(separator)
    
    if output_file:
        output_file.write("\n" + separator + "\n")
        output_file.write("Error Statistics Report\n")
        output_file.write(separator + "\n")

    for hostname, patterns in error_hourly_counts.items():
        host_header = f"\n{separator}\nError Statistics for Hostname: {hostname}\n{separator}"
        print(host_header)
        if output_file:
            output_file.write(host_header + '\n')

        for pattern, date_hourly_counts in patterns.items():
            clean_pattern = pattern.replace(r'\b', '')
            total_count = sum(info['total'] for info in date_hourly_counts.values())
            result = f"\nPattern: \"{clean_pattern}\" - {total_count} occurrences"
            print(result)
            if output_file:
                output_file.write(result + '\n')

            # Group occurrences by file path
            file_grouped_data = defaultdict(list)
            for date_hour, info in sorted(date_hourly_counts.items()):
                for file_path, file_count in info['files'].items():
                    file_grouped_data[file_path].append((date_hour, file_count))

            for file_path, occurrences in file_grouped_data.items():
                print(f"\n[{file_path}]")
                if output_file:
                    output_file.write(f"\n[{file_path}]\n")

                for date_hour, count in occurrences:
                    if count > 0:
                        date, hour = date_hour.split()
                        hourly_result = f"{date} {hour}:00 ~ {hour}:59 - {count} occurrences"
                        print(hourly_result)
                        if output_file:
                            output_file.write(hourly_result + '\n')

def should_process_file(file_path, processed_files):
    """
    Determine if a given log file should be processed based on whether it has
    a compressed counterpart.

    :param file_path: Path to the log file.
    :param processed_files: Set of processed file names to avoid duplicates.
    :return: Boolean indicating if the file should be processed.
    """
    # Check if the file is a compressed log file
    if file_path.endswith(('.gz', '.xz')):
        # Consider the base name without the compression extension
        base_name = os.path.basename(file_path)[:-3]
        if base_name in processed_files:
            # If the base name is already in the processed files, skip this file
            return False
        # Otherwise, mark this compressed file as processed
        processed_files.add(base_name)
        return True
    else:
        # For uncompressed files, only process if there's no compressed counterpart
        compressed_name_gz = f"{file_path}.gz"
        compressed_name_xz = f"{file_path}.xz"
        if not os.path.exists(compressed_name_gz) and not os.path.exists(compressed_name_xz):
            # If no compressed version exists, mark this file as processed
            processed_files.add(os.path.basename(file_path))
            return True
    return False
    
def main():
    parser = argparse.ArgumentParser(description="Pacemaker Log file analyzer")
    parser.add_argument('-d', '--directory', help="Directory containing log files", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    patterns = compile_patterns()

    directory_path = args.directory

    if not directory_path or not os.path.isdir(directory_path):
        logging.error("The directory path is invalid or does not exist.")
        sys.exit(1)

    timestamp = datetime.now().strftime('%m-%d-%H%M%S')
    output_file_name = f'clusterlogparser_{timestamp}.txt'
    output_file = open(output_file_name, 'w')

    try:
        error_hourly_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'total': 0, 'files': defaultdict(int)})))
        all_matched_lines = []

        processed_files = set()  # To keep track of processed files

        for root, _, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if is_target_file(file_name) and should_process_file(file_path, processed_files):
                    if os.path.isfile(file_path):
                        parse_log(file_path, patterns, error_hourly_counts, output_file)

        # Print error statistics to console and output file
        print_error_statistics(None, error_hourly_counts, output_file)

        # Process matched log lines and write sorted results to separate files for each hostname
        grouped_logs = extract_and_format_logs(all_matched_lines)

        for hostname, logs in grouped_logs.items():
            hostname_output_file_name = f"{hostname}_{timestamp}_sort.txt"
            with open(hostname_output_file_name, 'w') as hostname_output_file:
                if logs:
                    hostname_output_file.write(f"======= Hostname: {hostname} =======\n")
                    for log_timestamp, remaining_line in logs:
                        hostname_output_file.write(f"{log_timestamp} | {remaining_line}\n")
                else:
                    hostname_output_file.write(f"======= Hostname: {hostname} =======\nNo errors captured.\n")

            logging.info(f"Output saved to file: {hostname_output_file_name}")

        logging.info(f"Output saved to file: {output_file_name}")
    finally:
        output_file.close()

if __name__ == "__main__":
    main()
