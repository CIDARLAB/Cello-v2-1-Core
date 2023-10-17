"""

"""

import matplotlib.pyplot as plt
import numpy as np


def plot_bars(filepath, table, inputs, outputs, hr_params, plot_name):

    cms = {}
    for k, v in hr_params.items():
        if 'kd' in v.keys():
            cms[k] = v

    inputs = [(x.name + '_I/O') for x in inputs]
    outputs = [x.name for x in outputs]

    input_indices = []
    output_indices = {}

    for index, header in enumerate(table[0]):
        if header in inputs:
            input_indices.append(index)
        elif header in outputs:
            output_indices[header] = index

    bar_graphs: dict[str: float] = {}
    for output in outputs:
        bar_graphs[output] = {}

    for row in table[1:]:
        bar_label = ' '
        for ind, num in enumerate(row):
            if ind in input_indices:
                if num == 0:
                    bar_label += '— '
                elif num == 1:
                    bar_label += '+ '
        if not bar_label.isspace():
            for output, bar_graph in bar_graphs.items():
                bar_graph[bar_label] = row[output_indices[output]]

    fig = plt.subplots()
    plt.subplots_adjust(hspace=0.2*len(bar_graphs), wspace=0.4)
    if plot_name.endswith('.UCF'):
        plot_name = plot_name[:-4]
    plt.suptitle(f'{plot_name}: Response Plots', fontsize='medium', y=.98, fontweight='bold')
    hr_graphs = {}

    i = 1
    for name, graph in bar_graphs.items():

        # Output Response Plots (all outputs)
        ax1 = plt.subplot(len(bar_graphs), 3, 3*i - 2)
        ax1.set_title(f'{name}', fontsize='small')
        plt.bar(list(graph.keys()), list(graph.values()), color='gray')
        plt.yscale('log')
        plt.ylim(ax1.get_ylim()[0]*0.1, ax1.get_ylim()[1])
        plt.ylabel('Output (RNAP/s)', fontsize=7, fontweight='bold')
        plt.yticks(fontsize=7)
        plt.xticks(fontsize=7)

        # CMs Only...
        if name in cms.keys():
            promoter = ('pLuxB ' if name.startswith('OC6') else 'pCin ' if name.startswith('OHC12') else 'pRpa ' if
                        name.startswith('pC-HSL') else 'pPhlF ' if name.startswith('DAPG') else '')
            hr_graphs[name] = {}
            curve = lambda ymax, ymin, kd, n, x : ymin + (ymax - ymin) / (1.0 + (kd / x)**n)

            # Promoter Hill Response Curve (CM only)
            ax2 = plt.subplot(len(bar_graphs), 3, 3*i - 1)
            x = np.linspace(ax1.get_ylim()[0], ax1.get_ylim()[1], 1000)
            ax2.plot(x, curve(cms[name]['ymax'], cms[name]['ymin'], cms[name]['kd'], cms[name]['n'], x))
            ax2.set_title(f'{promoter}Hill Response', fontsize='small')
            plt.yscale('log')
            plt.xscale('log')
            if i >= len(cms):
                plt.xlabel('Input (RNAP/s)', fontsize=7, fontweight='bold')
            plt.yticks(fontsize=7)
            plt.xticks(fontsize=7)

            # Promoter Activity Bars (CM only)
            for k, v in graph.items():
                hr_graphs[name][k] = cms[name]['ymin'] + (cms[name]['ymax'] - cms[name]['ymin']) / \
                                   (1.0 + ((cms[name]['kd']) / v)**cms[name]['n'])
            ax3 = plt.subplot(len(bar_graphs), 3, 3*i)
            ax3.sharey(ax2)
            ax3.set_title(f'{promoter}Activity', fontsize='small')
            plt.bar(list(hr_graphs[name].keys()), list(hr_graphs[name].values()))
            plt.yscale('log')
            plt.yticks(fontsize=7)
            plt.xticks(fontsize=7)

        i += 1

    plt.savefig(f'{filepath}_response_plots.png')
