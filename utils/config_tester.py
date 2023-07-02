"""
This utility will run through every combination of configuration files currently
available in the sample_inputs folder (matching every .v to every .ucf/input/out),
completing the first X iterations, logging the outputs, and producing a CSV of
the results.

To Do:
 - Trigger (flag near verbose)
 - Read folders to generate arrays of all file names
 - Loop through all combinations, starting the program
 - Auto stop the program after 1000 (small num) of iterations
 - Capture the terminal output (and files?) from the program and dump into a log
 - Automatically go on to the next combination and finish all iterations
 - Generate a CSV of the results (by reading the log files)
 TODO: Debug verbosity

"""

from os import listdir
from os.path import isfile, join


def testAllConfigs():

    vnames = ucfnames = []

    for f in listdir('sample_inputs/'):
        if isfile(join('sample_inputs/', f)):
            if f.endswith('.v'):
                vnames.append(f.split('.')[0])
            elif f.endswith('.UCF.json'):
                ucfnames.append(f.split('.')[0])

    print("Total number of configurations to be test: ", vnames.len() * ucfnames.len())

    return vnames, ucfnames
