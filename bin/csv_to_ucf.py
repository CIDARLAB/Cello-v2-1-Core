#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command line script to take in a CSV and translate it into a UCF.  This only works for some of the UCF collections;
other collections will need to be filled in manually...

@author: chris-krenz

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

    """

    print("\nStarting csv_to_ucf.py program...\n")

    # Parse Arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''This program 'translates' CSV files into a User Constraint Files (UCFs).''',
        epilog=dedent('''

        ''')
    )
    parser.add_argument('paths', type=str, nargs='+')  # CSV file...
    arg = parser.parse_args().paths[0]

    """
    block-transition keys...
        root: "collection"
        variables: "name"
        parameters: "name"
        locations: "symbol"
    
    lists: author, plasmid_sequence, available_gates, outputs, inputs, netlist, parameters, components, variables, 
           output, bin, locations, sequences, data
    ambiguous: x, table, rules
    """
    ucf_dict = {}

    with open(arg, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)

        curr_sec = 'root'
        for row in csv_reader:
            key = row[0]
            for cell in row:
                if cell == 'collection':
                    curr_sec = 'collection'
                    new_collection = {'collection': None}



    with open(Path(arg).with_suffix('.json'), 'w') as ucf_file:
        ucf_file.write(json.dumps(ucf_dict))

    # Process Files
    # for pair_of_filepaths in file_paths:
    #     ucf_file = pair_of_filepaths[0]
    #     csv_file = pair_of_filepaths[1]
    #
    #     # Read from UCF .json
    #     with open(ucf_file, 'r') as file:
    #         json_data = json.load(file)
    #
    #     # Write to .csv
    #     with open(csv_file, 'w', newline='') as file:
    #         csv_writer = csv.writer(file)
    #         # TODO: Reason for rename?
    #         csv_writer.writerow(['name', 'type', 'dnasequence'])  # name -> id, type -> role, dnasequence -> sequence
    #         for block in json_data:
    #             if block['collection'] == 'parts':
    #                 try:
    #                     row = [block['name'], block['type'], block['dnasequence']]
    #                     csv_writer.writerow(row)
    #                 except KeyError as err_msg:
    #                     print(f"\nError with .json structure. "
    #                           f"Check if 'parts' collections match specification in help file. \n{err_msg}\n")
    #                     # raise
    #                     sys.exit(1)
    #
    #     # Confirm file generated
    #     if os.path.isfile(csv_file):
    #         print(f"Generated {csv_file} (from {ucf_file})...")
    #     else:
    #         print(f"\nError generating {csv_file} from {ucf_file} (unknown reason); see help documentation...\n")
    #
    # # Exit
    # print("\nProgram completed execution\n")


if __name__ == '__main__':
    main()
