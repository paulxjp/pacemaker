import os
import re
import sys
import logging
from datetime import datetime
from collections import defaultdict

def compile_patterns(pattern_file='err_pattern.txt'):
    """
    Compile regex patterns from a pattern file, automatically adding word boundaries.

    Args:
        pattern_file (str): The file containing the regex patterns.

    Returns:
        list: A list of compiled regex patterns.

    Raises:
        FileNotFoundError: If the pattern file does not exist.
    """
    if not os.path.isfile(pattern_file):
        logging.error(f"Pattern file '{pattern_file}' not found.")
        sys.exit(1)

    with open(pattern_file, 'r') as f:
        raw_patterns = [line.strip() for line in f if line.strip()]

    # Add word boundaries to each pattern where appropriate
    processed_patterns = [
        fr'\b{pattern}\b' if not pattern.startswith('^') and not pattern.endswith('$') else pattern
        for pattern in raw_patterns
    ]

    return [re.compile(pattern, re.IGNORECASE) for pattern in processed_patterns]

def parse_log(file_path, patterns, output_file=None):
    """
    Parse the log file and search for patterns.

    Args:
        file_path (str): The path to the log file.
        patterns (list): The list of compiled regex patterns.
        output_file (file object, optional): The output file to write matches to.

    Raises:
        FileNotFoundError: If the file_path does not exist.
    """
    if not file_path:
        return

    error_counts = defaultdict(int)

    try:
        with open(file_path, 'r') as f:
            logging.info(f"Start parsing {file_path}")
            header = f"======= {os.path.basename(file_path)} ======="
            if output_file:
                output_file.write(header + '\n')
            print(header)
            for line in f:
                matched = False
                for pattern in patterns:
                    if pattern.search(line):
                        matched = True
                        error_counts[pattern.pattern] += 1
                        if output_file:
                            output_file.write(line.strip() + '\n')
                        else:
                            print(line.strip())
                        break  # Break the loop once a match is found
                if not matched:
                    logging.debug(f"No match for line: {line.strip()}")
            if output_file:
                output_file.write('\n')
            print('\n')
    except FileNotFoundError:
        logging.error(f"File {file_path} not found.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred while processing {file_path}: {e}")
        sys.exit(1)
    
    return error_counts

def get_directory_path(prompt):
    """
    Prompt the user for a directory path and validate it.

    Args:
        prompt (str): The prompt message for the user.

    Returns:
        str: The validated directory path.
    """
    directory = input(prompt)
    if directory:
        if os.path.isdir(directory):
            if not any(os.scandir(directory)):
                logging.warning(f"The directory '{directory}' is empty.")
                sys.exit(1)  # Exit the script if the directory is empty
            return directory
        else:
            logging.error(f"Directory path '{directory}' does not exist.")
            sys.exit(1)
    return None

def print_error_statistics(error_counts, output_file=None):
    """
    Print the statistics of each matched error string.

    Args:
        error_counts (dict): Dictionary containing the error patterns and their counts.
        output_file (file object, optional): The output file to write the statistics to.
    """
    print("\nError Statistics:")
    if output_file:
        output_file.write("\nError Statistics:\n")

    for pattern, count in error_counts.items():
        clean_pattern = pattern.replace(r'\b', '')  # Remove word boundary markers
        result = f"\"{clean_pattern}: {count} occurrences\""
        print(result)
        if output_file:
            output_file.write(result + '\n')

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    patterns = compile_patterns()

    # Ask the user for the directory path
    logging.info("Fetching directory path...")
    directory_path = get_directory_path("Please input the directory path: ")

    if not directory_path:
        logging.error("The directory path is required and cannot be empty.")
        sys.exit(1)

    # Set up the output file
    timestamp = datetime.now().strftime('%m-%d-%H%M%S')
    output_file_name = f'clusterlogparser_{timestamp}.txt'
    output_file = open(output_file_name, 'w')

    try:
        error_counts = defaultdict(int)

        # Parse each log file in the directory and its subdirectories
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if os.path.isfile(file_path):
                    counts = parse_log(file_path, patterns, output_file)
                    for key, value in counts.items():
                        error_counts[key] += value

        # Print error statistics
        print_error_statistics(error_counts, output_file)

        logging.info(f"Output saved to file: {output_file_name}")
    finally:
        output_file.close()

if __name__ == "__main__":
    main()
