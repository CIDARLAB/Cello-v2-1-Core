"""
Class to generate the final circuit design/part order.
See and+Bth-dna_design-to-sbol_diagram.png for a visual depiction of the relationship between the file this class
produces and the SBOL diagram...

"""

import os
import csv
from dataclasses import dataclass
import re


@dataclass
class CirRuleSet:
    """
    Circuit rules categorized by type.  (After rule conversions, before is not needed.)
    """

    after: list[str]
    before: list[str]
    startswith: bool
    endswith: bool
    not_startswith: bool
    not_endswith: bool
    nextto: list[str]
    not_nextto: list[str]
    equals: int


@dataclass
class DevRuleSet:
    """
    Device rules categorized by type.  (After rule conversions, before is not needed.)
    """

    after: list[str]
    before: list[str]
    startswith: bool
    endswith: bool
    not_startswith: bool
    not_endswith: bool
    nextto: list[str]
    not_nextto: list[str]
    equals: int


@dataclass
class DevChain:
    """
    A chain of devices, based on the 'NEXTTO' rule.  The internal order will already have been validated.
    """
    chain: list[any]  # in order
    after: list[str]  # excluding internal rules (already validated against these)
    before: list[str]  # excluding internal rules (already validated against these)
    reversible: bool  # whether the chain can be reversed and still be internally valid


def hex_to_rgb(hex_value):
    """

    :param hex_value:
    :return:
    """
    if not hex_value:
        return '0.0;0.0;0.0'
    value = hex_value.lstrip('#')
    lv = len(value)
    vals = list(round(int(value[i:i + lv // 3], 16) / 255, 2) for i in range(0, lv, lv // 3))
    return ';'.join(str(val) for val in vals)


class DNADesign:
    """
    Object that generates DNA design (i.e. order of parts/dna sequences).
    Produces a csv of the part order. (Corresponds to v2.0 'dpl_dna_designs.csv'.)
    Relies heavily on the eugene.py object:
        ~ EugeneObject.structs_cas_dict{EugeneCassette{cassette name, inputs, outputs, components}}

    gen_seq()
    """

    def __init__(self, structs, cassettes, sequences, device_rules, circuit_rules, fenceposts):

        self.structs = structs  # mainly used for regulatory info file
        self.cassettes = cassettes  # contains the input, output, components, color, dev_rules, and cir_rules (critical)
        self.sequences = sequences  # contains the part type and actual dna sequence; also contains scars
        self.device_rules = device_rules  # rules that govern the short sequences of parts that make up devices
        self.circuit_rules = circuit_rules  # rules that govern the broader order of those devices
        self.fenceposts = fenceposts  # contains the fenceposts/genetic locations that become the nonce_pads
        # rules types: 'NOT', 'EQUALS', 'NEXTTO', 'CONTAINS', 'STARTSWITH', 'ENDSWITH', 'BEFORE', 'AFTER', 'ALL_FORWARD'
        #                                            TODO                                                      TODO

        self.dev_parts: dict[DevRuleSet] = {}
        self.cir_devices: dict[CirRuleSet] = {}
        self.chains: list[DevChain] = []
        self.valid_dev_orders: list[list[str]] = []
        self.valid_circuits: list[str] = []

        # Debugging info...
        # debug_print('EUGENE OBJECTS:')
        # log.cf.info(f'\nself.structs:\n{self.structs}')
        # log.cf.info(f'\nself.sequences:\n{self.sequences}')
        # log.cf.info(f'\nself.cassettes:\n{self.cassettes}')
        # log.cf.info(f'\nself.device_rules:\n{self.device_rules}')
        # log.cf.info(f'\nself.circuit_rules:\n{self.circuit_rules}')
        # log.cf.info(f'\nself.fenceposts:\n{self.fenceposts}')

    # NOTE: CREATE OUTPUT FILES BASED ON DNA PART ORDER AND RELATED INFO ###############################################
    def write_dna_parts_info(self, filepath) -> None:  # equivalent of 2.0 dpl_part_information.csv
        """

        :param filepath:
        """
        dna_part_info_path = filepath + '_dna-part-info.csv'
        os.makedirs(os.path.dirname(dna_part_info_path), exist_ok=True)
        with open(dna_part_info_path, 'w', newline='') as dna_part_info:
            csv_writer = csv.writer(dna_part_info)
            csv_writer.writerow(['part_name', 'type', 'x_extent', 'y_extent', 'start_pad', 'end_pad', 'color',
                                 'hatch', 'arrowhead_height', 'arrowhead_length', 'linestyle', 'linewidth'])
            csv_writer.writerow(['_NONCE_PAD', 'UserDefined', '30', '', '', '', '1.00;1.00;1.00', '', '', '', '', ''])
            for seq in self.sequences.values():
                if seq.parts_type == 'cassette':
                    csv_writer.writerow(
                        [seq.parts_name, 'UserDefined', 25, 5, '', '', '0.00;0.00;0.00', '', '', '', '', ''])
                elif seq.parts_type in ['cds', 'rbs']:
                    csv_writer.writerow(
                        [seq.parts_name, seq.parts_type.upper(), '', '', '', '', hex_to_rgb(seq.color), '', '', '', '',
                         ''])
                elif seq.parts_type == 'scar':
                    continue
                else:
                    csv_writer.writerow([seq.parts_name, seq.parts_type.capitalize(), '', '', '', '',
                                         hex_to_rgb(seq.color), '', '', '', '', ''])
            dna_part_info.close()

    def write_dna_parts_order(self, filepath) -> None:  # equivalent of 2.0 dpl_dna_designs.csv
        """

        :param filepath:
        """
        dna_part_order_path = filepath + '_dna-part-order.csv'
        os.makedirs(os.path.dirname(dna_part_order_path), exist_ok=True)
        with open(dna_part_order_path, 'w', newline='') as dna_part_order:
            csv_writer = csv.writer(dna_part_order)
            csv_writer.writerow(['design_name', 'parts'])
            new_row = ['first_device']
            for part in self.valid_circuits:
                new_row.append(part)
            csv_writer.writerow(new_row)
            dna_part_order.close()

    def write_plot_params(self, filepath) -> None:  # equivalent of 2.0 plot_parameters.csv
        """

        :param filepath:
        """
        plot_parameters = filepath + '_plot-parameters.csv'
        os.makedirs(os.path.dirname(plot_parameters), exist_ok=True)
        with open(plot_parameters, 'w', newline='') as plot_params:
            csv_writer = csv.writer(plot_params)
            csv_writer.writerows([['parameter', 'value'],
                                  ['linewidth', 1],
                                  ['y_scale', 1],
                                  ['show_title', 'N'],
                                  ['backbone_pad_left', 3],
                                  ['backbone_pad_right', 3],
                                  ['axis_y', 48]
                                  ])
            plot_params.close()

    def write_regulatory_info(self, filepath) -> None:
        """

        :param filepath:
        """
        regulatory_info = filepath + '_regulatory-info.csv'
        os.makedirs(os.path.dirname(regulatory_info), exist_ok=True)
        with open(regulatory_info, 'w', newline='') as reg_info:
            csv_writer = csv.writer(reg_info)
            csv_writer.writerow(['from_partname', 'type', 'to_partname', 'arrowhead_length', 'linestyle',
                                 'linewidth', 'color'])
            for struct in self.structs.values():
                if struct.gates_group:
                    new_row = [struct.gates_group, 'Repression', struct.outputs[0], 3, '-', '', hex_to_rgb(
                        struct.color)]
                    csv_writer.writerow(new_row)
            reg_info.close()

    # NOTE: GENERATE INFO PROVIDED TO FILE CREATION FUNCTIONS ABOVE ####################################################
    def gen_seq(self, filepath) -> list[str]:
        """
        Traverses all parts in the cassettes and fenceposts, generating their order based on the provided rules.
        Device order just follows the circuit rules.
        Part order within a device *generally* goes:
            1. inputs (i.e. 'output' from the previous device, which isn't necessarily the precedent in the part order)
            2. cassette components (in order, ending in Terminator...)
            3. next device (not necessarily the device to which the current device outputs)
            ('_nonce_pad' is inserted according to landing pad rules)

        :return: list[str]: part_order
        """

        def check_rules(dev, index, dev_placed):
            """

            :param dev:
            :param index:
            :param dev_placed:
            :return:
            """
            if index >= (end := len(dev_placed)):
                print('Past end')
                return False
            elif dev_placed[index] != '':
                print('Already taken')
                return False
            elif index == 0 and self.cir_devices[dev].not_startswith:
                print('Startswith violated')
                return False
                # TODO: add func to check after cond outside the chain (b/c rules could be invalid)
                # TODO: if not_endswith condition
            elif self.cir_devices[dev].not_nextto == dev_placed[index - 1]:
                print('Not_NextTo violated')
                return False
            elif index + 1 < end and self.cir_devices[dev].not_nextto == dev_placed[index + 1] or \
                    (equals_index := self.cir_devices[dev].equals) and index != equals_index:
                print('Equals violated')
                return False
            elif [d for i, d in enumerate(dev_placed) if i < index and d in self.cir_devices[dev].before] or \
                    [d for i, d in enumerate(dev_placed) if i > index and d in self.cir_devices[dev].after]:
                print('After/Before violated')
                return False
            else:
                return True

        # NOTE: 1. PREPARE THE DEVICES
        def consolidate_devices() -> dict:
            """

            """
            consolidated_devices = {}
            for device, cassette in self.cassettes.items():
                consolidated_devices[cassette.struct_var_name] = cassette.cir_rules
            for loc, rules in self.fenceposts.items():
                consolidated_devices[loc] = rules
            for part, part_info in self.sequences.items():
                if part_info.cir_rules:
                    consolidated_devices[part] = part_info.cir_rules
            return consolidated_devices
            # print(consolidated_devices)

        def get_device_colors() -> None:
            """

            """
            for device in self.cassettes:
                for part in list(self.cassettes[device].comps):
                    self.sequences[part].color = self.cassettes[device].color
                for part in list(self.cassettes[device].outputs):
                    self.sequences[part].color = self.cassettes[device].color

        # NOTE: 2. FUNCS TO SIMPLIFY THE RULES
        def reformulate_rules():
            """

            :return:
            """
            def rule_simplification(rule: list[str], x: str, y: str):
                """
                Simplifies rule sets by converting rules to (non-negated) AFTER and BEFORE rules (e.g. b/c the
                'contrapositive' of a true statement is always true).
                Possible permutations of these parameters include:
                        x AFTER  y -> y
                    NOT x AFTER  y -> x
                        y AFTER  x -> x
                    NOT y AFTER  x -> y
                        x BEFORE y -> x
                    NOT x BEFORE y -> y
                        y BEFORE x -> y
                    NOT y BEFORE x -> x

                :param rule: str
                :param x: str: operand/device/part
                :param y: str: operand/device/part
                :return: str | bool
                """

                if rule in [[x, 'AFTER', y], ['NOT', y, 'AFTER', x], ['NOT', x, 'BEFORE', y], [y, 'BEFORE', x]]:
                    return 'AFTER'
                if rule in [['NOT', x, 'AFTER', y], [y, 'AFTER', x], [x, 'BEFORE', y], ['NOT', y, 'BEFORE', x]]:
                    return 'BEFORE'
                else:  # TODO: error handling
                    return False

            max_index = 0
            for device, rules in consolidated_devices.items():  # TODO: convert EQUALS 0 to STARTSWITH?
                self.cir_devices[device] = CirRuleSet([], [], False, False, False, False, [], [], 0)
                for rule in rules:
                    if 'AFTER' in rule or 'BEFORE' in rule:
                        words = rule.split()
                        y = ""
                        for word in words:
                            if word not in [device, 'NOT', 'AFTER', 'BEFORE']:
                                y = word
                                break
                        res = rule_simplification(rule.split(), device, y)
                        if res == 'AFTER':
                            if res not in self.cir_devices[device].after:
                                self.cir_devices[device].after.append(y)
                        elif res == 'BEFORE':
                            if res not in self.cir_devices[device].before:
                                self.cir_devices[device].before.append(y)
                    elif 'STARTSWITH' in rule:
                        if 'NOT' in rule:
                            self.cir_devices[device].not_startswith = True
                        else:
                            self.cir_devices[device].startswith = True
                    elif 'ENDSWITH' in rule:
                        if 'NOT' in rule:
                            self.cir_devices[device].not_endswith = True
                        else:
                            self.cir_devices[device].endswith = True
                    elif 'NEXTTO' in rule:
                        words = rule.split()
                        y = ""
                        for word in words:
                            if word not in [device, 'NOT', 'NEXTTO']:
                                y = word
                        if 'NOT' in rule:
                            self.cir_devices[device].not_nextto.append(y)
                        else:
                            self.cir_devices[device].nextto.append(y)
                    elif 'EQUALS' in rule:
                        index = int(re.search('(?<=\\[)(.*)(?=\\])', rule)[0])
                        self.cir_devices[device].equals = index
                        if index > max_index:
                            max_index = index
            # print('\ncircuit rule sets', self.cir_devices)

        # NOTE: 3. FUNCS TO CREATE CHAINS OF DEVICES
        def create_chains() -> None:
            """
            Create chains based on NEXTTO rules
            :return: None
            """
            def chain_devices(device):
                """
                Construct an individual chain
                :param device:
                :return:
                """
                chain = [device]
                after = self.cir_devices[device].after
                before = self.cir_devices[device].before
                end = False
                while not end:
                    end = True
                    for adj_dev in self.cir_devices[device].nextto:
                        if adj_dev not in chain:
                            if not [d for d in self.cir_devices[adj_dev].before if d in chain]:
                                chain.append(adj_dev)
                                after.extend(self.cir_devices[adj_dev].after)
                                before.extend(self.cir_devices[adj_dev].before)
                                device = adj_dev
                                end = False
                            else:
                                return None, None, None
                return chain, after, before

            devices_left = list(self.cir_devices)
            chained_devices = []
            chain_sets = []
            for device in devices_left:
                if device not in chained_devices:
                    chain, after, before = chain_devices(device)
                    if after:
                        after = [x for x in after if x not in chain]
                    if before:
                        before = [x for x in before if x not in chain]
                    if chain:  # if invalid, the reverse order captured at another time, should be valid
                        if set(chain) in chain_sets:
                            i = chain_sets.index(set(chain))
                            self.chains[i].reversible = True
                        else:
                            chained_devices.append(chain)
                            chain_sets.append(set(chain))
                            self.chains.append(DevChain(chain, list(set(after)), list(set(before)), False))
            # print('self.chains', self.chains)

        # NOTE: 4. FUNCS TO PLACE THE CHAINS OF DEVICES
        def place_chains(chain, chain_num, rev, dev_placed, dev_left, chains):
            """

            :param chain:
            :param chain_num:
            :param rev:
            :param dev_placed:
            :param dev_left:
            :param chains:
            """
            def place_remaining_devices(chains, dev_placed, dev_left):
                """

                :param chains:
                :param dev_placed:
                :param dev_left:
                """
                if len(dev_left) == 0:
                    self.valid_dev_orders.append(dev_placed)
                else:
                    for chain in list(chains):
                        print('for chain')
                        if not [x for x in chain.after if x in dev_left]:  # should always be met for at least 1 chain
                            f = max([i for i, x in enumerate(dev_placed) if x in chain.after], default=0)
                            b = min([i for i, x in enumerate(dev_placed) if x in chain.before], default=len(dev_placed))
                            print('outer while: ', f, b, f + len(chain.chain))
                            while f + len(chain.chain) - 1 < b:
                                print(f + len(chain.chain))
                                print('b', b)
                                temp_dev_placed = dev_placed
                                temp_dev_left = dev_left
                                failed = False
                                print('while')
                                for ind, dev in enumerate(chain.chain):
                                    print('\nplaced: ', temp_dev_placed)
                                    print('left: ', temp_dev_left)
                                    print('dev: ', dev)
                                    if check_rules(dev, f + ind, temp_dev_placed):
                                        temp_dev_placed[f + ind] = dev
                                        temp_dev_left.remove(dev)
                                    else:
                                        failed = True
                                        break
                                if not failed:
                                    chains.remove(chain)
                                    place_remaining_devices(chains, temp_dev_placed, temp_dev_left)
                                f += 1

            # if any device in the chain has an equals rule, determine start pos of first dev and proceed
            # TODO: equals could be 0, which would be truthy false...
            temp_dev_placed = dev_placed
            temp_dev_left = dev_left
            failed = False
            if rev:
                place_chains(chain[::-1], chain_num, False, dev_placed, dev_left, chains)
            if eq_loc := next(((i, eq) for i, d in enumerate(chain) if (eq := self.cir_devices[d].equals)), None):
                start_loc = eq_loc[1] - eq_loc[0]
                for ind, dev in enumerate(list(chain)):
                    print(start_loc + ind - 1)
                    if check_rules(dev, ind, temp_dev_placed):
                        temp_dev_placed[ind] = dev
                        temp_dev_left.remove(dev)
                if not failed:
                    dev_placed = temp_dev_placed
                    dev_left = temp_dev_left
                    chains.remove(chain)  # TODO: chain not present...
            if (i := chain_num + 1) < len(self.chains):
                place_chains(self.chains[i].chain, i, self.chains[i].reversible, dev_placed, dev_left, chains)
            else:
                place_remaining_devices(chains, dev_placed, dev_left)  # chains w/ no 'equals' rules

        # NOTE: MAIN SCRIPT TO EXECUTE FUNCTIONS ABOVE FOR FILE GENERATION #############################################
        devices_left = list(self.cir_devices)
        temp_devices_placed = [''] * len(devices_left)  # TODO: if equals go beyond this?
        chains = self.chains
        place_chains(chains[0].chain, 0, chains[0].reversible, temp_devices_placed, devices_left, chains)
        print('VALID DEVICE ORDERS: ', self.valid_dev_orders)

        return self.valid_circuits
