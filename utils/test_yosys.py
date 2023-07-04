import sys
sys.path.insert(0, '../')  # Add parent directory to Python path
from logic_synthesis import *
import time
from logger import *


# NOTE: This script batch runs YOSYS to a folder you desire to quickly compare results 

# define path to folder containing verilogs
verilog_path = '../../../IO/inputs'
# define path to store YOSYS outputs for Restricted Graph & netlist
out_path = '../../../IO/temp_folder'

# find all verilogs in input folder
def find_verilogs(v_path):
    verilogs = []
    for root, dirs, files in os.walk(v_path):
        print(root)
        print(dirs)
        print()
        prefix = ''
        if root != v_path:
            prefix = root.split('/')[-1] + '/'
        for filename in files:
            if filename.endswith('.v'):
                vrlg = filename.split('.')[0]
                vloc = prefix + vrlg
                verilogs.append(vloc)
                # verilogs.append(prefix+file)
    return verilogs

verilogs_to_test = find_verilogs(verilog_path)
print(verilogs_to_test)

failed_verilogs = []
for verilog in verilogs_to_test:
    try:
        yosys_ok = call_YOSYS(verilog_path, out_path, verilog, 1)
        if yosys_ok == False:
            failed_verilogs.append(str(verilog))
    except Exception as e:
        print('ERROR:\n' + str(e))
        failed_verilogs += [verilog]
        time.sleep(2)
print('NUMBER OF ERRORS: ' + str(len(failed_verilogs)))
print('FAILED Verilogs: ' + str(failed_verilogs))