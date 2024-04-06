"""
Calls the YOSYS library to generate the netlist, figures, and associated information from the provided Verilog file.
https://yosyshq.net/yosys/

call_YOSYS() [see parameters below for customizing YOSYS output; note, changing parameters may cause problems]
"""

import subprocess
import os
import shutil
from core_algorithm.utils import log
import re


def call_YOSYS(in_path=None, out_path=None, v_name=None, ucf_name=None, choice=0, no_files=False):
    try:
        # Setting up the output directory
        new_out = os.path.join(out_path, v_name)

        # Remove the directory if it exists, then create it
        if os.path.exists(new_out):
            shutil.rmtree(new_out)
        os.makedirs(new_out)
    except Exception as e:
        log.cf.error(
            f"YOSYS output folder for {v_name} could not be re-initialized, please double-check. \n{e}")
        return False

    log.cf.info(f'new_out: {new_out}')  # Log the new out_path

    print('v_name: ', v_name)
    # Check if v_name has a directory component
    if '/' in v_name or '\\' in v_name:
        new_in = os.path.join(in_path, os.path.dirname(v_name))
        v_name = os.path.basename(v_name)
        log.cf.info(new_in)
    else:
        new_in = in_path

    # Construct the path to the Verilog file
    verilog = v_name
    if not verilog.endswith('.v'):
        verilog += '.v'
    v_loc = os.path.join(new_in, verilog)

    # Logging the information
    log.cf.info(f'verilog: {verilog}')
    log.cf.info(f'v_loc: {v_loc}')
    log.cf.info(f'new_in: {new_in}')
    log.cf.info(f'new_out: {new_out}')
    log.cf.info('\n')

    # Check for file existence
    if not os.path.isfile(v_loc):
        error_message = f"ERROR finding {verilog} in {v_loc}, please check verilog input."
        log.cf.error(error_message)
        raise Exception(error_message)

    command_start = [f"read_verilog {os.path.join(new_in, verilog)}"]

    # Commands depending on whether to create files or not
    if no_files:
        command_end = [
            f"show -format pdf -prefix {os.path.join(new_out, f'{v_name}_{ucf_name}_yosys')}"
        ]
    else:
        command_end = [
            f"show -format pdf -prefix {os.path.join(new_out, f'{v_name}_{ucf_name}_yosys')}",
            f"write_verilog -noexpr {os.path.join(new_out, f'{v_name}_{ucf_name}_yosys')}",
            f"write_edif {os.path.join(new_out, f'{v_name}_{ucf_name}_yosys.edif')}",
            f"write_json {os.path.join(new_out, f'{v_name}_{ucf_name}_yosys.json')}"
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
        error_message = f"Yosys output for {v_name} already exists, please double-check. \n{e}"
        log.cf.error(error_message)
        raise Exception(error_message)

    return True


def replace_techmap_diagram_labels(path: str, gate_labels: dict[str], in_labels: dict[str], out_labels: dict[str]):
    """
    Cleans up labels in YOSYS circuit diagram by using regex on the .dot file and regenerating the PDF via dot shell cmd
    :param v_name: str
    :param gate_labels: dict[str]
    :param in_labels: dict[str]
    :param out_labels: dict[str]
    """
    with open(f'{path}_yosys.dot', 'r') as dot_old:
        lines = dot_old.readlines()
        with open(f'{path}_yosys.dot', 'w') as dot_new:
            for line in lines:
                if old_label := re.search(r'(shape=record.*)(?<=\$)(.+)(?=\\n\$)', line):
                    new_label = gate_labels[old_label[2]]
                    line = re.sub(r'(\$.*\\n\$_)([A-Z]{3})_',
                                  f'${old_label[2]}\\\\n\\2\\\\n{new_label}', line)
                elif old_label := re.search(r'(shape=octagon.*)(?<=label=")([^"]+)(?=",)', line):
                    if old_label[2] in in_labels:
                        new_label = in_labels[old_label[2]]
                        line = re.sub(r'(?<=label=")(.*)(?=", )',
                                      f'{old_label[2]}\\\\nPRIMARY_INPUT\\\\n{new_label}', line)
                    elif old_label[2] in out_labels:
                        new_label = out_labels[old_label[2]]
                        line = re.sub(r'(?<=label=")(.*)(?=", )',
                                      f'{old_label[2]}\\\\nPRIMARY_OUTPUT\\\\n{new_label}', line)
                dot_new.write(line)

    os.system(f'dot -o{path}_tech-mapping.png -Tpng {path}_yosys.dot')
    os.remove(f'{path}_yosys.pdf')
    os.system(f'dot -o{path}_tech-mapping.pdf -Tpdf {path}_yosys.dot')
