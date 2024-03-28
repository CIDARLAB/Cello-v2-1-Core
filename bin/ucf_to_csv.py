#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command line script to take in a .json UCF and translate it into a .csv file.

Run with:
> python ucf_to_csv.py

@author: chris-krenz

"""

# import os
# import sys
import csv
import json
# import argparse
from pathlib import Path
# from textwrap import dedent


def parse_header(header: str):
    pass


def main():
    """
    Takes user input as filepath to a .json UCF, runs the conversion, and generates a .csv file. The .csv file will have
    the same name as and be in the same folder as the .json UCF.
    """
    # TODO: This is the 'compact' form of csv; also generate a 'long' form that is indented like a .json
    # TODO: Test bidirectional conversion of all UCFs (and then test UCFs)
    print("\nStarting ucf_to_csv.py program...")

    print(json_filepath := input(
        f'\nWhat .json UCF do you want to convert to a .csv?\n'
        f'.json filepath: '))

    def convert_val_type(value: str, key=''):
        """
        If dict value, optionally include key to help identify appropriate value type.
        """
        # Check if boolean
        if value == 'true' or value == 'false':
            return bool(value)
        # Check if float
        elif key == 'value':
            return float(value)
        # Check if int
        elif type(value) == str and value.isnumeric() and key != 'color':
            return int(value)
        else:
            return value

    csv_rows = []

    # Read from UCF .json
    with open(json_filepath, 'r') as file:
        json_data = json.load(file)

        # Iterate over all collections to convert to .csv rows
        headers = []
        for collection in json_data:
            # TODO: Only generate headers for first instance of a (grouping of a) collection type
            # TODO: Also populate the values (1 row per each actual collection)
            # create the .csv header row for the collection
            if collection['collection'] != 'motif_library':
                for k, v in collection.items():
                    if type(v) == str:
                        header_group = [k]
                    elif type(v) == dict:
                        header_group = []
                        for key in v.keys():
                            header_group.append(k + ':' + key)
                    elif type(v) == list:
                        if any(True for item in v if type(item) == str):
                            header_group = [k]
                        # if all list items are dicts (should not have a list of lists) TODO: add test
                        elif all(True for item in v if type(item) == dict):
                            header_group = []
                            for i, item in enumerate(v):
                                header_dicts = []
                                for key, value in item.items():
                                    header_dicts.append(k + ':' + key)
                                temp = header_dicts[0]
                                header_dicts[0] = ';' + temp
                                header_group.extend(header_dicts)
                            header_group[-1] += ';'
                    headers.extend(header_group)

            # populate the .csv rows
            # for k, v in collection.items():
            #     pass

    # Write to .csv
    with open(Path(json_filepath).with_suffix('.csv'), 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(headers)

    print('Ending script...\n')


if __name__ == '__main__':
    main()
