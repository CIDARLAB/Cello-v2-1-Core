# Python default libraries
import subprocess
import os
import shutil


def call_YOSYS(in_path=None, out_path=None, vname=None, choice=0):
    try:
        new_out = os.path.join(out_path, vname)
        new_out = os.path.join(*new_out.split('/'))
        if os.path.exists(new_out):
            shutil.rmtree(new_out) # this could be switched out for making a new dir path instead
        os.makedirs(new_out)
    except Exception as e:
        print(f"YOSYS output folder for {vname} could not be re-initialized, please double-check. \n{e}") 
        return False
    print(new_out) # new out_path
    if '/' in vname:
        new_in = os.path.join(in_path, '/'.join(vname.split('/')[:-1]))
        vname = vname.split('/')[-1]
        print(new_in)
    else:
        new_in = in_path
        new_in = os.path.join(*new_in.split('/'))
    verilog = vname + '.v'
    print(verilog)
    print()
   
    v_loc = os.path.join(new_in, verilog)
    if not os.path.isfile(v_loc):
        print(f"ERROR finding {verilog}, please check verilog input.")
        return False


    command_start = ["read_verilog {}/{};".format(new_in, verilog)]
    command_end = [
        "show -format pdf -prefix {}/{}_yosys".format(new_out, vname),
        "write_verilog -noexpr {}/{}".format(new_out, 'struct_'+vname),
        "write_edif {}/{}.edif;".format(new_out, vname),
        "write_json {}/{}.json;".format(new_out, vname),
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
        print(f"Yosys output for {vname} already exists, pleas double-check. \n{e}")
        return False
    
    return True