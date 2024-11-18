import os
import sys
from datetime import datetime

# Define the separator used to split the log file
SEPARATOR = '#====\n'

def split_log_file(input_file):
    # Read the entire content of the input file
    with open(input_file, 'r') as file:
        content = file.read()
    
    # Split the content by the separator
    sections = content.split(SEPARATOR)
    
    # Remove empty sections
    sections = [section for section in sections if section.strip()]
    
    # Create output directory if it doesn't exist
    output_dir = 'split_logs'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Write sections to separate files
    for i in range(0, len(sections), 2):
        # Extract datetime from the second line of the section
        second_line = sections[i].split('\n')[0].strip()
        try:
            # Parse the datetime string
            log_datetime = datetime.strptime(second_line, "%Y-%m-%dT%H:%M:%S.%f")
            # Format the datetime to create a filename
            filename = log_datetime.strftime("%Y%m%dT%H%M%S.%f") + '.log'
        except ValueError:
            # Handle invalid datetime format
            print(f"Error: Invalid datetime format in section {i//2 + 1}. Exiting.")
            sys.exit(1)

        # Write the section to a new file
        with open(os.path.join(output_dir, filename), 'w') as output_file:
            output_file.write(SEPARATOR)
            output_file.write(sections[i])
            if i + 1 < len(sections):
                output_file.write(SEPARATOR)
                output_file.write(sections[i + 1])
        print(f"Created file: {filename}")

if __name__ == "__main__":
    # Check if the input file is provided as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python LogSplitter.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    # Check if the input file exists and is readable
    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' does not exist or is not readable.")
        sys.exit(1)

    # Check if the input file starts with the separator
    with open(input_file, 'r') as file:
        first_line = file.readline()
        if first_line.strip() != SEPARATOR.strip():
            print(f"Error: File '{input_file}' is not properly formatted (does not start with the separator).")
            sys.exit(1)

    # Split the log file into separate files
    split_log_file(input_file)