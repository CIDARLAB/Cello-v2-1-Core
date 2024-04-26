#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to take in a CSV with pre-generated design options (i.e. part orders), rather than Verilog,
and scores each design option, returning just the scores for each.

@author: chris-krenz
"""

import csv
import statistics as stat
# from dataclasses import dataclass

from ucf_class import UCF
# from gate_assignment import *

# Global config vars
ucf_file = 'Bsup'  # to mix-and-match, change below in main...
csv_file = './2-gate.csv'  # 2-gate, 3-gate
verbose = False
design_cnt = 0  # 0 for no restriction


def convert_part_names(design: list[str]) -> list[str]:
    new_list   = []
    part_types = []
    suffixes   = {}
    bases      = {
        'A': 'AmtR',
        'B': 'BM3R1',
        'H': 'HlyIIR',
        'P': 'PhlF',
        'S': 'SrpR'
    }

    for part in design:
        length = len(part)

        if length == 3 and part.startswith('P'):
            part_types.append('Promoter')
            suffixes[part[1]] = part[2]
        elif length == 4 and 'In' in part:
            part_types.append('Input')
        elif part == 'Y':
            part_types.append('Output')
        else:
            part_types.append('Gate')

    for i, type in enumerate(part_types):
        name = design[i]
        if type == 'Promoter':
            new_list.append(name)
        elif type == 'Input':
            if name == 'PIn1':
                new_list.append('Xyl_sensor')
            else:
                new_list.append('Xyl-tetO_sensor')
        elif type == 'Output':
            new_list.append('GFP_reporter')
        else:
            suffix = suffixes[name[0]]
            base   = bases[name[0]]
            new_list.append(name + '-' + suffix + '_' + base)

    return new_list


def collection_list_to_dict(collection_list):
    collection_dict = {}
    for collection in collection_list:
        collection_dict[collection['name']] = collection
    return collection_dict


# @dataclass
class Node:

    def __init__(self, name, type, inputs=[], output=None, params=None):
        self.name   = name
        self.type   = type
        self.inputs = inputs
        self.output = output
        self.params = params

        self.root_input = None  # TODO: Rolling values, changing in main loop

        # if verbose: print(self.name, self.type, self.inputs, self.output, self.params, self.root_input)

    def calc_score(self):
        if self.type == 'input':
            if self.root_input == 'hi':
                return self.params['ymax'], 1
            elif self.root_input == 'lo':
                return self.params['ymin'], 0
            else:
                raise ValueError('Unknown root_input (should be "hi" or "lo")')
        elif self.type == 'promoter':
            if len(self.inputs) > 1:
                # Need to sum inputs, run sum through each of the equations, and then average result
                x = 0
                bin = 0
                for input in self.inputs:
                    result = input.calc_score()[0]  # take raw score (to combine into NOR gate)
                    x   += result[0]
                    bin += result[1]
                partial_results = []
                for input in self.inputs:
                    ymax = input.params['ymax']
                    ymin = input.params['ymin']
                    K    = input.params['K']
                    n    = input.params['n']
                    partial_results.append(ymin + (ymax - ymin) * (K**n) / ((x**n) + (K**n)))
                # if verbose: print('partial_results: ', partial_results)
                cell_score = stat.mean(partial_results)
                binary = 1 if bin == 0 else 0  # acts as either NOR or NOT gate
                if verbose: print(self.name, len(self.inputs), cell_score, binary)
                return cell_score, binary
                # raise ValueError('Promoter inputs are already summed in the calculations of the antecedents; promoter should have a single node as input.')
            else:
                cell_score, binary = self.inputs[0].calc_score()[1]  # take NOT gate result
                if verbose: print(self.name, len(self.inputs), cell_score, binary)
                return cell_score, binary
        elif self.type == 'output':
            row_score, binary = self.inputs[0].calc_score()
            if verbose: print(row_score, self.name, binary)
            return row_score, binary
        elif self.type == 'gate':  # TODO: Check for actual equation
            ymax = self.params['ymax']
            ymin = self.params['ymin']
            K    = self.params['K']
            n    = self.params['n']
            x = 0
            bin = 0
            for input in self.inputs:
                result = input.calc_score()
                x += result[0]
                bin += result[1]
            cell_score = ymin + (ymax - ymin) * (K ** n) / ((x ** n) + (K ** n))
            binary = 1 if bin == 0 else 0  # acts as either NOR or NOT gate
            if verbose: print(self.name, len(self.inputs), cell_score, binary)
            if len(self.inputs) == 1:
                return self.inputs[0].calc_score(), (cell_score, binary)
            else:
                return (cell_score, binary), (cell_score, binary)  # TODO: Messy, fix logic!
        else:
            raise ValueError('Unknown node type')

    def __repr__(self):
        return f"{self.name}, {self.type}, {self.inputs}, {self.output}, {self.params}, {self.root_input}"


def main():

    # csv_file = input('Where is the csv of design options?\n')
    # ucf_file = input('Where is the UCF file you want to use?\n')
    # ins_file = ucf_file.replace('UCF.json', 'input.json')
    # out_file = ucf_file.replace('UCF.json', 'output.json')
    # Xyl-tetO_sensor,B2-1_BM3R1,Xyl_sensor,B2-1_BM3R1,PB1,GFP_reporter

    ucf = UCF('./', f'{ucf_file}.UCF', f'{ucf_file}.input', f'{ucf_file}.output')

    with open(csv_file, 'r') as f:
        csv_reader = csv.reader(f)
        print("File found, script starting...\n")

        u_gates      = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFmain, 'gates'))
        u_models     = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFmain, 'models'))
        u_structures = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFmain, 'structures'))
        u_functions  = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFmain, 'functions'))

        i_gates      = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFin, 'input_sensors'))
        i_models     = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFin, 'models'))
        i_structures = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFin, 'structures'))
        i_functions  = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFin, 'functions'))

        o_gates      = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFout, 'output_devices'))
        o_models     = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFout, 'models'))
        o_structures = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFout, 'structures'))
        o_functions  = collection_list_to_dict(ucf.query_top_level_collection(ucf.UCFout, 'functions'))

        if verbose:
            print('\nu_gates: ', u_gates)
            print('\ni_gates: ', i_gates)
            print('\no_gates: ', o_gates)

        csv_rows = []
        for i, row in enumerate(csv_reader):
            if 'design' in row[0]:
                continue
            if design_cnt and i == design_cnt + 1:
                break

            if verbose: print(row)

            try:
                design_option = convert_part_names(row)
                # print('Input csv appears to be raw Knox output; parts converted to UCF names...')
            except Exception:
                design_option = row
                # print('Input csv appears to already have parts converted to UCF names...')
                pass

            # Construct the parts graph
            nodes, gates, inputs, outputs, promoters = [], [], [], [], []
            prev_promoter = []
            for part in design_option:

                # Gates
                if part in u_gates.keys():
                    struct_name = u_gates[part]['structure']
                    model_name  = u_gates[part]['model']
                    parameters = u_models[model_name]['parameters']
                    params = {}
                    for param in parameters:
                        params[param['name']] = param['value']

                    existing_node = None  # Check if gate already exists
                    for gate in gates:
                        if gate.name == part:
                            existing_node = gate
                            break
                    if existing_node:
                        gate.inputs.extend(prev_promoter if prev_promoter else [])
                    else:
                        node = Node(part, 'gate', prev_promoter if prev_promoter else [],
                                    u_structures[struct_name]['outputs'][0], params)  # should only be 1 output
                        gates.append(node)

                    for promoter in prev_promoter:
                        promoter.output = part
                    prev_promoter = []

                # Inputs
                elif part in i_gates.keys():
                    struct_name = i_gates[part]['structure']  # input actually has the name of its output promoter
                    model_name  = i_gates[part]['model']
                    parameters  = i_models[model_name]['parameters']
                    params = {}
                    for param in parameters:
                        params[param['name']] = param['value']
                    node = Node(i_structures[struct_name]['outputs'][0], 'input', [], None, params)  # output set on next round
                    inputs.append(node)
                    prev_promoter.append(node)

                # Outputs
                elif part in o_gates.keys():
                    node = Node(part, 'output', prev_promoter if prev_promoter else [], None, None)
                    outputs.append(node)
                    for promoter in prev_promoter:
                        promoter.output = part
                    prev_promoter = []

                # Promoters
                else:
                    node = Node(part, 'promoter', [], None, None)  # output set on next round
                    promoters.append(node)
                    prev_promoter.append(node)

                nodes.append(node)

            # Add inputs to promoters (and promoters as nodes to gate outputs)
            for promoter in promoters:
                for node in nodes:
                    if promoter.name == node.output:
                        node.output = promoter
                        promoter.inputs.append(node)

            if verbose:
                for input in inputs:
                    print('input: ', input)
                for gate in gates:
                    print('gate: ', gate)
                for output in outputs:
                    print('output: ', output)
                for promoter in promoters:
                    print('promoter: ', promoter)

            # Calculate output scores
            scores         = []
            output_scores  = []
            output_truths  = []
            gate_scores = {'lolo': [], 'lohi': [], 'hilo': [], 'hihi': []}
            input_permutes = [('lo', 'lo'),  # TODO: Accommodate more than 2 inputs!
                              ('lo', 'hi'),
                              ('hi', 'lo'),
                              ('hi', 'hi')]
            for permute in input_permutes:
                # print('PERMUTATION...')
                row_scores = []
                row_truths = []
                for i, input in enumerate(inputs):
                    input.root_input = permute[i]
                for output in outputs:
                    result = output.calc_score()
                    row_scores.append(result[0])
                    row_truths.append(result[1])
                output_scores.append(row_scores)
                output_truths.append(row_truths)
                gate_scores[''.join(permute)].append(row_scores[0])
                # print(permute, output_scores, output_truths)

            # Calculate final score
            # for output in outputs:  # TODO: Add for multiple outputs...
            lowest_hi  = min(v[0] for i, v in enumerate(output_scores) if output_truths[i][0] == 1)
            highest_lo = max(v[0] for i, v in enumerate(output_scores) if output_truths[i][0] == 0)
            score = lowest_hi / highest_lo
            scores.append(score)
            first  = inputs[0].name
            second = inputs[1].name
            csv_row = [score, f'{first};{second}', *[v[0] for v in (g for g in gate_scores.values())], *design_option]
            for i, cell in enumerate(csv_row):  # request from Bipoc to change these names
                if cell == 'PIn1':
                    csv_row[i] = 'Pxyl'
                elif cell == 'PIn2':
                    csv_row[i] = 'Pxyl-tetO'
            csv_rows.append(csv_row)
            print(','.join(str(v) for v in csv_row))

        with open((csv_loc := '-'.join([csv_file[:-4], ucf_file, 'output.csv'])), 'w') as file:
            file = csv.writer(file)
            file.writerow(['score', 'input_order', '0;0', '0;1', '1;0', '1;1', 'design'])
            file.writerows(csv_rows)
        print(f'\n{len(scores)} scores generated. CSV generated at {csv_loc}. Script completed.')


if __name__ == '__main__':
    main()


# Example 2-gate output...
# 44.308928339334244,0.6675408966203453,0.014523068884012105,0.015065606902249338,0.0145048481526393,Pxyl,B1,Pxyl-tetO,B1,PB1,Y
# 32.34116996224632,0.9279142043976469,0.019574656547713103,0.02869142351624427,0.01906796034088929,Pxyl,B2,Pxyl-tetO,B1,PB1,Y
# 32.34116996224632,0.9279142043976469,0.019574656547713103,0.02869142351624427,0.01906796034088929,Pxyl,B1,Pxyl-tetO,B2,PB1,Y
# 28.080458662185247,1.1882875121749485,0.0246262442114141,0.0423172401302392,0.023631072529139284,Pxyl,B2,Pxyl-tetO,B2,PB1,Y
# 44.23033871055055,0.49056611451091126,0.011056506303518555,0.011091167936136409,0.011055893761221545,Pxyl,B1,Pxyl-tetO,B1,PB2,Y
# 49.999736912975216,0.7727404031179309,0.014700422090613475,0.015454889381975936,0.014679184628406353,Pxyl,B2,Pxyl-tetO,B1,PB2,Y
# 49.999736912975216,0.7727404031179309,0.014700422090613475,0.015454889381975936,0.014679184628406353,Pxyl,B1,Pxyl-tetO,B2,PB2,Y
# 53.228488156413846,1.0549146917249506,0.018344337877708394,0.019818610827815462,0.01830247549559116,Pxyl,B2,Pxyl-tetO,B2,PB2,Y
# 1.000025220730539,5.807309588,0.12382792989932026,5.807163127103576,0.12380970723865821,Pxyl,S1,Pxyl-tetO,S1,PS1,Y
# 14.247966106900305,3.196816181886522,0.22437000185860215,0.17199424360757387,0.17036253873397048,Pxyl-tetO,H2,Pxyl,H2,PH1,Y
# 14.444870331017666,2.6996526126466254,0.18689351657588954,0.1602744010570372,0.15944800307260665,Pxyl-tetO,H1,Pxyl,H2,PH1,Y
# 14.444870331017666,2.6996526126466254,0.18689351657588954,0.1602744010570372,0.15944800307260665,Pxyl-tetO,H2,Pxyl,H1,PH1,Y
# 14.740548813910905,2.2024890434067284,0.14941703129317696,0.1485545585065005,0.1485334674112428,Pxyl-tetO,H1,Pxyl,H1,PH1,Y
# 14.247966106900305,3.196816181886522,0.17199424360757387,0.22437000185860215,0.17036253873397048,Pxyl,H2,Pxyl-tetO,H2,PH1,Y
# 14.444870331017666,2.6996526126466254,0.1602744010570372,0.18689351657588954,0.15944800307260665,Pxyl,H1,Pxyl-tetO,H2,PH1,Y
# 14.444870331017666,2.6996526126466254,0.1602744010570372,0.18689351657588954,0.15944800307260665,Pxyl,H2,Pxyl-tetO,H1,PH1,Y
# 14.740548813910905,2.2024890434067284,0.1485545585065005,0.14941703129317696,0.1485334674112428,Pxyl,H1,Pxyl-tetO,H1,PH1,Y
# 1.0000451953445197,4.768509838,0.31567039918950396,4.768294333294835,0.31566279747794956,Pxyl,P2,Pxyl-tetO,P2,PP1,Y
# 1.9418270449412387,5.312207546910235,0.219641248970257,2.7356749205596667,0.21502468337494135,Pxyl,P1,Pxyl-tetO,P2,PP1,Y
# 1.9418270449412387,5.312207546910235,0.219641248970257,2.7356749205596667,0.21502468337494135,Pxyl,P2,Pxyl-tetO,P1,PP1,Y
# 8.329221790667297,5.855905255820471,0.12361209875101001,0.703055507824498,0.11438656927193315,Pxyl,P1,Pxyl-tetO,P1,PP1,Y
# 1.000063799270972,2.979821511,0.12211029127968986,2.9796314126881054,0.12210674196572506,Pxyl,P2,Pxyl-tetO,P2,PP2,Y
# 1.0000663435285375,2.980415522,0.1001363619681919,2.980217803835083,0.10013289206377349,Pxyl,P1,Pxyl-tetO,P2,PP2,Y
# 1.0000663435285375,2.980415522,0.1001363619681919,2.980217803835083,0.10013289206377349,Pxyl,P2,Pxyl-tetO,P1,PP2,Y
# 1.000068886785078,2.981009533,0.07816243265669393,2.9808041949820607,0.0781590421618219,Pxyl,P1,Pxyl-tetO,P1,PP2,Y
# 19.84316315651205,0.9305500725178698,0.0468952487654412,0.025609589722490493,0.024283962986096287,Pxyl-tetO,A1,Pxyl,A1,PA2,Y
# 12.416881503678193,1.076345723552596,0.08668406179391784,0.037375864686983645,0.034446998445008856,Pxyl-tetO,A1,Pxyl,A1,PA1,Y
# 1.0000451953445197,4.768509838,4.768294333294835,0.31567039918950396,0.31566279747794956,Pxyl-tetO,P2,Pxyl,P2,PP1,Y
# 1.9418270449412387,5.312207546910235,2.7356749205596667,0.219641248970257,0.21502468337494135,Pxyl-tetO,P1,Pxyl,P2,PP1,Y
# 1.9418270449412387,5.312207546910235,2.7356749205596667,0.219641248970257,0.21502468337494135,Pxyl-tetO,P2,Pxyl,P1,PP1,Y
# 8.329221790667297,5.855905255820471,0.703055507824498,0.12361209875101001,0.11438656927193315,Pxyl-tetO,P1,Pxyl,P1,PP1,Y
# 1.000063799270972,2.979821511,2.9796314126881054,0.12211029127968986,0.12210674196572506,Pxyl-tetO,P2,Pxyl,P2,PP2,Y
# 1.0000663435285375,2.980415522,2.980217803835083,0.1001363619681919,0.10013289206377349,Pxyl-tetO,P1,Pxyl,P2,PP2,Y
# 1.0000663435285375,2.980415522,2.980217803835083,0.1001363619681919,0.10013289206377349,Pxyl-tetO,P2,Pxyl,P1,PP2,Y
# 1.000068886785078,2.981009533,2.9808041949820607,0.07816243265669393,0.0781590421618219,Pxyl-tetO,P1,Pxyl,P1,PP2,Y
# 1.000025220730539,5.807309588,5.807163127103576,0.12382792989932026,0.12380970723865821,Pxyl-tetO,S1,Pxyl,S1,PS1,Y
# 44.308928339334244,0.6675408966203453,0.015065606902249338,0.014523068884012105,0.0145048481526393,Pxyl-tetO,B1,Pxyl,B1,PB1,Y
# 32.34116996224632,0.9279142043976469,0.02869142351624427,0.019574656547713103,0.01906796034088929,Pxyl-tetO,B2,Pxyl,B1,PB1,Y
# 32.34116996224632,0.9279142043976469,0.02869142351624427,0.019574656547713103,0.01906796034088929,Pxyl-tetO,B1,Pxyl,B2,PB1,Y
# 28.080458662185247,1.1882875121749485,0.0423172401302392,0.0246262442114141,0.023631072529139284,Pxyl-tetO,B2,Pxyl,B2,PB1,Y
# 44.23033871055055,0.49056611451091126,0.011091167936136409,0.011056506303518555,0.011055893761221545,Pxyl-tetO,B1,Pxyl,B1,PB2,Y
# 49.999736912975216,0.7727404031179309,0.015454889381975936,0.014700422090613475,0.014679184628406353,Pxyl-tetO,B2,Pxyl,B1,PB2,Y
# 49.999736912975216,0.7727404031179309,0.015454889381975936,0.014700422090613475,0.014679184628406353,Pxyl-tetO,B1,Pxyl,B2,PB2,Y
# 53.228488156413846,1.0549146917249506,0.019818610827815462,0.018344337877708394,0.01830247549559116,Pxyl-tetO,B2,Pxyl,B2,PB2,Y
# 19.84316315651205,0.9305500725178698,0.025609589722490493,0.0468952487654412,0.024283962986096287,Pxyl,A1,Pxyl-tetO,A1,PA2,Y
# 12.416881503678193,1.076345723552596,0.037375864686983645,0.08668406179391784,0.034446998445008856,Pxyl,A1,Pxyl-tetO,A1,PA1,Y
