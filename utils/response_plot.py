"""

"""

import matplotlib.pyplot as plt


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
    plt.subplots_adjust(hspace=0.2*len(bar_graphs), wspace=0.2)
    plt.suptitle(f'{plot_name}: Response Plots', fontsize='medium', y=.98, fontweight='bold')
    hr_graphs = {}

    i = 1
    for name, graph in bar_graphs.items():

        # Base Response Plots (for all outputs)
        ax1 = plt.subplot(len(bar_graphs), 2, 2*i - 1)
        ax1.set_title('Fluorescent Reporter', fontsize='small')
        plt.bar(list(graph.keys()), list(graph.values()), color='gray')
        plt.yscale('log')
        plt.ylabel(f'\n{name}\n(RNAP/s)')
        plt.yticks(fontsize=8)

        # CM Response Plots (for CM outputs)
        if name in cms.keys():
            hr_graphs[name] = {}
            for k, v in graph.items():
                hr_graphs[name][k] = cms[name]['ymin'] + (cms[name]['ymax'] - cms[name]['ymin']) / \
                                   (1.0 + ((cms[name]['kd']) / v)**cms[name]['n'])  # TODO: Or should it be reverse hr?
            ax2 = plt.subplot(len(bar_graphs), 2, 2*i)
            ax2.sharey(ax1)
            ax2.set_title('CM Hill Response', fontsize='small')
            plt.bar(list(hr_graphs[name].keys()), list(hr_graphs[name].values()))
            plt.yscale('log')
            plt.yticks(fontsize=8)
        i += 1

    plt.savefig(f'{filepath}_response_plots.png')
