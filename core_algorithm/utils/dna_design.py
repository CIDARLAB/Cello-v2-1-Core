"""
Class to generate the final circuit design/part order.
See and+Bth-dna_design-to-sbol_diagram.png for a visual depiction of the relationship between the file this class
produces and the SBOL diagram...

"""

import os
import csv
from dataclasses import dataclass
from core_algorithm.utils.py4j_gateway.run_eugene_script import call_mini_eugene
from core_algorithm.utils import log


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


def hex_to_rgb(hex_value: str):
    """
    Converts hex color code to rgb (scaled from 0-1.0; for dnaplotlib part info .csv, which is used for SBOL diagrams)
    :param hex_value: str (6-digits, with default of '000000', which is black)
    :return: str (semicolon-separated decimal values)
    """
    try:
        int(hex_value, 16)
        value = hex_value.lstrip('#')
    except:
        log.cf.warn(f'Passed non-hex val ({hex_value}) to dna_design.py hex_to_rgb func; defaulting to black...')
        return '0.0;0.0;0.0'
    vals = list(round(int(value[i:i + 6 // 3], 16) / 255, 2)
                for i in range(0, 6, 6 // 3))
    return ';'.join(str(val) for val in vals)


class DNADesign:
    """
    Object that generates DNA design (i.e. order of parts/dna sequences).
    Produces a csv of the part order. (Corresponds to v2.0 'dpl-dna-designs.csv'.)
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
    def prep_to_get_part_orders(self):

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

        cycle_thru_alt_rulesets()

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

        for loc in self.fenceposts.keys():
            if f'CONTAINS {loc}' not in self.circuit_rules:
                self.circuit_rules.append(f'CONTAINS {loc}')
        # consolidated_devices = consolidate_devices()  # len(consolidated_devices)

    def get_part_orders(self):
        selected_device_orders = call_mini_eugene(self.circuit_rules)  # NOTE: miniEugene*
        for order in selected_device_orders:
            main_devices = []
            for device in order:
                # if device in list(self.cassettes) or device in list(self.fenceposts):  #  or device in list(self.sequences)
                main_devices.append(device)
            parts = []
            for i, device in enumerate(main_devices):
                if device in list(self.fenceposts):
                    # if len(parts) != 0 and i != len(main_devices) - 1:
                    #     parts.append('_NONCE_PAD')
                    parts.append(f'{device}_NONCE_PAD')
                elif device in list(self.cassettes):
                    parts.extend(self.cassettes[device].inputs)
                    parts.extend(self.cassettes[device].comps)
                else:
                    parts.extend([self.sequences[device].parts_name])
            if parts not in self.valid_circuits:
                self.valid_circuits.append(parts)
        log.cf.info(f'\nSBOL FILES:'
                    f'\n - Circuit orders selected...')
        for circuit_order in self.valid_circuits:
            log.cf.info(f'   + {circuit_order}')

        return self.valid_circuits

    def write_dna_parts_info(self, filepath) -> None:  # equivalent of 2.0 dpl_part_information.csv
        """

        :param filepath:
        """

        def transfer_part_colors() -> None:
            """

            """
            # print(self.cassettes)
            # print('\nself.cassettes count: ', len(self.cassettes))
            for device in self.cassettes:
                # print('device: ', device)
                # print('\nself.cassettes[device].comps count: ', len(self.cassettes[device].comps))
                for part in list(self.cassettes[device].comps):
                    # print('comp: ', part)
                    if self.cassettes[device].color:
                        self.sequences[part].color = self.cassettes[device].color
                    else:
                        self.sequences[part].color = '000000'
                # print('\nself.cassettes[device].outputs count: ', len(self.cassettes[device].outputs))
                for part in list(self.cassettes[device].outputs):
                    # print('output: ', part)
                    # print('self.cassettes[device].color: ', self.cassettes[device].color)
                    if self.cassettes[device].color:
                        # print('IF START..........')
                        # print(self.cassettes[device].color)
                        # print('self.sequences', self.sequences)
                        # print('self.cassettes[device].color', self.cassettes[device].color)
                        # print('part', part)
                        # print('self.sequences[part]', self.sequences[part])
                        self.sequences[part].color = self.cassettes[device].color
                        # print('IF END...........')
                    else:
                        # print('ELSE START........')
                        self.sequences[part].color = '000000'
                        # print('ELSE END..........')

        transfer_part_colors()
        dna_part_info_path = filepath + '_dpl-part-information.csv'
        os.makedirs(os.path.dirname(dna_part_info_path), exist_ok=True)
        with open(dna_part_info_path, 'w', newline='') as dna_part_info:
            csv_writer = csv.writer(dna_part_info)
            csv_writer.writerow(['part_name', 'type', 'x_extent', 'y_extent', 'start_pad', 'end_pad',
                                 'color', 'hatch', 'arrowhead_height', 'arrowhead_length', 'linestyle', 'linewidth',
                                 'label', 'label_size', 'label_color', 'label_y_offset', 'label_rotation'])
            for part in self.valid_circuits[0]:
                if part.endswith('_NONCE_PAD'):
                    csv_writer.writerow([part, 'UserDefined', 30, '', '', 25,
                                         '1.00;1.00;1.00', '', '', '', '', '',
                                         part[:-10], 4, '0.0;0.0;0.0', -10, 90])
            for seq in self.sequences.values():
                lab = seq.parts_name[:10] + '...' if len(seq.parts_name) > 12 else seq.parts_name
                if seq.parts_type == 'cassette':
                    csv_writer.writerow(
                        [seq.parts_name, 'UserDefined', 25, 5, '', '',
                         '0.00;0.00;0.00', '', '', '', '', '',
                         lab, 4, '0.00;0.00;0.00', -10 - len(lab)*2, 90])
                elif seq.parts_type in ['cds', 'rbs']:
                    csv_writer.writerow(
                        [seq.parts_name, seq.parts_type.upper(), '', '', '', '',
                         hex_to_rgb(seq.color), '', '', '', '', '',
                         lab, 4, hex_to_rgb(seq.color), -10 - len(lab)*2, 90])
                # elif seq.parts_type == 'scar':
                #     continue
                else:
                    csv_writer.writerow([seq.parts_name, seq.parts_type.capitalize(), '', '', '', '',
                                         hex_to_rgb(seq.color), '', '', '', '', '',
                                         lab, 4, hex_to_rgb(seq.color), -10 - len(lab)*2, 90])
            dna_part_info.close()

    def write_dna_parts_order(self, filepath) -> None:  # equivalent of 2.0 dpl_dna_designs.csv
        """

        :param filepath:
        """
        dna_part_order_path = filepath + '_dpl-dna-designs.csv'
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
        plot_parameters = filepath + '_dpl-plot-parameters.csv'
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
        regulatory_info = filepath + '_dpl-regulatory-info.csv'
        os.makedirs(os.path.dirname(regulatory_info), exist_ok=True)
        with open(regulatory_info, 'w', newline='') as reg_info:
            csv_writer = csv.writer(reg_info)
            csv_writer.writerow(['from_partname', 'type', 'to_partname', 'arrowhead_length', 'linestyle',
                                 'linewidth', 'color'])
            for struct in self.structs.values():
                # if struct.gates_group:
                #     new_row = [struct.gates_group, 'Repression', struct.outputs[0], 3, '-', '',
                #                hex_to_rgb(struct.color)]
                #     csv_writer.writerow(new_row)
                if struct.struct_cassettes:
                    for part in struct.struct_cassettes[0][3]:  # TODO: Validate
                        if self.sequences[part].parts_type.lower() == 'cds':
                            new_row = [part, 'Repression', struct.outputs[0], 3, '-', '',
                                       hex_to_rgb(struct.color)]
                            csv_writer.writerow(new_row)
                            break
            reg_info.close()

    def write_dna_sequences(self, filepath) -> None:
        """

        :param filepath:
        """
        dna_sequences = filepath + '_dna-sequences.csv'
        os.makedirs(os.path.dirname(dna_sequences), exist_ok=True)
        with open(dna_sequences, 'w', newline='') as dna_seq:
            csv_writer = csv.writer(dna_seq)
            for order in self.valid_circuits:
                segments = ['']
                count = 1
                for seq in order:
                    if seq.endswith('_NONCE_PAD'):
                        segments.append(f'Location {count} ({seq[:-10]})')
                        count += 1
            csv_writer.writerow(segments)
            for num, order in enumerate(self.valid_circuits):
                sequence = [f'Design Option {num + 1}:']
                index = 0
                for seq in order:
                    if not seq.endswith('_NONCE_PAD'):
                        sequence[index] += self.sequences[seq].parts_sequence
                    else:
                        index += 1
                        sequence.append('')
                csv_writer.writerow(sequence)
