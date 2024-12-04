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
    except FileNotFoundError:
        logging.error(f"File {file_path} not found.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred while processing {file_path}: {e}")
        sys.exit(1)
    
    return error_counts

def get_file_path(prompt):
    """
    Prompt the user for a file path and validate it.

    Args:
        prompt (str): The prompt message for the user.

    Returns:
        str: The validated file path.
    """
    file_name = input(prompt)
    if file_name:
        current_directory = os.path.dirname(os.path.realpath(__file__))
        full_path = os.path.join(current_directory, file_name)
        if os.path.isfile(full_path):
            return full_path
        else:
            logging.error(f"File path '{full_path}' does not exist.")
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

    # Ask the user for the file paths
    logging.info("Fetching file paths...")
    file_path1 = get_file_path("Please input the first file path: ")
    file_path2 = get_file_path("Please input the second file path (press enter to skip): ")

    if not file_path1:
        logging.error("The first file path is required and cannot be empty.")
        sys.exit(1)

    # Ask the user if they want to save the output to a file
    save_output = input("Do you want to save the output to a file? (y/n): ").lower()

    output_file = None
    if save_output in ['y', 'yes']:
        timestamp = datetime.now().strftime('%m-%d-%H%M%S')
        output_file_name = f'clusterlogparser_{timestamp}.txt'
        output_file = open(output_file_name, 'w')

    try:
        error_counts = defaultdict(int)

        # Parse the first file
        counts1 = parse_log(file_path1, patterns, output_file)
        for key, value in counts1.items():
            error_counts[key] += value

        # Parse the second file if provided
        if file_path2:
            counts2 = parse_log(file_path2, patterns, output_file)
            for key, value in counts2.items():
                error_counts[key] += value

        # Print error statistics
        print_error_statistics(error_counts, output_file)

        if output_file:
            logging.info(f"Output saved to file: {output_file_name}")
    finally:
        if output_file:
            output_file.close()

if __name__ == "__main__":
    main()