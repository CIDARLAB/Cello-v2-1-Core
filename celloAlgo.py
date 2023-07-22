"""
This software package is for designing genetic circuits based on logic gate designs written in the Verilog format.

General flow of control...
    __main__
    CELLO3 Class
    call_YOSYS()
    UCF Class (read in UCF data)
    __load_netlist() (rnl ~ netlist)
    check_conditions()
    techmap()
      GraphParser Class (initialize in/out/gate assignments from UCF to netlist)
      [append to node (i, o, g) lists, querying UCF]
      simulated_annealing_assign() or exhaustive_assign()
        [generate permutations of nodes]
        scipy.dual_annealing()
          prep_assign_for_scoring()
            AssignGraph Class (map UCF parts to netlist)
              score_circuit()
                ...
    [techmap() returns best graph]
    [info printed]
    [eugene file created]
    [end]
"""

import itertools
import scipy
import sys

sys.path.insert(0, 'utils/')  # links the utils folder to the search path
from gate_assignment import *
from logic_synthesis import *
from netlist_class import Netlist
from ucf_class import UCF
from eugene import *


# CELLO arguments:
# 1. verilog name
# 2. ucf name
# 3. path-to-verilog-and-ucf
# 4. path-for-output
# 5. options (optional)


class CELLO3:
    """

    """

    def __init__(self, v_name: str, ucf_name: str, in_path: str, out_path: str, options: dict = None):
        self.verbose = True
        self.simulated_annealing = False
        if options is not None:
            yosys_cmd_choice = options['yosys_choice']
            self.verbose = options['verbose']
            self.simulated_annealing = options['simulated_annealing']  # Scipy's dual annealing
        else:
            yosys_cmd_choice = 1

        self.in_path = in_path
        self.out_path = out_path
        self.verilog_name = v_name
        self.ucf_name = ucf_name
        self.iter_count = 0
        self.best_score = 0
        self.best_graphs = []

        print_centered(['CELLO V3', self.verilog_name + ' + ' + self.ucf_name], padding=True)

        cont = call_YOSYS(in_path, out_path, v_name, yosys_cmd_choice)  # yosys cmd set 1 seems best after trial & error

        print_centered('End of Logic Synthesis', padding=True)
        if not cont:
            return  # break if run into problem with yosys, call_YOSYS() will show the error.

        self.ucf = UCF(in_path, ucf_name)  # initialize UCF from file
        if not self.ucf.valid:
            return  # breaks early if UCF file has errors

        self.rnl = self.__load_netlist()  # initialize RG from netlist JSON output from Yosys

        valid: bool
        iter_: int
        valid, iter_ = self.check_conditions(verbose=True)
        print()
        print(f'Condition check passed? {valid}\n')

        if valid:
            cont = input('\nDo you want to continue with the evaluation?\n'
                         '(y: yes, or n: no)\n\n'
                         'Continue? ')  # TODO: put simulated vs. exhaustive option here...
            if (cont == 'Y' or cont == 'y') and valid:
                best_result = self.techmap(iter_)  # Executing the algorithm if things check out

                # best_score = best_result[0]
                best_graph = best_result[1]
                truth_table = best_result[2]
                truth_table_labels = best_result[3]

                graph_inputs_for_printing = list(zip(self.rnl.inputs, best_graph.inputs))
                graph_gates_for_printing = list(zip(self.rnl.gates, best_graph.gates))
                graph_outputs_for_printing = list(zip(self.rnl.outputs, best_graph.outputs))

                debug_print(f'final result for {self.verilog_name}.v+{self.ucf_name}: {best_result[0]}', padding=False)
                debug_print(best_result[1], padding=False)
                print()

                print_centered('RESULTS:')
                print()

                for rnl_in, g_in in graph_inputs_for_printing:
                    print(f'{rnl_in} {str(g_in)} with max sensor output of {str(list(g_in.out_scores.items()))}')
                print(f'in_eval: input_response = {best_graph.inputs[0].function}\n')

                for rnl_g, g_g in graph_gates_for_printing:
                    print(rnl_g, str(g_g))
                print(f'gate_eval: hill_response = {best_graph.gates[0].hill_response}')
                print(f'gate_eval: input_composition = {best_graph.gates[0].input_composition}\n')

                for rnl_out, g_out in graph_outputs_for_printing:
                    print(rnl_out, str(g_out))
                print(f'output_eval: unit_conversion = {best_graph.outputs[0].function}\n')

                debug_print('Truth Table: ', padding=False)
                tb = [truth_table_labels] + truth_table
                print_table(tb)
                print()
                debug_print("Truth Table (same as before, simpler format):", padding=False)
                for r in tb:
                    print(r)
                print()

                # EUGENE FILE
                filepath = f"temp_out/{self.verilog_name}/{self.ucf_name}/{self.verilog_name}+{self.ucf_name}.eug"
                eugene = EugeneObject(self.ucf, graph_inputs_for_printing, graph_gates_for_printing,
                                      graph_outputs_for_printing, filepath, best_graph)
                if eugene.generate_eugene_device():
                    print("Eugene objects created...")
                if eugene.generate_eugene_helpers():
                    print("Eugene helpers created...")
                if eugene.write_eugene():
                    print("Eugene script written...")

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
            print()
            print_centered('condition checks for valid input')

        if verbose:
            print('\nNETLIST:')
        netlist_valid = False
        if self.rnl is not None:
            netlist_valid = self.rnl.is_valid_netlist()
        if verbose:
            print(f'isvalid: {netlist_valid}')

        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors')
        num_ucf_input_sensors = len(in_sensors)
        num_ucf_input_structures = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'structures'))
        num_ucf_input_models = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'))
        num_ucf_input_parts = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'parts'))
        num_netlist_inputs = len(self.rnl.inputs) if netlist_valid else 99999
        inputs_match = (num_ucf_input_sensors == num_ucf_input_models) and \
                       (num_ucf_input_models == num_ucf_input_structures == num_ucf_input_parts) and \
                       (num_ucf_input_parts >= num_netlist_inputs)
        if verbose:
            print('\nINPUTS:')
            print(f'num IN-SENSORS in {ucf_name_} in-UCF: {num_ucf_input_sensors}')
            print(f'num IN-STRUCTURES in {ucf_name_} in-UCF: {num_ucf_input_structures}')
            print(f'num IN-MODELS in {ucf_name_} in-UCF: {num_ucf_input_models}')
            print(f'num IN-PARTS in {ucf_name_} in-UCF: {num_ucf_input_parts}')
            print(f'num IN-NODES in {v_name_} netlist: {num_netlist_inputs}')

        if verbose:
            print([i['name'] for i in in_sensors])
            print(('Valid' if inputs_match else 'NOT valid') + ' input match!')

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
            print('\nOUTPUTS:')
            print(f'num OUT-SENSORS in {ucf_name_} out-UCF: {num_ucf_output_sensors}')
            print(f'num OUT-STRUCTURES in {ucf_name_} out-UCF: {num_ucf_output_structures}')
            print(f'num OUT-MODELS in {ucf_name_} out-UCF: {num_ucf_output_models}')
            print(f'num OUT-PARTS in {ucf_name_} out-UCF: {num_ucf_output_parts}')
            print(f'num OUT-NODES in {v_name_} netlist: {num_netlist_outputs}')

            print([out['name'] for out in out_sensors])
            print(('Valid' if outputs_match else 'NOT valid') + ' output match!')

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
            print('\nGATES:')
            print(f'num PARTS in {ucf_name_} UCF: {num_parts}')
            # print(f'(ref only) num FUNCTIONS in {ucf_name} UCF: {numFunctions}')
            print(f'num STRUCTURES in {ucf_name_} UCF: {num_structs}')
            print(f'num MODELS in {ucf_name_} UCF: {num_models}')
            print(f'num GATES in {ucf_name_} UCF: {num_gates}')

        num_gates_available = []
        logic_constraints = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'logic_constraints')
        for logic_constraint in logic_constraints:
            for g in logic_constraint['available_gates']:
                num_gates_available.append(g['max_instances'])
        if verbose:
            print(f'num GATE USES: {num_gates_available}')
        num_netlist_gates = len(self.rnl.gates) if netlist_valid else 99999
        if verbose:
            print(f'num GATES in {v_name_} netlist: {num_netlist_gates}')

            print(sorted(g_list))
            print(sorted(gate_names))

        gates_match = (num_structs == num_models == num_gates) and (num_gates_available[0] >= num_netlist_gates)
        if verbose:
            print(('Valid' if gates_match else 'NOT valid') + ' intermediate match!')

        pass_check = netlist_valid and inputs_match and outputs_match and gates_match

        (max_iterations, confirm) = permute_count_helper(num_netlist_inputs, num_netlist_outputs, num_netlist_gates,
                                                         num_ucf_input_sensors, num_ucf_output_sensors,
                                                         num_groups) if pass_check else (None, None)
        if verbose:
            debug_print(f'#{max_iterations} possible permutations for {self.verilog_name}.v+{self.ucf_name}')
            debug_print(f'#{confirm} permutations of UCF gate groups confirmed.\n', padding=False)

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
        print_centered('Beginning GATE ASSIGNMENT', padding=True)

        circuit = GraphParser(self.rnl.inputs, self.rnl.outputs, self.rnl.gates)

        debug_print('Netlist de-construction: ')
        print(circuit)

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

        debug_print('Listing available assignments from UCF: ')
        print(i_list)
        print(o_list)
        print(g_list)

        debug_print('Netlist requirements: ')
        i = len(self.rnl.inputs)
        o = len(self.rnl.outputs)
        g = len(self.rnl.gates)
        print(f'need {i} inputs')
        print(f'need {o} outputs')
        print(f'need {g} gates')
        # NOTE: ^ This is the input to whatever algorithm to use

        # best_assignments = []
        if self.simulated_annealing:
            best_assignments = self.simulated_annealing_assign(i_list, o_list, g_list, i, o, g, circuit, iter_)
        else:
            best_assignments = self.exhaustive_assign(i_list, o_list, g_list, i, o, g, circuit, iter_)

        print_centered('End of GATE ASSIGNMENT', padding=True)

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

        print_centered('Running SIMULATED ANNEALING gate-assignment algorithm...', padding=True)
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
        # TODO: CK: Implement seed
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
        :param seed:    For replicating the same results across runs
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
        print(f'\nDONE!\nCompleted: {self.iter_count:,}/{max_fun:,} iterations (out of {iter_:,} possible iterations)')
        print("Best Score: ", self.best_score)

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
        print_centered('Running EXHAUSTIVE gate-assignment algorithm...', padding=True)
        for I_perm in itertools.permutations(i_list, i):
            for O_perm in itertools.permutations(o_list, o):
                for G_perm in itertools.permutations(g_list, g):
                    self.prep_assign_for_scoring((I_perm, O_perm, G_perm), (None, None, None, netgraph, i, o, g, iter_))

        if not self.verbose:
            print()
        print(f'\nDONE!\nCounted: {self.iter_count:,} iterations')

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
            if self.verbose:
                print_centered(f'beginning iteration {self.iter_count}:')
            # Output the combination
            map_helper = lambda l, c: list(map(lambda x_, y: (x_, y), l, c))
            new_i = map_helper(i_perm, netgraph.inputs)
            new_g = map_helper(g_perm, netgraph.gates)
            new_o = map_helper(o_perm, netgraph.outputs)
            new_i = [Input(i[0], i[1].id) for i in new_i]
            new_o = [Output(o[0], o[1].id) for o in new_o]
            new_g = [Gate(g[0], g[1].gate_type, g[1].inputs, g[1].output) for g in new_g]

            graph = AssignGraph(new_i, new_o, new_g)
            (circuit_score, tb, tb_labels) = self.score_circuit(graph, verbose=self.verbose)
            # NOTE: follow the circuit scoring functions

            if not self.verbose:
                # block = '\u2588'
                block = '#'
                num_blocks = int(round(self.iter_count / max_fun, 2) * 100)
                ph_pb = '_' * 100
                format_cnt = format(self.iter_count, ',')
                format_itr = format(max_fun, ',')
                print(
                    f'{ph_pb} #{format_cnt}/{format_itr} | Best Score: {self.best_score} | '
                    f'Current Score: {circuit_score}\r'
                    f'{num_blocks * block}', end='\r')

            if self.verbose:
                print_centered(f'end of iteration {self.iter_count} : intermediate circuit score = {circuit_score}',
                               padding=True)

            if circuit_score > self.best_score:
                self.best_score = circuit_score
                self.best_graphs = [(circuit_score, graph, tb, tb_labels)]
            elif circuit_score == self.best_score:
                self.best_graphs.append((circuit_score, graph, tb, tb_labels))

        return -self.best_score  # Inverted because Dual Annealing designed to find minimum; should ONLY return score

    def score_circuit(self, graph: AssignGraph, verbose=True):
        """
        Calculates the circuit score. Returns circuit_score, the core mapping from UCF. (See Pseudocode below).

        NOTE: Please ensure the UCF files follow the same format as those provided in the samples folder!

        NOTE: Use one gate from each group only! (graph.gates.gate_id = group name)

        :param graph: AssignGraph
        :param verbose: bool: default True
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
        input_function_json = self.ucf.query_top_level_collection(self.ucf.UCFin, 'functions')[0]
        input_function_str = input_function_json['equation'][1:]  # remove the '$' sign

        input_model_names = [i.name + '_model' for i in graph.inputs]
        input_params = query_helper(self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'), 'name',
                                    input_model_names)
        input_params = {c['name'][:-6]: {p['name']: p['value'] for p in c['parameters']} for c in input_params}

        if verbose:
            debug_print(f'Assignment configuration: {repr(graph)}')
            print(f'INPUT parameters:')
            for p in input_params:
                print(p, input_params[p])
            print(f'input_response = {input_function_str}\n')
            # print(f'Parameters in sensor_response function json: \n{input_function_params}\n')

        gate_groups = [(g.gate_id, g.gate_type) for g in graph.gates]
        gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        gate_query = query_helper(gates, 'group', [g[0] for g in gate_groups])
        gate_ids = [(g['group'], g['name']) for g in gate_query]
        gate_functions = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'models')
        gate_id_names = [i[1] + '_model' for i in gate_ids]
        gate_functions = query_helper(gate_functions, 'name', gate_id_names)
        gate_params = {gf['name'][:-6]: {g['name']: g['value'] for g in gf['parameters']} for gf in gate_functions}
        if verbose:
            print(f'GATE parameters: ')
            for f in gate_params:
                print(f, gate_params[f])

        ucf_main_functions = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'functions')
        hill_response = query_helper(ucf_main_functions, 'name', ['Hill_response'])[0]
        input_composition = query_helper(ucf_main_functions, 'name', ['linear_input_composition'])[0]
        hill_response_equation = hill_response['equation'].replace('^', '**')  # substitute power operator
        linear_input_composition = input_composition['equation']
        if verbose:
            print(f'hill_response = {hill_response_equation}')
            print(f'linear_input_composition = {linear_input_composition}')
            print()

        output_names = [o.name for o in graph.outputs]
        output_model_names = [o + '_model' for o in output_names]
        output_jsons = query_helper(self.ucf.query_top_level_collection(self.ucf.UCFout, 'models'), 'name',
                                    output_model_names)
        output_params = {o['name'][:-6]: {p['name']: p['value'] for p in o['parameters']} for o in output_jsons}
        output_function_json = self.ucf.query_top_level_collection(self.ucf.UCFout, 'functions')[0]
        output_function_str = output_function_json['equation']

        if verbose:
            print('OUTPUT parameters: ')
            for op in output_params:
                print(op, output_params[op])
            print(f'output_response = {output_function_str}\n')

        # adding parameters to inputs
        for graph_input in graph.inputs:
            if repr(graph_input) in input_params:
                graph_input.add_eval_params(input_function_str, input_params[repr(graph_input)])

        # adding parameters to outputs
        for graph_output in graph.outputs:
            if repr(graph_output) in output_params:
                graph_output.add_eval_params(output_function_str, output_params[repr(graph_output)])

        # adding parameters and individual gates to gates
        for (gate_group, gate_name) in gate_ids:
            gate_param = gate_params[gate_name]
            for graph_gate in graph.gates:
                if graph_gate.gate_id == gate_group:
                    graph_gate.add_eval_params(hill_response_equation, linear_input_composition, gate_name, gate_param)

        # NOTE: creating a truth table for each graph assignment
        num_inputs = len(graph.inputs)
        num_outputs = len(graph.outputs)
        num_gates = len(graph.gates)
        (truth_table, truth_table_labels) = generate_truth_table(num_inputs, num_gates, num_outputs, graph.inputs,
                                                                 graph.gates, graph.outputs)
        if verbose:
            print('generating truth table...\n')

        # io_indexes = [i for i, x in enumerate(truth_table_labels) if x.split('_')[-1] == 'I/O']
        # io_names = ['_'.join(x.split('_')[:-1]) for x in truth_table_labels if x.split('_')[-1] == 'I/O']

        def get_tb_IO_index(node_name):
            """
            TODO: add get_tb_IO_index docstring

            :param node_name: str
            :return:
            """
            return truth_table_labels.index(node_name + '_I/O')

        circuit_scores = []
        for r in range(len(truth_table)):
            if verbose:
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
                TODO: docstring

                :param node_name:
                :return:
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
                    raise NameError('not suppose to recurse to input to fill truth table')
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
                    print()
                    raise RecursionError

            # if verbose:
            #     print_table([truth_table_labels] + truth_table)

            for graph_output in graph.outputs:
                # TODO: add function to test whether g_output is intermediate or final?
                output_name = graph_output.name
                graph_output_idx = truth_table_labels.index(output_name)
                if truth_table[r][graph_output_idx] is None:
                    output_score = graph.get_score(graph_output, verbose=verbose)
                    truth_table[r][graph_output_idx] = output_score
                    circuit_scores.append((output_score, output_name))

            for graph_gate in graph.gates:
                graph_gate_idx = truth_table_labels.index(graph_gate.gate_id)
                truth_table[r][graph_gate_idx] = graph_gate.best_score

            if verbose:
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
        if verbose:
            print('reconstructing netlist: ')
            for rnl_in, g_in in graph_inputs_for_printing:
                print(f'{rnl_in} {str(g_in)} and max composition of {max(g_in.out_scores)}')
                # print(g_in.out_scores)
            for rnl_g, g_g in graph_gates_for_printing:
                print(rnl_g, str(g_g))
            for rnl_out, g_out in graph_outputs_for_printing:
                print(rnl_out, str(g_out))
            print()

        truth_table_vis = f'{truth_table_labels}\n'
        for r in truth_table:
            truth_table_vis += str(r) + '\n'
        if verbose:
            print(truth_table_vis)
            print(truth_tested_output_values)
            print()
            print_table([truth_table_labels] + truth_table)
        # take the output columns of the truth table, and calculate the outputs

        # NOTE: **return the lower-scored output of the multiple outputs**
        score = min(truth_tested_output_values.values()), truth_table, truth_table_labels

        if verbose:
            print('\nscore_circuit returns:')
            print(score)
        return score


# class Tee(object):
#     def __init__(self, *files):
#         self.files = files
#
#     def write(self, obj):
#         for f in self.files:
#             f.write(obj)
#
#     def flush(self):
#         pass


if __name__ == '__main__':

    # NOTE: SETTINGS
    verbose = False
    assigns = 0
    testers = False

    # f = open('logfile', 'w')
    # backup = sys.stdout
    # sys.stdout = Tee(sys.stdout, f)

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

    # Example v_names: 'and', 'xor', 'priorityDetector', 'g70_boolean'
    v_name_ = input('Welcome to Cello 2.1\n\n\n'
                    'For which Verilog file do you want a genetic circuit design and score to be generated?\n'
                    '(Hint: ___.v, without the .v, from the sample_inputs folder...)\n\n'
                    'Verilog File: ')

    ucf_list = ['Bth1C1G1T1', 'Eco1C1G1T1', 'Eco1C2G2T2', 'Eco2C1G3T1', 'Eco2C1G5T1', 'Eco2C1G6T1', 'SC1C1G1T1']
    # 'Bth1C1G1T1': (3 in, 2 out,  7 gate_groups)
    # 'Eco1C1G1T1': (4 in, 2 out, 12 gate_groups)
    # 'Eco1C2G2T2': (4 in, 2 out, 18 gate_groups) # FIXME: uses a tandem Hill function...
    # 'Eco2C1G3T1': (7 in, 2 out,  6 gate_groups)
    # 'Eco2C1G5T1': (7 in, 3 out, 13 gate_groups) # FIXME: seemingly has incomplete input file...
    # 'SC1C1G1T1' : (3 in, 2 out,  9 gate_groups)
    ucf_name_ = input(f'\n\nWhich of the following UCF (User Constraint File) do you want to use? \n'
                      f'Options: {list(zip(range(len(ucf_list)), ucf_list))} \n\n'
                      f'Index of UCF: ')

    options = input(f'\n\nIf you want any additional options set, type the space-separated characters below.\n'
                    f'Available Settings: Verbosity: {verbose} (enter \'v\' to toggle {not verbose})\n'
                    f'Otherwise, just press Enter...\n\n'
                    f'Options (if any): ')
    if options == 'v':
        verbose = True

    try:
        ucf_name_ = ucf_list[int(ucf_name_)]
    except Exception as e:
        print('Cello was unable to identify the UCF you specified...')
        print(e)

    # TODO: source UCF files from CELLO-UCF instead
    in_path_ = 'sample_inputs/'  # (contains the verilog files, and UCF files)
    out_path_ = 'temp_out/'  # (any path to a local folder)

    Cello3Process = CELLO3(v_name_, ucf_name_, in_path_, out_path_, options={'yosys_choice': 1,
                                                                             'verbose': verbose,
                                                                             'simulated_annealing': assigns})

    print("\nExiting Cello...\n")
