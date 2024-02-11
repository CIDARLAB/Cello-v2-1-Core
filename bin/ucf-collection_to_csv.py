#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command line script to take in a UCF .json file and generate a .csv containing the UCF 'parts' info.

@author: chris-krenz
TODO: Allow to convert multiple UCF collection types
"""

import json
import csv
import argparse
from pathlib import Path
import os
import sys
from textwrap import dedent


def main():
    """
    Command line func that 'translates' UCF .json 'parts' to .csv with labeled columns: id, role, sequence..
    Assumes UCF .json file has the following format for the parts collections...
    {
        "collection": "parts",
        "type": "terminator",
        "name": "L3S3P41",
        "dnasequence": "GGATCCAAAAAAAAAAAACACCCTAACGGGTGTTTTTTTTTTTTTGGTCTGCCgcggccgc"
    }
    """

    print("\nStarting ucf-collection_to_csv.py program...")

    # Validate Arguments
    def validate_file_arg(arg: str) -> dict[Path, Path | None]:
        file_paths = {}
        arg_paths = arg.split(':')
        try:
            file_paths[(input_file := Path(arg_paths[0]))] = None
            print(file_paths)
            assert input_file.is_file()               # check that input file exists
            assert input_file.suffix == '.json'  # check that input file type is '.json'
            if len(arg_paths) == 2:
                file_paths[input_file] = (output_file := Path(arg_paths[1]))  # if output_file specified...
                assert output_file.parent.is_dir()        # check that output file directory exists
                assert output_file.with_suffix == '.csv'  # check that output file type is '.csv'
        except AssertionError as err_msg:
            print(f"\nProblem with file specification: {arg}\n"
                  f"Confirm file(s) exist. Inputs must be '.json' and outputs must be '.csv'.")
            # raise
            sys.exit(1)
        print(file_paths)
        return file_paths

    # Parse Arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''This program 'translates' UCF .json 'parts' to .csv with labeled columns: id, role, sequence.''',
        epilog=dedent('''
            Assumes UCF .json file has following format for 'parts' collections:
                {
                    "collection": "parts",
                    "type": "terminator",
                    "name": "L3S3P41",
                    "dnasequence": "GGATCCAAAAAAAAAAAACACCCTAACGGGTGTTTTTTTTTTTTTGGTCTGCCgcggccgc"
                }
                
            Run with:
                > python ucf-collection_to_csv.py <ucf>.json [<target-csv-file-name>.csv]
            
            Other notes:
                - Second argument (output file path) is relative to the folder containing the script.
                - Any non-.csv extension is converted to .csv.
                - If no output file is specified, a .csv of the same name and directory as the UCF will be generated. 
                - Note, unless a unique output file name is specified, an existing .csv file will be overwritten.
        ''')
    )
    # parser.add_argument('--related', action='store_true', help='')  # TODO: setup to automatically run .input & .output
    parser.add_argument('paths', type=validate_file_arg, nargs='+',
                        help="Space-separated list of input files. "
                             "To specify output path/name for a file, follow that file by ':' and then the filepath.")
    # parser.add_argument('out_file', nargs='?', type=argparse.FileType('w'))  # TODO: replace with colon per file...
    args = parser.parse_args()
    print(args)
    file_paths = args.paths
    # for arg in args.paths:
    #     file_paths[arg.split(':')[0]] = file_paths[arg.split(':')[1]] if ':' in arg else None

    # Process Files
    for ucf_file, csv_file in file_paths.items():
        # Read from UCF .json
        with open(list(ucf_file.keys())[0], 'r') as file:
            json_data = json.load(file)

        # Write to .csv
        with open(csv_file, 'w', newline='') as file:
            csv_writer = csv.writer(file)
            # TODO: Reason for rename?
            csv_writer.writerow(['id', 'role', 'sequence'])  # name -> id, type -> role, dnasequence -> sequence
            for block in json_data:
                if block['collection'] == 'parts':
                    try:
                        row = [block['name'], block['type'], block['dnasequence']]
                        csv_writer.writerow(row)
                    except KeyError as err_msg:
                        print(f"\nError with .json structure. "
                              f"Check if 'parts' collections match specification in help file. \n{err_msg}\n")
                        # raise
                        sys.exit(1)

        # Confirm file generated
        if os.path.isfile(csv_file):
            print(f"Generated {csv_file} (from {ucf_file})...")
        else:
            print(f"\nError generating {csv_file} from {ucf_file} (unknown reason); see help documentation...\n")

    # Exit
    print("\n\nProgram completed execution...")


if __name__ == '__main__':
    main()
