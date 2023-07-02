"""
This utility will run through every combination of configuration files currently
available in the sample_inputs folder (matching every .v to every .ucf/input/out),
completing the first X iterations, logging the outputs, and producing a CSV of
the results.

To Do:
 - Trigger (flag near verbose)
 - Read folders to generate arrays of all file names
 - Loop through all combinations, starting the program
 - Auto stop the program after x (small num) of iterations
 - Capture the terminal output (and files?) from the program and dump into a log
 - Automatically go on to the next combination and finish all iterations
 - Generate a CSV of the results (by reading the log files)

"""

def testAllConfigs():

