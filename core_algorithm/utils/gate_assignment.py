"""
Contains a function that generates the truth table and classes for: representing netlist inputs, outputs, and gates,
assigning gates to the graph, and initializing permutations of gate assignments.

generate_truth_table()
Classes: IO, Input(IO), Output(IO), Gate, AssignGraph, GraphParser
"""

from core_algorithm.utils.ucf_class import *


def generate_truth_table(num_in, num_gates, num_out, in_list, gate_list, out_list):
    """

    :param num_in:
    :param num_gates:
    :param num_out:
    :param in_list:
    :param gate_list:
    :param out_list:
    :return:
    """
    table = []
    for i in range(2 ** num_in):
        row = [(i >> j) & 1 for j in range(num_in - 1, -1, -1)] + ([None] * num_in) + ([None] * num_gates) * 2 + (
            [None] * num_out) * 2
        table.append(row)
    labels = [f'{i.name}_I/O' for i in in_list] + [i.name for i in in_list] + \
             [f'{g.name}_I/O' for g in gate_list] + [g.name for g in gate_list] + \
             [f'{o.name}_I/O' for o in out_list] + [o.name for o in out_list]
    return table, labels


class IO:
    """

    """

    def __init__(self, name, id_):
        self.name = name
        self.id = id_

    def __lt__(self, other):
        if isinstance(other, IO):
            return self.id < other.id
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, IO):
            return self.id == other.id
        return NotImplemented

    def __repr__(self):
        return f'{self.name}'


class Input(IO):
    """

    """

    def __init__(self, name, id_):
        super().__init__(name, id_)
        self.functions = None
        self.resp_func_eq = None
        self.tandem_func_eq = None
        self.params = {}
        self.ymax = None
        self.ymin = None
        # self.states = {'high': 10, 'low': 0.1}
        self.states = {'high': 1, 'low': 0}
        self.out_scores = {'high': -1, 'low': -1}
        self.score_in_use = None
        self.tandem_scores = {'high': -1, 'low': -1}

    def switch_onoff(self, state):
        """

        :param state:
        """
        if int(state) == 0:
            self.score_in_use = 'low'
        else:
            self.score_in_use = 'high'

    def add_eval_params(self, functions, params):
        """

        :param function:
        :param params:
        """
        try:
            self.functions = functions
            self.resp_func_eq = None
            self.tandem_func_eq = None
            self.params = params
            self.ymax = params['ymax']
            self.ymin = params['ymin']
            # self.vars = vars  # TODO: Add proper var/func tracing
            # comment out below two lines to change STATE from 0/1
            # self.states['high'] = self.ymax
            # self.states['low'] = self.ymin
            try:
                self.resp_func_eq = self.functions.get('response_function', '')
                self.resp_func_eq = self.resp_func_eq.replace('$', '')
                self.tandem_func_eq = self.functions.get('tandem_interference_factor', '')
                self.tandem_func_eq = self.tandem_func_eq.replace('$', '')
                self.tandem_func_eq = self.tandem_func_eq.replace('^', '**')
                for p in params.keys():
                    locals()[p] = params[p]
                for (lvl, val) in self.states.items():
                    STATE = val
                    self.out_scores[lvl] = eval(self.resp_func_eq)
                    if self.tandem_func_eq:
                        self.tandem_scores[lvl] = eval(self.tandem_func_eq)
                # print(f'IN - {self.name}: {self.params} -> {self.out_scores} (tandem: {self.tandem_scores})')
            except Exception as e:
                debug_print(f'ERROR calculating input score for {str(self)}, with function {self.resp_func_eq}\n{e}')
        except Exception as e:
            debug_print(f'Error adding evaluation parameters to {str(self)}\n{self.resp_func_eq} | {params}\n{e}')

    def __str__(self):
        if self.resp_func_eq is None:
            return f'input {self.name} {self.id}'
        else:
            return f'input {self.name} {self.id} with ymax: {self.ymax} and ymin: {self.ymin}'


class Output(IO):
    """

    """

    def __init__(self, name, id_):
        super().__init__(name, id_)
        self.function = None
        self.unit_conversion = None
        self.out_score = None
        self.params = {}
        self.IO = None
        self.func_name = None
        self.vars = {}

    def add_eval_params(self, function, params, func_name, vars):
        """

        :param function:
        :param params:
        """
        try:
            self.func_name = func_name
            self.vars = vars
            self.function = function.replace('^', '**')
            if function == 'c * x':
                self.unit_conversion = params['unit_conversion']
            elif 'ymax' in function or 'ymin' in function:  # Usually: Hill response for Comm Molecule
                self.params = params
            else:
                log.cf.error("Cannot identify UCF-in function input parameter")
        except Exception as e:
            debug_print(f'Error adding evaluation parameters to {str(self)}\n{e}\n{function} | {params}')

    def eval_output(self, input_score):
        """

        :param input_score:
        :return:
        """
        x = input_score
        c = self.unit_conversion
        for p in self.params.keys():
            locals()[p] = self.params[p]
        self.out_score = eval(self.function)
        # print(f'OUT - {self.name}: (unit_conv: {self.unit_conversion}, CM params: {self.params}) -> {self.out_score}')
        return self.out_score

    def __str__(self):
        if self.function is None:
            return f'output {self.name} {self.id}'
        else:
            return f'output {self.name} {self.id} with {self.function}: ' \
                   f'{("c = " + str(self.unit_conversion)) if self.unit_conversion else self.params}'


class Gate:
    """
    Used ot represent a gate in a netlist.
    """

    def __init__(self, gate_id, gate_type, inputs, output):
        self.name = gate_id
        self.gate_type = gate_type
        self.inputs = inputs if type(inputs) == list else list(inputs.values())  # each gate can have up to 2 inputs
        self.output = output if type(output) == int else list(output.values())[0]  # each gate can have only 1 output
        self.uid = ','.join(str(i) for i in self.inputs) + '-' + str(self.output)
        self.gate_params = {}
        self.hill_response = None
        self.response_func = None
        self.input_comp = None
        self.tandem_factor_func = None
        self.gate_in_use = None
        self.best_score = None
        self.IO = None
        self.tandem_score = None

    def add_eval_params(self, gate_funcs, g_name, params):
        """

        :param hill_response:
        :param input_composition:
        :param g_name:
        :param params:
        """
        self.response_func = gate_funcs.get('response_function', '')
        self.response_func = self.response_func.replace('^', '**')
        self.input_comp = gate_funcs.get('input_composition', '')
        self.tandem_factor_func = gate_funcs.get('tandem_interference_factor', '')
        self.tandem_factor_func = self.tandem_factor_func.replace('^', '**')

        # if 'response_function' in gate_funcs.keys():
        #     self.response_func = gate_funcs['response_function'].replace('^', '**')
        # else:
        #     log.cf.error("Cannot find gate response_function in UCF; is it named 'response_function'?")
        # if 'input_composition' in gate_funcs.keys():
        #     self.input_comp = gate_funcs['input_composition'].replace('^', '**')
        # else:
        #     log.cf.error("Cannot find gate input_composition function in UCF; is it named 'input_composition'?")
        # if 'tandem_interference_factor' in gate_funcs.keys():
            # Usually: alpha * (K**n + beta * x**n) / (K**n + x**n)
            # self.tandem_factor_func = gate_funcs['tandem_interference_factor'].replace('^', '**')
            # Usually: x1 + (alpha * (K ** n + beta * x ** n) / (K ** n + x ** n)) * x2
            # self.input_comp = self.input_comp.replace('t1', f'({self.tandem_factor_func})')
            # self.tandem_score = eval(self.tandem_factor_func)
            # print(self.tandem_score)
            # TODO: Generalize tandem_inter_factor param
        # self.hill_response = hill_response
        # self.input_comp = input_composition
        self.gate_params[g_name] = params

    def eval_gates(self, in_comp, io_gate_val):
        """
        Returns the best gate assignment from gate group.

        :param in_comp:
        :return:
        """

        if self.response_func is not None and self.input_comp is not None:
            # this means that add_eval_params was already called
            scores = []
            for gname in self.gate_params.keys():
                scores.append(self.eval_gate(gname, in_comp))
                # NOTE: this eval function needs to be modified
            best_score = max(scores)
            # print(best_score)
            # if io_gate_val == 1:
            #     best_score = max(scores)
            # elif io_gate_val == 0:
            #     best_score = min(scores)
            # else:
            #     print('ERROR')
            # TODO: CK: Correct this ^ to replace simplistic max func
            self.best_score = best_score[0]
            self.gate_in_use = best_score[1]
            self.tandem_score = best_score[2]
            return best_score[0], best_score[2]

    def eval_gate(self, gate_name, in_comp):
        """

        :param gate_name:
        :param in_comp:
        :return:
        """
        eval_params = self.gate_params[gate_name]
        for k in eval_params.keys():
            locals()[k] = eval_params[k]
        x = in_comp  # NOTE: UCF has to use 'x' as input_composition in the gate response_function
        result = eval(self.response_func)
        tandem = 0
        if self.tandem_factor_func:
            tandem = eval(self.tandem_factor_func)
        # print(gate_name, result)
        return result, gate_name, tandem

    def __str__(self):
        if self.response_func is not None:
            if self.gate_in_use is not None:
                return f'gate {self.gate_type} {self.name} w/ inputs {self.inputs} and ' \
                       f'output {self.output}, and best_gate = {self.gate_in_use}'
            else:
                return f'gate {self.gate_type} {self.name} w/ inputs {self.inputs} and ' \
                       f'output {self.output}, and individual gates {list(self.gate_params.keys())}'
        else:
            return f'gate {self.gate_type} {self.name} w/ inputs {self.inputs} and output {self.output}'

    def __repr__(self):
        return f'{self.name}'

    def __lt__(self, other):
        if isinstance(other, Gate):
            return self.name < other.name
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, Gate):
            return (self.inputs == other.inputs) and (self.output == other.output)
        return NotImplemented

    def __hash__(self):
        return hash((tuple(self.inputs), self.output))


class AssignGraph:
    """

    """

    def __init__(self, inputs: list = None, outputs: list = None, gates: list = None):
        if gates is None:
            gates = []
        if outputs is None:
            outputs = []
        if inputs is None:
            inputs = []
        self.inputs = inputs
        self.outputs = outputs
        self.gates = gates
        self.in_binary = {}

    def switch_input_ios(self, truth_row, indexes):
        """

        :param truth_row:
        :param indexes:
        """
        # NOTE: this is where the inputs get (unused)
        self.in_binary = dict(zip(indexes, truth_row))

    def find_prev(self, node):
        """

        :param node:
        :return:
        """
        if type(node) == Output:
            node_id = node.id
            # prev node of output has to be a gate
            for g in self.gates:
                if g.output == node_id:
                    return g
            # if it gets here, then something is not right
            return ValueError()
        elif type(node) == Gate:
            prevs = []
            for i_no in node.inputs:
                for g in self.gates:
                    if g.output == i_no:
                        prevs.append(g)
                # for o in self.outputs:  # NOTE: commented out to permit intermediate output nodes
                #     if o.id == i_no:    # TODO: OK that conversion factor of output not part of next node score?
                #         prevs.append(o)
                for i in self.inputs:
                    if i.id == i_no:
                        prevs.append(i)
            if len(prevs) > 1:
                return prevs
            else:
                return prevs[0]
        else:
            # this should not happen also
            return ValueError()

    # NOTE: needs modification
    def get_score(self, node, verbose=False, table_info={}):
        """

        :param node:
        :param verbose:
        :return:
        """

        if type(node) == Input:
            if node.score_in_use is not None:
                # if verbose:
                #     print(f'{node.name} {node.out_scores[node.score_in_use]}')
                return node.out_scores[node.score_in_use], node.tandem_scores[node.score_in_use]
            else:
                log.cf.warning('this should not happen')
                return max(node.out_scores.values()), node.tandem_scores[node.score_in_use]
        elif type(node) == Output:
            input_score = self.get_score(self.find_prev(node), table_info=table_info)[0]
            output_score = node.eval_output(input_score=input_score)
            # if verbose:
            #     print(f'{node.name} {output_score}')
            return output_score, 0
        elif type(node) == Gate:
            if table_info:
                table, labels, r = table_info['table'], table_info['labels'], table_info['r']
                c = labels.index(node.name + '_I/O')
                io_gate_val = table[r][c]
                # print(node.name, io_gate_val)
            if node.gate_type == 'NOT':  # has single input
                input_score = self.get_score(self.find_prev(node), table_info=table_info)[0]
                x = input_score
            elif node.gate_type == 'NOR':  # has two inputs
                scores = [self.get_score(x, table_info=table_info) for x in self.find_prev(node)]
                x1 = scores[0][0]
                x2 = scores[1][0]
                t1 = scores[0][1]
                # TODO: Retrieve tandem score(s)
                eval_params = node.gate_params
                for k in eval_params.values():
                    for r in k:
                        locals()[r] = k[r]
                x = eval(node.input_comp)  # usually x = x1 + x2
            else:
                # there shouldn't be gates other than NOR/NOT
                raise Exception
            # below tries to calculate scores for a gate (the best gate choice in this case)
            gate_score, tandem_score = node.eval_gates(x, io_gate_val)
            # if verbose:
            #     print(f'{node.gate_in_use} {gate_score}')
            return gate_score, tandem_score  # CRIT: Fix tandem scoring...
        else:
            raise Exception

    def __repr__(self):
        return f"Inputs: {self.inputs}, Gates: {self.gates}, Outputs: {self.outputs}"


class GraphParser:
    """
    Used to initialize all permutations of gate assignments from UCF to netlist.
    """

    def __init__(self, inputs, outputs, gates):
        self.inputs = self.load_inputs(inputs)
        self.outputs = self.load_outputs(outputs)
        self.gates = self.load_gates(gates)

    @staticmethod
    def load_inputs(in_data):
        """

        :param in_data:
        :return:
        """
        inputs = []
        for (name, id) in in_data:
            inputs.append(Input(name, id))
        return inputs

    @staticmethod
    def load_outputs(out_data):
        """

        :param out_data:
        :return:
        """
        outputs = []
        for (name, id) in out_data:
            outputs.append(Output(name, id))
        return outputs

    @staticmethod
    def load_gates(gates_data):
        """

        :param gates_data:
        :return:
        """
        gates = []
        for gate_id, gate_info in gates_data.items():
            gate = Gate(gate_id, gate_info["type"], gate_info["inputs"], gate_info["output"])
            gates.append(gate)
        return gates

    def permute_inputs(self, UCFobj: UCF):
        """
        Return the different input combo permutations.
        :param UCFobj:
        :return:
        """
        input_sensors = UCFobj.query_top_level_collection(UCFobj.UCFin, 'input_sensors')
        new_inputs = []
        for (_, edge_no) in self.inputs:
            for sensor in input_sensors:
                sensor_name = sensor['name']
                new_inputs.append((sensor_name, edge_no))
        return new_inputs

    def permute_outputs(self, UCFobj: UCF):
        """
        Return the different output combo permutations.
        :param UCFobj:
        :return:
        """
        output_devices = UCFobj.query_top_level_collection(UCFobj.UCFout, 'output_devices')
        new_outputs = []
        for (_, edge_no) in self.outputs:
            for device in output_devices:
                device_name = device['name']
                new_outputs.append((device_name, edge_no))
        return new_outputs

    def permute_gates(self, UCFobj: UCF):
        """
        return the different gate combo permutations.
        :param UCFobj:
        :return:
        """
        ucf_gates = UCFobj.query_top_level_collection(UCFobj.UCFmain, 'gates')
        new_gates = []
        for g in self.gates:
            for ug in ucf_gates:
                new_gates.append(Gate(ug['name'], ug['gate_type'], g.inputs, g.output))
        uids = list(set([g.uid for g in new_gates]))
        # log.cf.info(uids)
        gate_dict = {id_: [] for id_ in uids}
        for g in new_gates:
            gate_dict[g.uid].append(g)
        return new_gates, gate_dict

    @staticmethod
    def traverse_graph(start_node):
        """
        Traverse the graph and assign gates to each node.
        :param start_node:
        :return:
        """
        return 0  # return 0 exit code

    def __str__(self):
        gates_str = "\n".join(str(gate) for gate in self.gates)
        return f"Inputs: {self.inputs},\n\nOutputs: {self.outputs}\n\nGates:\n{gates_str}"
