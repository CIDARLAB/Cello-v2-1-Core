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

    print("\nStarting ucf-collection_to_csv.py program...\n")

    # Validates Arguments
    def validate_file_paths(args: str) -> list[list[Path, Path | None]]:
        """
        Validates the file paths and extensions, generating a list of [input file, <optionally: output file>] lists.
        """
        file_paths = []
        for i, arg in enumerate(args):
            arg_paths = arg.split('>')
            try:
                file_paths.append([input_file := Path(arg_paths[0])])
                assert input_file.is_file()          # check that input file exists
                assert input_file.suffix == '.json'  # check that input file type is '.json'
                if len(arg_paths) == 2:  # if output_file specified...
                    file_paths[i].extend([output_file := Path(arg_paths[1])])
                    assert output_file.parent.is_dir()   # check that output file directory exists
                    assert output_file.suffix == '.csv'  # check that output file type is '.csv'
                else:
                    file_paths[i].extend([Path(input_file).with_suffix('.csv')])
            except AssertionError:
                print(f"\nProblem with file specification: {arg}\n"
                      f"Confirm file(s) exist. Inputs must be '.json' and outputs must be '.csv'.")
                # raise
                sys.exit(1)

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
    parser.add_argument('paths', type=str, nargs='+', help="Space-separated list of input files. "
                        "To specify output path/name for a file, follow that file by '>' and then the filepath.")
    args = parser.parse_args()
    file_paths = validate_file_paths(args.paths)

    # Process Files
    for pair_of_filepaths in file_paths:
        ucf_file = pair_of_filepaths[0]
        csv_file = pair_of_filepaths[1]

        # Read from UCF .json
        with open(ucf_file, 'r') as file:
            json_data = json.load(file)

        # Write to .csv
        with open(csv_file, 'w', newline='') as file:
            csv_writer = csv.writer(file)
            # TODO: Reason for rename?
            csv_writer.writerow(['name', 'type', 'dnasequence'])  # name -> id, type -> role, dnasequence -> sequence
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
    print("\nProgram completed execution\n")


if __name__ == '__main__':
    main()
