"""
script to count occurrence of early stopping due to parsing failures
signified by '[Early stop: Failed to parse actions for 3 times]'
"""
import os
import re
import argparse
import glob
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_examples", type=int, default=812)
    parser.add_argument("--result_dir", type=str, default="outputs")
    parser.add_argument("--search_str", type=str, default="Failed to parse actions for")
    parser.add_argument("--num_scan_lines", type=int, default=10)

    args = parser.parse_args()
    return args

def search_string_in_file(file_name, string_to_search, x):

    # Open the file in read only mode
    with open(file_name, 'r') as read_obj:
        # Read all lines in the file into a list
        lines = read_obj.readlines()

        for line in lines[-x:]:
            # Check if string is found
            if string_to_search in line:
                return True

    return False


if __name__ == "__main__":
    args = parse_args()
    num_files = 0
    num_match = 0
    for fname in glob.glob(f"{args.result_dir}/render_*.html"):
        print(f'searching file {fname}')
        num_files += 1
        num_match += search_string_in_file(fname, args.search_str, args.num_scan_lines)
    print(f'num_files: {num_files}, num_match: {num_match}, ratio: {num_match/num_files}')

