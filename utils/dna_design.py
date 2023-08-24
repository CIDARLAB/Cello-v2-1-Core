"""
Class to generate the final circuit design/part order.
See and+Bth-dna_design-to-sbol_diagram.png for a visual depiction of the relationship between the file this class
produces and the SBOL diagram...

"""

import os
import csv
from dataclasses import dataclass
from cello_helpers import debug_print
from copy import deepcopy
import log
import re
import random


@dataclass
class RuleSet:
    """
    Circuit rules categorized by type.  (After rule conversions, before is not needed.)
    after[], before[], startswith, endswith, not_startswith, not_endswith, nextto[], not_nextto[], equals[]
    """

    after: set[str]
    before: set[str]
    startswith: bool
    endswith: bool
    not_startswith: bool
    not_endswith: bool
    nextto: set[str]
    not_nextto: set[str]
    equals: any


@dataclass
class DevChain:
    """
    A chain of devices, based on the 'NEXTTO' rule.  The internal order will already have been validated.
    """
    chain: list[any]  # in order
    after: list[str]  # excluding internal rules (already validated against these)
    before: list[str]  # excluding internal rules (already validated against these)
    reversible: bool  # whether the chain can be reversed and still be internally valid


def deep_copy_params(to_call):
    """

    :param to_call:
    :return:
    """
    def f(*args, **kwargs):
        return to_call(*deepcopy(args), **deepcopy(kwargs))
    return f


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
    Relies heavily on the make_eugene_script.py object:
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

        self.dev_parts: dict[RuleSet] = {}
        self.cir_devices: dict[RuleSet] = {}
        self.chains: list[DevChain] = []
        self.valid_dev_orders: list[list[str]] = []
        self.valid_circuits: list[list[str]] = []

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
        dna_part_info_path = filepath + '_dpl_part_information.csv'
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
        dna_part_order_path = filepath + '_dpl_dna_designs.csv'
        os.makedirs(os.path.dirname(dna_part_order_path), exist_ok=True)
        with open(dna_part_order_path, 'w', newline='') as dna_part_order:
            csv_writer = csv.writer(dna_part_order)
            csv_writer.writerow(['design_name', 'parts'])
            for i, circuit in enumerate(self.valid_circuits):
                new_row = [i]
                for part in circuit:
                    new_row.append(part)
                csv_writer.writerow(new_row)
            dna_part_order.close()

    def write_plot_params(self, filepath) -> None:  # equivalent of 2.0 plot_parameters.csv
        """

        :param filepath:
        """
        plot_parameters = filepath + '_plot_parameters.csv'
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
        regulatory_info = filepath + '_dpl_regulatory_information.csv'
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
    def gen_seq(self, filepath) -> list[list[str]]:
        """
        Traverses all parts in the cassettes and fenceposts, generating their order based on the provided rules.
        Device order just follows the circuit rules.
        Part order within a device *generally* goes:
            1. inputs (i.e. 'output' from the previous device, which isn't necessarily the precedent in the part order)
            2. cassette components (in order, ending in Terminator...)
            3. next device (not necessarily the device to which the current device outputs)
            ('_nonce_pad' is inserted according to landing pad rules)

        General process:
            1. prepare the devices (consolidate devices from inputs and get part colors)
            2. simplify the rules (e.g. NOT x BEFORE y -> x AFTER y)
            3. create chains of devices based on the NEXTTO rules
            4. place the chains of devices, checking all other rules as needed

        :return: list[str]: part_order
        """

        # NOTE: 1. FUNCS TO PREPARE THE DEVICES/PARTS
        def consolidate_devices() -> dict:
            """

            """
            consolidated_devices = {}
            for device, cassette in self.cassettes.items():
                consolidated_devices[cassette.struct_var_name] = cassette.cir_rules
            for loc, rules in self.fenceposts.items():
                consolidated_devices[loc] = rules
            for part, part_info in self.sequences.items():  # primarily for capturing any scars
                if part_info.cir_rules:
                    consolidated_devices[part] = part_info.cir_rules
            # log.cf.info(f'\nconsolidated_devices: {consolidated_devices}')
            return consolidated_devices

        def transfer_part_colors() -> None:
            """

            """
            for device in self.cassettes:
                for part in list(self.cassettes[device].comps):
                    if self.cassettes[device].color:
                        self.sequences[part].color = self.cassettes[device].color
                    else:
                        self.sequences[part].color = '000000'
                for part in list(self.cassettes[device].outputs):
                    if self.cassettes[device].color:
                        self.sequences[part].color = self.cassettes[device].color
                    else:
                        self.sequences[part].color = '000000'

        # NOTE: 2. FUNCS TO SIMPLIFY THE RULES
        # rules types: 'NOT', 'EQUALS', 'NEXTTO', 'CONTAINS', 'STARTSWITH', 'ENDSWITH', 'BEFORE', 'AFTER', 'ALL_FORWARD'
        def reformulate_rules(consolidated_devices):
            """

            :return:
            """
            def rule_simplification(rule: list[str], x: str, y: str) -> None:
                """
                Simplifies rule sets by converting rules to (non-negated) AFTER and BEFORE rules (e.g. b/c the
                'contrapositive' of a true statement is always true).
                Possible permutations of these parameters include:  (x = device, y = other_operand)
                        x AFTER  y -> y
                    NOT x AFTER  y -> x
                        y AFTER  x -> x
                    NOT y AFTER  x -> y
                        x BEFORE y -> x
                    NOT x BEFORE y -> y
                        y BEFORE x -> y
                    NOT y BEFORE x -> x

                :param rule: str
                :param x: str: device/part (from looping over devices/parts)
                :param y: str: other device/part mentioned in the rule
                :return: None
                """

                if rule in [[x, 'AFTER', y], ['NOT', y, 'AFTER', x], ['NOT', x, 'BEFORE', y], [y, 'BEFORE', x]]:
                    self.cir_devices[device].after.add(y)
                if rule in [['NOT', x, 'AFTER', y], [y, 'AFTER', x], [x, 'BEFORE', y], ['NOT', y, 'BEFORE', x]]:
                    self.cir_devices[device].before.add(y)

            for device, rules in consolidated_devices.items():
                # after[], before[], startswith, endswith, not_startswith, not_endswith, nextto[], not_nextto[], equals
                self.cir_devices[device] = RuleSet(set(), set(), False, False, False, False, set(), set(), None)
                for rule in rules:
                    if 'AFTER' in rule or 'BEFORE' in rule:
                        words = rule.split()
                        other_operand = next(word for word in words if word not in [device, 'NOT', 'AFTER', 'BEFORE'])
                        rule_simplification(rule.split(), device, other_operand)
                    elif 'STARTSWITH' in rule:
                        if 'NOT' in rule:
                            self.cir_devices[device].not_startswith = True
                        else:
                            self.cir_devices[device].equals = 0  # Convert STARTSWITH to an EQUALS rule
                    elif 'ENDSWITH' in rule:
                        if 'NOT' in rule:
                            self.cir_devices[device].not_endswith = True
                        else:
                            self.cir_devices[device].endswith = True
                    elif 'NEXTTO' in rule:
                        words = rule.split()
                        other_operand = next(word for word in words if word not in [device, 'NOT', 'NEXTTO'])
                        if 'NOT' in rule:
                            self.cir_devices[device].not_nextto.add(other_operand)
                        else:
                            self.cir_devices[device].nextto.add(other_operand)
                    elif 'EQUALS' in rule:
                        index = int(re.search('(?<=\\[)(.*)(?=\\])', rule)[0])
                        self.cir_devices[device].equals = index
            # log.cf.info(f'\ncircuit rule sets: {self.cir_devices}')

        # NOTE: 3. FUNCS TO CREATE CHAINS OF DEVICES/PARTS
        def create_chains(devices_left) -> None:
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
                after_rules = self.cir_devices[device].after
                before_rules = self.cir_devices[device].before
                for adj_dev in self.cir_devices[device].nextto:
                    if adj_dev not in chain:
                        if not [d for d in self.cir_devices[adj_dev].before if d in chain]:
                            chain.append(adj_dev)
                            after_rules.update(x for x in self.cir_devices[adj_dev].after)
                            before_rules.update(x for x in self.cir_devices[adj_dev].before)
                        else:
                            return None, None, None  # violates BEFORE rule, so not vaild order
                after_rules.difference_update(set(chain))
                before_rules.difference_update(set(chain))
                return chain, after_rules, before_rules

            for device in devices_left:
                if len(self.cir_devices[device].nextto) < 2:
                    chain, after, before = chain_devices(device)
                    if chain:  # else, reverse order should be captured in another loop
                        if index := next((i for i, c in enumerate(self.chains) if set(c.chain) == set(chain)), None):
                            self.chains[index].reversible = True
                        else:
                            self.chains.append(DevChain(chain, list(set(after)), list(set(before)), False))
            # log.cf.info(f'\nself.chains: {self.chains}')

        # NOTE: 4. FUNCS TO PLACE THE CHAINS OF DEVICES/PARTS
        @deep_copy_params
        def place_chains(chain_obj, chains_obj, chain_num, dev_placed):
            """

            :param chain_obj:
            :param chains_obj:
            :param chain_num:
            :param dev_placed:
            """
            def check_rules(dev, ind, placed):
                """

                :param dev:
                :param ind:
                :param placed:
                :return:
                """
                if ind < 0:
                    # print('Index less than 0')
                    return False
                elif placed[ind] != '':
                    # print('Already taken')
                    return False
                elif ind == 0 and self.cir_devices[dev].not_startswith:
                    # print('Startswith violated')
                    return False
                elif next((d for d in placed[0:ind] if d != '' and self.cir_devices[d].endswith), None):
                    # print('Endswith violated')
                    return False
                elif placed[ind - 1] in self.cir_devices[dev].not_nextto or \
                     (ind + 1 < len(placed) and placed[ind + 1] in self.cir_devices[dev].not_nextto):
                    # print('Not_NextTo violated')
                    return False
                elif (equals_index := self.cir_devices[dev].equals) and ind != equals_index:
                    # print('Equals violated')
                    return False
                elif [d for i, d in enumerate(placed) if (i < ind and d in self.cir_devices[dev].before)] or \
                     [d for i, d in enumerate(placed) if (i > ind and d in self.cir_devices[dev].after)]:
                    # print('Before or After violated')
                    return False
                # TODO: add func to check after/before cond outside the chain (b/c rules could be invalid)
                else:
                    # print('Valid placement')
                    return True

            def place_remaining_chains(c_objs, d_placed, d_left):

                def reset():
                    c_objs_copy = deepcopy(c_objs)
                    d_placed_copy = deepcopy(d_placed)
                    d_left_copy = deepcopy(d_left)
                    return c_objs_copy, d_placed_copy, d_left_copy

                if not d_left and d_placed not in self.valid_dev_orders:
                    self.valid_dev_orders.append(d_placed)
                    log.cf.info(f'\nORDER VALID: {d_placed}')
                    return
                # else:
                elif len(self.valid_dev_orders) < 15:  # TODO: Ensures sufficient variety of DPLs?  Appropriate #?
                    poss_next_chains = [c for c in c_objs if not any(d for d in c.after if d in d_left)]
                    placed = 0
                    for chain in poss_next_chains:
                        c_objs_copy, d_placed_copy, d_left_copy = reset()
                        # index = 0  # TODO: narrow placement range?
                        end = min([i for i, v in enumerate(d_placed_copy) if v in chain.before], default=len(d_placed_copy))
                        index = max([i for i, v in enumerate(d_placed_copy) if v in chain.after], default=0)
                        while 0 <= index <= min(len(d_placed_copy) - len(chain.chain), end):  # TODO: Better?
                        # while 0 <= index <= len(d_placed_copy) - len(chain.chain):
                            c_objs_copy, d_placed_copy, d_left_copy = reset()
                            if all([check_rules(dev, index, d_placed_copy) for ind, dev in enumerate(chain.chain)]):
                                d_placed_copy[index:index + len(chain.chain)] = chain.chain
                                c_objs_copy.remove(chain)
                                d_left_copy = [d for d in d_left_copy if d not in chain.chain]
                                # print('\nCHAIN: ', chain)
                                # print('PLACED: ', d_placed_copy)
                                place_remaining_chains(c_objs_copy, d_placed_copy, d_left_copy)
                                placed += 1
                                break
                            index += 1
                        if placed > 2:  # TODO: Ensures valid result (at least for any demoed configs)?  Appropriate #?
                            break

            success = False
            if eq := next(((eq_ind, i) for i, x in enumerate(chain_obj.chain)
                           if (eq_ind := self.cir_devices[x].equals) is not None), None):
                start = eq[0] - eq[1]
                if len(dev_placed) < start + len(chain_obj.chain):
                    dev_placed += ['']*(start + len(chain_obj.chain) - len(dev_placed))
                if all([check_rules(dev, start + ind, dev_placed) for ind, dev in enumerate(chain_obj.chain)]):
                    dev_placed[start:start+len(chain_obj.chain)] = chain_obj.chain
                    success = True
            if success:
                chains_obj.pop(chain_num)
            else:
                chain_num += 1
            if chain_num < len(chains_obj):
                place_chains(chains_obj[chain_num], chains_obj, chain_num, dev_placed)
                if chains_obj[chain_num].reversible:
                    reversed = deepcopy(chains_obj[chain_num])
                    reversed.chain.reverse()
                    place_chains(reversed, chains_obj, chain_num, dev_placed)
            else:
                dev_left = []
                for chain in chains_obj:
                    for d in chain.chain:
                        dev_left.append(d)

                # print(f'\nPARTIALLY PLACED: {dev_placed}')  # TODO: Doesn't know invalid via not_nextto ?
                place_remaining_chains(chains_obj, dev_placed + ['']*len(dev_left), dev_left)

        # NOTE: MAIN SCRIPT TO EXECUTE FUNCTIONS ABOVE FOR FILE GENERATION #############################################

        def cycle_thru_alt_rulesets():  # TODO: Finish setting up ruleset traversal

            rules_keywords = ['NOT', 'EQUALS',
                              'NEXTTO', 'CONTAINS',
                              'STARTSWITH', 'ENDSWITH',
                              'BEFORE', 'AFTER',
                              'ALL_FORWARD']

            all_things = list(self.sequences.keys()) + \
                         list(self.cassettes.keys()) + \
                         list(self.fenceposts.keys())

            for r in self.circuit_rules:
                operands = [word for word in r.split() if word not in rules_keywords and not word.startswith('[')]
                if len(operands) == 0:
                    if r not in self.circuit_rules:
                        self.circuit_rules.append(r)
                elif all([1 if o in all_things else 0 for o in operands]):
                    for o in operands:
                        if o in self.cassettes.keys():
                            self.cassettes[o].cir_rules.append(r)
                        if o in self.sequences.keys():
                            self.sequences[o].cir_rules.append(r)
                        if o in self.fenceposts.keys():
                            self.fenceposts[o].append(r)

            # print(self.circuit_rules)
            # print(self.cassettes)
            # print(self.sequences)
            # print(self.fenceposts)

        cycle_thru_alt_rulesets()

        # First: Prep
        consolidated_devices = consolidate_devices()
        transfer_part_colors()
        reformulate_rules(consolidated_devices)
        devices_left = list(self.cir_devices)
        create_chains(devices_left)
        # log.cf.info(f'\nDevices: {self.cir_devices}')

        # Second: Generate device orders
        chains_copy = deepcopy(self.chains)
        place_chains(chains_copy[0], chains_copy, 0, [])
        if chains_copy[0].reversible:
            reversed = deepcopy(chains_copy[0])
            reversed.chain.reverse()
            place_chains(reversed, chains_copy, 0, [])
        # log.cf.info(f'\nValid Device Orders: {self.valid_dev_orders}')

        # Third: Generate final part orders
        selected_device_orders = []
        for index in random.sample(range(0, len(self.valid_dev_orders)), min(5, len(self.valid_dev_orders))):
            selected_device_orders.append(self.valid_dev_orders[index])
        # log.cf.info(f'\nSelected Device Orders: {selected_device_orders}')

        for order in selected_device_orders:  # TODO: Stop at first 5?
            main_devices = []
            for device in order:
                if device in list(self.cassettes) or device in list(self.fenceposts):
                    main_devices.append(device)
            parts = []
            for i, device in enumerate(main_devices):
                if device in list(self.fenceposts):
                    if len(parts) != 0 and i != len(main_devices) - 1:
                        parts.append('_NONCE_PAD')
                else:
                    parts.extend(self.cassettes[device].inputs)
                    parts.extend(self.cassettes[device].comps)
            self.valid_circuits.append(parts)
        log.cf.info(f'\nDPL FILES:'
                    f'\n - Circuit orders selected...')
        for circuit_order in self.valid_circuits:
            log.cf.info(f'   + {circuit_order}')

        return self.valid_circuits  # FIXME: Add outer loop for Eco5/6, Fix tandem functions...
