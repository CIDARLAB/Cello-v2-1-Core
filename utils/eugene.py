"""
Classes used to generate the eugene file.
"""

import os
from dataclasses import dataclass, field
# from typing import Annotated, Type, TypeDict


@dataclass
class EugeneDevice:
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
    outputs: str = ""
    """gates_name of output nodes"""


@dataclass
class EugeneSequence:
    """
    Corresponds to dna sequences from the input, UCF, and output 'parts' (along with associated names and types).
    Prints to second block in eugene file with form:

    <type> <name>(.SEQUENCE("<dnasequence>"));

    Attributes: parts_type, parts_name, parts_sequence
    """
    parts_type: str = ""
    """type such as 'cds', 'promoter', 'terminator', etc. from UCF parts block"""
    parts_name: str = ""
    """name in UCF parts block, corresponds to 'outputs'/'components' from structures block"""
    parts_sequence: str = ""
    """dna sequence from UCF parts block"""


@dataclass
class EugeneCassette:
    """
    Corresponds to a cassette block in the eugene output file.
    Prints to 4th set of blocks in eugene file with form:

    cassette <cassette name>();  # unless an output...
    Device <variant name>(<component>, [etc.]);

    Once established, this set of objects are iterated throughout the eugene file.

    Attributes: struct_var_name, struct_cas_name, type, inputs
    """
    struct_var_name: str = ""
    """name ending in letter to indicate structures variant (from structures block)"""
    struct_cas_name: str = ""
    """name ending in cassette (from structures block)"""
    type: str = ""
    """'input', 'gate', or 'output'"""
    inputs: list[str] = field(default_factory=list[str])
    """'outputs' (from input node's UCF structures block) name for each input node"""


class EugeneObject:
    """
    Contains all info needed to construct the eugene file. Generated once a circuit design has been finalized.
    Extracts info from the UCF files into data objects, then iterates over data to print to eugene file.
    """

    def __init__(self, ucf, in_map, gate_map, out_map, filepath, best_graphs):
        self.ucf = ucf
        self.in_map = in_map
        self.gate_map = gate_map
        self.out_map = out_map
        self.filepath = filepath
        self.best_graphs = best_graphs

        self.devices_dict: dict[str, {}] = {}  # 'in/gate/out name: EugeneDevice
        self.parts_seq_dict: dict[str, {}] = {}  # part name: EugeneSequence
        self.structs_cas_dict: dict[str, {}] = {}  # device var name: EugeneCassette

        self.parts_types: [str] = ['terminator', 'spacer', 'scar']  # always present; *all* associated parts used
        self.genlocs_fenceposts: [str] = []  # usually 'L1', 'L2', etc.
        self.dev_rules_operands: dict[str, [str]] = {}  # [rule, [operands]]
        self.cir_rules_operands: dict[str, [str]] = {}  # [rule, [operands]]

    # 1. GENERATE CORE EUGENE OBJECTS ##################################################################################
    def generate_eugene_device(self):
        """
        Generates dict of EugeneDevices objects based on data in the UCF, input, and output files for the final circuit.
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
        print('BASIC CIRCUIT INFO:')
        print(f'{self.best_graphs}')
        print(f'Mappings: {self.in_map}, {self.gate_map}, {self.out_map}')
        print(f'Connections: {edges}\n')

        # Add names and inputs to dict
        for key, val in edges.items():
            self.devices_dict[key] = EugeneDevice(gates_name=key)
            self.devices_dict[key].inputs = val
            for edge in val:
                if edge not in self.devices_dict.keys():
                    self.devices_dict[edge] = EugeneDevice(gates_name=edge)

        # Add gate group names to dict
        for id_, g in self.gate_map:
            self.devices_dict[g.gate_in_use].group = g.gate_id  # Only use a subset according to range(len(g.inputs))

        # Add type, model, structure, outputs to the Inputs in dict
        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors')
        i_structures = self.ucf.query_top_level_collection(self.ucf.UCFin, 'structures')
        for k, v in self.devices_dict.items():
            for in_sensor in in_sensors:
                if k == in_sensor['name']:
                    v.type = 'input'
                    v.model = in_sensor['model']
                    v.structure = in_sensor['structure']
                    for structure in i_structures:
                        if v.structure == structure['name']:
                            v.outputs = structure['outputs']

        # Add type, model, structure, outputs, and cassettes/components to the Gates in dict
        gate_devices = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        g_structures = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'structures')
        for k, v in self.devices_dict.items():
            for gate_device in gate_devices:
                if k == gate_device['name']:
                    v.type = 'gate'
                    v.model = gate_device['model']
                    v.structure = gate_device['structure']
                    for structure in g_structures:
                        if v.structure == structure['name']:
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
                                    cassette = ["", "", 0,
                                                []]  # [~'X_a' name, 'X_cassette' name, #in cnt, [components]]
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
                            v.cassettes = cassettes

        # Add type, model, structure, and cassettes/components to the Outputs in dict
        out_devices = self.ucf.query_top_level_collection(self.ucf.UCFout, 'output_devices')
        o_structures = self.ucf.query_top_level_collection(self.ucf.UCFout, 'structures')
        for k, v in self.devices_dict.items():
            for out_device in out_devices:
                if k == out_device['name']:
                    v.type = 'output'
                    v.model = out_device['model']
                    v.structure = out_device['structure']
                    for structure in o_structures:
                        if v.structure == structure['name']:
                            cassettes = []
                            for d in structure['devices']:
                                cassette = ["", "", 0, []]  # [~'X_a' name, 'X_cassette' name, #in cnt, [components]]
                                for c in d['components']:
                                    if c.startswith('#in'):
                                        cassette[2] += 1
                                    elif c.endswith('_cassette'):
                                        cassette[1] = c
                                        if c not in cassette[3]:
                                            cassette[3].append(c)
                                if cassette[2] > 0:
                                    cassette[0] = d['name']
                                    cassettes.append(cassette)
                            v.cassettes = cassettes
        return True

    # 2. GENERATE ADDITIONAL EUGENE OBJECTS ############################################################################
    def generate_eugene_helpers(self):
        """
        Generates some additional objects to help with writing the eugene file.
        :return: bool
        """
        # Get PartTypes and Sequences
        # TODO: Why include all terminators and all scars even if corresponding parts not in the circuit?
        ins, mains, outs = [], [], []
        # From UCFin:   'structures' name > 'outputs' name > 'parts' type (probably 'promoter')
        # From UCFmain: 'structures' name > 'outputs' name and cassette 'components' names > 'parts' type (e.g. cds)
        # From UCFout:  'structures' name > 'components' names > 'parts' type (probably 'cassette')
        # Also include: 'scar' and 'terminator' (*all* of these parts will be included below) as well as 'spacer'
        for v in self.devices_dict.values():
            if v.type == 'input':
                ins.extend(v.outputs)
            if v.type == 'gate':
                for c in v.cassettes:
                    mains.extend(c[3])
                mains.extend(v.outputs)
            if v.type == 'output':
                for c in v.cassettes:
                    outs.extend(c[3])
                outs.extend(v.outputs)
        in_parts = self.ucf.query_top_level_collection(self.ucf.UCFin, 'parts')
        for in_part in in_parts:
            p = in_part['name']
            t = in_part['type']
            if p in ins or t in ['terminator', 'scar']:
                if t not in self.parts_types:
                    self.parts_types.append(t)
                self.parts_seq_dict[p] = EugeneSequence(t, p, in_part['dnasequence'])
        main_parts = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'parts')
        for main_part in main_parts:
            p = main_part['name']
            t = main_part['type']
            if p in mains or t in ['terminator', 'scar']:
                if t not in self.parts_types:
                    self.parts_types.append(t)
                self.parts_seq_dict[p] = EugeneSequence(t, p, main_part['dnasequence'])
        out_parts = self.ucf.query_top_level_collection(self.ucf.UCFout, 'parts')
        for out_part in out_parts:
            p = out_part['name']
            t = out_part['type']
            if p in outs or t in ['terminator', 'scar']:
                if t not in self.parts_types:
                    self.parts_types.append(t)
                self.parts_seq_dict[p] = EugeneSequence(t, p, out_part['dnasequence'])

        # Get Fenceposts/Genetic Locations
        genetic_locations = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'genetic_locations')[0]
        locations = genetic_locations['locations']  # TODO: Take names as is?  Eco1 has Loc1, etc., but still L1 in .eug
        for location in locations:
            self.genlocs_fenceposts.append(location['symbol'])

        # Get Cassettes/Devices
        # Need to cover all netlist Inputs; start with 1st cassette, use all its inputs; to next cassette as needed
        # Source each input from the 'outputs' parameter of the associated input's 'structures' block
        # e.g. and+Bth on the 2-input NOR should specify *2* cassette blocks b/c each only permits one #in
        for eu in self.devices_dict.values():
            if eu.type in ['gate', 'output']:
                input_ = 0
                for c in eu.cassettes:
                    if input_ < len(eu.inputs):
                        self.structs_cas_dict[c[0]] = EugeneCassette(c[0], c[1], eu.type)
                        for i in range(c[2]):
                            if input_ < len(eu.inputs):
                                output = self.devices_dict[eu.inputs[input_]].outputs[0]  # TODO: Only ever 1 'outputs'?
                                input_ += 1
                                self.structs_cas_dict[c[0]].inputs.append(output)

        # Get Device Rules
        device_rules = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'device_rules')[0]
        circuit_rules = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'circuit_rules')[0]
        # TODO: comprehensive rule keywords?  SC1 odd case...
        rules_keywords = ['NOT', 'EQUALS',
                          'NEXTTO', 'CONTAINS',
                          'STARTSWITH', 'ENDSWITH',
                          'BEFORE', 'AFTER',
                          'ALL_FORWARD']
        # TODO: Pattern in SC1 breaks from other UCFs... has 2 layers of func>rules>func>rules (b/c 2 outputs?)
        while 'rules' in device_rules:
            device_rules = device_rules['rules']
        while 'rules' in circuit_rules:
            circuit_rules = circuit_rules['rules']
        if isinstance(device_rules[0], dict):
            temp = []
            for v in device_rules:
                temp.extend(v['rules'])
            device_rules = temp
        if isinstance(circuit_rules[0], dict):
            temp = []
            for v in circuit_rules:
                temp.extend(v['rules'])
            circuit_rules = temp

        for rule in device_rules:
            self.dev_rules_operands[rule] = [word for word in rule.split() if word not in rules_keywords]
        for rule in circuit_rules:
            self.cir_rules_operands[rule] = [word for word in rule.split() if word not in rules_keywords]

        return True

    # 3. CREATE, WRITE, AND CLOSE THE EUGENE FILE ######################################################################
    def write_eugene(self):
        """
        Creates the eugene file at filepath, uses previously created objects to write to the file, then closes it.
        :return: bool
        """
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w') as eug:
            # Debugging Info...
            # for k, v in self.devices_dict.items():
            #     print(f'{k}...')
            #     print(f"Name: {v.name}, Type: {v.type}, Group: {v.group}, Model: {v.model}, Structure: {v.structure},"
            #           f" Cassette: {v.cassettes}, Inputs: {v.inputs}, Outputs: {v.outputs}\n")

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
            # Include every rule for which all the operands exist in a given cassette (as specified in blocks above)
            for device, cassette in self.structs_cas_dict.items():
                eug.write(f'Rule {device}Rule0( ON {device}:\n')  # TODO: Always 'Rule0'?  Always ON?
                sep = ""
                for rule, operands in self.dev_rules_operands.items():
                    if all([1 if operand in cassette.inputs else 0 for operand in operands]):
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
            # Include every rule for which all the operands exist in the list of cassettes or fenceposts
            eug.write('Rule CircuitRule0( ON circuit:\n')  # TODO: Always 'Rule0'?  Always ON?
            for device in self.structs_cas_dict.keys():
                eug.write(f'    CONTAINS {device} AND\n')
            sep = ""
            for rule, operands in self.cir_rules_operands.items():
                if all([1 if operand in self.structs_cas_dict.keys() or operand in self.genlocs_fenceposts else 0 for
                        operand in operands]):
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
