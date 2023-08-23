"""
Classes used to generate the Eugene file. (Suggest looking at example_eugene_objects file...)

Dataclasses: EugeneStruct, EugeneSequence, EugeneCassette
Class: EugeneObject: generate_eugene_structs(), generate_eugene_cassettes(), write_eugene()
"""

import os
from dataclasses import dataclass, field
from cello_helpers import debug_print
import log
import dna_design

# from typing import Annotated, Type, TypeDict


@dataclass
class EugeneStruct:
    """
    Corresponds to all the inputs, gates, and outputs in the circuit.
    Info used to print various data to file and generate additional helper objects.

    Attributes: type, gates_name, gates_group, gates_model, gates_struct, struct_cassettes, inputs, outputs
    """

    type: str = ""
    """'input', 'gate', or 'output'"""
    gates_name: str = ""
    """name of node (from 'gates' block in UCF, as with group, model, and structure)"""
    gates_group: str = ""
    """from 'gates' block in UCF"""
    gates_model: str = ""
    """from 'gates' block in UCF"""
    gates_struct: str = ""
    """from 'gates' block in UCF"""
    struct_cassettes: list[str, str, int, list[str]] = field(default_factory=list[str, str, int, list[str]])
    """[ [ 1st name, cassette name, num of ins, [components] ] , etc.]"""
    inputs: list[str] = field(default_factory=list[str])
    """gates_name of input nodes"""
    outputs: str = ""  # TODO: Change to support mult outputs
    """gates_name of output nodes"""
    color: str = ""
    """color from 'gates' block in UCF; used in SBOL diagram"""


@dataclass
class EugeneSequence:
    """
    Corresponds to dna sequences from the input, UCF, and output 'parts' (along with associated names and types).
    Prints to second block in eugene file with form:

    <type> <name>(.SEQUENCE("<dnasequence>"));

    Attributes: parts_type, parts_name, parts_sequence, dev_rules, cir_rules, color
    """

    parts_type: str = ""
    """type such as 'cds', 'promoter', 'terminator', etc. from UCF parts block"""
    parts_name: str = ""
    """name in UCF parts block, corresponds to 'outputs'/'components' from structures block"""
    parts_sequence: str = ""
    """dna sequence from UCF parts block"""
    dev_rules: list[str] = field(default_factory=list[str])  # TODO: can probably remove this; captured better below...
    """all device rules for this part (that are relevant to this circuit)"""
    cir_rules: list[str] = field(default_factory=list[str])
    """circuit rules associated with each part (mostly for scars)"""
    color: str = ""
    """"""


@dataclass
class EugeneCassette:
    """
    Corresponds to a cassette block in the eugene output file.
    Prints to 4th set of blocks in eugene file with form:

    cassette <cassette name>();  # unless an output...
    Device <variant name>(<component>, [etc.]);

    Once established, this set of objects are iterated throughout the eugene file.

    Attributes: struct_var_name, struct_cas_name, type, inputs, comps, outputs, color, dev_rules, cir_rules
    """

    struct_var_name: str = ""
    """name ending in letter to indicate structures variant (from structures block)"""
    struct_cas_name: str = ""
    """name ending in cassette (from structures block)"""
    type: str = ""
    """'input', 'gate', or 'output'"""
    inputs: list[str] = field(default_factory=list[str])
    """'outputs' (from input node's UCF structures block) name for each input node"""
    comps: list[str] = field(default_factory=list[str])
    """'components' (from main UCF 'structures' block)"""
    outputs: str = ""  # TODO: Change to support mult outputs
    """same 'outputs' as the EugeneStruct object"""
    color: str = ""
    """color from structs dict (i.e. from 'gates' block in UCF); used in SBOL diagram"""
    dev_rules: list[str] = field(default_factory=list[str])
    """all device rules that include all of the inputs to this cassette"""
    cir_rules: list[str] = field(default_factory=list[str])  # TODO: Account for other types of circuits not ALL_FORWARD
    """all circuit rules for this cassette (that are relevant to this circuit)"""


class EugeneObject:
    """
    Contains all info needed to construct the eugene file. Generated once a circuit design has been finalized.
    Extracts info from the UCF files into data objects, then iterates over data to print to eugene file.
    """

    def __init__(self, ucf, in_map, gate_map, out_map, best_graphs):
        self.ucf = ucf
        self.in_map = in_map
        self.gate_map = gate_map
        self.out_map = out_map
        self.best_graphs = best_graphs

        # NOTE: first term corresponds to the UCF block from which the data were taken
        self.structs_dict: dict[str, EugeneStruct] = {}
        '''in/gate/out name: EugeneStruct [See 'example_eugene_objects' for example data...]'''
        self.parts_seq_dict: dict[str, EugeneSequence] = {}
        '''part name: EugeneSequence [See 'example_eugene_objects' for example data...]'''
        self.structs_cas_dict: dict[str, EugeneCassette] = {}
        '''device var name: EugeneCassette [See 'example_eugene_objects' for example data...]'''

        self.parts_types: [str] = ['spacer', 'scar']  # always present; *all* associated parts used  # and terminator?
        self.genlocs_fenceposts: dict[[str]] = {}  # usually 'L1', 'L2', etc.
        self.device_rules: list[str] = []
        self.circuit_rules: list[str] = []

    # NOTE: 1. GENERATE EUGENE STRUCTS FROM CIRCUIT DESIGN #############################################################
    def generate_eugene_structs(self) -> bool:
        """
        Generates dict of EugeneStruct objects based on data in the UCF, input, and output files for the final circuit.

        :return: bool
        """

        # Enumerate edges from circuit parameters
        edges = {}  # key: to; val: from
        for rnl_gate, g_gate in self.gate_map:
            edges[g_gate.gate_in_use] = []
        for rnl_out, g_out in self.out_map:
            edges[g_out.name] = []
        for rnl_gate, g_gate in self.gate_map:
            for g_in in g_gate.inputs:
                for rnl_input, g_input in self.in_map:
                    if rnl_input[1] == g_in:
                        edges[g_gate.gate_in_use].append(g_input.name)  # TODO: Still need to merge multi-inputs?
                for rnl_gate2, g_gate2 in self.gate_map:
                    if g_gate2.output == g_in:
                        edges[g_gate.gate_in_use].append(g_gate2.gate_in_use)
        for rnl_output, g_output in self.out_map:  # TODO: Can assume an input is not directly connected to output?
            for rnl_gate, g_gate in self.gate_map:
                if g_gate.output == rnl_output[1]:
                    edges[g_output.name].append(g_gate.gate_in_use)

        # Debugging info...
        # debug_print('BASIC CIRCUIT INFO:')
        # log.cf.info(f'self.best_graphs: {self.best_graphs}')
        # log.cf.info(f'Mappings: {self.in_map}, {self.gate_map}, {self.out_map}')
        # log.cf.info(f'Connections: {edges}\n')

        # Add names and inputs to dict
        for key, val in edges.items():
            self.structs_dict[key] = EugeneStruct(gates_name=key)
            self.structs_dict[key].inputs = val
            for edge in val:
                if edge not in self.structs_dict.keys():
                    self.structs_dict[edge] = EugeneStruct(gates_name=edge)

        # Add gate group names to dict
        for id_, g in self.gate_map:
            self.structs_dict[g.gate_in_use].gates_group = g.gate_id

        # Add type, model, structure, outputs to the Inputs in dict
        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors')
        i_structures = self.ucf.query_top_level_collection(self.ucf.UCFin, 'structures')
        for k, v in self.structs_dict.items():
            for in_sensor in in_sensors:
                if k == in_sensor['name']:
                    v.type = 'input'
                    v.gates_model = in_sensor['model']
                    v.gates_struct = in_sensor['structure']
                    for structure in i_structures:
                        if v.gates_struct == structure['name']:
                            v.outputs = structure['outputs']

        # Add type, model, structure, outputs, and cassettes/components to the Gates in dict
        gate_devices = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        g_structures = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'structures')
        for k, v in self.structs_dict.items():
            for gate_device in gate_devices:
                if k == gate_device['name']:
                    v.type = 'gate'
                    v.gates_model = gate_device['model']
                    v.gates_struct = gate_device['structure']
                    v.color = gate_device['color']
                    for structure in g_structures:
                        if v.gates_struct == structure['name']:
                            v.outputs = structure['outputs']
                            cassettes = []
                            for d in structure['devices']:
                                if d['name'].endswith('_cassette'):
                                    components = []
                                    for c in d['components']:
                                        components.append(c)
                                    for c in cassettes:
                                        if c[1] == d['name']:
                                            c[3] = components
                                else:  # TODO: improve robustness
                                    cassette = ["", "", 0, []]  # [~'X_a' name, 'X_cassette' name, #in cnt,[components]]
                                    for c in d['components']:
                                        if c.startswith('#in'):
                                            cassette[2] += 1
                                        elif c.endswith('_cassette'):
                                            cassette[1] = c
                                        else:
                                            print('ERROR: UNRECOGNIZED COMPONENT IN DEVICE IN STRUCTURES IN UCF')
                                    if cassette[2] > 0:
                                        cassette[0] = d['name']
                                        cassettes.append(cassette)
                            v.struct_cassettes = cassettes

        # Add type, model, structure, and cassettes/components to the Outputs in dict
        out_devices = self.ucf.query_top_level_collection(self.ucf.UCFout, 'output_devices')
        o_structures = self.ucf.query_top_level_collection(self.ucf.UCFout, 'structures')
        for k, v in self.structs_dict.items():
            for out_device in out_devices:
                if k == out_device['name']:
                    v.type = 'output'
                    v.gates_model = out_device['model']
                    v.gates_struct = out_device['structure']
                    for structure in o_structures:
                        if v.gates_struct == structure['name']:
                            cassettes = []
                            for d in structure['devices']:
                                cassette = ["", "", 0, []]  # [~'X_a' name, 'X_cassette' name, #in cnt, [components]]
                                for c in d['components']:
                                    if c.startswith('#in'):
                                        cassette[2] += 1
                                    elif '_cassette' in c:
                                        cassette[1] = c
                                        if c not in cassette[3]:
                                            cassette[3].append(c)
                                if cassette[2] > 0:
                                    cassette[0] = d['name']
                                    cassettes.append(cassette)
                            v.struct_cassettes = cassettes
        return True

    # NOTE: 2. GENERATE EUGENE CASSETTES FROM EUGENE STRUCTS ###########################################################
    def generate_eugene_cassettes(self) -> bool:
        """
        Generates dict of EugeneCassettes used for Eugene file, DNA design, and other files.

        :return: bool: True
        """

        # Get PartTypes and Sequences
        # TODO: Why include all terminators and all scars even if corresponding parts not in the circuit?
        # TODO: Why does SC1 have no terminators?
        ins, mains, outs = [], [], []
        # From UCFin:   'structures' name > 'outputs' name > 'parts' type (probably 'promoter')
        # From UCFmain: 'structures' name > 'outputs' name and cassette 'components' names > 'parts' type (e.g. cds)
        # From UCFout:  'structures' name > 'components' names > 'parts' type (probably 'cassette')
        # Also include: 'scar' and 'terminator' (*all* of these parts will be included in Eugene) as well as 'spacer'
        for v in self.structs_dict.values():
            if v.type == 'input':
                ins.extend(v.outputs)
            if v.type == 'gate':
                for c in v.struct_cassettes:
                    mains.extend(c[3])
                mains.extend(v.outputs)
            if v.type == 'output':
                for c in v.struct_cassettes:
                    outs.extend(c[3])
                outs.extend(v.outputs)
        in_parts = self.ucf.query_top_level_collection(self.ucf.UCFin, 'parts')
        for in_part in in_parts:
            p = in_part['name']
            t = in_part['type']
            if p in ins or t in ['scar']:
                if t not in self.parts_types:
                    self.parts_types.append(t)
                self.parts_seq_dict[p] = EugeneSequence(t, p, in_part['dnasequence'], ['ALL_FORWARD'], [])
        main_parts = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'parts')
        for main_part in main_parts:
            p = main_part['name']
            t = main_part['type']
            if p in mains or t in ['scar']:
                if t not in self.parts_types:
                    self.parts_types.append(t)
                self.parts_seq_dict[p] = EugeneSequence(t, p, main_part['dnasequence'], ['ALL_FORWARD'], [])
        out_parts = self.ucf.query_top_level_collection(self.ucf.UCFout, 'parts')
        for out_part in out_parts:
            p = out_part['name']
            t = out_part['type']
            if p in outs or t in ['scar']:
                if t not in self.parts_types:
                    self.parts_types.append(t)
                self.parts_seq_dict[p] = EugeneSequence(t, p, out_part['dnasequence'], ['ALL_FORWARD'], [])

        # Get Cassettes/Devices
        # Need to cover all netlist Inputs; start with 1st cassette, use all its inputs; to next cassette as needed
        # Source each input from the 'outputs' parameter of the associated input's 'structures' block
        # e.g. and+Bth on the 2-input NOR should specify *2* cassette blocks b/c each only permits one #in
        for eu in self.structs_dict.values():
            if eu.type in ['gate', 'output']:
                input_ = 0
                for c in eu.struct_cassettes:
                    if input_ < len(eu.inputs):
                        self.structs_cas_dict[c[0]] = EugeneCassette(struct_var_name=c[0],
                                                                     struct_cas_name=c[1],
                                                                     type=eu.type,
                                                                     inputs=[],
                                                                     comps=list(c[3]),
                                                                     outputs=eu.outputs,
                                                                     color=eu.color,
                                                                     dev_rules=[],
                                                                     cir_rules=[])
                        for i in range(int(c[2])):
                            if input_ < len(eu.inputs):
                                output = self.structs_dict[eu.inputs[input_]].outputs[0]  # TODO: Only ever 1 'outputs'?
                                input_ += 1
                                self.structs_cas_dict[c[0]].inputs.append(output)

        return True

    # NOTE: 3. GENERATE ADDITIONAL EUGENE OBJECTS ######################################################################
    def generate_eugene_helpers(self) -> (dict, dict, dict, dict[str], dict[str], dict[[str]]):
        """
        Generate dicts of landing_pads/fenceposts/genetic_locations, as well as device_rules and circuit_rules.

        :return:
        """

        def extract_rules(rule_sets, func_type = 'AND') -> list[str]:  # FIXME: UCF5/6 have rules w/ non-extant devices?
            """
            Recursively extract all rules from circuit or device ruleset and returns as a flat list of rules.
            :param rule_sets: List/dict of rules from 'device_rules' or 'circuit_rules' in UCFs
            :return: list[str]: Flat list of rules
            """
            flat_rules = []
            if func_type == 'OR':
                rule_sets = rule_sets[0]  # FIXME: Traverse all OR branches
            if type(rule_sets) == list:
                for rule_set in rule_sets:
                    flat_rules.extend(extract_rules(rule_set))
                return flat_rules
            elif type(rule_sets) == dict:
                if 'function' not in rule_sets.keys() or rule_sets['function'] == 'AND':
                    flat_rules.extend(extract_rules(rule_sets['rules']))
                else:
                    flat_rules.extend(extract_rules(rule_sets['rules'], 'OR'))
            elif type(rule_sets) == str:  # i.e. a rule, at deepest layer
                flat_rules = [rule_sets]
            else:
                log.cf.error('rule_set type is unrecognized; cannot parse or flatten rule_sets.')
            return flat_rules

        # NOTE: Only comprehensive for our default set of UCFs
        rules_keywords = ['NOT', 'EQUALS',
                          'NEXTTO', 'CONTAINS',
                          'STARTSWITH', 'ENDSWITH',
                          'BEFORE', 'AFTER',
                          'ALL_FORWARD']

        # Get Fenceposts/Genetic Locations
        genetic_locations = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'genetic_locations')[0]
        locations = genetic_locations['locations']
        for location in locations:
            self.genlocs_fenceposts[location['symbol']] = []

        # Includes parts, cassettes, and fenceposts, any of which could appear in the rule sets
        all_things = list(self.parts_seq_dict.keys()) + \
                     list(self.structs_cas_dict.keys()) + \
                     list(self.genlocs_fenceposts.keys())

        # Get Device Rules
        device_rules = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'device_rules')[0]
        self.device_rules = extract_rules(device_rules)
        device_rules = []
        for r in self.device_rules:
            # if r != 'ALL_FORWARD':
            operands = [word for word in r.split() if word not in rules_keywords]
            if all([1 if o in all_things else 0 for o in operands]):
                for o in operands:
                    if r not in device_rules:
                        device_rules.append(r)
                    self.parts_seq_dict[o].dev_rules.append(r)
            for device, cassette in self.structs_cas_dict.items():
                if all([1 if o in cassette.inputs else 0 for o in operands]):  # TODO: only check inputs?
                    if r not in device_rules:
                        device_rules.append(r)
                    cassette.dev_rules.append(r)
        self.device_rules = device_rules

        # Get Circuit Rules  # FIXME: Needs to be extended for more complex rule layout (e.g. Eco5/6)
        circuit_rules = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'circuit_rules')[0]
        self.circuit_rules = extract_rules(circuit_rules)
        # print('FLATTENED RULES!: ', self.circuit_rules)
        circuit_rules = []
        for r in self.circuit_rules:
            # if r != 'ALL_FORWARD':
            operands = [word for word in r.split() if word not in rules_keywords and not word.startswith('[')]
            if len(operands) == 0:
                if r not in circuit_rules:
                    circuit_rules.append(r)
            elif all([1 if o in all_things else 0 for o in operands]):
                for o in operands:
                    if o in self.structs_cas_dict.keys():
                        if r not in circuit_rules:
                            circuit_rules.append(r)
                        # self.structs_cas_dict[o].cir_rules.append(r)
                    if o in self.parts_seq_dict.keys():
                        if r not in circuit_rules:
                            circuit_rules.append(r)
                        # self.parts_seq_dict[o].cir_rules.append(r)
                    if o in self.genlocs_fenceposts.keys():
                        if r not in circuit_rules:
                            circuit_rules.append(r)
                        # self.genlocs_fenceposts[o].append(r)
        self.circuit_rules = circuit_rules

        # Debugging info...
        # debug_print('EUGENE OBJECTS:')
        # log.cf.info(f'\nself.structs_dict:\n{self.structs_dict}')
        # log.cf.info(f'\nself.parts_seq_dict:\n{self.parts_seq_dict}')
        # log.cf.info(f'\nself.structs_cas_dict:\n{self.structs_cas_dict}')
        # log.cf.info(f'\nself.device_rules:\n{self.device_rules}')
        # log.cf.info(f'\nself.circuit_rules:\n{self.circuit_rules}')
        # log.cf.info(f'\nself.genlocs_fenceposts:\n{self.genlocs_fenceposts}\n')

        return self.structs_dict, self.structs_cas_dict, self.parts_seq_dict, self.device_rules, self.circuit_rules, \
               self.genlocs_fenceposts

    # NOTE: 4. CREATE, WRITE, AND CLOSE THE EUGENE FILE ################################################################
    def write_eugene(self, filepath: str) -> bool:
        """
        Creates the eugene file at filepath, uses previously created objects to write to the file, then closes it.

        :param: filepath: str
        :return: bool
        """

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as eug:

            # PartTypes
            for type_ in self.parts_types:
                eug.write(f'PartType {type_};\n')
            eug.write('\n')

            # Sequences
            for s in self.parts_seq_dict.values():
                eug.write(f"{s.parts_type} {s.parts_name}(.SEQUENCE(\"{s.parts_sequence}\"));\n")
            eug.write('\n')

            # Fenceposts/Genetic Locations
            eug.write('PartType fencepost;\n')
            for fencepost in self.genlocs_fenceposts:
                eug.write(f"fencepost {fencepost}();\n")
            eug.write('\n')

            # Cassettes/Devices
            for c in self.structs_cas_dict.values():
                if c.type == 'gate':
                    eug.write(f"cassette {c.struct_cas_name}();\n")
                eug.write(f"Device {c.struct_var_name}(\n")
                sep = ""
                for input_ in c.inputs:
                    eug.write(f"{sep}    {input_}")
                    if not sep:
                        sep = ",\n"
                eug.write(f',\n    {c.struct_cas_name}\n);\n\n')
            eug.write('\n')

            # Device Rules
            for device, cassette in self.structs_cas_dict.items():
                eug.write(f'Rule {device}Rule0( ON {device}:\n')  # TODO: Always 'Rule0'?  Always ON?
                sep = ""
                # for comp in cassette.inputs:    # NOTE: multiple ALL_FORWARD if multiple inputs...
                #     for rule in self.parts_seq_dict[comp].dev_rules:
                for rule in cassette.dev_rules:
                    eug.write(f'{sep}    {rule}')
                    if not sep:
                        sep = " AND\n"
                eug.write('\n);\n\n')
            eug.write('\n')

            # Product Mappings
            for device in self.structs_cas_dict.keys():  # TODO: Are these always identical 1 to 1 mappings?
                eug.write(f"{device}_devices = product({device});\n")
            eug.write("\n")

            # Devices
            for device in self.structs_cas_dict.keys():  # TODO: Are these always just a replication of cassette blocks?
                eug.write(f"Device {device}Device();\n")
            eug.write("\nDevice circuit();\n\n")

            # Circuit Rules
            eug.write('Rule CircuitRule0( ON circuit:\n')  # TODO: Always 'Rule0'?  Always ON?
            for device in self.structs_cas_dict.keys():
                eug.write(f'    CONTAINS {device} AND\n')
            sep = ""
            # for device in self.structs_cas_dict.keys():
            #     for rule in self.structs_cas_dict[device].cir_rules:
            for rule in self.circuit_rules:  # TODO: Add 'Device' after each device name/operand in each rule...
                # FIXME: extra outputs don't have rules! (and those extra outputs may be selected by the annealing)
                # NOTE: I really think this should be fixed at the UCF level, not the program level
                eug.write(f'{sep}    {rule}')
                if not sep:
                    sep = " AND\n"
            eug.write('\n);\nArray allResults;\n\n')

            # Device Iter Loops
            device_iters_dict = {}  # Used in next block
            i = 1
            for device in self.structs_cas_dict.keys():
                eug.write(f"for(num i{i} = 0; i{i} < sizeof({device}_devices); i{i} = i{i} + 1) {{}} \n")
                device_iters_dict[device] = i
                i += 1
            eug.write('\n')

            # Device Iter Assignments
            for device, iter_ in device_iters_dict.items():
                eug.write(f"{device}Device = {device}_devices[i{iter_}];\n")
            eug.write('\n')

            # Device Circuit
            eug.write('Device circuit(\n')
            for device in self.structs_cas_dict.keys():
                eug.write(f"    {device}Device,\n")
            sep = ""
            for fencepost in self.genlocs_fenceposts:
                eug.write(f'{sep}    {fencepost}')
                if not sep:
                    sep = ",\n"
            eug.write('\n);\n\n')

            # Closing...
            eug.write("\nresult = permute(circuit);\n\nallResults = allResults + result;\n\n")  # TODO: Static?
            eug.write('}\n' * len(self.structs_cas_dict))

            eug.close()

        return True
