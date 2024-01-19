"""
Tests all possible combinations of Verilogs and UCFs in the inputs folder. By default does 1000 dual_annealing
iterations per config.  Also produces a csv that summarizes the results.
TEAM: Note this is still being fixed up since merge & not fully working!\n\n'  # TODO: Remove line
"""

from os import listdir
from os.path import isfile, join
from core_algorithm.celloAlgo import CELLO3
from datetime import datetime
from core_algorithm.utils import log
import csv


def test_all_configs(input_folder: str):
    """
    This utility will run through every combination of configuration files currently
    available in the inputs folder (matching every .v to every .ucf/input/out),
    completing the first 100 iterations, logging the outputs, and producing a CSV of
    the results. Intended for testing the validity of all configurations.
    """

    # SCAN FILES
    v_names = []
    ucf_names = []
    for f in listdir(f'{input_folder}'):
        if isfile(join(f'{input_folder}', f)):
            if f.endswith('.v'):
                v_names.append(f.split('.')[0])
            elif f.endswith('.UCF.json'):
                ucf_names.append(f.split('.')[0])

    start_test = input(
        f'\n\nThis utility tests the validity of all combos of verilogs & UCFs in "{input_folder}" (not subfolders).\n'
        f'By default, each valid config will only run for the first 1000 iterations to check for errors.\n'
        f'(Note: log overwrite is turned on by default.)\n'
        f'Each config produces a log file of the terminal output, and a csv summarizing all results is generated.\n\n'
        f'Total number of configurations to be tested: ' +
        str(len(v_names) * len(ucf_names)) + '\n'
        f'(Depending on the number of valid configs, this may take awhile to complete...)\n'
        f'\nDo you want to proceed? (y/n) ')

    if start_test == 'y' or start_test == 'Y':

        # RUN ALL COMBOS, GENERATE LOGS AND THE CSV
        with open('logs/test-all-configs_' + datetime.now().strftime("%Y-%m-%d_%H%M%S") + '.csv',
                  'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            headings = [' ']
            for ucf_name in ucf_names:
                headings.append(ucf_name)
            csv_writer.writerow(headings)
            for i, v_name in enumerate(v_names):
                new_row = [v_name]
                for j, ucf_name in enumerate(ucf_names):
                    # NOTE: Do *not* enable verbose
                    best = 0
                    try:
                        cello_config_test = CELLO3(v_name, ucf_name, f'{input_folder}', 'test_all_configs_out/',
                                                   options={'yosys_cmd_choice': 1,
                                                            'verbose': False,
                                                            'log_overwrite': True,
                                                            'print_iters': False,
                                                            'exhaustive': False,
                                                            'test_configs': True})
                        exception = "Done"
                    except Exception as e:
                        log.cf.info(
                            "FAILED with error (will go to next iteration)!")
                        log.cf.critical(e)
                        exception = "Failed"
                    w, e, c = log.log_counts['WARNING'], log.log_counts['ERROR'], log.log_counts['CRITICAL']
                    if 'cello_config_test' in locals():
                        best = round(cello_config_test.best_score, 1)
                    new_row.append(f'{exception}\n'
                                   f'{log.iter_validity}\n'
                                   f'{best}\n'
                                   f'Warn: {w}\n'
                                   f'Err: {e}\n'
                                   f'Crit: {c}\n'
                                   f'Last log...\n{log.last_log}')
                    # TODO: Capture YOSYS output and track issues...
                csv_writer.writerow(new_row)

    else:
        print('Exiting...')

    return
