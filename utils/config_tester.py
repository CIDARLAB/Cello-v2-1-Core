"""
This utility will run through every combination of configuration files currently
available in the sample_inputs folder (matching every .v to every .ucf/input/out),
completing the first 1000 iterations, logging the outputs, and producing a CSV of
the results. Intended for testing the validity of all configurations.
"""

from os import listdir
from os.path import isfile, join
from celloAlgo import CELLO3
from logger import *
import csv


def test_all_configs(ucflist: list):

    start_test = input(
        '\nThis utility tests validity of all combos of verilog & UCFs in samples_input folder (not subdirectories)...'
        'Each valid config will only run for the first 1000 iterations to check for errors.'
        'Each config produces a log file of the terminal output, and a csv summarizing all results is generated.'
        'Do you want to proceed? y/n ')

    if start_test == 'y' or start_test == 'Y':

        # SCAN FILES
        v_names = []
        ucf_names = []
        for f in listdir('sample_inputs/'):
            if isfile(join('sample_inputs/', f)):
                if f.endswith('.v'):
                    v_names.append(f.split('.')[0])
                elif f.endswith('.UCF.json'):
                    ucf_names.append(f.split('.')[0])
        out.info("Total number of configurations to be test: ", len(v_names) * len(ucf_names))

        # RUN ALL COMBOS, GENERATE LOGS AND THE CSV
        with open('logs/test-all-configs_' + datetime.now().strftime("%Y-%m-%d_%H%M%S") + '.csv',
                  'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            for i, v_name in enumerate(v_names):
                new_row = []
                for j, ucf_name in enumerate(ucf_names):  # TODO: Change to scan for UCFs?
                # for ucf_name in ucflist:  # Do *NOT* enable verbose
                    cello_config_test = CELLO3(v_name, ucf_name, 'sample_inputs/', 'test_all_configs_out/',
                                               options={'yosys_choice': 1, 'verbose': False, 'test_configs': True})
                    if cello_config_test.best_score:
                        status = "Completed: "
                    else:
                        status = "Incomplete: "
                    new_row.append(status + str(cello_config_test.best_score))
                    del cello_config_test
                csv_writer.writerow(new_row)  # TODO: Check for warnings to better summarize overall status
    else:
        out.info('Exiting...')

    return
