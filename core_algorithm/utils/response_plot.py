"""

"""

import matplotlib.pyplot as plt
import numpy as np
import logging


def get_table_values(table, col_name, input_cnt, next_node=None, conversions=None):
    bar_values: dict[str:float] = {}

    col_index = None
    for index, header in enumerate(table[0]):
        if header == col_name:
            col_index = index

    for row in table[1:]:
        bar_label = ''
        for i, v in enumerate(row):
            if i < input_cnt:
                if v == 0:
                    bar_label += '—\n'
                elif v == 1:
                    bar_label += '+\n'
            elif i == col_index:
                if next_node and conversions:  # if CM, apply unit_conversion to first bar plot
                    bar_values[bar_label] = v * conversions[next_node]
                else:                          # otherwise it would have already been applied
                    bar_values[bar_label] = v
                break

    return bar_values


def plot_bars(filepath, plot_name, best_graph, table, units, convs):
    input_cnt = len(best_graph.inputs)
    output_cnt = len(best_graph.outputs)

    outputs_dict = {o.name: {'node': None,
                             'func_name': o.func_name,
                             'equation': o.function,
                             'params': o.params,
                             'first_var': o.vars[0]['name'],
                             'prev_node': None,
                             'name': None,
                             'scores_pre_HR': {},
                             'scores_post_HR': {}}
                    for o in best_graph.outputs}
    for v in best_graph.outputs:
        if v.name in outputs_dict.keys():
            outputs_dict[v.name]['node'] = v
    for k in outputs_dict.keys():
        if outputs_dict[k]['func_name'] == 'Hill_response':
            outputs_dict[k]['prev_node'] = best_graph.find_prev(outputs_dict[k]['node']).name

    for k, o in outputs_dict.items():
        if prev_node := o['prev_node']:
            outputs_dict[k]['name'] = prev_node
            outputs_dict[k]['scores_pre_HR']  = get_table_values(table, prev_node, input_cnt, k, convs)
            outputs_dict[k]['scores_post_HR'] = get_table_values(table, k,         input_cnt)
        else:
            outputs_dict[k]['name'] = k
            outputs_dict[k]['scores_pre_HR']  = get_table_values(table, k,         input_cnt)

    # fig = plt.subplots()
    px = 1 / plt.rcParams['figure.dpi']
    plt.figure(
        figsize=(px * (640 + 180 * input_cnt), px * (120 + output_cnt * (280 + 120 * input_cnt))))
    plt.subplots_adjust(top=0.8 + (0.03 * output_cnt), hspace=0.5, wspace=0.5)
    if plot_name.endswith('.UCF'):
        plot_name = plot_name[:-4]
    plt.suptitle(f'{plot_name}: Response Plots', fontsize=15, y=.95, fontweight='bold')
    plt.rc('ytick', labelsize=12)
    plt.rc('xtick', labelsize=12)

    last = 0
    for ind, val in enumerate(list(outputs_dict.values())):
        if val['prev_node'] and (ind + 1 > last):
            last = ind + 1
    i = 1
    for output, data in outputs_dict.items():

        # Output Response Plots (all outputs)
        ax1 = plt.subplot(output_cnt, 3, 3 * i - 2)
        ax1.set_title(f'{data["name"]}', fontsize=12)
        plt.bar(list(data['scores_pre_HR'].keys()), list(data['scores_pre_HR'].values()),
                color='gray')
        plt.yscale('log')
        plt.ylim(ax1.get_ylim()[0] * 0.1, ax1.get_ylim()[1] * 10)
        plt.ylabel(f'Output ({units})', fontsize=12, fontweight='bold')

        # Outputs with Hill Response functions (i.e. Communication Molecules) only...
        if data['prev_node']:

            # Hill Response Curve
            curve = lambda ymax, ymin, kd, n, x: ymin + (ymax - ymin) / (1.0 + (kd / x) ** n)
            ax2 = plt.subplot(output_cnt, 3, 3 * i - 1)
            # for logspace, need ints corresponding to powers; geom uses real vals as endpoints
            x = np.geomspace(ax1.get_ylim()[0] * 0.1, ax1.get_ylim()[1], 10000)
            ax2.plot(x, curve(data['params']['ymax'], data['params']['ymin'], data['params']['kd'],
                              data['params']['n'], x))
            ax2.set_title(f'{output} Hill', fontsize=12)
            plt.yscale('log')
            plt.xscale('log')
            if i == last:
                plt.xlabel(f'Input ({units})', fontsize=12, fontweight='bold')

            # Promoter Activity Bars
            ax3 = plt.subplot(output_cnt, 3, 3 * i)
            ax3.sharey(ax2)
            ax3.set_title(f'{output} Promoter', fontsize=12)
            plt.bar(list(data['scores_post_HR'].keys()), list(data['scores_post_HR'].values()))
            plt.yscale('log')

        i += 1

    # Suppress (useless) console output
    matplotlib_logger = logging.getLogger("matplotlib")
    matplotlib_logger.setLevel(logging.INFO)
    logging.disable(logging.INFO)

    plt.savefig(f'{filepath}_response-plots.png')
    plt.savefig(f'{filepath}_response-plots.pdf')

    # Re-enable console output
    logging.disable(logging.NOTSET)
