import json
from logic_synthesis import *
from netlist_class import Netlist
from ucf_class import UCF
import sys
import itertools
sys.path.insert(0, 'utils/')  # links the utils folder to the search path
from cello_helpers import *
from gate_assignment import *

#temp
# from tqdm import tqdm

# CELLO arguments:
# 1. verilog name
# 2. ucf name (could be made optional)
# 3. path-to-verilog-and-ucf
# 4. path-for-output
# 5. options (optional)

# NOTE: if verilog has multiple outputs, SC1C1G1T1 is the only UCF with 2 output devices, 
# therefore so far it is the only one that will work for 2-output circuits
# TODO: fix the UCFs with syntax errors
class CELLO3:
    def __init__(self, vname, ucfname, inpath, outpath, options=None):
        self.verbose = True
        if options is not None:
            yosys_cmd_choice = options['yosys_choice']
            self.verbose = options['verbose']
        else:
            yosys_cmd_choice = 1  
        self.inpath = inpath
        self.outpath = outpath
        self.vrlgname = vname
        self.ucfname = ucfname
        print_centered(['CELLO V3', self.vrlgname + ' + ' + self.ucfname], padding=True)
        cont = call_YOSYS(inpath, outpath, vname, yosys_cmd_choice) # yosys command set 1 seems to work best after trial & error
        print_centered('End of Logic Synthesis', padding=True)
        if not cont:
            return # break if run into problem with yosys, call_YOSYS() will show the error.
        self.ucf = UCF(inpath, ucfname) # initialize UCF from file
        if self.ucf.valid == False:
            return # breaks early if UCF file has errors
        self.rnl = self.__load_netlist() # initialize RG from netlist JSON output from Yosys
        valid, iter = self.check_conditions(verbose=self.verbose)
        if self.verbose: print(f'\nCondition check passed? {valid}\n')
        if valid:
            cont = input('Continue to evaluation? y/n ')
            if (cont == 'Y' or cont == 'y') and valid:
                    best_result = self.techmap(iter) # Executing the algorithm if things check out
                    graph = best_result[1]
                    graph_inputs_for_printing = list(zip(self.rnl.inputs, graph.inputs))
                    graph_gates_for_printing = list(zip(self.rnl.gates, graph.gates))
                    graph_outputs_for_printing = list(zip(self.rnl.outputs, graph.outputs))
                    debug_print(f'final result for {self.vrlgname}.v+{self.ucfname}: \n{best_result}')
                    if self.verbose:
                        print('reconstructing netlist: ')
                        for rnl_in, g_in in graph_inputs_for_printing:
                            print(f'{rnl_in} {str(g_in)} and max composition of {max(g_in.out_scores)}')
                            # print(g_in.out_scores)
                        print(f'input_response = {graph.inputs[0].function}')
                        for rnl_g, g_g in graph_gates_for_printing:
                            print(rnl_g, str(g_g))
                        print(f'hill_response = {graph.gates[0].hill_response}')
                        print(f'input_composition = {graph.gates[0].input_composition}')
                        for rnl_out, g_out in graph_outputs_for_printing:
                            print(rnl_out, str(g_out))
                        print(f'unit_conversion = {graph.outputs[0].function}')
                        print()
                    
        return
        
        
    def __load_netlist(self):
        netpath = self.outpath + '/' + self.vrlgname + '/' + self.vrlgname + '.json'
        netfile = open(netpath, 'r')
        netjson = json.load(netfile)
        netlist = Netlist(netjson)
        if not netlist.is_valid_netlist():
            return None
        return netlist
                
                
    def techmap(self, iter):
        # NOTE: POE of the CELLO gate assignment simulation & optimization algorithm
        # TODO: Give it parameter for which evaluative algorithm to use (exhaustive vs simulation)
        print_centered('Beginning GATE ASSIGNMENT', padding=True)
        
        circuit = GraphParser(self.rnl.inputs, self.rnl.outputs, self.rnl.gates)
        
        debug_print('Netlist de-construction: ')
        print(circuit)
        # scrapped this because it uses networkx library for visualzations
        # G = circuit.to_networkx()
        # visualize_logic_circuit(G, preview=False, outfile=f'{self.outpath}/{self.vrlgname}/techmap_preview.png')
        
        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors')
        I_list = []
        for sensor in in_sensors:
            I_list.append(sensor['name'])
            
        out_devices = self.ucf.query_top_level_collection(self.ucf.UCFout, 'output_devices')
        O_list = []
        for device in out_devices:
            O_list.append(device['name'])
            
        gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        G_list = []
        for gate in gates:
            # G_list.append((gate['name'], gate['gate_type']))
            # NOTE: below assumes that all gates in our UCFs are 'NOR' gates
            G_list.append(gate['group'])
        G_list = list(set(G_list))
        
        debug_print('Listing available assignments from UCF: ')
        print(I_list)
        print(O_list)
        print(G_list)
        
        debug_print('Netlist requirements: ')
        i = len(self.rnl.inputs)
        o = len(self.rnl.outputs)
        g = len(self.rnl.gates)
        print(f'need {i} inputs')
        print(f'need {o} outputs')
        print(f'need {g} gates')
        # NOTE: ^ This is the input to whatever algorithm to use
        
        bestassignments = []
        if iter is not None:
            bestassignments = self.exhaustive_assign(I_list, O_list, G_list, i, o, g, circuit)
        else:
            # TODO: make the other simulation() functions
            bestassignments = self.genetic_simulation(I_list, O_list, G_list, i, o, g, circuit)
        
        print_centered('End of GATE ASSIGNMENT', padding=True)
        
        return max(bestassignments, key=lambda x: x[0]) if len(bestassignments) > 0 else bestassignments
    
    def genetic_simulation(self, I_list: list, O_list: list, G_list: list, i: int, o: int, g: int, netgraph: GraphParser):
        # TODO: work on this algorithm
        print_centered('Running GENETIC SIMULATION gate-assignment algorithm...', padding=True)
        debug_print('Too many combinations for exhaustive search, using simulation algorithm instead.')
        bestassignments = [AssignGraph()]
        return bestassignments
        
    def exhaustive_assign(self, I_list: list, O_list: list, G_list: list, i: int, o: int, g: int, netgraph: GraphParser):
        print_centered('Running EXHAUSTIVE gate-assignment algorithm...', padding=True)
        count = 0
        bestgraphs = []
        bestscore = 0
        # bestgraph = None
        for I_comb in itertools.permutations(I_list, i):
            for O_comb in itertools.permutations(O_list, o):
                for G_comb in itertools.permutations(G_list, g):
                    # Check if inputs, outputs, and gates are unique and the correct number
                    if len(set(I_comb + O_comb + G_comb)) == i+o+g:
                        count += 1
                        # Output the combination
                        map_helper = lambda l, c: list(map(lambda x, y: (x, y), l, c))
                        newI = map_helper(I_comb, netgraph.inputs)
                        newG = map_helper(G_comb, netgraph.gates)
                        newO = map_helper(O_comb, netgraph.outputs)
                        # print(f"Inputs: {newI}, Gates: {newG}, Outputs: {newO}")
                        # TODO: Make each gate assign
                        newI = [Input(i[0], i[1].id) for i in newI]
                        newO = [Output(o[0], o[1].id) for o in newO]
                        newG = [Gate(g[0], g[1].gate_type, g[1].inputs, g[1].output) for g in newG]
                        
                        graph = AssignGraph(newI, newO, newG)
                        circuit_score = self.score_circuit(graph, verbose=False)
                        print(f'iteration {count} : intermediate circuit score = {circuit_score}', end='\r')
                        if circuit_score > bestscore:
                            bestscore = circuit_score
                            bestgraphs = [(circuit_score, graph)]
                        elif circuit_score == bestscore:
                            bestgraphs.append((circuit_score, graph))
                        
        print(f'\nCOUNTed: {count:,} iterations')
        
        
        # temp
        # circuit_score = self.score_circuit(graph)
        # print(f'circuit score: {circuit_score}')
        # bestgraphs = [graph]   
        # end temp    
        
        return bestgraphs
    
    # NOTE: this function calculates CIRCUIT SCORE
    # NOTE: modify it if you want circuit score to be caldulated differently
    def score_circuit(self, graph: AssignGraph, verbose=True):
        # NOTE: PLEASE ENSURE ALL FUTURE UCF FILES FOLLOW THE SAME FORAMT AS ORIGINALS
        # (THAT'S THE ONLY TO GET THIS TO WORK)
        
        # NOTE: RETURNS circuit_score
        # NOTE: this is the core mapping from UCF
        
        # NOTE: use one gate from each group only!
        # NOTE: try every gate from each group (graph.gates.gate_id = group name)
        # print(graph.gates)
        
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
        # input_response_functions = [(c['name'], c['functions']['response_function'], c['parameters']) for c in self.ucf.query_top_level_collection(self.ucf.UCFin, 'models')]
        # print(input_response_functions)
        # Looks good!
        
        
        input_function_json = self.ucf.query_top_level_collection(self.ucf.UCFin, 'functions')[0]
        input_function_str = input_function_json['equation'][1:] #remove the '$' sign
        # input_function_params =[p['name'] for p in input_function_json['parameters']]
        
        input_model_names = [i.name+'_model' for i in graph.inputs]
        input_params = query_helper(self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'), 'name', input_model_names)
        input_params = {c['name'][:-6]: {p['name']: p['value'] for p in c['parameters']} for c in input_params}
        
        if verbose:
            debug_print(f'Assignment configuration: {repr(graph)}')
            print(f'INPUT paramters:')
            for p in input_params:
                print(p, input_params[p])
            print(f'input_response = {input_function_str}\n')
        # print(f'Parameters in sensor_response function json: \n{input_function_params}\n')
            
        gate_groups = [(g.gate_id, g.gate_type) for g in graph.gates]
        gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        gate_query = query_helper(gates, 'group', [g[0] for g in gate_groups])
        gate_ids = [(g['group'] ,g['name']) for g in gate_query]
        
        # print(f'Gate mappings: ')
        # for g in gate_ids:
        #     print(g)
        # print()  
        
        
        gate_functions = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'models')
        gate_id_names = [i[1]+'_model' for i in gate_ids]
        gate_functions = query_helper(gate_functions, 'name', gate_id_names)
        gate_params = {gf['name'][:-6]: {g['name']: g['value'] for g in gf['parameters']} for gf in gate_functions}
        if verbose:
            print(f'GATE parameters: ')
            for f in gate_params:
                print(f, gate_params[f])
            
        # TEMP
        # print('\nGate Function Mappings: ')
        # gate_function_names = [gf['functions'] for gf in gate_functions]
        # check that all the gates use the same RESPONSE & INPUT COMPOSITION functions
        # Here, we can check whether all the gates have the toxicity and cytometry functions
        # for gn in gate_function_names:
        #     print(gn)
        # END TEMP
        
        # print('\nGate Functions: ')
        ucfmain_functions = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'functions')
        hill_response = query_helper(ucfmain_functions, 'name', ['Hill_response'])[0]
        input_composition = query_helper(ucfmain_functions, 'name', ['linear_input_composition'])[0]
        hill_response_equation = hill_response['equation'].replace('^', '**') # substitute power operator
        linear_input_composition = input_composition['equation']
        if verbose:
            print(f'hill_response = {hill_response_equation}')
            print(f'linear_input_composition = {linear_input_composition}')
            print()
        
            
        output_names = [o.name for o in graph.outputs]
        output_model_names = [o+'_model' for o in output_names]
        # output_jsons = query_helper(self.ucf.UCFout, 'collection', [output_model_names])
        output_jsons = query_helper(self.ucf.query_top_level_collection(self.ucf.UCFout, 'models'), 'name', output_model_names)
        output_params = {o['name'][:-6]: {p['name']: p['value'] for p in o['parameters']} for o in output_jsons}
        
        output_function_json = self.ucf.query_top_level_collection(self.ucf.UCFout, 'functions')[0]
        output_function_str = output_function_json['equation']
        
        if verbose:
            print('OUTPUT parameters: ')
            for op in output_params:
                print(op, output_params[op])
            print(f'output_response = {output_function_str}\n')
        
        # adding parameters to inputs
        for ginput in graph.inputs:
            if repr(ginput) in input_params:
                ginput.add_eval_params(input_function_str, input_params[repr(ginput)])
                
        # adding parameters to outputs
        for goutput in graph.outputs:
            if repr(goutput) in output_params:
                goutput.add_eval_params(output_function_str, output_params[repr(goutput)])
                
        # adding parameters to gates
        for (ggroup, gname) in gate_ids:
            gprams = gate_params[gname]
            for ggate in graph.gates:
                if ggate.gate_id == ggroup:
                    ggate.add_eval_params(hill_response_equation, linear_input_composition, gname, gprams)
                  
        circuit_scores = []  
        for goutput in graph.outputs:
            # NOTE: add funtion to test whether goutput is intermediate or final
            output_name = goutput.name
            output_score = graph.get_score(goutput)
            circuit_scores.append((output_score, output_name))


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
        
        # NOTE: this part needs to be modified, to return the lower-scored output
        return max(circuit_scores)[0]
    
    
    def check_conditions(self, verbose=True):
        if verbose: print()
        if verbose: print_centered('condition checks for valid input')
        
        if verbose: print('\nNETLIST:')
        netlist_valid = False
        if self.rnl is not None:
            netlist_valid = self.rnl.is_valid_netlist()
        if verbose: print(f'isvalid: {netlist_valid}')

        num_ucf_input_sensors = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors'))
        num_ucf_input_structures = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'structures'))
        num_ucf_input_models = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'))
        num_ucf_input_parts = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'parts'))
        num_netlist_inputs = len(self.rnl.inputs) if netlist_valid else 99999
        if verbose: print('\nINPUTS:')
        if verbose: print(f'num IN-SENSORS in {ucfname} in-UCF: {num_ucf_input_sensors}')
        if verbose: print(f'num IN-STRUCTURES in {ucfname} in-UCF: {num_ucf_input_structures}')
        if verbose: print(f'num IN-MODELS in {ucfname} in-UCF: {num_ucf_input_models}')
        if verbose: print(f'num IN-PARTS in {ucfname} in-UCF: {num_ucf_input_parts}')
        if verbose: print(f'num IN-NODES in {vname} netlist: {num_netlist_inputs}')
        inputs_match = (num_ucf_input_sensors == num_ucf_input_models == num_ucf_input_structures == num_ucf_input_parts) and (num_ucf_input_parts >= num_netlist_inputs)
        if verbose: print(('Valid' if inputs_match else 'NOT valid') + ' input match!')
        
        num_ucf_output_sensors = len(self.ucf.query_top_level_collection(self.ucf.UCFout, 'output_devices'))
        num_ucf_output_structures = len(self.ucf.query_top_level_collection(self.ucf.UCFout, 'structures'))
        num_ucf_output_models = len(self.ucf.query_top_level_collection(self.ucf.UCFout, 'models'))
        num_ucf_output_parts = len(self.ucf.query_top_level_collection(self.ucf.UCFout, 'parts'))
        num_netlist_outputs = len(self.rnl.outputs) if netlist_valid else 99999
        if verbose: print('\nOUTPUTS:')
        if verbose: print(f'num OUT-SENSORS in {ucfname} out-UCF: {num_ucf_output_sensors}')
        if verbose: print(f'num OUT-STRUCTURES in {ucfname} out-UCF: {num_ucf_output_structures}')
        if verbose: print(f'num OUT-MODELS in {ucfname} out-UCF: {num_ucf_output_models}')
        if verbose: print(f'num OUT-PARTS in {ucfname} out-UCF: {num_ucf_output_parts}')
        if verbose: print(f'num OUT-NODES in {vname} netlist: {num_netlist_outputs}')
        outputs_match = (num_ucf_output_sensors == num_ucf_output_models == num_ucf_output_parts == num_ucf_output_structures) and (num_ucf_output_parts >= num_netlist_outputs)
        if verbose: print(('Valid' if outputs_match else 'NOT valid') + ' output match!')
        
        numStructs = self.ucf.collection_count['structures']
        numModels = self.ucf.collection_count['models']
        numGates = self.ucf.collection_count['gates']
        numParts = self.ucf.collection_count['parts']
        ucf_gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        G_list = []
        for gate in ucf_gates:
            # G_list.append((gate['name'], gate['gate_type']))
            # NOTE: below assumes that all gates in our UCFs are 'NOR' gates
            G_list.append(gate['group'])
        G_list = list(set(G_list))
        num_groups = len(G_list)
        # numFunctions = len(self.ucf.query_top_level_collection(self.ucf.UCFmain, 'functions'))
        if verbose: print('\nGATES:')
        if verbose: print(f'num PARTS in {ucfname} UCF: {numParts}')
        # if verbose: print(f'(ref only) num FUNCTIONS in {ucfname} UCF: {numFunctions}')
        if verbose: print(f'num STRUCTURES in {ucfname} UCF: {numStructs}')
        if verbose: print(f'num MODELS in {ucfname} UCF: {numModels}')
        if verbose: print(f'num GATES in {ucfname} UCF: {numGates}')
        
        num_gates_availabe = []
        logic_constraints = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'logic_constraints')
        for l in logic_constraints:
            for g in l['available_gates']:
                num_gates_availabe.append(g['max_instances'])
        if verbose: print(f'num GATE USES: {num_gates_availabe}')
        num_netlist_gates = len(self.rnl.gates) if netlist_valid else 99999
        if verbose: print(f'num GATES in {vname} netlist: {num_netlist_gates}')
        gates_match = (numStructs == numModels == numGates) and (numGates >= num_netlist_gates)
        if verbose: print(('Valid' if gates_match else 'NOT valid') + ' intermediate match!')
        
        pass_check = netlist_valid and inputs_match and outputs_match and gates_match
        
        (max_iterations, confirm) = permute_count_helper(num_netlist_inputs, num_netlist_outputs, num_netlist_gates, num_ucf_input_sensors, num_ucf_output_sensors, num_groups) if pass_check else (None, None)
        if verbose: debug_print(f'#{max_iterations} possible permutations for {self.vrlgname}.v+{self.ucfname}')
        if verbose: debug_print(f'#{confirm} permutations of UCF gate groups confirmed.\n', padding=False)
        
        if verbose: print_centered('End of condition checks')
        
        # NOTE: if max_iterations passes a threshold, switch from exhaustive algorithm to simulative algorithm
        threshold = 1000000 # 1 million iterations (which should take around an hour or so)
        # if max_iterations > threshold:
        #     max_iterations = None

        return pass_check, max_iterations
    
if __name__ == '__main__':
    # ucflist = ['Bth1C1G1T1', 'Eco1C1G1T1', 'Eco1C2G2T2', 'Eco2C1G3T1', 'Eco2C1G5T1', 'Eco2C1G6T1', 'SC1C1G1T1']
    # problem_ucfs = ['Eco1C2G2T2', 'Eco2C1G6T1']
    
    # vname = 'and'
    vname = 'and'
    # vname = 'xor'
    # vname = 'priorityDetector'
    # vname = 'chat_3x2'
    # vname = 'g70_boolean'
    # vname = 'g77_boolean'
    # vname = 'g92_boolean'
    
    # (3in, 1out, 7gategroups)
    # ucfname = 'Bth1C1G1T1'
    
    # (4in, 1out, 12gategroups)
    ucfname = 'Eco1C1G1T1'
    
    # (7in, 1out, 6gategroups)
    # ucfname = 'Eco2C1G3T1'
    
    # (7in, 1out, 13gategroups)
    # ucfname = 'Eco2C1G5T1'
    
    # (3in, 2out, 9gategroups)
    # ucfname = 'SC1C1G1T1'
    
    # TODO: source UCF files from CELLO-UCF instead
    inpath = '../../IO/inputs' # (contiains the verilog files, and UCF files)
    outpath = '../../IO/cello_demo' # (any path to a local folder)
    
    Cello3Process = CELLO3(vname, ucfname, inpath, outpath, options={'yosys_choice': 1, 'verbose': True})
    
    # it goes: gates -> models -> structures -> functions -> score -> parts
    # but what about circuit_rules, device_rules, and motif_library (which I think are useless)