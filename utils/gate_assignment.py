"""
Contains a function that generates the truth table and classes for: representing netlist inputs, outputs, and gates,
assigning gates to the graph, and initializing permutations of gate assignments.

generate_truth_table()
Classes: IO, Input(IO), Output(IO), Gate, AssignGraph, GraphParser
"""

# import networkx as nx
# import matplotlib.pyplot as plt
from ucf_class import *


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
             [f'{g.gate_id}_I/O' for g in gate_list] + [g.gate_id for g in gate_list] + \
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
        self.function = None
        self.params = {}
        self.ymax = None
        self.ymin = None
        self.states = {'high': 1, 'low': 0}
        self.out_scores = {'high': -1, 'low': -1}
        self.score_in_use = None

    def switch_onoff(self, state):
        """

        :param state:
        """
        if int(state) == 0:
            self.score_in_use = 'low'
        else:
            self.score_in_use = 'high'

    def add_eval_params(self, function, params):
        """

        :param function:
        :param params:
        """
        try:
            self.function = function
            self.params = params
            self.ymax = params['ymax']
            self.ymin = params['ymin']
            # comment out below two lines to change STATE from 0/1
            # self.states['high'] = self.ymax
            # self.states['low'] = self.ymin
            try:
                for p in params.keys():
                    locals()[p] = params[p]
                for (lvl, val) in self.states.items():
                    STATE = val
                    self.out_scores[lvl] = eval(self.function)
            except Exception as e:
                debug_print(f'ERROR calculating input score for {str(self)}, with function {self.function}\n{e}')
        except Exception as e:
            debug_print(f'Error adding evaluation parameters to {str(self)}\n{function} | {params}\n{e}')

    def __str__(self):
        if self.function is None:
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
        self.params = []
        self.IO = None

    def add_eval_params(self, function, params):
        """

        :param function:
        :param params:
        """
        try:
            self.function = function
            self.unit_conversion = params['unit_conversion']
        except Exception as e:
            debug_print(f'Error adding evaluation parameters to {str(self)}\n{e}\n{function} | {params}')

    def eval_output(self, input_score):
        """

        :param input_score:
        :return:
        """
        x = input_score
        c = self.unit_conversion
        score = eval(self.function)
        self.out_score = score
        return score

    def __str__(self):
        if self.function is None:
            return f'output {self.name} {self.id}'
        else:
            return f'output {self.name} {self.id} with c: {self.unit_conversion}'


class Gate:
    """
    Used ot represent a gate in a netlist.
    """
    def __init__(self, gate_id, gate_type, inputs, output):
        self.gate_id = gate_id
        self.gate_type = gate_type
        self.inputs = inputs if type(inputs) == list else list(inputs.values())  # each gate can have up to 2 inputs
        self.output = output if type(output) == int else list(output.values())[0]  # each gate can have only 1 output
        self.uid = ','.join(str(i) for i in self.inputs) + '-' + str(self.output)
        self.gate_params = {}
        self.hill_response = None
        self.input_composition = None
        self.gate_in_use = None
        self.best_score = None
        self.IO = None

    def add_eval_params(self, hill_response, input_composition, g_name, params):
        """

        :param hill_response:
        :param input_composition:
        :param g_name:
        :param params:
        """
        self.hill_response = hill_response
        self.input_composition = input_composition
        self.gate_params[g_name] = params

    def eval_gates(self, in_comp):
        """
        Returns the best gate assignment from gate group.

        :param in_comp:
        :return:
        """

        if self.hill_response is not None and self.input_composition is not None:
            # this means that add_eval_params was already called
            gate_scores = []
            for gname in self.gate_params.keys():
                gate_scores.append(self.eval_gate(gname, in_comp))
                # NOTE: this eval function needs to be modified
            best_score = max(gate_scores)
            self.gate_in_use = best_score[1]
            self.best_score = best_score[0]
            return best_score[0]

    def eval_gate(self, gate_name, in_comp):
        """

        :param gate_name:
        :param in_comp:
        :return:
        """
        eval_params = self.gate_params[gate_name]
        for k in eval_params.keys():
            locals()[k] = eval_params[k]
        x = in_comp  # UCF has to use 'x' as input_composition in the gate response_function
        return eval(self.hill_response), gate_name

    def __str__(self):
        if self.hill_response is not None:
            if self.gate_in_use is not None:
                return f'gate {self.gate_type} {self.gate_id} w/ inputs {self.inputs} and ' \
                       f'output {self.output}, and best_gate = {self.gate_in_use}'
            else:
                return f'gate {self.gate_type} {self.gate_id} w/ inputs {self.inputs} and ' \
                       f'output {self.output}, and individual gates {list(self.gate_params.keys())}'
        else:
            return f'gate {self.gate_type} {self.gate_id} w/ inputs {self.inputs} and output {self.output}'

    def __repr__(self):
        return f'{self.gate_id}'

    def __lt__(self, other):
        if isinstance(other, Gate):
            return self.gate_id < other.gate_id
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
                for o in self.outputs:
                    if o.id == i_no:
                        prevs.append(o)
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
    def get_score(self, node, verbose=False):
        """

        :param node:
        :param verbose:
        :return:
        """
        if type(node) == Input:
            if node.score_in_use is not None:
                if verbose:
                    debug_print(f'{node.name} {node.out_scores[node.score_in_use]}', padding=False)
                return node.out_scores[node.score_in_use]
            else:
                print('this should not happen')
                return max(node.out_scores.values())
        elif type(node) == Output:
            input_score = self.get_score(self.find_prev(node))
            output_score = node.eval_output(input_score=input_score)
            if verbose:
                debug_print(f'{node.name} {output_score}', padding=False)
            return output_score
        elif type(node) == Gate:
            if node.gate_type == 'NOT':
                input_score = self.get_score(self.find_prev(node))
                x = input_score
            elif node.gate_type == 'NOR':
                input_scores = [self.get_score(x) for x in self.find_prev(node)]
                x1 = input_scores[0]
                x2 = input_scores[1]
                x = eval(node.input_composition)  # basically x = x1 + x2
            else:
                # there shouldn't be gates other than NOR/NOT
                raise Exception
            # below tries to calculate scores for a gate (the best gate choice in this case)
            gate_score = node.eval_gates(x)
            if verbose:
                debug_print(f'{node.gate_in_use} {gate_score}', padding=False)
            return gate_score
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
        # print(uids)
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
