# import json
import itertools
import sys
sys.path.insert(0, 'utils/')  # links the utils folder to the search path

# from cello_helpers import *
from gate_assignment import *
from logic_synthesis import *
from netlist_class import Netlist
from ucf_class import UCF
import log

# CELLO arguments:
# 1. verilog name
# 2. ucf name (could be made optional)
# 3. path-to-verilog-and-ucf
# 4. path-for-output
# 5. options (optional)

# NOTE: if verilog has multiple outputs, SC1C1G1T1 is the only UCF with 2 output devices, 
# therefore so far it is the only one that will work for 2-output circuits
# TODO: fix the UCFs with syntax errors: ('Eco1C2G2T2', 'Eco2C1G6T1') (CK: fixed Eco1C2G2T2)

flag_test_all_configs: bool = False  # Runs brief tests of all configs, producing logs and csv summary


class CELLO3:

    def __init__(self, vname, ucfname, inpath, outpath, options=None):
        # Set these flags at the bottom...
        yosys_cmd_choice = 1
        self.verbose = False
        self.test_configs = False  # Set flag above to run brief tests of all configs
        self.log_overwrite = True  # Removes date/time from file name, allowing overwrite of log from equivalent config
        # NOTE: See logging.config to change log metadata verbosity

        if 'yosys_cmd_choice' in options:
            yosys_cmd_choice = options['yosys_cmd_choice']
        if 'verbose' in options:
            self.verbose = options['verbose']
        if 'test_configs' in options:
            self.test_configs = options['test_configs']
        if 'log_overwrite' in options:
            self.log_overwrite = options['log_overwrite']

        self.inpath = inpath
        self.outpath = outpath
        self.vrlgname = vname
        self.ucfname = ucfname
        self.best_score = 0

        # Loggers
        log.config_logger(vname, ucfname, self.log_overwrite)
        log.reset_counts()

        print_centered(['CELLO V3', self.vrlgname + ' + ' + self.ucfname],
                       padding=True)

        cont = call_YOSYS(inpath, outpath, vname,
                          yosys_cmd_choice)  # yosys command set 1 seems to work best after trial & error

        print_centered('End of Logic Synthesis', padding=True)
        if not cont:
            return  # break if run into problem with yosys, call_YOSYS() will show the error.

        self.ucf = UCF(inpath, ucfname)  # initialize UCF from file
        if not self.ucf.valid:
            return  # breaks early if UCF file has errors

        self.rnl = self.__load_netlist()  # initialize RG from netlist JSON output from Yosys
        if not self.rnl:
            return

        valid, iter = self.check_conditions(verbose=True)

        if valid:
            log.cf.info(f'\nCondition check passed? {valid}\n')
            log.cf.info('\nContinue to evaluation? y/n\n')
            log.cf.info(cont := input() if not self.test_configs else 'y')
            if (cont == 'Y' or cont == 'y') and valid:
                best_result = self.techmap(iter)  # Executing the algorithm if things check out
                if best_result is None:
                    log.cf.error('\nProblem with best_result...\n')
                    return

                # NOTE: best_result = tuple(circuit_score, graph_obj, truth_table)
                self.best_score = best_result[0]
                best_graph = best_result[1]
                truth_table = best_result[2]
                truth_table_labels = best_result[3]

                graph_inputs_for_printing = list(
                    zip(self.rnl.inputs, best_graph.inputs))
                graph_gates_for_printing = list(
                    zip(self.rnl.gates, best_graph.gates))
                graph_outputs_for_printing = list(
                    zip(self.rnl.outputs, best_graph.outputs))

                debug_print(
                    f'final result for {self.vrlgname}.v+{self.ucfname}: {best_result[0]}', padding=False)
                debug_print(best_result[1], padding=False)
                log.cf.info('\n')

                # if self.verbose:
                print_centered('RESULTS:')

                for rnl_in, g_in in graph_inputs_for_printing:
                    log.cf.info(f'{rnl_in} {str(g_in)} with max sensor output of {str(list(g_in.out_scores.items()))}')
                    # log.cf.info(g_in.out_scores)
                log.cf.info(f'in_eval: input_response = {best_graph.inputs[0].function}\n')

                for rnl_g, g_g in graph_gates_for_printing:
                    log.cf.info(str(rnl_g) + str(g_g))
                log.cf.info(f'gate_eval: hill_response = {best_graph.gates[0].hill_response}')
                log.cf.info(f'gate_eval: input_composition = {best_graph.gates[0].input_composition}\n')

                for rnl_out, g_out in graph_outputs_for_printing:
                    log.cf.info(str(rnl_out) + str(g_out))
                log.cf.info(f'output_eval: unit_conversion = {best_graph.outputs[0].function}\n')

                debug_print('Truth Table: ', padding=False)
                tb = [truth_table_labels] + truth_table
                print_table(tb)
                debug_print("Truth Table (same as before, simpler format):",
                            padding=False)
                for r in tb:
                    log.cf.info(r)
                log.cf.info('\n')

        else:
            log.cf.warning(f'\nCondition check passed? {valid}\n')

        return

    def __load_netlist(self):
        netpath = self.outpath + '/' + self.vrlgname + '/' + self.vrlgname + '.json'
        netpath = os.path.join(*netpath.split('/'))
        try:
            netfile = open(netpath, 'r')
        except Exception as e:
            log.cf.error(f'Netfile could not be constructed...\n{e}')
            return False
        netjson = json.load(netfile)
        netlist = Netlist(netjson)
        if not netlist.is_valid_netlist():
            return None
        return netlist

    def techmap(self, iter):
        # NOTE: POE of the CELLO gate assignment simulation & optimization algorithm
        # TODO: Give it parameter for which evaluative algorithm to use regardless of iter (exhaustive vs simulation)
        print_centered('Beginning GATE ASSIGNMENT', padding=True)

        circuit = GraphParser(self.rnl.inputs, self.rnl.outputs, self.rnl.gates)

        debug_print('Netlist de-construction: ')
        log.cf.info(circuit)
        # scrapped this because it uses networkx library for visualizations
        # G = circuit.to_networkx()
        # visualize_logic_circuit(G, preview=False, outfile=f'{self.outpath}/{self.vrlgname}/techmap_preview.png')

        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin,
                                                         'input_sensors')
        I_list = []
        for sensor in in_sensors:
            I_list.append(sensor['name'])

        out_devices = self.ucf.query_top_level_collection(self.ucf.UCFout,
                                                          'output_devices')
        O_list = []
        for device in out_devices:
            O_list.append(device['name'])

        gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        G_list = []
        for gate in gates:
            # NOTE: below assumes that all gates in our UCFs are 'NOR' gates
            G_list.append(gate['group'])
        G_list = list(set(G_list))

        debug_print('Listing available assignments from UCF: ')
        log.cf.info(I_list)
        log.cf.info(O_list)
        log.cf.info(G_list)

        debug_print('Netlist requirements: ')
        i = len(self.rnl.inputs)
        o = len(self.rnl.outputs)
        g = len(self.rnl.gates)
        log.cf.info(f'need {i} inputs')
        log.cf.info(f'need {o} outputs')
        log.cf.info(f'need {g} gates')
        # NOTE: ^ This is the input to whatever algorithm to use

        bestassignments = []
        if iter is not None:
            bestassignments = self.exhaustive_assign(I_list, O_list, G_list, i,
                                                     o, g, circuit, iter)
            if bestassignments is None:
                log.cf.error('\nProblem with the bestassignments...\n')
                return None
        else:
            # TODO: make the other simulation() functions
            bestassignments = self.genetic_simulation(I_list, O_list, G_list, i, o, g, circuit)

        print_centered('End of GATE ASSIGNMENT', padding=True)

        return max(bestassignments, key=lambda x: x[0]) if len(
            bestassignments) > 0 else bestassignments

    # NOTE: alternative to exhaustive assignment - simulation
    def genetic_simulation(self, I_list: list, O_list: list, G_list: list,
                           i: int, o: int, g: int, netgraph: GraphParser):
        # TODO: work on this algorithm
        print_centered('Running GENETIC SIMULATION gate-assignment algorithm...', padding=True)
        debug_print('Too many combinations for exhaustive search, using simulation algorithm instead.')
        bestassignments = [AssignGraph()]
        return bestassignments

    def exhaustive_assign(self, I_list: list, O_list: list, G_list: list,
                          i: int, o: int, g: int, netgraph: GraphParser,
                          iterations: int):
        print_centered('Running EXHAUSTIVE gate-assignment algorithm...', padding=True)
        count = 0
        bestgraphs = []
        bestscore = 0
        # bestgraph = None
        log.f.info('[*** Printing only the iterations that set a new best... ***]')
        for I_comb in itertools.permutations(I_list, i):
            for O_comb in itertools.permutations(O_list, o):
                for G_comb in itertools.permutations(G_list, g):
                    block = '\u2588'
                    num_blocks = int(round(count / iterations, 2) * 100)
                    ph_pb = '_' * 100
                    fmtd_cnt = format(count, ',')
                    fmtd_itr = format(iterations, ',')

                    if self.test_configs and count > 1000:
                        return bestgraphs

                    # Check if inputs, outputs, and gates are unique and the correct number
                    if len(set(I_comb + O_comb + G_comb)) == i + o + g:
                        count += 1
                        if self.verbose:
                            print_centered(f'beginning iteration {count}:')
                        # Output the combination
                        map_helper = lambda l, c: list(map(lambda x, y: (x, y), l, c))
                        newI = map_helper(I_comb, netgraph.inputs)
                        newG = map_helper(G_comb, netgraph.gates)
                        newO = map_helper(O_comb, netgraph.outputs)
                        newI = [Input(i[0], i[1].id) for i in newI]
                        newO = [Output(o[0], o[1].id) for o in newO]
                        newG = [Gate(g[0], g[1].gate_type, g[1].inputs, g[1].output) for g in newG]

                        graph = AssignGraph(newI, newO, newG)
                        (circuit_score, tb, tb_labels) = self.score_circuit(graph, verbose=self.verbose)  # NOTE: follow the circuit scoring functions
                        if circuit_score is None:
                            log.cf.error('\nProblem with the circuit_score...\n')
                            return None

                        if not self.verbose:
                            print(f'\r{ph_pb} #{fmtd_cnt}/{fmtd_itr} | best: {bestscore} circuit score: {circuit_score} \r{num_blocks * block}',
                                  end='\r')
                            pass

                        if self.verbose:
                            print_centered(
                                f'end of iteration {count} : intermediate circuit score = {circuit_score}',
                                padding=True)

                        if circuit_score > bestscore:
                            bestscore = circuit_score
                            bestgraphs = [(circuit_score, graph, tb, tb_labels)]
                            log.f.info(f'\r{ph_pb} #{fmtd_cnt}/{fmtd_itr} | best: {bestscore} circuit score: {circuit_score} \r{num_blocks * block}')
                        elif circuit_score == bestscore:
                            bestgraphs.append((circuit_score, graph, tb_labels))

        if not self.verbose:
            log.cf.info('\n')
        log.cf.info(f'\nDONE!\nCOUNTed: {count:,} iterations')

        return bestgraphs

    # NOTE: this function calculates CIRCUIT SCORE
    # NOTE: modify it if you want circuit score to be calculated differently
    def score_circuit(self, graph: AssignGraph, verbose=True):
        # NOTE: PLEASE ENSURE ALL FUTURE UCF FILES FOLLOW THE SAME FORMAT AS ORIGINALS
        # (THAT'S THE ONLY TO GET THIS TO WORK)

        # NOTE: RETURNS circuit_score
        # NOTE: this is the core mapping from UCF

        # NOTE: use one gate from each group only!
        # NOTE: try every gate from each group (graph.gates.gate_id = group name)
        # log.cf.info(graph.gates)

        '''
        Pseudo code:
        
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

        # First, make sure that all inputs use the same 'sensor_response' function
        # This has to do with UCF formatting
        input_function_json = \
            self.ucf.query_top_level_collection(self.ucf.UCFin, 'functions')[0]
        input_function_str = input_function_json['equation'][
                             1:]  # remove the '$' sign

        input_model_names = [i.name + '_model' for i in graph.inputs]
        input_params = query_helper(
            self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'),
            'name', input_model_names)
        input_params = {
            c['name'][:-6]: {p['name']: p['value'] for p in c['parameters']} for
            c in input_params}

        if verbose:
            debug_print(f'Assignment configuration: {repr(graph)}')
            log.cf.info(f'INPUT parameters:')
            for p in input_params:
                log.cf.info(p, input_params[p])
            log.cf.info(f'input_response = {input_function_str}\n')
        # log.cf.info(f'Parameters in sensor_response function json: \n{input_function_params}\n')

        gate_groups = [(g.gate_id, g.gate_type) for g in graph.gates]
        gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        gate_query = query_helper(gates, 'group', [g[0] for g in gate_groups])
        gate_ids = [(g['group'], g['name']) for g in gate_query]

        gate_functions = self.ucf.query_top_level_collection(self.ucf.UCFmain,
                                                             'models')
        gate_id_names = [i[1] + '_model' for i in gate_ids]
        gate_functions = query_helper(gate_functions, 'name', gate_id_names)
        gate_params = {
            gf['name'][:-6]: {g['name']: g['value'] for g in gf['parameters']}
            for gf in gate_functions}
        if verbose:
            log.cf.info(f'GATE parameters: ')
            for f in gate_params:
                log.cf.info(f, gate_params[f])

        ucfmain_functions = self.ucf.query_top_level_collection(
            self.ucf.UCFmain, 'functions')
        try:
            hill_response = query_helper(ucfmain_functions, 'name', ['Hill_response'])[0]
            input_composition = query_helper(ucfmain_functions, 'name', ['linear_input_composition'])[0]
        except Exception as error:
            log.cf.error(f'query_helper failed for hill_response or input_composition...\n{error}')
            return None, None, None

        hill_response_equation = hill_response['equation'].replace('^', '**')  # substitute power operator
        linear_input_composition = input_composition['equation']
        if verbose:
            log.cf.info(f'hill_response = {hill_response_equation}')
            log.cf.info(f'linear_input_composition = {linear_input_composition}\n')

        output_names = [o.name for o in graph.outputs]
        output_model_names = [o + '_model' for o in output_names]
        output_jsons = query_helper(
            self.ucf.query_top_level_collection(self.ucf.UCFout, 'models'),
            'name', output_model_names)
        output_params = {
            o['name'][:-6]: {p['name']: p['value'] for p in o['parameters']} for
            o in output_jsons}

        output_function_json = \
            self.ucf.query_top_level_collection(self.ucf.UCFout, 'functions')[0]
        output_function_str = output_function_json['equation']

        if verbose:
            log.cf.info('OUTPUT parameters: ')
            for op in output_params:
                log.cf.info(op, output_params[op])
            log.cf.info(f'output_response = {output_function_str}\n')

        # adding parameters to inputs
        for ginput in graph.inputs:
            if repr(ginput) in input_params:
                ginput.add_eval_params(input_function_str,
                                       input_params[repr(ginput)])

        # adding parameters to outputs
        for goutput in graph.outputs:
            if repr(goutput) in output_params:
                goutput.add_eval_params(output_function_str,
                                        output_params[repr(goutput)])

        # adding parameters and individual gates to gates
        for (ggroup, gname) in gate_ids:
            gprams = gate_params[gname]
            for ggate in graph.gates:
                if ggate.gate_id == ggroup:
                    ggate.add_eval_params(hill_response_equation,
                                          linear_input_composition, gname,
                                          gprams)

        # NOTE: creating a truth table for each graph assignment
        num_inputs = len(graph.inputs)
        num_outputs = len(graph.outputs)
        num_gates = len(graph.gates)
        (truth_table, truth_table_labels) = generate_truth_table(num_inputs, num_gates, num_outputs,
                                                                 graph.inputs, graph.gates, graph.outputs)
        if verbose:
            log.cf.info('generating truth table...\n')
        IO_indexes = [i for i, x in enumerate(truth_table_labels) if
                      x.split('_')[-1] == 'I/O']
        IO_names = ['_'.join(x.split('_')[:-1]) for x in truth_table_labels if
                    x.split('_')[-1] == 'I/O']

        def get_tb_IO_index(node_name):
            return truth_table_labels.index(node_name + '_I/O')

        circuit_scores = []
        for r in range(len(truth_table)):
            if verbose: log.cf.info(f'row{r} {truth_table[r]}')

            for (input_name, input_onoff) in list(
                    dict(zip(truth_table_labels[:num_inputs],
                             truth_table[r][:num_inputs])).items()):
                input_name = input_name[:input_name.rfind('_')]
                for grinput in graph.inputs:
                    if repr(grinput) == input_name:
                        # switch input on/off
                        grinput.switch_onoff(input_onoff)
                        ginput_idx = truth_table_labels.index(input_name)
                        truth_table[r][ginput_idx] = grinput.out_scores[grinput.score_in_use]

            # NOTE: filling out truth table IO values in this part
            def set_tb_IO(node_name, IO_val):
                tb_index = get_tb_IO_index(node_name)
                truth_table[r][tb_index] = IO_val

            def get_tb_IO_val(node_name):
                tb_index = get_tb_IO_index(node_name)
                return truth_table[r][tb_index]

            def fill_truth_table_IO(graph_node):
                if type(graph_node) == Gate:
                    gate_inputs = graph.find_prev(graph_node)
                    gate_type = graph_node.gate_type
                    gate_IO = None
                    if gate_type == 'NOR':  # gate_type is either 'NOR' or 'NOT'
                        IOs = []
                        for gate_input in gate_inputs:  # should be exactly 2 inputs
                            input_IO = get_tb_IO_val(repr(gate_input))
                            if input_IO is None:
                                # this might happen if the gate_input is a gate
                                fill_truth_table_IO(gate_input)
                            input_IO = get_tb_IO_val(repr(gate_input))
                            IOs.append(input_IO)
                        if len(IOs) == 2 and sum(IOs) == 0:
                            gate_IO = 1
                        else:
                            gate_IO = 0
                    else:  # (gate_type == 'NOT')
                        input_IO = get_tb_IO_val(repr(gate_inputs))
                        if input_IO is None:
                            fill_truth_table_IO(gate_inputs)
                        input_IO = get_tb_IO_val(repr(gate_inputs))
                        if input_IO == 0:
                            gate_IO = 1
                        elif input_IO == 1:
                            gate_IO = 0
                        else:
                            raise RecursionError
                    # finally, update the truth table for this gate 
                    set_tb_IO(repr(graph_node), gate_IO)
                    graph_node.IO = gate_IO
                elif type(graph_node) == Output:
                    input_gate = graph.find_prev(graph_node)
                    gate_IO = get_tb_IO_val(repr(input_gate))
                    if gate_IO == None: fill_truth_table_IO(input_gate)
                    gate_IO = get_tb_IO_val(repr(input_gate))
                    set_tb_IO(repr(graph_node), gate_IO)  # output just carries the gate I/O
                    graph_node.IO = gate_IO
                elif type(graph_node) == Input:
                    raise NameError(
                        'not suppose to recurse to input to fill truth table')
                else:
                    raise RecursionError

            for gout in graph.outputs:
                try:
                    fill_truth_table_IO(gout)
                except:
                    # NOTE: this happens for something like the sr_latch, it is not currently supported
                    # NOTE: but with modifications to the truth table, this type of unstable could work
                    debug_print(
                        f'{self.vrlgname} has unsupported circuit configuration due to flip-flopping.')
                    print_table([truth_table_labels] + truth_table)
                    raise (RecursionError)

            # if verbose:
            #     print_table([truth_table_labels] + truth_table)

            for goutput in graph.outputs:
                # NOTE: add function to test whether goutput is intermediate or final
                output_name = goutput.name
                goutput_idx = truth_table_labels.index(output_name)
                if truth_table[r][goutput_idx] == None:
                    output_score = graph.get_score(goutput, verbose=verbose)
                    truth_table[r][goutput_idx] = output_score
                    circuit_scores.append((output_score, output_name))

            for grgate in graph.gates:
                grgate_idx = truth_table_labels.index(grgate.gate_id)
                truth_table[r][grgate_idx] = grgate.best_score

            if verbose:
                log.cf.info(circuit_scores)
                log.cf.info(truth_table_labels)
                log.cf.info(f'row{r} {truth_table[r]}\n')

        # this part does this: for each output, find minOn/maxOff, and save output device score for this design
        # try:
        #   Min(On) / Max(Off)
        # except:
        #   either Max() ?
        truth_tested_output_values = {}
        for o in graph.outputs:
            tb_IO_index = get_tb_IO_index(repr(o))
            tb_index = truth_table_labels.index(repr(o))
            truth_values = {0: [], 1: []}
            for r in range(len(truth_table)):
                o_IO_val = truth_table[r][tb_IO_index]
                truth_values[o_IO_val].append(truth_table[r][tb_index])
            try:
                truth_tested_output_values[repr(o)] = min(
                    truth_values[1]) / max(truth_values[0])
            except:
                # this means that either all of the rows in the output is ON or all OFF
                try:
                    truth_tested_output_values[repr(o)] = max(truth_values[0])
                except:
                    truth_tested_output_values[repr(o)] = max(truth_values[1])

        graph_inputs_for_printing = list(zip(self.rnl.inputs, graph.inputs))
        graph_gates_for_printing = list(zip(self.rnl.gates, graph.gates))
        graph_outputs_for_printing = list(zip(self.rnl.outputs, graph.outputs))
        if verbose:
            log.cf.info('reconstructing netlist: ')
            for rnl_in, g_in in graph_inputs_for_printing:
                log.cf.info(
                    f'{rnl_in} {str(g_in)} and max composition of {max(g_in.out_scores)}')
                # log.cf.info(g_in.out_scores)
            for rnl_g, g_g in graph_gates_for_printing:
                log.cf.info(rnl_g, str(g_g))
            for rnl_out, g_out in graph_outputs_for_printing:
                log.cf.info(rnl_out, str(g_out))
            log.cf.info('\n')

        truth_table_vis = f'{truth_table_labels}\n'
        for r in truth_table:
            truth_table_vis += str(r) + '\n'
        if verbose:
            log.cf.info(truth_table_vis)
            log.cf.info(truth_tested_output_values)
            log.cf.info('\n')
            print_table([truth_table_labels] + truth_table)
        # take the output columns of the truth table, and calculate the outputs

        # NOTE: **return the lower-scored output of the multiple outputs**
        score = min(
            truth_tested_output_values.values()), truth_table, truth_table_labels

        if verbose:
            log.cf.info('\nscore_circuit returns:')
            log.cf.info(score)
        return score

    def check_conditions(self, verbose=True):
        if verbose: log.cf.info('\n')
        if verbose: print_centered('condition checks for valid input')

        if verbose: log.cf.info('\nNETLIST:')
        netlist_valid = False
        if self.rnl is not None:
            netlist_valid = self.rnl.is_valid_netlist()
        if verbose: log.cf.info(f'isvalid: {netlist_valid}')

        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors')
        num_ucf_input_sensors = len(in_sensors)
        num_ucf_input_structures = len(
            self.ucf.query_top_level_collection(self.ucf.UCFin, 'structures'))
        num_ucf_input_models = len(
            self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'))
        num_ucf_input_parts = len(
            self.ucf.query_top_level_collection(self.ucf.UCFin, 'parts'))
        num_netlist_inputs = len(self.rnl.inputs) if netlist_valid else 99999
        inputs_match = (
                                   num_ucf_input_sensors == num_ucf_input_models == num_ucf_input_structures == num_ucf_input_parts) \
                       and (num_ucf_input_parts >= num_netlist_inputs)
        if verbose: log.cf.info('\nINPUTS:')
        if verbose: log.cf.info(
            f'num IN-SENSORS in {self.ucfname} in-UCF: {num_ucf_input_sensors}\n'
            f'num IN-STRUCTURES in {self.ucfname} in-UCF: {num_ucf_input_structures}\n'
            f'num IN-MODELS in {self.ucfname} in-UCF: {num_ucf_input_models}\n'
            f'num IN-PARTS in {self.ucfname} in-UCF: {num_ucf_input_parts}\n'
            f'num IN-NODES in {self.vrlgname} netlist: {num_netlist_inputs}\n')

        if verbose: log.cf.info([i['name'] for i in in_sensors])
        if verbose: log.cf.info(
            ('Valid' if inputs_match else 'NOT valid') + ' input match!')

        out_sensors = self.ucf.query_top_level_collection(self.ucf.UCFout,
                                                          'output_devices')
        num_ucf_output_sensors = len(out_sensors)
        num_ucf_output_structures = len(
            self.ucf.query_top_level_collection(self.ucf.UCFout, 'structures'))
        num_ucf_output_models = len(
            self.ucf.query_top_level_collection(self.ucf.UCFout, 'models'))
        num_ucf_output_parts = len(
            self.ucf.query_top_level_collection(self.ucf.UCFout, 'parts'))
        num_netlist_outputs = len(self.rnl.outputs) if netlist_valid else 99999
        outputs_match = (
                                num_ucf_output_sensors == num_ucf_output_models == num_ucf_output_parts == num_ucf_output_structures) and (
                                num_ucf_output_parts >= num_netlist_outputs)
        if verbose: log.cf.info('\nOUTPUTS:')
        if verbose: log.cf.info(
            f'num OUT-SENSORS in {self.ucfname} out-UCF: {num_ucf_output_sensors}\n'
            f'num OUT-STRUCTURES in {self.ucfname} out-UCF: {num_ucf_output_structures}\n'
            f'num OUT-MODELS in {self.ucfname} out-UCF: {num_ucf_output_models}\n'
            f'num OUT-PARTS in {self.ucfname} out-UCF: {num_ucf_output_parts}\n'
            f'num OUT-NODES in {self.vrlgname} netlist: {num_netlist_outputs}')

        if verbose: log.cf.info([out['name'] for out in out_sensors])
        if verbose: log.cf.info(
            ('Valid' if outputs_match else 'NOT valid') + ' output match!')

        numStructs = self.ucf.collection_count['structures']
        numModels = self.ucf.collection_count['models']
        numGates = self.ucf.collection_count['gates']
        numParts = self.ucf.collection_count['parts']
        ucf_gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        gate_names = []
        G_list = []
        for gate in ucf_gates:
            # NOTE: below assumes that all gates in our UCFs are 'NOR' gates (currently)
            gate_names.append(gate['name'])
            G_list.append(gate['group'])
        G_list = list(set(G_list))
        num_groups = len(G_list)
        # numFunctions = len(self.ucf.query_top_level_collection(self.ucf.UCFmain, 'functions'))
        if verbose: log.cf.info('\nGATES:')
        if verbose: log.cf.info(
            f'num PARTS in {self.ucfname} UCF: {numParts}\n'
            # if verbose: log.cf.info(f'(ref only) num FUNCTIONS in {self.ucfname} UCF: {numFunctions}')
            f'num STRUCTURES in {self.ucfname} UCF: {numStructs}\n'
            f'num MODELS in {self.ucfname} UCF: {numModels}\n'
            f'num GATES in {self.ucfname} UCF: {numGates}\n')

        num_gates_available = []
        logic_constraints = self.ucf.query_top_level_collection(
            self.ucf.UCFmain, 'logic_constraints')
        for l in logic_constraints:
            for g in l['available_gates']:
                num_gates_available.append(g['max_instances'])
        if verbose: log.cf.info(f'num GATE USES: {num_gates_available}')
        num_netlist_gates = len(self.rnl.gates) if netlist_valid else 99999
        if verbose: log.cf.info(f'num GATES in {self.vrlgname} netlist: {num_netlist_gates}')

        if verbose: log.cf.info(sorted(G_list))
        if verbose: log.cf.info(sorted(gate_names))

        gates_match = (numStructs == numModels == numGates) and (
                num_gates_available[0] >= num_netlist_gates)
        if verbose: log.cf.info(
            ('Valid' if gates_match else 'NOT valid') + ' intermediate match!')

        pass_check = netlist_valid and inputs_match and outputs_match and gates_match

        (max_iterations, confirm) = permute_count_helper(num_netlist_inputs, num_netlist_outputs, num_netlist_gates,
                                                         num_ucf_input_sensors, num_ucf_output_sensors,
                                                         num_groups) if pass_check else (None, None)
        if verbose: debug_print(
            f'#{max_iterations} possible permutations for {self.vrlgname}.v+{self.ucfname}')
        if verbose: debug_print(
            f'#{confirm} permutations of UCF gate groups confirmed.\n',
            padding=False)

        if verbose: print_centered('End of condition checks')

        # NOTE: if max_iterations passes a threshold, switch from exhaustive algorithm to simulative algorithm
        threshold = 1000000  # 1 million iterations (which should take around an hour or so)
        # if max_iterations > threshold:
        #     max_iterations = None

        return pass_check, max_iterations

    def __del__(self):
        log.cf.info('Iteration object deleted...')


if __name__ == '__main__':
    ucflist = ['Bth1C1G1T1', 'Eco1C1G1T1', 'Eco1C2G2T2', 'Eco2C1G3T1',
               'Eco2C1G5T1', 'Eco2C1G6T1', 'SC1C1G1T1']
    # problem_ucfs = ['Eco1C2G2T2', 'Eco2C1G6T1']

    # vname = 'nand'
    # vname = 'and'
    # vname = 'xor'
    # vname = 'priorityDetector'
    # vname = 'chat_3x2'
    # vname = 'g70_boolean'
    # vname = 'g77_boolean'
    # vname = 'g92_boolean'

    if flag_test_all_configs:
        from config_tester import test_all_configs

        test_all_configs()
    else:
        log.cf.info(vname := input('\nWhich Verilog to use (without the .v)?\n(Hint, ___.v from your folder) \nName='))
        log.cf.info(ucfname := input(f'\nWhich UCF to use? \n{list(zip(range(len(ucflist)), ucflist))} \nIndex='))
        try:
            ucfname = ucflist[int(ucfname)]
        except Exception as e:
            ucfname = 'Eco1C1G1T1'

        # (3in, 1out, 7gategroups)
        # ucfname = 'Bth1C1G1T1'

        # (4in, 1out, 12gategroups)
        # ucfname = 'Eco1C1G1T1'

        # (7in, 1out, 6gategroups)
        # ucfname = 'Eco2C1G3T1'

        # (7in, 1out, 13gategroups)
        # ucfname = 'Eco2C1G5T1'

        # (3in, 2out, 9gategroups)
        # ucfname = 'SC1C1G1T1'

        # TODO: source UCF files from CELLO-UCF instead
        inpath = 'sample_inputs/'  # (contains the verilog files, and UCF files)
        outpath = 'temp_out/'  # (any path to a local folder)

        Cello3Process = CELLO3(vname, ucfname, inpath, outpath,
                               options={'yosys_cmd_choice': 1,
                                        'verbose': False,
                                        'test_configs': False,
                                        'log_overwrite': True})
