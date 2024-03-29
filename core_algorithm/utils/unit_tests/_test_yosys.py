"""
Batch runs YOSYS to a folder to quickly compare results.
"""

import sys

sys.path.insert(0, '../../')  # Add parent directory to Python path
from logic_synthesis import *
import time
from log import *


# define path to folder containing verilogs
verilog_path = '../../../IO/inputs'
# define path to store YOSYS outputs for Restricted Graph & netlist
out_path = '../../../IO/temp_folder'


def find_verilogs(v_path):
    """
    Finds all Verilogs in the input folder.
    :param v_path:
    :return:
    """
    verilogs = []
    for root, dirs, files in os.walk(v_path):
        log.cf.info(root)
        log.cf.info(dirs)
        log.cf.info('\n')
        prefix = ''
        if root != v_path:
            prefix = root.split('/')[-1] + '/'
        for filename in files:
            if filename.endswith('.v'):
                verilog = filename.split('.')[0]
                verilog_loc = prefix + verilog
                verilogs.append(verilog_loc)
                # verilogs.append(prefix+file)
    return verilogs


verilogs_to_test = find_verilogs(verilog_path)
log.cf.info(verilogs_to_test)

failed_verilogs = []
for verilog in verilogs_to_test:
    try:
        yosys_ok = call_YOSYS(verilog_path, out_path, verilog, 1)
        if not yosys_ok:
            failed_verilogs.append(str(verilog))
    except Exception as e:
        log.cf.error('ERROR:\n' + str(e))
        failed_verilogs += [verilog]
        time.sleep(2)
log.cf.info('NUMBER OF ERRORS: ' + str(len(failed_verilogs)))
log.cf.info('FAILED Verilogs: ' + str(failed_verilogs))
