import sys
import os
import re
import json

output_file='parsed_logs.json'

def convert_numeric_values(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                if value.isdigit():
                    data[key] = int(value)
                else:
                    try:
                        data[key] = float(value)
                    except ValueError:
                        pass
            elif isinstance(value, (dict, list)):
                convert_numeric_values(value)
    elif isinstance(data, list):
        for i in range(len(data)):
            if isinstance(data[i], str):
                if data[i].isdigit():
                    data[i] = int(data[i])
                else:
                    try:
                        data[i] = float(data[i])
                    except ValueError:
                        pass
            elif isinstance(data[i], (dict, list)):
                convert_numeric_values(data[i])

def print_section_content(section):
    print("--- Section Content: ---")
    print(section)

def parse_header(file):
    # Read and validate the first line of the header
    first_line = file.readline()
    if first_line.strip() != '#====':
        raise Exception(f"Invalid file format: {log_file_path}")

    # Read and validate the datetime line
    datetime = file.readline()
    datetime_pattern = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+')
    if not datetime_pattern.match(datetime.strip()):
        raise Exception(f"Invalid datetime format: {log_file_path}")

    # Create JSON object for datetime
    jsonized = '{"datetime": "' + datetime.strip() + '"}'

    # Read and validate the timestamp line
    timestamp = file.readline()
    timestamp_pattern = re.compile(r'\d{10}')
    if not timestamp_pattern.match(timestamp.strip()):
        raise Exception(f"Invalid timestamp format: {log_file_path}")

    # Read and validate the last line of the header
    last_header = file.readline()
    if last_header.strip() != '#====':
        raise Exception(f"Invalid file format: {log_file_path}")

    return jsonized

def parse_sysbench_memory_test(section):
    # Parse sysbench memory test section
    sysbench_data = {}

    # Split section into subsections based on the sysbench command
    subsections = section.split('sysbench --memory-block-size')
    for i in range(1, len(subsections)):
        subsection = subsections[i]
        if subsection:
            operation = ''

            # Extract operation type
            match = re.search(r'\s\soperation: (?P<opt_operation>\w+)\n', subsection)
            if not match:
                print(f"Cannot determine an operation in sysbench memory test section: {i}")
                continue
            
            operation = match.group('opt_operation')
            sysbench_data[f"sysbench_{operation}_{i}"] = {}

            # Extract general statistics
            match = re.search(r'General statistics:\s+total time:\s+(?P<total_time>[\d.]+)s\s+total number of events:\s+(?P<total_events>\d+)', subsection)
            if match:
                sysbench_data[f"sysbench_{operation}_{i}"]["general_statistics"] = match.groupdict()

            # Extract latency statistics
            match = re.search(r'Latency \(ms\):\s+min:\s+(?P<latency_min>[\d.]+)\s+avg:\s+(?P<latency_avg>[\d.]+)\s+max:\s+(?P<latency_max>[\d.]+)\s+95th percentile:\s+(?P<latency_95th>[\d.]+)\s+sum:\s+(?P<latency_sum>[\d.]+)', subsection)
            if match:
                sysbench_data[f"sysbench_{operation}_{i}"]["latency"] = match.groupdict()

            # Extract threads fairness statistics
            match = re.search(r'Threads fairness:\s+events \(avg/stddev\):\s+(?P<events_avg>[\d.]+)/(?P<events_stddev>[\d.]+)\s+execution time \(avg/stddev\):\s+(?P<exec_time_avg>[\d.]+)/(?P<exec_time_stddev>[\d.]+)', subsection)
            if match:
                sysbench_data[f"sysbench_{operation}_{i}"]["threads_fairness"] = match.groupdict()

    # Convert sysbench data to JSON
    convert_numeric_values(sysbench_data)
    jsonized = json.dumps(sysbench_data, indent=4)
    return jsonized
    
def parse_vmstat(section):
    # Parse /proc/vmstat section
    vmstat_data = {}
    lines = section.strip().split('\n')
    
    # Parse each line
    for line in lines[1:]:  # Skip the first line which is the header
        match = re.match(r'(?P<key>[\w_]+)\s+(?P<value>[\d]+)', line)
        if match:
            key = match.group('key')
            value = int(match.group('value'))
            vmstat_data[key] = value

    # Convert vmstat data to JSON
    convert_numeric_values(vmstat_data)
    jsonized = json.dumps(vmstat_data, indent=4)
    return jsonized

def parse_meminfo(section):
    # Parse /proc/meminfo section
    meminfo_data = {}
    lines = section.strip().split('\n')
    
    # Parse each line
    for line in lines[1:]:  # Skip the first line which is the header
        match = re.match(r'(?P<key>[\w\(\)]+):\s+(?P<value>[\d]+)', line)
        if match:
            key = match.group('key')
            value = int(match.group('value'))
            meminfo_data[key] = value

    # Convert meminfo data to JSON
    convert_numeric_values(meminfo_data)
    jsonized = json.dumps(meminfo_data, indent=4)
    return jsonized

def parse_top(section):
    # Parse top command output section
    top_data = {}
    lines = section.strip().split('\n')
    
    # Parse the first line
    match = re.match(r'top - (?P<time>[\d:]+) up (?P<uptime_days>\d+) days, (?P<uptime_hours>\d+):(?P<uptime_minutes>\d+),\s+(?P<users>\d+) users,  load average: (?P<load1>[\d.]+), (?P<load5>[\d.]+), (?P<load15>[\d.]+)', lines[1])
    if match:
        top_data.update(match.groupdict())
    
    # Parse the second line
    match = re.match(r'Tasks: (?P<total_tasks>\d+) total, +(?P<running_tasks>\d+) running, +(?P<sleeping_tasks>\d+) sleeping, +(?P<stopped_tasks>\d+) stopped, +(?P<zombie_tasks>\d+) zombie', lines[2])
    if match:
        top_data.update(match.groupdict())
    
    # Parse the third line
    match = re.match(r'%Cpu\(s\): +(?P<user_cpu>[\d.]+) us, +(?P<system_cpu>[\d.]+) sy, +(?P<nice_cpu>[\d.]+) ni, +(?P<idle_cpu>[\d.]+) id, +(?P<wait_cpu>[\d.]+) wa, +(?P<hardware_interrupts>[\d.]+) hi, +(?P<software_interrupts>[\d.]+) si, +(?P<steal_cpu>[\d.]+) st', lines[3])
    if match:
        top_data.update(match.groupdict())
    
    # Parse the fourth line
    match = re.match(r'MiB Mem : +(?P<total_mem>[\d.]+) total, +(?P<free_mem>[\d.]+) free, +(?P<used_mem>[\d.]+) used, +(?P<buff_cache_mem>[\d.]+) buff/cache', lines[4])
    if match:
        top_data.update(match.groupdict())
    
    # Parse the fifth line
    match = re.match(r'MiB Swap: +(?P<total_swap>[\d.]+) total, +(?P<free_swap>[\d.]+) free, +(?P<used_swap>[\d.]+) used. +(?P<avail_mem>[\d.]+) avail Mem', lines[5])
    if match:
        top_data.update(match.groupdict())

    # Convert numeric values to appropriate types
    for key in top_data:
        if key not in ['time']:
            if '.' in top_data[key]:
                top_data[key] = float(top_data[key])
            else:
                top_data[key] = int(top_data[key])

    # Convert top data to JSON
    convert_numeric_values(top_data)
    jsonized = json.dumps(top_data, indent=4)
    return jsonized

def parse_log_file(file_path):
    # Parse the entire log file
    with open(file_path, 'r') as file:
        jsonized = parse_header(file)

        content = file.read()
    
        # Split content into sections based on the delimiter
        tokenizer = re.compile(r'(^\*\*\*)', re.MULTILINE)
        tokens = tokenizer.split(content)
        
        for i in range(0, len(tokens), 2):
            section = tokens[i].strip()
            if not section:
                continue

            # Parse sysbench memory test section
            if 'Running sysbench memory test 1' in section:
                sysbench_json = parse_sysbench_memory_test(section)
                if sysbench_json:
                    jsonized_dict = json.loads(jsonized)
                    jsonized_dict["sysbench"] = json.loads(sysbench_json)
                    jsonized = json.dumps(jsonized_dict, indent=4)

            # Parse /proc/vmstat section
            elif 'cat /proc/vmstat 1' in section:
                vmstat_json = parse_vmstat(section)
                if vmstat_json:
                    jsonized_dict = json.loads(jsonized)
                    jsonized_dict["vmstat"] = json.loads(vmstat_json)
                    jsonized = json.dumps(jsonized_dict, indent=4)

            # Parse /proc/meminfo section
            elif 'cat /proc/meminfo 1' in section:
                meminfo_json = parse_meminfo(section)
                if meminfo_json:
                    jsonized_dict = json.loads(jsonized)
                    jsonized_dict["meminfo"] = json.loads(meminfo_json)
                    jsonized = json.dumps(jsonized_dict, indent=4)

            # Parse top command output section
            elif 'top -b -n 1|head -5 1' in section:
                top_json = parse_top(section)
                if top_json:
                    jsonized_dict = json.loads(jsonized)
                    jsonized_dict["top"] = json.loads(top_json)
                    jsonized = json.dumps(jsonized_dict, indent=4)

            else:
                pass

        return jsonized

if __name__ == "__main__":
    # Main function to parse log files provided as command-line arguments
    if len(sys.argv) < 2:
        print("Please provide at least one log file path.")
        sys.exit(1)

    logarray = '[]'

    for log_file_path in sys.argv[1:]:
        if not os.path.isfile(log_file_path):
            print(f"File not found: {log_file_path}")
            continue

        if not os.access(log_file_path, os.R_OK):
            print(f"File not readable: {log_file_path}")
            continue
            
        try:
            jsonized = parse_log_file(log_file_path)
            logarray_dict = json.loads(logarray)
            logarray_dict.append(json.loads(jsonized))
            logarray = json.dumps(logarray_dict, indent=4)
            print(f"Successfully parsed: {log_file_path}")
            
        except Exception as e:
            print(e)
            continue

    with open(output_file, 'w') as output:
        output.write(logarray)
        print(f"Output written to {output_file}")
