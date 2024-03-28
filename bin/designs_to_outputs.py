#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to take in a CSV with pre-generated design options (i.e. part orders), rather than a Verilog file, and
score each design option, returning the normal results/outputs that Cello generates.
TODO: For only the best design option?
TODO: Only on command line ok?
TODO: What outputs need to be generated?  Just score?
TODO: It still needs on vs. off designations, or can it just run every such combination?

@author: chris-krenz

"""

import json
import csv
import argparse
from pathlib import Path
import os
import sys
from textwrap import dedent

from core_algorithm.celloAlgo import cello_initializer
from config import LIBRARY_DIR, VERILOGS_DIR, CONSTRAINTS_DIR, TEMP_OUTPUTS_DIR
from core_algorithm.utils import log
from core_algorithm.utils.config_tester import test_all_configs
from core_algorithm.utils.cello_helpers import *
from core_algorithm.utils.gate_assignment import *
from core_algorithm.celloAlgo import *


def main():
    in_path_ = LIBRARY_DIR
    ucf_path = CONSTRAINTS_DIR
    out_path_ = TEMP_OUTPUTS_DIR
    ucf_name_ = ''
    in_name_ = ''
    out_name_ = ''
    designs_given = True
    verbose = False
    print_iters = False

    print(csv_filepath := input(
        f'\n\nFor which CSV file of pre-generated design options do you want Cello output generated?\n'
        f'(Hint: See the design_options_template.csv file in the bin folder as an example...)\n\n'
        f'Design Options CSV Filepath: '))

    ucf_list = ['Bth1C1G1T1', 'Eco1C1G1T1', 'Eco1C2G2T2', 'Eco2C1G3T1', 'Eco2C1G5T1', 'Eco2C1G6T1', 'SC1C1G1T1']
    log.cf.info(name := input(
        f'\n\nIf you want to use a built-in UCF (User Constrain File) and associated Input & Output files, '
        f'which of the following do you want to use? \n'
        f'Options: {list(zip(range(len(ucf_list)), ucf_list))} \n\n'
        f'Alternatively, just hit Enter if you want to specify your own UCF, Input, and Output files...\n\n'
        f'Index of built-in UCF (or leave blank for custom): '))
    if name:
        try:
            ucf_name_ = ucf_list[int(name)] + '.UCF'
            in_name_ = ucf_list[int(name)] + '.input'
            out_name_ = ucf_list[int(name)] + '.output'
        except Exception as e:
            log.cf.info(
                'Cello was unable to identify the UCF you specified...')
            log.cf.info(e)
    else:
        os.system('')
        label = "\u001b[4m" + '   .UCF' + "\u001b[0m"
        log.cf.info(ucf_name_ := input(
            f'\n\nPlease specify the name of the UCF file you want to use...\n'
            f'(Hint: {label}.json, with the .UCF but not the .json, from the'
            f' {ucf_path[:-1]} folder.)\n\n'
            f'UCF File Name: '))
        label = "\u001b[4m" + '   .input' + "\u001b[0m"
        log.cf.info(in_name_ := input(
            f'\n\nPlease specify the name of the Input file you want to use...\n'
            f'(Hint: {label}.json, with the .input but not the .json, from the {ucf_path[:-1]} folder.)\n\n'
            f'Input File Name: '))
        label = "\u001b[4m" + '   .output' + "\u001b[0m"
        log.cf.info(out_name_ := input(
            f'\n\nPlease specify the name of the Output file you want to use...\n'
            f'(Hint: {label}.json, with the .output but not the .json, from the {ucf_path[:-1]} folder.)\n\n'
            f'Output File Name: '))

    # result = cello_initializer('No Verilog', ucf_name_, in_name_, out_name_, 'No Verilog Path', ucf_path, out_path_,
    #                            options={'designs_given': True, 'verbose': False, 'print_iters': False})

    with open(csv_filepath, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        # TODO: Easier to construct netgraph and pass to prep_assign_for_scoring or to adjust how score_circuit works?
        # TODO: Can just trace outputs in UCF to reconstruct the graph...

        for design_option in csv_reader:

            print('test')

            # score_circuit()

    print('\nExisting script...\n')


if __name__ == '__main__':
    main()
