"""
This software package is for designing genetic circuits based on logic gate designs written in the Verilog format.
TODO: Link to articles and other sources
TODO: Add space/time complexity metrics for simulated annealing to the readme?
TODO: Also update examples and assets folder...
"""

import itertools
import scipy
import sys
import time
import shutil

sys.path.insert(0, 'utils/')  # links the utils folder to the search path
from gate_assignment import *
from logic_synthesis import *
from netlist_class import Netlist
from ucf_class import UCF
from make_eugene_script import *
from dna_design import *
from plotters import plotter


class CELLO3:
    """
    CELLO arguments:
    1. verilog name
    2. ucf name
    3. path-to-verilog-and-ucf
    4. path-for-output
    5. options (optional)

    General flow of control...
        call_YOSYS()
        UCF Class (read in UCF data)
        __load_netlist() (rnl ~ netlist)
        check_conditions()
        techmap()
          GraphParser Class (initialize in/out/gate assignments from UCF to netlist)
          append to node (i, o, g) lists, querying UCF
          simulated_annealing_assign() or exhaustive_assign()
            generate permutations of nodes
            scipy.dual_annealing()
              prep_assign_for_scoring()
                AssignGraph Class (map UCF parts to netlist)
                  score_circuit()
                    ...
        techmap() returns best graph
        info printed
        eugene file created
        [end]
    """

    def __init__(self, v_name: str, ucf_name: str, in_path: str, out_path: str, options: dict = None):
        # NOTE: SETTINGS (Defaults for specific Cello object; see __main__ at bottom for global program defaults)
        yosys_cmd_choice = 1  # Set of commands passed to YOSYS to convert Verilog to netlist and for image generation
        self.verbose = False  # Print more info to console and log. See logging.config to change log metadata verbosity
        self.print_iters = False  # Print to console info on *all* tested iterations (produces copious amounts of text)
        self.exhaustive = False  # Run *all* possible permutations to find true optimum score (may run for *long* time)
        self.test_configs = False  # Runs brief tests of all configs, producing logs and a csv summary of all tests
        self.log_overwrite = False  # Removes date/time from file name, allowing overwrite of log from equivalent config

        if 'yosys_cmd_choice' in options:
            yosys_cmd_choice = options['yosys_cmd_choice']
        if 'verbose' in options:
            self.verbose = options['verbose']
        if 'print_iters' in options:
            self.print_iters = options['print_iters']  # NOTE: Never prints to log (some configs have billions of iters)
        if 'test_configs' in options:
            self.test_configs = options['test_configs']
        if 'log_overwrite' in options:
            self.log_overwrite = options['log_overwrite']
        if 'exhaustive' in options:
            self.exhaustive = options['exhaustive']  # Normally uses Scipy's dual annealing

        self.in_path = in_path
        self.out_path = out_path
        self.verilog_name = v_name
        self.ucf_name = ucf_name
        self.iter_count = 0
        self.best_score = 0
        self.best_graphs = []

        # Loggers
        log.config_logger(v_name, ucf_name, self.log_overwrite)
        log.reset_logs()
        # TODO: print settings already chosen
        print_centered(['CELLO V3', self.verilog_name + ' + ' + self.ucf_name])

        cont = call_YOSYS(in_path, out_path, v_name, yosys_cmd_choice)  # yosys cmd set 1 seems best after trial & error

        print_centered('End of Logic Synthesis')
        if not cont:
            return  # break if run into problem with yosys, call_YOSYS() will show the error.

        self.ucf = UCF(in_path, ucf_name)  # initialize UCF from file

        if not self.ucf.valid:
            return  # breaks early if UCF file has errors

        self.rnl = self.__load_netlist()  # initialize RG from netlist JSON output from Yosys

        if not self.rnl:
            return

        valid: bool
        iter_: int
        valid, iter_ = self.check_conditions(verbose=True)

        if valid:
            log.cf.info(f'\nCondition check passed? {valid}\n')
            log.cf.info('\nContinue to evaluation? (y/n) ')
            log.cf.info(cont := input() if not self.test_configs else 'y')
            if (cont == 'Y' or cont == 'y') and valid:
                best_result = self.techmap(iter_)  # Executing the algorithm if things check out
                if best_result is None:
                    log.cf.error('\nProblem with best_result...\n')
                    return
                # best_score = best_result[0]
                best_graph = best_result[1]
                truth_table = best_result[2]
                truth_table_labels = best_result[3]

                graph_inputs_for_printing = list(zip(self.rnl.inputs, best_graph.inputs))
                graph_gates_for_printing = list(zip(self.rnl.gates, best_graph.gates))
                graph_outputs_for_printing = list(zip(self.rnl.outputs, best_graph.outputs))

                if self.verbose:
                    debug_print(f'final result for {self.verilog_name}.v+{self.ucf_name}: {best_result[0]}')
                    debug_print(best_result[1])

                # RESULTS/CIRCUIT DESIGN
                print_centered(['RESULTS', self.verilog_name + ' + ' + self.ucf_name])
                log.cf.info(f'CIRCUIT DESIGN:\n'
                            f' - Best Design: {best_result[1]}\n'
                            f' - Best Circuit Score: {self.best_score}')

                log.cf.info(f'\nInputs ( input_response = {best_graph.inputs[0].function} ):')
                in_labels = {}
                for rnl_in, g_in in graph_inputs_for_printing:
                    log.cf.info(f' - {rnl_in} {str(g_in)} with max sensor output of'
                                f' {str(list(g_in.out_scores.items()))}')
                    in_labels[rnl_in[0]] = g_in.name

                log.cf.info(f'\nGates ( hill_response = {best_graph.gates[0].hill_response}, '
                            f'input_composition = {best_graph.gates[0].input_comp} ):')
                gate_labels = {}
                for rnl_g, g_g in graph_gates_for_printing:
                    log.cf.info(f' - {rnl_g} {g_g}')
                    gate_labels[rnl_g] = g_g.gate_in_use

                log.cf.info(f'\nOutputs ( unit_conversion = {best_graph.outputs[0].function} ):')
                out_labels = {}
                for rnl_out, g_out in graph_outputs_for_printing:
                    log.cf.info(f' - {rnl_out} {str(g_out)}')
                    out_labels[rnl_out[0]] = g_out.name

                replace_techmap_diagram_labels(f'{out_path_}/{v_name}/{v_name}', gate_labels, in_labels, out_labels)

                # TRUTH TABLE/GATE SCORING
                # filepath = f"{out_path_}/{self.verilog_name}/{self.ucf_name}/{self.verilog_name}+{self.ucf_name}"
                filepath = f"{out_path_}{self.verilog_name}/{self.verilog_name}"
                log.cf.info(f'\n\nTRUTH TABLE/GATE SCORING:')
                tb = [truth_table_labels] + truth_table
                print_table(tb)
                print('(See log for more precision)')
                os.makedirs(os.path.dirname(f'{out_path_}/{self.verilog_name}/{self.ucf_name}/'), exist_ok=True)
                with open(filepath + '_activity-table' + '.csv', 'w', newline='') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(['Scores...'])
                    csv_writer.writerows(zip(*[["{:.2e}".format(float(c)) if i > 0 else c for i, c in enumerate(row)]
                                               for row in zip(*tb) if not row[0].endswith('_I/O')]))
                    csv_writer.writerows([[''], ['Binary...']])
                    csv_writer.writerows(zip(*[row for row in zip(*tb) if row[0].endswith('_I/O')]))

                if self.verbose:
                    debug_print("Truth Table (same as before, simpler format):")
                    for r in tb:
                        log.cf.info(r)

                # CIRCUIT SCORE FILE
                with open(filepath + '_circuit-score' + '.csv', 'w', newline='') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(['circuit_score', self.best_score])

                # EUGENE FILE
                eugene = EugeneObject(self.ucf, graph_inputs_for_printing, graph_gates_for_printing,
                                      graph_outputs_for_printing, best_graph)
                log.cf.info('\n\nEUGENE FILE:')
                if eugene.generate_eugene_structs():
                    log.cf.info(" - Eugene object and structs created...")
                if eugene.generate_eugene_cassettes():
                    log.cf.info(" - Eugene cassettes created...")
                structs, cassettes, sequences, device_rules, circuit_rules, fenceposts = \
                    eugene.generate_eugene_helpers()
                if structs and cassettes and sequences and device_rules and circuit_rules and fenceposts:
                    log.cf.info(" - Eugene helpers created...")
                if eugene.write_eugene(filepath + "_eugene.eug"):
                    log.cf.info(f" - Eugene script written to {filepath}_eugene.eug")

                # DNA DESIGN
                dna_designs = DNADesign(structs, cassettes, sequences, device_rules, circuit_rules, fenceposts)
                dna_designs.gen_seq(filepath)
                dna_designs.write_dna_parts_info(filepath)
                dna_designs.write_dna_parts_order(filepath)
                dna_designs.write_plot_params(filepath)
                dna_designs.write_regulatory_info(filepath)
                dna_designs.write_dna_sequences(filepath)

                # SBOL DIAGRAM
                print(' - ', end='')
                plotter(f"{filepath}_plot_parameters.csv", f"{filepath}_dpl_part_information.csv",
                        f"{filepath}_dpl_regulatory_information.csv", f"{filepath}_dpl_dna_designs.csv",
                        f"{filepath}_dpl.png", f"{filepath}_dpl.pdf")
                log.cf.info(' - SBOL and other DPL files generated')

                # ZIPFILE
                shutil.make_archive(f'{self.verilog_name}_all-files', 'zip', f'{out_path_}{self.verilog_name}')
                shutil.move(f'{self.verilog_name}_all-files.zip', f'{out_path_}{self.verilog_name}')

        else:
            log.cf.info(f'\nCondition check passed? {valid}\n')  # Specific mismatch was a 'warning'

        return

    def __load_netlist(self):
        net_path = self.out_path + '/' + self.verilog_name + '/' + self.verilog_name + '.json'
        net_path = os.path.join(*net_path.split('/'))
        net_file = open(net_path, 'r')
        net_json = json.load(net_file)
        netlist = Netlist(net_json)
        if not netlist.is_valid_netlist():
            return None
        return netlist

    def check_conditions(self, verbose=True):
        """

        NOTE: Ignore logic_constraints value, which is unreliable, and instead use the actual gate count

        :param verbose: bool: default True
        :return:
        """

        if verbose:
            log.cf.info('\n')
            print_centered('condition checks for valid input')

        if verbose:
            log.cf.info('\nNETLIST:')
        netlist_valid = False
        if self.rnl is not None:
            netlist_valid = self.rnl.is_valid_netlist()
        if verbose:
            log.cf.info(f'isvalid: {netlist_valid}')

        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors')
        print(in_sensors)
        num_ucf_input_sensors = len(in_sensors)
        num_ucf_input_structures = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'structures'))
        num_ucf_input_models = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'))
        num_ucf_input_parts = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'parts'))
        num_netlist_inputs = len(self.rnl.inputs) if netlist_valid else 99999
        inputs_match = (num_ucf_input_sensors == num_ucf_input_models) and \
                       (num_ucf_input_models == num_ucf_input_structures == num_ucf_input_parts) and \
                       (num_ucf_input_parts >= num_netlist_inputs)
        if verbose:
            log.cf.info(f'\nINPUTS (including the communication devices): \n'
                        f'num IN-SENSORS in {self.ucf_name} in-UCF: {num_ucf_input_sensors}\n'
                        f'num IN-STRUCTURES in {self.ucf_name} in-UCF: {num_ucf_input_structures}\n'
                        f'num IN-MODELS in {self.ucf_name} in-UCF: {num_ucf_input_models}\n'
                        f'num IN-PARTS in {self.ucf_name} in-UCF: {num_ucf_input_parts}\n'
                        f'num IN-NODES in {self.verilog_name} netlist: {num_netlist_inputs}')

        if verbose:
            log.cf.info([i['name'] for i in in_sensors])
            log.cf.info(f"{'Valid' if inputs_match else 'NOT valid'} input match!")

        out_sensors = self.ucf.query_top_level_collection(self.ucf.UCFout, 'output_devices')
        num_ucf_output_sensors = len(out_sensors)
        num_ucf_output_structures = len(self.ucf.query_top_level_collection(self.ucf.UCFout, 'structures'))
        num_ucf_output_models = len(self.ucf.query_top_level_collection(self.ucf.UCFout, 'models'))
        num_ucf_output_parts = len(self.ucf.query_top_level_collection(self.ucf.UCFout, 'parts'))
        num_netlist_outputs = len(self.rnl.outputs) if netlist_valid else 99999
        outputs_match = (num_ucf_output_sensors == num_ucf_output_models) and \
                        (num_ucf_output_models == num_ucf_output_parts == num_ucf_output_structures) and \
                        (num_ucf_output_parts >= num_netlist_outputs)
        if verbose:
            log.cf.info(f'\nOUTPUTS: \n'
                        f'num OUT-SENSORS in {self.ucf_name} out-UCF: {num_ucf_output_sensors}\n'
                        f'num OUT-STRUCTURES in {self.ucf_name} out-UCF: {num_ucf_output_structures}\n'
                        f'num OUT-MODELS in {self.ucf_name} out-UCF: {num_ucf_output_models}\n'
                        f'num OUT-PARTS in {self.ucf_name} out-UCF: {num_ucf_output_parts}\n'
                        f'num OUT-NODES in {self.verilog_name} netlist: {num_netlist_outputs}')

            log.cf.info([out['name'] for out in out_sensors])
            log.cf.info(f"{'Valid' if outputs_match else 'NOT valid'} output match!")

        num_structs = self.ucf.collection_count['structures']
        num_models = self.ucf.collection_count['models']
        num_gates = self.ucf.collection_count['gates']
        num_parts = self.ucf.collection_count['parts']
        ucf_gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        gate_names = []
        g_list = []
        for gate in ucf_gates:
            # NOTE: below assumes that all gates in our UCFs are 'NOR' gates (currently)
            gate_names.append(gate['name'])
            g_list.append(gate['group'])
        g_list = list(set(g_list))
        num_groups = len(g_list)
        # numFunctions = len(self.ucf.query_top_level_collection(self.ucf.UCFmain, 'functions'))
        if verbose:
            log.cf.info(f'\nGATES: \n'
                        f'num PARTS in {self.ucf_name} UCF: {num_parts}\n'
                        # f'(ref only) num FUNCTIONS in {self.ucf_name} UCF: {numFunctions}\n'
                        f'num STRUCTURES in {self.ucf_name} UCF: {num_structs}\n'
                        f'num MODELS in {self.ucf_name} UCF: {num_models}\n'
                        f'num GATES in {self.ucf_name} UCF: {num_gates}')

        num_gates_available = []
        logic_constraints = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'logic_constraints')
        for logic_constraint in logic_constraints:
            for g in logic_constraint['available_gates']:
                num_gates_available.append(g['max_instances'])
        if verbose:
            log.cf.info(f'num GATE USES: {num_gates_available}')
        num_netlist_gates = len(self.rnl.gates) if netlist_valid else 99999
        if verbose:
            log.cf.info(f'num GATES in {self.verilog_name} netlist: {num_netlist_gates}')

            log.cf.info(sorted(g_list))
            log.cf.info(sorted(gate_names))

        gates_match = (num_structs == num_models == num_gates) and (num_gates_available[0] >= num_netlist_gates)
        if verbose:
            log.cf.info(f"{'Valid' if gates_match else 'NOT valid'} intermediate match!")

        pass_check = netlist_valid and inputs_match and outputs_match and gates_match

        (max_iterations, confirm) = permute_count_helper(num_netlist_inputs, num_netlist_outputs, num_netlist_gates,
                                                         num_ucf_input_sensors, num_ucf_output_sensors,
                                                         num_groups) if pass_check else (None, None)
        if verbose:
            log.cf.info(f'\n#{max_iterations} possible permutations for {self.verilog_name}.v+{self.ucf_name}...')
            log.cf.info(f'(#{confirm} permutations of UCF gate groups confirmed.)')

            print_centered('End of condition checks')

        return pass_check, max_iterations

    def techmap(self, iter_: int):
        """
        Calls functions that will generate the gate assignments.

        :param iter_: int
        :return: list: best_assignment
        """

        # NOTE: POE of the CELLO gate assignment simulation & optimization algorithm
        # NOTE: Give it parameter for which evaluative algorithm to use regardless of iter (exhaustive vs simulation)
        print_centered('Beginning GATE ASSIGNMENT')

        circuit = GraphParser(self.rnl.inputs, self.rnl.outputs, self.rnl.gates)

        log.cf.info('Netlist de-construction: ')
        log.cf.info(circuit.inputs)
        log.cf.info(circuit.gates)
        log.cf.info(circuit.outputs)

        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors')
        i_list = []
        for sensor in in_sensors:
            i_list.append(sensor['name'])

        out_devices = self.ucf.query_top_level_collection(self.ucf.UCFout, 'output_devices')
        o_list = []
        for device in out_devices:
            o_list.append(device['name'])

        gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        g_list = []
        for gate in gates:
            # NOTE: below assumes that all gates in our UCFs are 'NOR' gates
            g_list.append(gate['group'])
        g_list = list(set(g_list))

        log.cf.info('\nListing available assignments from UCF: ')
        log.cf.info(i_list)
        log.cf.info(o_list)
        log.cf.info(g_list)

        log.cf.info('\nNetlist requirements: ')
        i = len(self.rnl.inputs)
        o = len(self.rnl.outputs)
        g = len(self.rnl.gates)
        log.cf.info(f'need {i} inputs')
        log.cf.info(f'need {o} outputs')
        log.cf.info(f'need {g} gates')
        # NOTE: ^ This is the input to whatever algorithm to use

        # best_assignments = []
        if not self.exhaustive:
            best_assignments = self.simulated_annealing_assign(i_list, o_list, g_list, i, o, g, circuit, iter_)
        else:
            best_assignments = self.exhaustive_assign(i_list, o_list, g_list, i, o, g, circuit, iter_)

        print_centered('End of GATE ASSIGNMENT')
        log.cf.info('\n')

        return max(best_assignments, key=lambda x: x[0]) if len(best_assignments) > 0 else best_assignments

    def simulated_annealing_assign(self, i_list: list, o_list: list, g_list: list, i: int, o: int, g: int,
                                   netgraph: GraphParser, iter_: int) -> list:
        """
        Uses scipy's dual annealing func to efficiently find a regional optimum when exhaustive search is not feasible.
        (See notes on Dual Annealing below...)

        :param i_list: list of available inputs
        :param o_list: list of available outputs
        :param g_list: list of available gates
        :param i: int of required inputs
        :param o: int of required outputs
        :param g: int of required gates
        :param netgraph: GraphParser of circuit parameters
        :param iter_: int of total possible configurations
        :return: list: self.best_graphs: [(circuit_score, graph, tb, tb_labels)]
        """

        print_centered('Running SIMULATED ANNEALING gate-assignment algorithm...')
        i_perms, o_perms, g_perms = [], [], []
        # TODO: Optimize permutation arrays
        for i_perm in itertools.permutations(i_list, i):
            i_perms.append(i_perm)
        for o_perm in itertools.permutations(o_list, o):
            o_perms.append(o_perm)
        for g_perm in itertools.permutations(g_list, g):
            g_perms.append(g_perm)
        max_fun = iter_ if iter_ < 1000 else 1000

        # DUAL ANNEALING SCIPY FUNC
        func = lambda x: self.prep_assign_for_scoring(x, (i_perms, o_perms, g_perms, netgraph, i, o, g, max_fun))
        lo = [0, 0, 0]
        hi = [len(i_perms), len(o_perms), len(g_perms)]
        bounds = list(zip(lo, hi))
        # TODO: CK: Implement seed (test in simplified script; test other scipy func seeding)
        # TODO: CK: Implement toxicity check...
        ret = scipy.optimize.dual_annealing(func, bounds, maxfun=max_fun)
        """
        Dual Annealing: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html
        Dual Annealing combines Classical Simulated Annealing, Fast Simulated Annealing, and local search optimizations
        to improve upon the standard simulated annealing technique. The algorithm does not guarantee a global optimal 
        score but can find a good regional optimum in far less time than would be required by exhaustive search.
        
        Key Parameters:
        :param func:    Function of form func(x, *args) with return value that dual_annealing is attempting to optimize
        :param bounds:  Upper and lower bounds for each dimension/variable being passed into func
        :param maxiter: Max number of ~global searches (to identify neighborhoods with potential local maxima)
        :param max_fun: Max number of total function calls/circuit iterations, including local minimization searches
        :param no_local_search: Enable to function more like traditional simulated annealing
        Note: Additional parameters specified in URL above...

        :return OptimizeResult: Array including the solution input array, best score, number of iterations run, and a 
        message indicating the specific reason for termination, among additional attributes specified here...
        docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.OptimizeResult.html#scipy.optimize.OptimizeResult  
        """

        # TODO: CK: Capture multiple equivalent optimums
        # self.best_graphs = ret.x     # solution inputs (already stored in object attribute)
        self.best_score = -ret.fun  # solution score (reverses inversion from prep_assign_for_scoring)
        # count = ret.nfev     # number of func executions
        # reason = ret.message # reason for termination
        log.cf.info(f'\n\nDONE!\n'
                    f'Completed: {self.iter_count:,}/{max_fun:,} iterations (out of {iter_:,} possible iterations)\n'
                    f'Best Score: {self.best_score}')

        return self.best_graphs

    def exhaustive_assign(self, i_list: list, o_list: list, g_list: list, i: int, o: int, g: int,
                          netgraph: GraphParser, iter_: int) -> list:
        """
        Algorithm to check *all* possible permutations of inputs, gates, and outputs for this circuit.
        Depending on the number of possible iterations, this could take prohibitively long.
        Use simulated_annealing_assign for a far more efficient (though it does not guarantee the global optimum).

        :param i_list: list
        :param o_list: list
        :param g_list: list
        :param i: int
        :param o: int
        :param g: int
        :param netgraph: GraphParser
        :param iter_: int
        :return: list: self.best_graphs: [(circuit_score, graph, tb, tb_labels)]
        """
        print_centered('Running EXHAUSTIVE gate-assignment algorithm...')
        log.cf.info('Scoring potential gate assignments...')
        for I_perm in itertools.permutations(i_list, i):
            for O_perm in itertools.permutations(o_list, o):
                for G_perm in itertools.permutations(g_list, g):
                    self.prep_assign_for_scoring((I_perm, O_perm, G_perm), (None, None, None, netgraph, i, o, g, iter_))

        if not self.verbose:
            log.cf.info('\n')
        log.cf.info(f'\nDONE!\nCounted: {self.iter_count:,} iterations')

        return self.best_graphs

    def prep_assign_for_scoring(self, x, args):
        """
        Prepares a specific iteration/configuration to be scored by score_circuit.

        :param x: Tuple of dimensions passed into func, including the following
            - i_perm: Specific inputs permutation to be tested
            - o_perm: Specific outputs permutation to be tested
            - g_perm: Specific gates permutation to be tested
            - netgraph:
            - i
        :param args: Tuple of additional arguments to be passed to func
            - i_perms: First dimension domain:  all permutations of inputs
            - o_perms: Second dimension domain: all permutations of outputs
            - g_perms: Third dimension domain:  all permutations of gates
            - i: Number of required inputs
            - o: Number of required outputs
            - g: Number of required gates
            - netgraph: Circuit parameters
            - iter: Number of total possible configurations
        :return: Best score (only returns score because of how dual_annealing functions; graph info in obj attributes)
        """

        (i_perm, o_perm, g_perm) = x
        (i_perms, o_perms, g_perms, netgraph, i, o, g, max_fun) = args
        # TODO: CK: Account for duplicates
        if i_perms and o_perms and g_perms:
            i_perm = i_perms[math.ceil(i_perm) - 1]
            o_perm = o_perms[math.ceil(o_perm) - 1]
            g_perm = g_perms[math.ceil(g_perm) - 1]

        # Check if inputs, outputs, and gates are unique and the correct number
        if len(set(i_perm + o_perm + g_perm)) == i + o + g:
            self.iter_count += 1
            if self.print_iters:
                print_centered(f'beginning iteration {self.iter_count}:', also_logfile=False)
            # Output the combination
            map_helper = lambda l, c: list(map(lambda x_, y: (x_, y), l, c))
            new_i = map_helper(i_perm, netgraph.inputs)
            new_g = map_helper(g_perm, netgraph.gates)
            new_o = map_helper(o_perm, netgraph.outputs)
            new_i = [Input(i[0], i[1].id) for i in new_i]
            new_o = [Output(o[0], o[1].id) for o in new_o]
            new_g = [Gate(g[0], g[1].gate_type, g[1].inputs, g[1].output) for g in new_g]

            graph = AssignGraph(new_i, new_o, new_g)
            (circuit_score, tb, tb_labels) = self.score_circuit(graph)
            # NOTE: follow the circuit scoring functions

            block = '\u2588'  # str: █,   utf-8: '\u2588',   byte: b'\xe2\x96\x88'
            # block = '#'
            num_blocks = int(round(self.iter_count / max_fun, 2) * 50)
            ph_pb = '_' * 50
            format_cnt = format(self.iter_count, ',')
            format_itr = format(max_fun, ',')

            print(f'{ph_pb} #{format_cnt}/{format_itr} | Best: {round(self.best_score, 2)} | '
                  f'Current: {round(circuit_score, 2)}\r'
                  f'{num_blocks * block}', end='\r')

            if self.print_iters:
                print_centered(f'end of iteration {self.iter_count} : intermediate circuit score = {circuit_score}',
                               also_logfile=False)

            if circuit_score > self.best_score:
                self.best_score = circuit_score
                self.best_graphs = [(circuit_score, graph, tb, tb_labels)]
                log.f.info(
                    f'{ph_pb} #{format_cnt}/{format_itr} | Best Score: {self.best_score} | '
                    f'Current Score: {circuit_score}\r'
                    f'{num_blocks * block}')
            elif circuit_score == self.best_score:
                self.best_graphs.append((circuit_score, graph, tb, tb_labels))

        return -self.best_score  # Inverted because Dual Annealing designed to find minimum; should ONLY return score

    def score_circuit(self, graph: AssignGraph):
        """
        Calculates the circuit score. Returns circuit_score, the core mapping from UCF. (See Pseudocode below).

        NOTE: Please ensure the UCF files follow the same format as those provided in the samples folder!

        NOTE: Use one gate from each group only! (graph.gates.gate_id = group name)

        :param graph: AssignGraph
        :return: score: tuple[SupportsLessThan, list[list[int] | int], list[str]]
        """

        # print(graph.gates)

        '''
        Pseudocode:

        initialize traversal circuit()

        for each input:
            assign input function

        for each gate(group):
            find all gates in group
            for each gate in group:
                assign response function
                (basically find all individual gate permutations)

        for each output:
            assign output function

        create truth table of circuit

        if toxicity & cytometry in all gates:
            label circuit for extra tox and cyt plot evaluations
            (maybe ignore this part because they can just look in the UCF instead to find the plots)

        for each truth table combination:
            for each individual gate assignment:
                traverse circuit from inputs (input composition is mostly x1+x2)
                evaluate output
        '''

        # First, make sure that all inputs use the same 'sensor_response' function; this has to do with UCF formatting
        input_function_json = self.ucf.query_top_level_collection(self.ucf.UCFin, 'functions')
        input_model_names = [i.name + '_model' for i in graph.inputs]
        input_params = query_helper(self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'), 'name',
                                    input_model_names)
        input_functions = {c['name'][:-6]: c['functions']['response_function'] for c in input_params}
        input_equations = {k: (e['equation']) for e in input_function_json for (k, f) in
                           input_functions.items() if (e['name'] == f)}
        input_params = {c['name'][:-6]: {p['name']: p['value'] for p in c['parameters']} for c in input_params}

        if self.print_iters:
            debug_print(f'Assignment configuration: {repr(graph)}', False)
            print(f'INPUT parameters:')
            for p in input_params:
                print(f'{p} {input_params[p]}')
            print(f'input_response = {input_equations}\n')  # TODO: Fix to print mult functions w/ CM
            print(f'Parameters in sensor_response function json: \n{input_params}\n')

        gate_groups = [(g.gate_id, g.gate_type) for g in graph.gates]
        gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        gate_query = query_helper(gates, 'group', [g[0] for g in gate_groups])
        gate_ids = [(g['group'], g['name']) for g in gate_query]
        gate_functions = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'models')
        gate_func_names = gate_functions[0]['functions']
        gate_id_names = [i[1] + '_model' for i in gate_ids]
        gate_functions = query_helper(gate_functions, 'name', gate_id_names)
        gate_params = {
            gf['name'][:-6]: {g['name']: g['value'] for g in gf['parameters']}
            for gf in gate_functions}
        if self.print_iters:
            print(f'GATE parameters: ')
            for f in gate_params:
                print(f'{f} {gate_params[f]}')

        ucf_main_functions = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'functions')
        gate_funcs = {}
        for func_type, func_name in gate_func_names.items():
            if func_type not in ['toxicity', 'cytometry']:  # TODO: add cytometry and toxicity evaluation
                gate_funcs[func_type] = query_helper(ucf_main_functions, 'name', [func_name])[0]['equation']
        # try:
        #     input_composition = query_helper(ucf_main_functions, 'name', ['linear_input_composition'])[0]
        # except Exception as e:
        #     raise Exception(f"UCF contains 'tandem' or no input_composition...") from e  # TODO: handle tandem?
        # hill_response_equation = gate_funcs['Hill_response']['equation'].replace('^', '**')  # substitute power operator
        # linear_input_composition = gate_funcs['linear_input_composition']['equation']
        # if self.print_iters:
        #     print(f'hill_response = {hill_response_equation}')
        #     print(f'linear_input_composition = {linear_input_composition}')
        #     print('\n')

        output_function_json = self.ucf.query_top_level_collection(self.ucf.UCFout, 'functions')
        output_function_str = output_function_json[0]['equation']
        output_names = [o.name for o in graph.outputs]
        output_model_names = [o + '_model' for o in output_names]
        output_jsons = query_helper(self.ucf.query_top_level_collection(self.ucf.UCFout, 'models'), 'name',
                                    output_model_names)
        output_params = {o['name'][:-6]: {p['name']: p['value'] for p in o['parameters']} for o in output_jsons}
        output_functions = {c['name'][:-6]: c['functions']['response_function'] for c in output_jsons}
        output_equations = {k: (e['equation']) for e in output_function_json for (k, f) in
                           output_functions.items() if (e['name'] == f)}

        if self.print_iters:
            print('OUTPUT parameters: ')
            for op in output_params:
                print(f'{op} {output_params[op]}')
            print(f'output_response = {output_equations}\n')

        # adding parameters to inputs
        for graph_input in graph.inputs:
            if repr(graph_input) in input_params and repr(graph_input) in input_equations:
                graph_input.add_eval_params(input_equations[repr(graph_input)], input_params[repr(graph_input)])

        # adding parameters to outputs
        for graph_output in graph.outputs:
            if repr(graph_output) in output_params and repr(graph_output) in output_equations:
                graph_output.add_eval_params(output_equations[repr(graph_output)], output_params[repr(graph_output)])

        # adding parameters and individual gates to gates
        for (gate_group, gate_name) in gate_ids:
            gate_param = gate_params[gate_name]
            for graph_gate in graph.gates:
                if graph_gate.gate_id == gate_group:
                    graph_gate.add_eval_params(gate_funcs, gate_name, gate_param)

        # NOTE: creating a truth table for each graph assignment
        num_inputs = len(graph.inputs)
        num_outputs = len(graph.outputs)
        num_gates = len(graph.gates)
        (truth_table, truth_table_labels) = generate_truth_table(num_inputs, num_gates, num_outputs, graph.inputs,
                                                                 graph.gates, graph.outputs)
        if self.print_iters:
            print('generating truth table...\n')

        # io_indexes = [i for i, x in enumerate(truth_table_labels) if x.split('_')[-1] == 'I/O']
        # io_names = ['_'.join(x.split('_')[:-1]) for x in truth_table_labels if x.split('_')[-1] == 'I/O']

        def get_tb_IO_index(node_name):
            """
            returns index/col num of column with label ending in '_I/O'

            :param node_name: str
            :return: int
            """
            return truth_table_labels.index(node_name + '_I/O')

        circuit_scores = []
        for r in range(len(truth_table)):
            if self.print_iters:
                print(f'row{r} {truth_table[r]}')

            for (input_name, input_onoff) in list(
                    dict(zip(truth_table_labels[:num_inputs], truth_table[r][:num_inputs])).items()):
                input_name = input_name[:input_name.rfind('_')]
                for graph_input in graph.inputs:
                    if repr(graph_input) == input_name:
                        # switch input on/off
                        graph_input.switch_onoff(input_onoff)
                        graph_input_idx = truth_table_labels.index(input_name)
                        truth_table[r][graph_input_idx] = graph_input.out_scores[graph_input.score_in_use]

            def set_tb_IO(node_name, io_val):
                """
                Fills out truth table IO values

                :param node_name:
                :param io_val:
                """
                tb_index_ = get_tb_IO_index(node_name)
                truth_table[r][tb_index_] = io_val

            def get_tb_IO_val(node_name):
                """
                Uses get_tb_IO_index to return value of corresponding col.

                :param node_name: str
                :return: float
                """
                tb_index_ = get_tb_IO_index(node_name)
                return truth_table[r][tb_index_]

            def fill_truth_table_IO(graph_node):
                """
                TODO: docstring

                :param graph_node:
                """
                if type(graph_node) == Gate:
                    gate_inputs = graph.find_prev(graph_node)
                    gate_type = graph_node.gate_type
                    # gate_io = None
                    if gate_type == 'NOR':  # gate_type is either 'NOR' or 'NOT'
                        io_s = []
                        for gate_input in gate_inputs:  # should be exactly 2 inputs
                            input_io = get_tb_IO_val(repr(gate_input))
                            if input_io is None:
                                # this might happen if the gate_input is a gate
                                fill_truth_table_IO(gate_input)
                            input_io = get_tb_IO_val(repr(gate_input))
                            io_s.append(input_io)
                        if len(io_s) == 2 and sum(io_s) == 0:
                            gate_io = 1
                        else:
                            gate_io = 0
                    else:  # (gate_type == 'NOT')
                        input_io = get_tb_IO_val(repr(gate_inputs))
                        if input_io is None:
                            fill_truth_table_IO(gate_inputs)
                        input_io = get_tb_IO_val(repr(gate_inputs))
                        if input_io == 0:
                            gate_io = 1
                        elif input_io == 1:
                            gate_io = 0
                        else:
                            raise RecursionError
                    # finally, update the truth table for this gate 
                    set_tb_IO(repr(graph_node), gate_io)
                    graph_node.IO = gate_io
                elif type(graph_node) == Output:
                    input_gate = graph.find_prev(graph_node)
                    gate_io = get_tb_IO_val(repr(input_gate))
                    if gate_io is None:
                        fill_truth_table_IO(input_gate)
                    gate_io = get_tb_IO_val(repr(input_gate))
                    set_tb_IO(repr(graph_node), gate_io)  # output just carries the gate I/O
                    graph_node.IO = gate_io
                elif type(graph_node) == Input:
                    raise NameError(
                        'not suppose to recurse to input to fill truth table')
                else:
                    raise RecursionError

            for gout in graph.outputs:
                try:
                    fill_truth_table_IO(gout)
                except Exception as e_:
                    # FIXME: this happens for something like the sr_latch, it is not currently supported,
                    #  but with modifications to the truth table, this type of unstable could work
                    debug_print(f'{self.verilog_name} has unsupported circuit configuration due to flip-flopping.\n'
                                f'{e_}')
                    print_table([truth_table_labels] + truth_table)
                    log.cf.info('\n')
                    raise RecursionError

            for graph_output in graph.outputs:
                output_name = graph_output.name
                graph_output_idx = truth_table_labels.index(output_name)
                if truth_table[r][graph_output_idx] is None:
                    output_score = graph.get_score(graph_output, verbose=self.verbose)
                    truth_table[r][graph_output_idx] = output_score
                    circuit_scores.append((output_score, output_name))

            for graph_gate in graph.gates:
                graph_gate_idx = truth_table_labels.index(graph_gate.gate_id)
                truth_table[r][graph_gate_idx] = graph_gate.best_score

            if self.print_iters:
                print(circuit_scores)
                print(truth_table_labels)
                print(f'row{r} {truth_table[r]}\n')

        # this part does this: for each output, find minOn/maxOff, and save output device score for this design
        # try:
        #   Min(On) / Max(Off)
        # except:
        #   either Max() ?
        truth_tested_output_values = {}
        for o in graph.outputs:
            tb_io_index = get_tb_IO_index(repr(o))
            tb_index = truth_table_labels.index(repr(o))
            truth_values = {0: [], 1: []}
            for r in range(len(truth_table)):
                o_io_val = truth_table[r][tb_io_index]
                truth_values[o_io_val].append(truth_table[r][tb_index])
            try:
                truth_tested_output_values[repr(o)] = min(truth_values[1]) / max(truth_values[0])
            except Exception:  # TODO: improve exception handling...
                # this means that either all the rows in the output is ON or all OFF
                try:
                    truth_tested_output_values[repr(o)] = max(truth_values[0])
                except Exception:
                    truth_tested_output_values[repr(o)] = max(truth_values[1])

        graph_inputs_for_printing = list(zip(self.rnl.inputs, graph.inputs))
        graph_gates_for_printing = list(zip(self.rnl.gates, graph.gates))
        graph_outputs_for_printing = list(zip(self.rnl.outputs, graph.outputs))
        if self.print_iters:
            print('reconstructing netlist: ')
            for rnl_in, g_in in graph_inputs_for_printing:
                print(
                    f'{rnl_in} {str(g_in)} and max composition of {max(g_in.out_scores)}')
                # print(g_in.out_scores)
            for rnl_g, g_g in graph_gates_for_printing:
                print(f'{rnl_g} {str(g_g)}')
            for rnl_out, g_out in graph_outputs_for_printing:
                print(f'{rnl_out} {str(g_out)}')
            print('\n')

        truth_table_vis = f'{truth_table_labels}\n'
        for r in truth_table:
            truth_table_vis += str(r) + '\n'
        if self.print_iters:
            print(truth_table_vis)
            print(truth_tested_output_values)
            print('\n')
            print_table([truth_table_labels] + truth_table, False)
        # take the output columns of the truth table, and calculate the outputs

        # NOTE: **return the lower-scored output of the multiple outputs**
        score = min(truth_tested_output_values.values()), truth_table, truth_table_labels

        if self.print_iters:
            print('\nscore_circuit returns:')
            print(score)
        return score

    def __del__(self):

        log.cf.info('Cello object deleted...\n')


if __name__ == '__main__':

    # NOTE: SETTINGS
    yosys_cmd_choice = 1  # Set of commands passed to YOSYS to convert Verilog to netlist and for image generation
    verbose = False  # Print more info to console and log. See logging.config to change log metadata verbosity
    log_overwrite = False  # Removes date/time from file name, allowing overwrite of log from equivalent config
    print_iters = False  # Print to console info on *all* tested iterations (produces copious amounts of text)
    exhaustive = False  # Run *all* possible permutations to find true optimum score (may run for *long* time)
    test_configs = False  # Runs brief tests of all configs, producing logs and a csv summary of all tests

    # TODO: source UCF files from CELLO-UCF instead
    in_path_ = 'sample_inputs/'  # (contains the verilog files, and UCF files)
    out_path_ = 'temp_out/'  # (any path to a local folder)

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
                  f' TEAM: Note this is still being fixed up since merge & not fully working!\n\n'  # TODO: Remove line
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
            from config_tester import test_all_configs

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
            # 'SC1C1G1T1' : (3 in,  2 out,  9 gate_groups)  # NOTE: longer execution times
            log.cf.info(ucf_name_ := input(
                f'\n\nWhich one of the following UCF (User Constraint File) do you want to use? \n'
                f'Options: {list(zip(range(len(ucf_list)), ucf_list))} \n\n'
                f'Index of UCF: '))
            try:
                ucf_name_ = ucf_list[int(ucf_name_)]
            except Exception as e:
                log.cf.info('Cello was unable to identify the UCF you specified...')
                log.cf.info(e)

            log.cf.info(options := input(
                f'\n\nIf you want any additional options set, type the space-separated strings below...\n'
                f'Available Settings:\n'
                f' - (v)  Verbose: {verbose} \n'
                f'        Include \'v\' to print more details to both console and the log file\n'
                f' - (o)  Log overwrite: {log_overwrite} \n'
                f'        Include \'o\' to overwrite an old log when a new log is run; removes dates from log name\n'
                f' - (pi) Print all iterations: {print_iters} \n'
                f'        Include \'pi\' to print info on all iterations (copious output)\n'
                f' - (ex) Exhaustive: {exhaustive} \n'
                f'        Include \'ex\' to test *all* possible permutations to get global optimum \n'
                f'        May take *long* time; normally uses simulated annealing to efficiently find good solution\n'
                f'Otherwise, just press Enter to proceed with default settings...\n\n'
                f'Options (if any): '))
            options_list = options.split()
            if 'v' in options_list:
                verbose = True
            if 'o' in options_list:
                log_overwrite = True
            if 'pi' in options_list:
                print_iters = True
            if 'ex' in options_list:
                exhaustive = True

            start_time = time.time()
            Cello3Process = CELLO3(v_name_, ucf_name_, in_path_, out_path_,
                                   options={'yosys_cmd_choice': yosys_cmd_choice,
                                            'verbose': verbose,
                                            'log_overwrite': log_overwrite,
                                            'print_iters': print_iters,
                                            'exhaustive': exhaustive,
                                            'test_configs': test_configs})
            log.cf.info(f'\nCompletion Time: {round(time.time() - start_time, 1)} seconds')

    log.cf.info("Exiting Cello...")
