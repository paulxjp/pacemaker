import os
import re
import sys
import logging
import argparse
from datetime import datetime
from collections import defaultdict

# Define relevant keywords for log files
TARGET_KEYWORDS = ['messages', 'journal', 'analysis', 'crm_mon', 'ha-log', 'corosync', 'pacemaker']

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
    """
    Check if the file name contains any of the target keywords.
    
    Args:
        file_name (str): The name of the file to check.

    Returns:
        bool: True if the file name contains any target keywords, False otherwise.
    """
    return any(keyword in file_name for keyword in TARGET_KEYWORDS)

def parse_log(file_path, patterns, output_file=None):
    error_counts = defaultdict(int)

    if not file_path or not is_text_file(file_path):
        logging.warning(f"Skipping non-text or unreadable file: {file_path}")
        return error_counts

    # Try reading the file with different encodings
    encodings = ['utf-8', 'latin-1']  # Add more encodings if needed

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                logging.info(f"Start parsing {file_path} with encoding {encoding}")
                header = f"======= {os.path.basename(file_path)} ======="
                if output_file:
                    output_file.write(header + '\n')
                print(header)
                for line in f:
                    matched_any = False
                    for pattern in patterns:
                        if pattern.search(line):
                            matched_any = True
                            error_counts[pattern.pattern] += 1
                            if output_file:
                                output_file.write(line.strip() + '\n')
                            else:
                                print(line.strip())
                    if not matched_any:
                        logging.debug(f"No match for line: {line.strip()}")
                if output_file:
                    output_file.write('\n')
                print('\n')
            break  # Exit the loop if the file was successfully read
        except UnicodeDecodeError:
            logging.warning(f"Failed to decode {file_path} using {encoding}, trying next encoding...")
        except FileNotFoundError:
            logging.error(f"File {file_path} not found.")
            sys.exit(1)
        except Exception as e:
            logging.error(f"An unexpected error occurred while processing {file_path}: {e}")
            sys.exit(1)
    else:
        logging.error(f"Unable to decode {file_path} with the specified encodings.")
    
    return error_counts

def print_error_statistics(error_counts, output_file=None):
    print("\nError Statistics:")
    if output_file:
        output_file.write("\nError Statistics:\n")

    for pattern, count in error_counts.items():
        clean_pattern = pattern.replace(r'\b', '')
        result = f"\"{clean_pattern}: {count} occurrences\""
        print(result)
        if output_file:
            output_file.write(result + '\n')

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
        error_counts = defaultdict(int)

        for root, _, files in os.walk(directory_path):
            for file_name in files:
                if is_target_file(file_name):
                    file_path = os.path.join(root, file_name)
                    if os.path.isfile(file_path):
                        counts = parse_log(file_path, patterns, output_file)
                        for key, value in counts.items():
                            error_counts[key] += value

        print_error_statistics(error_counts, output_file)

        logging.info(f"Output saved to file: {output_file_name}")
    finally:
        output_file.close()

if __name__ == "__main__":
    main()
