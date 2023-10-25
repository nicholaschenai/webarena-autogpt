"""
extracts results from logfile and saves them elsewhere. also spot errors
so i know which to rerun
"""

import re
import pandas as pd
import os
import argparse
import numpy as np

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_examples", type=int, default=812)
    parser.add_argument("--LOG_FILE_PATH", type=str, default="")
    parser.add_argument("--result_dir", type=str, default="outputs")
    parser.add_argument("--result_fname", type=str, default="logged_results")
    parser.add_argument("--delete_error_files", action="store_true")
    parser.add_argument("--extract_from_logs", action="store_true")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    # check if df exists, else create
    RESULT_FILE_PATH = args.result_dir + f'/{args.result_fname}.csv'
    if os.path.exists(RESULT_FILE_PATH):
        print('results file exists, resuming from there')
        df = pd.read_csv(RESULT_FILE_PATH, index_col=0)
        df = df.astype(float)
    else:
        print('create new results file')
        df = pd.DataFrame(index=range(args.num_examples), columns=['score'])

    if args.extract_from_logs:
        with open(args.LOG_FILE_PATH, 'r') as file:
            for line in file:
                match = re.search(r'\[Result\]\s\((\w+)\)\sconfig_files/(\d+).json', line)
                if match:
                    result = match.group(1)
                    idx = match.group(2)
                    assert(result in ['PASS', 'FAIL'])
                    df.score[int(idx)] = float(result == 'PASS')

    print(f'df stats: len: {len(df.index)} avg: {df.score.mean()} number of nan: {df.score.isnull().sum()}')

    # save df
    if not os.path.exists(args.result_dir):
        os.makedirs(args.result_dir)
    df.to_csv(RESULT_FILE_PATH)

    # remove error files. render_{idx}.html
    if args.delete_error_files:
        for nullIdx in df[df.score.isnull()].index:
            RENDER_FILE_PATH = args.result_dir + f'/render_{nullIdx}.html'
            if os.path.exists(RENDER_FILE_PATH):
                print('removing error file ' + RENDER_FILE_PATH)
                os.remove(RENDER_FILE_PATH)