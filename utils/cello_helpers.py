"""
Contains funcs for printing headers, debug info, JSON, and tables, counting permutations of nodes, and query parsing.

permute_count_helper(), query_helper(),
print_centered(), debug_print(), print_json(), print_table(), print_row(), print_separator()
"""

import json
import math

'''
pseudocode:

def assign_hash_table_for_every_gate_permutation():
    max_score = 0
    best_design = None
    for each possibility in (I)P(i) * (O)P(o) * (G)P(g) permutations: (* choice in algorithm)
        design = new Circuit(possibility)
        circuit_score = evaluate(design)
        if circuit_score > max_score:
            max_score = circuit_score
            best_design = design
    return best_design


(*) def exhaustive_assign:
    permute available inputs with number of inputs needed
        permute available outputs with number of outputs needed
            permute available gates with the number of gates needed
                newI, newO, newG = permutation
time complexity: O((I)P(i) * (O)P(o) * (G)P(g))
space: O(1) using itertools


(*) def genetic_algorithm:
    population = random circuits
    fitness_scores = circuit_score(population)
    convergence_score = int (indicate insignificant change in circuit )
    While difference > convergence_score (wait for convergence)
        parents = fittest pair from population
        baby = new circuit from parents
        mutation = randomly modify lowest score circuits
        apply babies and mutation to population
        new_fitness_scores = circuit_score(population)
        difference = new_fitness_scores - fitness_scores
    return best circuit in population
time complexity: O(g(i+o+g)(I+O+G)), where g = number of generations
space complexity: O(p) where p = population size
advantage: random, simulative, able to reach global optimum (not local), time efficient
disadvantage: sometimes would evaluate the same design again, still time-consuming with larger solution spaces


(*) def simulated_annealing:
    temperature = some value
    cur_circuit = generate random initial solution
    while True:
        uses hill-climb
advantage: less resource-intensive than genetic simulation algorithm
disadvantage: not guaranteed to reach global optima
'''


def permute_count_helper(i_netlist, o_netlist, g_netlist, i_ucf, o_ucf, g_ucf):
    """

    :param i_netlist:
    :param o_netlist:
    :param g_netlist:
    :param i_ucf:
    :param o_ucf:
    :param g_ucf:
    :return:
    """
    # print("i_netlist, o_netlist, g_netlist, i_ucf, o_ucf, g_ucf")
    # print((i_netlist, o_netlist, g_netlist, i_ucf, o_ucf, g_ucf))
    factorial = lambda n: 1 if n == 0 else n * factorial(n - 1)
    partial_factorial = lambda n, k: 1 if n <= k else n * partial_factorial(n - 1, k)
    # check it thrice
    total_permutations = partial_factorial(i_ucf, i_ucf - i_netlist) * \
                         partial_factorial(g_ucf, g_ucf - g_netlist) * \
                         partial_factorial(o_ucf, o_ucf - o_netlist)
    confirm_permutations = (factorial(i_ucf) / factorial(i_ucf - i_netlist)) * (
            factorial(o_ucf) / factorial(o_ucf - o_netlist)) * (factorial(g_ucf) / factorial(g_ucf - g_netlist))
    confirm_permutations2 = math.perm(i_ucf, i_netlist) * math.perm(o_ucf, o_netlist) * math.perm(g_ucf, g_netlist)
    return total_permutations, (confirm_permutations + confirm_permutations2) / 2


def query_helper(dict_list, key, vals):
    """

    :param dict_list:
    :param key:
    :param vals:
    :return:
    """
    out = []
    for d in dict_list:
        if key in list(d.keys()):
            if d[key] in vals:
                out.append(d)
    return out


def print_centered(text, padding=False):
    """

    :param text:
    :param padding:
    """
    length = 88  # Length of the string of slashes
    if padding:
        print()
    print("/" * length)
    if type(text) == list:
        for t in text:
            print(t.center(length))
    else:
        print(text.center(length))
    print("/" * length)
    if padding:
        print()


def debug_print(msg, padding=True):
    """

    :param msg:
    :param padding:
    """
    # integral = '∫'
    integral = ''
    out_msg = f'{integral}DEBUG{integral} {msg}'
    if padding:
        out_msg = '\n' + out_msg + '\n'
    print(out_msg)


def print_json(chunk):
    """

    :param chunk:
    """
    print(json.dumps(chunk, indent=4))


def print_table(table):
    """

    :param table:
    :return:
    """
    if not table:
        print("Table is empty.")
        return

    num_columns = len(table[0])
    column_widths = [max(len(str(row[column])) if row[column] is not None else 0 for row in table) for column in
                     range(num_columns)]

    # Print table header
    print_separator(column_widths)
    print_row(table[0], column_widths)
    print_separator(column_widths)

    # Print table body
    for row in table[1:]:
        print_row(row, column_widths)
    print_separator(column_widths)


def print_row(row, column_widths):
    """

    :param row:
    :param column_widths:
    """
    max_lines = 1
    for i, item in enumerate(row):
        if item is None:
            item = ""
        item = str(item)

        lines = item.splitlines()
        max_lines = max(max_lines, len(lines))

        if len(lines) > 1:
            row[i] = lines

    for line_index in range(max_lines):
        formatted_row = "|"
        for i, item in enumerate(row):
            if isinstance(item, list):
                if line_index < len(item):
                    formatted_row += f" {item[line_index]:<{column_widths[i]}} |"
                else:
                    formatted_row += f" {'':<{column_widths[i]}} |"
            else:
                formatted_row += f" {str(item):<{column_widths[i]}} |"
        print(formatted_row)


def print_separator(column_widths):
    """

    :param column_widths:
    """
    separator = "+"
    for width in column_widths:
        separator += f"{'-' * (width + 2)}+"
    print(separator)
