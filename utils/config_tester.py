"""
Tests all possible combinations of Verilogs and UCFs in the sample_inputs folder. By default does 1000 dual_annealing
iterations per config.  Also produces a csv that summarizes the results.
TEAM: Note this is still being fixed up since merge & not fully working!\n\n'  # TODO: Remove line
"""

from os import listdir
from os.path import isfile, join
from celloAlgo import CELLO3
from datetime import datetime
import log
import csv


# TODO: implement more robust exception handling
def test_all_configs():
    """
    This utility will run through every combination of configuration files currently
    available in the sample_inputs folder (matching every .v to every .ucf/input/out),
    completing the first 100 iterations, logging the outputs, and producing a CSV of
    the results. Intended for testing the validity of all configurations.
    """

    # SCAN FILES
    v_names = []
    ucf_names = []
    for f in listdir('sample_inputs/'):
        if isfile(join('sample_inputs/', f)):
            if f.endswith('.v'):
                v_names.append(f.split('.')[0])
            elif f.endswith('.UCF.json'):
                ucf_names.append(f.split('.')[0])

    start_test = input(
        '\n\nThis utility tests the validity of all combos of verilogs & UCFs in "sample_inputs" (not subdirectories).\n'
        'By default, each valid config will only run for the first 1000 iterations to check for errors.\n'
        '(Note: log overwrite is turned on by default.)\n'
        'Each config produces a log file of the terminal output, and a csv summarizing all results is generated.\n\n'
        'Total number of configurations to be tested: ' + str(len(v_names) * len(ucf_names)) + '\n'
        '(Depending on the number of valid configs, this may take awhile to complete...)\n'
        '\nDo you want to proceed? (y/n) ')

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
                        cello_config_test = CELLO3(v_name, ucf_name, 'sample_inputs/', 'test_all_configs_out/',
                                            options={'yosys_cmd_choice': 1, 'verbose': False,    'log_overwrite': True,
                                                     'print_iters': False,  'exhaustive': False, 'test_configs': True})
                        exception = "Done"
                    except Exception as e:
                        log.cf.info("FAILED with error (will go to next iteration)!")
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
