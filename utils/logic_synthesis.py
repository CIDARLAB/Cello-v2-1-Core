"""
Calls the YOSYS library to generate the netlist, figures, and associated information from the provided Verilog file.
https://yosyshq.net/yosys/

call_YOSYS() [see parameters below for customizing YOSYS output; note, changing parameters may cause problems]
"""

# Python default libraries
import subprocess
import os
import shutil
import sys


def call_YOSYS(in_path=None, out_path=None, v_name=None, choice=0):
    """

    :param in_path: 
    :param out_path: 
    :param v_name: 
    :param choice: 
    :return: 
    """
    try:
        new_out = os.path.join(out_path, v_name)
        new_out = os.path.join(*new_out.split('/'))
        if os.path.exists(new_out):
            shutil.rmtree(new_out)  # this could be switched out for making a new dir path instead
        os.makedirs(new_out)
    except Exception as e:
        print(f"YOSYS output folder for {v_name} could not be re-initialized, please double-check. \n{e}")
        return False
    print(new_out)  # new out_path
    if '/' in v_name:
        new_in = os.path.join(in_path, '/'.join(v_name.split('/')[:-1]))
        v_name = v_name.split('/')[-1]
        print(new_in)
    else:
        new_in = in_path
        new_in = os.path.join(*new_in.split('/'))
    verilog = v_name + '.v'
    v_loc = os.path.join(new_in, verilog)

    print(verilog)
    print(v_loc)
    print(new_in)
    print(new_out)
    print()

    if not os.path.isfile(v_loc):
        print(f"ERROR finding {verilog}, please check verilog input.")
        return False

    slash = '/'
    if sys.platform.startswith('win'):
        slash = '\\'

    command_start = ["read_verilog {}{}{};".format(new_in, slash, verilog)]
    command_end = [
        "show -format pdf -prefix {}{}{}_yosys".format(new_out, slash, v_name),
        "write_verilog -noexpr {}{}{}".format(new_out, slash, 'struct_' + v_name),
        "write_edif {}{}{}.edif;".format(new_out, slash, v_name),
        "write_json {}{}{}.json;".format(new_out, slash, v_name),
    ]
    core_commands = [
        [
            # Old Cello Yosys commands
            "flatten",
            "splitnets -ports",
            "hierarchy -auto-top",
            "proc",
            "techmap",
            "opt",
            "abc -g NOR",
            "opt",
            "hierarchy -auto-top",
            "opt_clean -purge",
        ],
        [
            # JAI's MD5 Yosys commands
            'splitnets',
            'hierarchy -auto-top',
            'flatten',
            'proc',
            'opt -full',
            'memory',
            'opt -full',
            'fsm',
            'opt -full',
            'techmap',
            'opt -full',
            'abc -g NOR',
            'splitnets -ports',
            'opt -full',
            'opt_clean',
            'clean -purge',
            'flatten'
        ],
        [
            # general application Yosys commands
            'splitnets',
            'hierarchy -auto-top',
            'proc',
            'opt',
            'fsm',
            'opt',
            'memory',
            'opt',
            'techmap',
            'opt',
            'abc -g NOR',
            'opt',
            'clean',
        ]
    ]

    try:
        commands = command_start + core_commands[choice] + command_end
        command = f"yosys -p \"{'; '.join(commands)}\""
        subprocess.call(command, shell=True)
    except Exception as e:
        print(f"Yosys output for {v_name} already exists, pleas double-check. \n{e}")
        return False

    return True
