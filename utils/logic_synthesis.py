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
import log
import re


def call_YOSYS(in_path=None, out_path=None, v_name=None, choice=0, no_files=False):
    try:
        new_out = os.path.join(out_path, v_name)
        new_out = os.path.join(*new_out.split('/'))
        if os.path.exists(new_out):
            shutil.rmtree(new_out)  # this could be switched out for making a new dir path instead
        os.makedirs(new_out)
    except Exception as e:
        log.cf.error(f"YOSYS output folder for {v_name} could not be re-initialized, please double-check. \n{e}")
        return False
    log.cf.info(new_out)  # new out_path
    if '/' in v_name:
        new_in = os.path.join(in_path, '/'.join(v_name.split('/')[:-1]))
        v_name = v_name.split('/')[-1]
        log.cf.info(new_in)
    else:
        new_in = in_path
        new_in = os.path.join(*new_in.split('/'))
    verilog = v_name + '.v'
    v_loc = os.path.join(new_in, verilog)

    log.cf.info(verilog)
    log.cf.info(v_loc)
    log.cf.info(new_in)
    log.cf.info(new_out)
    log.cf.info('\n')

    if not os.path.isfile(v_loc):
        log.cf.error(f"ERROR finding {verilog}, please check verilog input.")
        return False

    slash = '/'
    if sys.platform.startswith('win'):
        slash = '\\'

    command_start = ["read_verilog {}{}{};".format(new_in, slash, verilog)]
    if no_files:
        command_end = [
            "show -format pdf -prefix {}{}{}_yosys".format(new_out, slash, v_name)
        ]
    else:
        command_end = [
            "show -format pdf -prefix {}{}{}_yosys".format(new_out, slash, v_name),
            "write_verilog -noexpr {}{}{}".format(new_out, slash, 'struct_'+v_name),
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
        log.cf.error(f"Yosys output for {v_name} already exists, pleas double-check. \n{e}")
        return False
    
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

    os.system(f'dot -o{path}_technologyMapping.png -Tpng {path}_yosys.dot')
    os.remove(f'{path}_yosys.pdf')
