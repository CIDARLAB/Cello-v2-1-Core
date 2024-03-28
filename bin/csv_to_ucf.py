#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command line script to take in a .csv and translate it into a .json UCF collections.

Run with:
> python csv_to_ucf.py

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
    Takes user input as filepath to a .csv, runs the conversion, and generates a .json UCF file. The .json file will have
    the same name as and be in the same folder as the .csv file.


        Just for reference...

        block-transition keys...
            root: "collection"
            variables: "name"
            parameters: "name"
            locations: "symbol"

        lists: author, plasmid_sequence, available_gates, outputs, inputs, netlist, parameters, components, variables, 
               output, bin, locations, sequences, data
        ambiguous: x, table, rules
    """

    print("\nStarting csv_to_ucf.py program...")

    # For now replaced with interactive script...
    # Parse Arguments
    # parser = argparse.ArgumentParser(
    #     formatter_class=argparse.RawDescriptionHelpFormatter,
    #     description='''This program 'translates' CSV files into a User Constraint Files (UCFs).''',
    #     epilog=dedent('''
    #
    #     ''')
    # )
    # parser.add_argument('paths', type=str, nargs='+')  # CSV file...
    # arg = parser.parse_args().paths[0]

    print(csv_filepath := input(
        f'\nWhat .csv file do you want to convert to collections in a .json UCF?\n'
        f'(Note: Use the csv_template.csv file in the bin/examples/ folder as a template...)\n'
        f'.csv filepath: '))

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

    ucf_list = []  # outermost list of collections

    with open(csv_filepath, 'r', encoding='utf-8-sig') as csv_file:
        # Read from the .csv file and prep data
        csv_reader = csv.reader(csv_file)
        data = []
        for row in csv_reader:
            data.append([cell for cell in row])

        # Iterate over all rows/cells to convert to python dicts
        headers = []
        for row in data:
            if row[0] == 'collection':  # changes headers to handle concatenation of multiple types of collections
                headers = row
            else:
                collection = {}
                list_item = 0
                for index, cell in enumerate(row):
                    if index < len(headers) and (header := headers[index]):  # if header exists, add cell to dict
                        last_entry = False
                        if header.startswith(';'):
                            list_item += 1
                            add_entry = True
                            header = header[1:]
                        if header.endswith(';'):
                            last_entry = True
                            header = header[:-1]
                        if cell:
                            if ';' in cell:
                                temp = []
                                for val in cell.split(';'):
                                    if val:
                                        temp.append(val)
                                cell = temp
                            if ':' in header:
                                keys = header.split(':')
                                if keys[0] not in collection:
                                    if list_item:
                                        collection[keys[0]] = []
                                    else:
                                        collection[keys[0]] = {}
                                if add_entry:
                                    collection[keys[0]].append({})
                                if list_item:
                                    cell = convert_val_type(cell, keys[1])
                                    collection[keys[0]][list_item-1][keys[1]] = cell
                                else:
                                    cell = convert_val_type(cell, keys[1])
                                    collection[keys[0]][keys[1]] = cell
                            else:
                                cell = convert_val_type(cell, header)
                                collection[header] = cell
                        add_entry = False
                        if last_entry:
                            list_item = 0
                            last_entry = False
                ucf_list.append(collection)

    with open(Path(csv_filepath).with_suffix('.json'), 'w') as ucf_file:
        # Write to the .json file
        json.dump(ucf_list, ucf_file, indent=4)

    print('Ending script...\n')


if __name__ == '__main__':
    main()
