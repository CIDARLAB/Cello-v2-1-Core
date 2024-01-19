import os
from core_algorithm.celloAlgo import cello_initializer
from config import LIBRARY_DIR, TEMP_OUTPUTS_DIR
from core_algorithm.utils import log
from core_algorithm.utils.config_tester import test_all_configs


def start_cli():
    # NOTE: SETTINGS
    # Set of commands passed to YOSYS to convert Verilog to netlist and for image generation
    yosys_cmd_choice = 1
    verbose = False  # Print more info to console and log. See logging.config to change log metadata verbosity
    # Removes date/time from file name, allowing overwrite of log from equivalent config
    log_overwrite = False
    # Print to console info on *all* tested iterations (produces copious amounts of text)
    print_iters = False
    # Run *all* possible permutations to find true optimum score (may run for *long* time)
    exhaustive = False
    # Runs brief tests of all configs, producing logs and a csv summary of all tests
    test_configs = False

    # TODO: source UCF files from CELLO-UCF instead
    # (contains the verilog files, and UCF files)
    in_path_ = LIBRARY_DIR
    out_path_ = TEMP_OUTPUTS_DIR
    v_name_ = ''
    ucf_name_ = ''
    in_name_ = ''
    out_name_ = ''

    figlet = r"""
    
    


     ######  ######## ##       ##        #######        #######         ##   
    ##    ## ##       ##       ##       ##     ##      ##     ##      ####   
    ##       ##       ##       ##       ##     ##             ##        ##   
    ##       ######   ##       ##       ##     ##       #######         ##   
    ##       ##       ##       ##       ##     ##      ##               ##   
    ##    ## ##       ##       ##       ##     ##      ##        ###    ##   
     ######  ######## ######## ########  #######       ######### ###  ###### 
================================================================================
    """
    print(figlet)
    print('Welcome to Cello 2.1')
    at_menus = True
    ucf_list = ['Bth1C1G1T1', 'Eco1C1G1T1', 'Eco1C2G2T2', 'Eco2C1G3T1', 'Eco2C1G5T1', 'Eco2C1G6T1', 'SC1C1G1T1']

    while at_menus:
        v_name_ = ""
        # Example v_names: 'and', 'xor', 'priorityDetector', 'g70_boolean'
        print(user_input := input(
            f'\n\nFor which Verilog file do you want a genetic circuit design and score to be generated?\n'
            f'(Hint: ___.v, without the .v, from the {in_path_[:-1]} folder...or type \'help\' for more info.)\n\n'
            f'Verilog File: '))

        if user_input == 'help':
            print(f'\n\nHELP INFO:\n'
                  f'Cello is a software package used for designing genetic circuits based on logic gate designs '
                  f'written in the Verilog format.\n\n'
                  f'Steps: \n'
                  f'To test a Verilog file and produce a corresponding circuit design (and circuit score), you can...\n'
                  f' 1. First specify a Verilog file name (exclude the \'.v\'; should be in the \'inputs\' folder)\n'
                  f' 2. Then you will be asked to choose a UCF (User Constraint File)\n'
                  f'    (Available UCFs: {list(zip(range(len(ucf_list)), ucf_list))})\n'
                  f' 3. Then you will be able to specify any additional settings (optional; see choices below)\n'
                  f' 4. Finally, the test will run, producing various files and console output\n\n'
                  f'Config Tester: \n'
                  f' - You can also run a test of all possible combinations of Verilogs and UCFs in \'inputs\'.\n'
                  f' - This only runs a small number of tests per config but can be used to test config validity.\n'
                  f' - It produces log files for each run and a spreadsheet that summarizes the result of each test.\n'
                  f' - To run the utility, enter \'test_all_configs\'.\n'  # NOTE: Still being fixed up
                  # TODO: Remove line
                  f' TEAM: Note this is still being fixed up since merge & not fully working!\n\n'
                  f'Available Settings:\n'
                  f' - (v)  Verbose: {verbose} \n'
                  f'        Print more details to both console and the log file\n'
                  f' - (o)  Log overwrite: {log_overwrite} \n'
                  f'        Overwrite an old log when a new log is run; removes dates from log name\n'
                  f' - (pi) Print all iterations: {print_iters} \n'
                  f'        Print info on all iterations (copious output)\n'
                  f' - (ex) Exhaustive: {exhaustive} \n'
                  f'        Test *all* possible permutations to get global optimum \n'
                  f'        May take *long* time; normally uses simulated annealing to efficiently find good solution')

        elif user_input == 'test_all_configs':
            at_menus = False

            if not os.path.isdir('test_all_configs_out'):
                os.mkdir('test_all_configs_out')
            if not os.path.isdir('logs'):
                os.mkdir('logs')
            test_all_configs(out_path_)

        else:
            at_menus = False
            v_name_ = user_input
            if not os.path.isdir('logs'):
                os.mkdir('logs')

            # 'Bth1C1G1T1': (3 in,  2 out,  7 gate_groups)
            # 'Eco1C1G1T1': (4 in,  2 out, 12 gate_groups)
            # 'Eco1C2G2T2': (4 in,  2 out, 18 gate_groups)  # FIXME: uses a tandem Hill function... circular reference?
            # 'Eco2C1G3T1': (7 in,  2 out,  6 gate_groups)
            # 'Eco2C1G5T1': (7 in,  3 out, 13 gate_groups)  # FIXME: incomplete inputs? non-existent devices in rules
            # 'Eco2C1G6T1': (11 in, 3 out, 16 gate_groups)  # FIXME: non-existent devices in rules
            # 'SC1C1G1T1' : (3 in,  2 out,  9 gate_groups)
            log.cf.info(name_ := input(
                f'\n\nIf you want to use a built-in UCF (User Constrain File) and associated Input & Output files, '
                f'which of the following do you want to use? \n'
                f'Options: {list(zip(range(len(ucf_list)), ucf_list))} \n\n'
                f'Alternatively, just hit Enter if you want to specify your own UCF, Input, and Output files...\n\n'
                f'Index of built-in UCF (or leave blank for custom): '))
            if name_:
                try:
                    ucf_name_ = ucf_list[int(name_)] + '.UCF'
                    in_name_ = ucf_list[int(name_)] + '.input'
                    out_name_ = ucf_list[int(name_)] + '.output'
                except Exception as e:
                    log.cf.info(
                        'Cello was unable to identify the UCF you specified...')
                    log.cf.info(e)
            else:
                os.system('')
                label = "\u001b[4m" + '   .UCF' + "\u001b[0m"
                log.cf.info(ucf_name_ := input(
                    f'\n\nPlease specify the name of the UCF file you want to use...\n'
                    f'(Hint: {label}.json, with the .UCF but not the .json, from the'
                    f' {in_path_[:-1]} folder.)\n\n'
                    f'UCF File Name: '))
                label = "\u001b[4m" + '   .input' + "\u001b[0m"
                log.cf.info(in_name_ := input(
                    f'\n\nPlease specify the name of the Input file you want to use...\n'
                    f'(Hint: {label}.json, with the .input but not the .json, from the {in_path_[:-1]} folder.)\n\n'
                    f'Input File Name: '))
                label = "\u001b[4m" + '   .output' + "\u001b[0m"
                log.cf.info(out_name_ := input(
                    f'\n\nPlease specify the name of the Output file you want to use...\n'
                    f'(Hint: {label}.json, with the .output but not the .json, from the {in_path_[:-1]} folder.)\n\n'
                    f'Output File Name: '))

            options = ''
            # log.cf.info(options := input(
            #     f'\n\nIf you want any additional options set, type the space-separated strings below...\n'
            #     f'Available Settings:\n'
            #     f' - (v)  Verbose: {verbose} \n'
            #     f'        Include \'v\' to print more details to both console and the log file\n'
            #     f' - (o)  Log overwrite: {log_overwrite} \n'
            #     f'        Include \'o\' to overwrite an old log when a new log is run; removes dates from log name\n'
            #     f' - (pi) Print all iterations: {print_iters} \n'
            #     f'        Include \'pi\' to print info on all iterations (copious output)\n'
            #     f' - (ex) Exhaustive: {exhaustive} \n'
            #     f'        Include \'ex\' to test *all* possible permutations to get global optimum \n'
            #     f'        May take *long* time; normally uses simulated annealing to efficiently find good solution\n'
            #     f'Otherwise, just press Enter to proceed with default settings...\n\n'
            #     f'Options (if any): '))
            options_list = options.split()
            # if 'v' in options_list:
            #     verbose = True
            # if 'o' in options_list:
            #     log_overwrite = True
            # if 'pi' in options_list:
            #     print_iters = True
            # if 'ex' in options_list:
            #     exhaustive = True

    result = cello_initializer(v_name_, ucf_name_, in_name_, out_name_, in_path_, out_path_,
                               options={'yosys_cmd_choice': yosys_cmd_choice,
                                        'verbose': verbose,
                                        'log_overwrite': log_overwrite,
                                        'print_iters': print_iters,
                                        'exhaustive': exhaustive,
                                        'test_configs': test_configs})
    # log.cf.error(result, exc_info=True)

    log.cf.info("Exiting Cello...")


if __name__ == '__main__':
    start_cli()
