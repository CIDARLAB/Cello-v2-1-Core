"""
This software package is for designing genetic circuits based on logic gate designs written in the Verilog format.
TODO: Update examples/docs
TODO: Space/time complexity metrics for dual annealing
"""

import os

# Note: environment variables should set before numpy/scipy import
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

# from memory_profiler import memory_usage  # Note: memory reported in simulated annealing function
# mem_usage = 0
from threadpoolctl import threadpool_limits, threadpool_info
import \
    scipy  # Note: 'user_api' for use in thread-limiting with statement around scipy annealing algo

import time
import itertools

from core_algorithm.utils.gate_assignment import *
from core_algorithm.utils.logic_synthesis import *
from core_algorithm.utils.netlist_class import Netlist
from core_algorithm.utils.ucf_class import UCF
from core_algorithm.utils.make_eugene_script import *
from core_algorithm.utils.dna_design import *
from core_algorithm.utils.sbol_plot import plotter
from core_algorithm.utils.response_plot import plot_bars
from core_algorithm.utils.sbol import *


def cello_initializer(v_name, ucf_name, in_name, out_name, in_path, out_path, options):
    try:
        start_time = time.time()
        verilogs_path = os.path.join(in_path, 'verilogs')
        constraints_path = os.path.join(in_path, 'constraints')
        process = CELLO3(v_name, ucf_name, in_name, out_name, verilogs_path, constraints_path,
                         out_path, options)
        log.cf.info(f'\nThread count: {threadpool_info()[0]["num_threads"]}')
        log.cf.info(f'Completion Time: {round(time.time() - start_time, 1)} seconds')
        # log.cf.info(f'Annealing mem (usually peak for program): {round(mem_usage[0], 2)} MiB')
        print("\nCello completed execution")
        return {'status': 'SUCCESS', 'msg': 'Cello process executed successfully'}
    except CelloError as e:
        return e.to_dict()


class CelloError(Exception):
    def __init__(self, error_msg, exception):
        super().__init__(error_msg)
        self.msg = error_msg
        self.exception = exception
        self.status = "FAILURE"

    def to_dict(self):
        return {'status': self.status, 'msg': self.msg}


class CELLO3:
    """
    General flow of control...
        call_YOSYS()
        UCF Class (read in UCF data)
        __load_netlist() (rnl ~ netlist)
        check_conditions()
        techmap()
          GraphParser Class (initialize in/out/gate assignments from UCF to netlist)
          append to node (i, o, g) lists, querying UCF
          simulated_annealing_assign() or exhaustive_assign()
            generate permutations of nodes
            scipy.dual_annealing()
              prep_assign_for_scoring()
                AssignGraph Class (map UCF parts to netlist)
                  score_circuit()
                    ...
        techmap() returns best graph
        info printed
        eugene file, dna designs, SBOL diagram, plots, zipfile, etc. created
        [end]
    """

    def __init__(self, v_name, ucf_name, in_name, out_name, verilogs_path, constraints_path,
                 out_path,
                 options: dict = None):
        # NOTE: Initialization
        try:
            # NOTE: SETTINGS (Defaults for specific Cello object; see __main__ at bottom for global program defaults)
            yosys_cmd_choice = 1  # Set of cmds passed to YOSYS to convert Verilog to netlist & image generation
            self.verbose = False  # Print more info to console & log. See logging.config to change verbosity
            self.print_iters = False  # Print to console info on *all* tested iters (produces copious amounts of text)
            self.exhaustive = False  # Run *all* possible permutes to find true optimum score (*long* run time)
            self.test_configs = False  # Runs brief tests of all configs, producing logs and a csv summary of all tests
            self.log_overwrite = False  # Removes date/time from file name, allowing overwrite of logs
            self.total_iters = 1_000  # Number of iterations to run Cello for

            if 'yosys_cmd_choice' in options:
                yosys_cmd_choice = options['yosys_cmd_choice']
            if 'verbose' in options:
                self.verbose = options['verbose']
            if 'print_iters' in options:  # NOTE: Never prints to log (some configs have billions of iters)
                self.print_iters = options['print_iters']
            if 'test_configs' in options:
                self.test_configs = options['test_configs']
            if 'log_overwrite' in options:
                self.log_overwrite = options['log_overwrite']
            if 'exhaustive' in options:
                # Normally uses Scipy's dual annealing
                self.exhaustive = options['exhaustive']
            if 'iterations' in options:
                self.total_iters = options['iterations']

            self.verilogs_path = os.path.abspath(verilogs_path)
            self.constraints_path = os.path.abspath(constraints_path)
            self.out_path = os.path.abspath(out_path)
            self.verilog_name = v_name
            self.ucf_name = ucf_name
            self.in_name = in_name
            self.out_name = out_name
            self.iter_count = 0
            self.best_score = 0
            self.best_graphs = []
            self.units = 'Unknown_Units'
            self.conversions = {}
            self.filepath = os.path.join(out_path, self.verilog_name,
                                         f'{self.verilog_name}_{self.ucf_name[:-4]}')
            # Loggers
            log.config_logger(self.verilog_name, self.ucf_name, self.log_overwrite)
            log.reset_logs()
            # TODO: print settings already chosen
            print_centered(['CELLO V2.1', self.verilog_name + ' + ' + self.ucf_name])

        except Exception as e:
            raise CelloError("Error with initialization", e)

        # NOTE: Logic Synthesis (YOSYS)
        try:
            # yosys cmd set 1 seems best after trial & error
            cont = call_YOSYS(self.verilogs_path, self.out_path, self.verilog_name,
                              self.ucf_name[:-4], yosys_cmd_choice)

            print_centered('End of Logic Synthesis')
            if not cont:
                # raise an error
                # break if run into problem with yosys, call_YOSYS() will show the error.
                raise CelloError('Error with logic synthesis')

            # initialize RG from netlist JSON output from Yosys
            self.rnl = self.__load_netlist()

            if not self.rnl:
                raise CelloError('Error with logic synthesis')
        except Exception as e:
            raise CelloError('Error with logic synthesis', e)

        # NOTE: Initializes UCF, Input, and Output from filepaths
        try:
            self.ucf = UCF(self.constraints_path, self.ucf_name, self.in_name, self.out_name)
            units = self.ucf.query_top_level_collection(self.ucf.UCFout, 'measurement_std')
            if units:
                self.units = units[0]['signal_carrier_units']
            else:
                units = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'measurement_std')
                if units:
                    self.units = units[0]['signal_carrier_units']
                else:
                    log.cf.warning('Cannot find units...')
            if not self.ucf.valid:
                raise CelloError('Error with UCF')
            conversions = self.ucf.query_top_level_collection(self.ucf.UCFout, 'models')
            for gate in conversions:
                print(gate['name'][:-6])
                print([param['value'] for param in gate['parameters'] if param['name'] == 'unit_conversion'])
                self.conversions[gate['name'][:-6]] = [param['value'] for param in gate['parameters'] if param['name'] == 'unit_conversion'][0]
        except Exception as e:
            raise CelloError('Error reading UCF', e)

        # NOTE: Verilog/UCF Compatibility Check
        try:
            valid: bool
            iter_: int
            valid, iter_ = self.check_conditions(verbose=True)
            if not valid:
                raise Exception("Condition check failed")
            log.cf.info(f'\nCondition check passed? {valid}\n')
        except Exception as e:
            raise CelloError('Error with Verilog/UCF compatibility check', e)

        # NOTE: Circuit Scoring
        try:
            best_result = self.techmap(iter_)  # Executing the algorithm if things check out
            if best_result is None:
                log.cf.error('\nProblem with best_result...\n')
                raise CelloError('Problem with best result')
            # best_score = best_result[0]
            best_graph = best_result[1]
            truth_table = best_result[2]
            truth_table_labels = best_result[3]

            graph_inputs_for_printing = list(zip(self.rnl.inputs, best_graph.inputs))
            graph_gates_for_printing = list(zip(self.rnl.gates, best_graph.gates))
            graph_outputs_for_printing = list(zip(self.rnl.outputs, best_graph.outputs))
            # NOTE: only rnl Gate nodes are dictionaries with inputs and outputs; Input and Output nodes are lists

            if self.verbose:
                debug_print(
                    f'final result for {self.verilog_name}.v+{self.ucf_name}: {best_result[0]}')
                debug_print(best_result[1])
        except Exception as e:
            raise CelloError('Error with circuit scoring', e)

        # NOTE: RESULTS/CIRCUIT DESIGN
        try:
            print_centered(['RESULTS', self.verilog_name + ' + ' + self.ucf_name])
            log.cf.info(f'CIRCUIT DESIGN:\n'
                        f' - Best Design: {best_result[1]}\n'
                        f' - Best Circuit Score: {self.best_score}')

            if self.best_score == 0.0:
                log.cf.error('ERROR: Cello was unable to find any valid configurations...')
                raise Exception

            log.cf.info(f'\nInputs ( input response = {best_graph.inputs[0].resp_func_eq} ):')
            in_labels = {}
            for rnl_in, g_in in graph_inputs_for_printing:
                log.cf.info(
                    f' - {rnl_in} {str(g_in)} with max sensor output of {str(list(g_in.out_scores.items()))}')
                in_labels[rnl_in[0]] = g_in.name

            log.cf.info(f'\nGates ( response function = {best_graph.gates[0].response_func};   '
                        f'input composition = {best_graph.gates[0].input_comp} ):')
            gate_labels = {}
            for rnl_g, g_g in graph_gates_for_printing:
                log.cf.info(f' - {rnl_g} {g_g}')
                gate_labels[rnl_g] = g_g.gate_in_use

            log.cf.info(f'\nOutputs ( unit conversion and/or hill response... ):')
            out_labels = {}
            for rnl_out, g_out in graph_outputs_for_printing:
                log.cf.info(f' - {rnl_out} {str(g_out)}')
                out_labels[rnl_out[0]] = g_out.name
            tech_diagram_filepath = os.path.join(self.out_path, v_name,
                                                 f'{self.verilog_name}_{self.ucf_name[:-4]}')
            replace_techmap_diagram_labels(tech_diagram_filepath, gate_labels, in_labels,
                                           out_labels)
        except Exception as e:
            log.cf.error('Error with results/circuit design\n')
            raise CelloError('Error with results/circuit design', e)

        # NOTE: TRUTH TABLE/GATE SCORING
        try:
            # Create the full path for the file
            filepath = os.path.join(out_path, self.verilog_name,
                                    f'{self.verilog_name}_{self.ucf_name[:-4]}')

            # Ensure the directory exists
            directory_path = os.path.dirname(filepath)
            os.makedirs(directory_path, exist_ok=True)

            log.cf.info(f'\n\nTRUTH TABLE/GATE SCORING:')
            tb = [truth_table_labels] + truth_table
            print_table(tb)
            print('(See log for more precision)')

            # Now write the CSV file
            fullpath = os.path.join(os.path.dirname(filepath),
                                    f"{os.path.basename(filepath)}_activity-table.csv")
            with open(fullpath, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Scores...'])
                csv_writer.writerows(
                    zip(*[["{:.2e}".format(float(c)) if i > 0 else c for i, c in enumerate(row)]
                          for row in zip(*tb) if not row[0].endswith('_I/O')]))
                csv_writer.writerows([[''], ['Binary...']])
                csv_writer.writerows(zip(*[row for row in zip(*tb) if row[0].endswith('_I/O')]))

            if self.verbose:
                debug_print("Truth Table (same as before, simpler format):")
                for r in tb:
                    log.cf.info(r)

        except Exception as e:
            raise CelloError(
                'Error with generating truth table/gate scoring', e)

        # NOTE: CIRCUIT SCORE FILE
        try:
            fullpath = os.path.join(os.path.dirname(filepath),
                                    f"{os.path.basename(filepath)}_circuit-score.csv")

            with open(fullpath, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['circuit_score', self.best_score])
        except Exception as e:
            raise CelloError('Error with generating circuit score file', e)

        # NOTE: EUGENE FILE
        try:
            eugene = EugeneObject(self.ucf, graph_inputs_for_printing, graph_gates_for_printing,
                                  graph_outputs_for_printing, best_graph)
            log.cf.info('\n\nEUGENE FILES:')
            if eugene.generate_eugene_structs():
                log.cf.info(" - Eugene object and structs created...")
            if eugene.generate_eugene_cassettes():
                log.cf.info(" - Eugene cassettes created...")
            structs, cassettes, sequences, device_rules, circuit_rules, fenceposts = \
                eugene.generate_eugene_helpers()
            if structs and cassettes and sequences and device_rules and circuit_rules and fenceposts:
                log.cf.info(" - Eugene helpers created...")
            if eugene.write_eugene(filepath + "_eugene.eug"):
                log.cf.info(f" - Eugene script written to {filepath}_eugene.eug")
        except Exception as e:
            raise CelloError('Error with generating eugene file', e)

        # NOTE: DNA DESIGN
        try:
            dna_designs = DNADesign(structs, cassettes, sequences, device_rules, circuit_rules,
                                    fenceposts)
            dna_designs.prep_to_get_part_orders()
            mini_eugene_part_orders = dna_designs.get_part_orders()  # Calls miniEugene
            dna_designs.write_dna_parts_info(filepath)
            dna_designs.write_dna_parts_order(filepath)
            dna_designs.write_plot_params(filepath)
            dna_designs.write_regulatory_info(filepath)
            dna_designs.write_dna_sequences(filepath)
        except Exception as e:
            raise CelloError('Error with generating DNA design', e)

        # NOTE: SBOL DIAGRAM
        try:
            # SBOL XML
            sbol_instance = SBOL(filepath, mini_eugene_part_orders[0],
                                 sequences)  # TODO: loop part orders
            sbol_instance.generate_xml()

            base_dir = os.path.dirname(filepath)

            plot_parameters_file = os.path.join(base_dir,
                                                f"{os.path.basename(filepath)}_dpl-plot-parameters.csv")
            dpl_part_info_file = os.path.join(base_dir,
                                              f"{os.path.basename(filepath)}_dpl-part-information.csv")
            dpl_reg_info_file = os.path.join(base_dir,
                                             f"{os.path.basename(filepath)}_dpl-regulatory-info.csv")
            dpl_dna_designs_file = os.path.join(base_dir,
                                                f"{os.path.basename(filepath)}_dpl-dna-designs.csv")
            dpl_png_file = os.path.join(base_dir, f"{os.path.basename(filepath)}_dpl-sbol.png")
            dpl_pdf_file = os.path.join(base_dir, f"{os.path.basename(filepath)}_dpl-sbol.pdf")

            print(' - ', end='')
            plotter(plot_parameters_file, dpl_part_info_file, dpl_reg_info_file,
                    dpl_dna_designs_file, dpl_png_file, dpl_pdf_file)

            log.cf.info('SBOL XML and related files generated')
        except Exception as e:
            raise CelloError('Error with generating SBOL diagram', e)

        # NOTE: PLOTS
        try:
            plot_name = self.verilog_name + ' + ' + self.ucf_name
            plot_bars(filepath, plot_name, best_graph, tb, self.units, self.conversions)
            log.cf.info(' - Response plots generated\n\n')
        except Exception as e:
            log.cf.error(
                f'Unable to generate response plots:\n{e}', exc_info=True)
            raise CelloError('Error with generating response plots', e)

        # NOTE: ZIPFILE
        try:
            archive_name = os.path.join(
                out_path, f"{self.verilog_name}_{self.ucf_name[:-4]}_all-files")
            target_directory = os.path.join(out_path, self.verilog_name)

            shutil.make_archive(archive_name, 'zip', target_directory)
            shutil.move(f"{archive_name}.zip", target_directory)
        except Exception as e:
            raise CelloError('Error with generating zipfile', e)

    def __load_netlist(self):
        net_path = os.path.join(self.out_path, self.verilog_name,
                                f'{self.verilog_name}_{self.ucf_name[:-4]}_yosys.json')
        # net_path = os.path.join(self.out_path, self.verilog_name, self.verilog_name)
        net_file = open(net_path, 'r')
        net_json = json.load(net_file)
        netlist = Netlist(net_json)

        if not netlist.is_valid_netlist():
            return None
        return netlist

    def check_conditions(self, verbose=True):
        """
        Ignores logic_constraints value, which is unreliable, and instead use the actual gate count

        :param verbose: bool: default True
        :return:
        """

        if verbose:
            log.cf.info('\n')
            print_centered('condition checks for valid input')

        if verbose:
            log.cf.info('\nNETLIST:')
        netlist_valid = False
        if self.rnl is not None:
            netlist_valid = self.rnl.is_valid_netlist()
        if verbose:
            log.cf.info(f'isvalid: {netlist_valid}')

        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors')
        num_ucf_input_sensors = len(in_sensors)
        num_ucf_input_structures = len(
            self.ucf.query_top_level_collection(self.ucf.UCFin, 'structures'))
        num_ucf_input_models = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'))
        num_ucf_input_parts = len(self.ucf.query_top_level_collection(self.ucf.UCFin, 'parts'))
        num_netlist_inputs = len(self.rnl.inputs) if netlist_valid else 99999
        inputs_match = (num_ucf_input_sensors == num_ucf_input_models) and \
                       (num_ucf_input_models == num_ucf_input_structures) and \
                       (
                                   num_ucf_input_parts >= num_netlist_inputs)  # TODO: why must part number match in line above?
        # == num_ucf_input_parts
        if verbose:
            log.cf.info(f'\nINPUTS (including the communication devices): \n'
                        f'num IN-SENSORS in {self.ucf_name} in-UCF: {num_ucf_input_sensors}\n'
                        f'num IN-STRUCTURES in {self.ucf_name} in-UCF: {num_ucf_input_structures}\n'
                        f'num IN-MODELS in {self.ucf_name} in-UCF: {num_ucf_input_models}\n'
                        f'num IN-PARTS in {self.ucf_name} in-UCF: {num_ucf_input_parts}\n'
                        f'num IN-NODES in {self.verilog_name} netlist: {num_netlist_inputs}')

        if verbose:
            log.cf.info([i['name'] for i in in_sensors])
            log.cf.info(f"{'Valid' if inputs_match else 'NOT valid'} input match!")

        out_sensors = self.ucf.query_top_level_collection(self.ucf.UCFout, 'output_devices')
        num_ucf_output_sensors = len(out_sensors)
        num_ucf_output_structures = len(
            self.ucf.query_top_level_collection(self.ucf.UCFout, 'structures'))
        num_ucf_output_models = len(self.ucf.query_top_level_collection(self.ucf.UCFout, 'models'))
        num_ucf_output_parts = len(self.ucf.query_top_level_collection(self.ucf.UCFout, 'parts'))
        num_netlist_outputs = len(self.rnl.outputs) if netlist_valid else 99999
        outputs_match = (num_ucf_output_sensors == num_ucf_output_models) and \
                        (
                                    num_ucf_output_models == num_ucf_output_parts == num_ucf_output_structures) and \
                        (
                                    num_ucf_output_parts >= num_netlist_outputs)  # TODO: why must part number match in line above?
        if verbose:
            log.cf.info(f'\nOUTPUTS: \n'
                        f'num OUT-SENSORS in {self.ucf_name} out-UCF: {num_ucf_output_sensors}\n'
                        f'num OUT-STRUCTURES in {self.ucf_name} out-UCF: {num_ucf_output_structures}\n'
                        f'num OUT-MODELS in {self.ucf_name} out-UCF: {num_ucf_output_models}\n'
                        f'num OUT-PARTS in {self.ucf_name} out-UCF: {num_ucf_output_parts}\n'
                        f'num OUT-NODES in {self.verilog_name} netlist: {num_netlist_outputs}')

            log.cf.info([out['name'] for out in out_sensors])
            log.cf.info(f"{'Valid' if outputs_match else 'NOT valid'} output match!")

        num_structs = self.ucf.collection_count['structures']
        num_models = self.ucf.collection_count['models']
        num_gates = self.ucf.collection_count['gates']
        num_parts = self.ucf.collection_count['parts']
        ucf_gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        gate_names = []
        g_list = []
        for gate in ucf_gates:
            # NOTE: below assumes that all gates in our UCFs are 'NOR' gates (currently)
            gate_names.append(gate['name'])
            g_list.append(gate['group'])
        g_list = list(set(g_list))
        num_groups = len(g_list)
        # numFunctions = len(self.ucf.query_top_level_collection(self.ucf.UCFmain, 'functions'))
        if verbose:
            log.cf.info(f'\nGATES: \n'
                        f'num PARTS in {self.ucf_name} UCF: {num_parts}\n'
                        # f'(ref only) num FUNCTIONS in {self.ucf_name} UCF: {numFunctions}\n'
                        f'num STRUCTURES in {self.ucf_name} UCF: {num_structs}\n'
                        f'num MODELS in {self.ucf_name} UCF: {num_models}\n'
                        f'num GATES in {self.ucf_name} UCF: {num_gates}')

        num_gates_available = []
        logic_constraints = self.ucf.query_top_level_collection(self.ucf.UCFmain,
                                                                'logic_constraints')
        for logic_constraint in logic_constraints:
            for g in logic_constraint['available_gates']:
                num_gates_available.append(g['max_instances'])
        if verbose:
            log.cf.info(f'num GATE USES: {num_gates_available}')
        num_netlist_gates = len(self.rnl.gates) if netlist_valid else 99999
        if verbose:
            log.cf.info(f'num GATES in {self.verilog_name} netlist: {num_netlist_gates}')
            log.cf.info(sorted(g_list))
            log.cf.info(sorted(gate_names))
        gates_match = (num_structs == num_models == num_gates) and (
                    num_gates_available[0] >= num_netlist_gates)
        if verbose:
            log.cf.info(f"{'Valid' if gates_match else 'NOT valid'} intermediate match!")

        # log.cf.info(f'RULE CHECKS:')  # NOTE: make sure will start with landing pad
        # lp_list = []
        # landing_pads = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'genetic_locations')[0]
        # for lp in landing_pads.values():
        #     lp_list.append(lp['symbol'])
        # rules = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'circuit_rules')
        # log.cf.info(f'Starts with Landing Pad: {}')

        pass_check = netlist_valid and inputs_match and outputs_match and gates_match

        (max_iterations, confirm) = permute_count_helper(num_netlist_inputs, num_netlist_outputs,
                                                         num_netlist_gates,
                                                         num_ucf_input_sensors,
                                                         num_ucf_output_sensors,
                                                         num_groups) if pass_check else (None, None)
        if verbose:
            log.cf.info(
                f'\n#{max_iterations:,} possible permutations for {self.verilog_name}.v+{self.ucf_name}...')
            log.cf.info(f'(#{confirm:,} permutations of UCF gate groups confirmed.)')
            print_centered('End of condition checks')

        # QUEST: Is this feature needed/appropriate?
        if confirm and (
                confirm > 10_000_000_000_000):  # if > 10 trillion iters, may not want to hand off to server
            # TODO: Add check for server vs. local...
            # TODO: Add instructions for now to run locally...
            log.cf.error(
                'Circuit too complex for online version of Cello. Simplify the circuit or run Cello locally.')
            raise Exception

        return pass_check, max_iterations

    def techmap(self, iter_: int):
        """
        Calls functions that will generate the gate assignments.

        :param iter_: int
        :return: list: best_assignment
        """

        # NOTE: POE of the CELLO gate assignment simulation & optimization algorithm
        # NOTE: Give it parameter for which evaluative algorithm to use regardless of iter (exhaustive vs simulation)
        print_centered('Beginning GATE ASSIGNMENT')

        in_sensors = self.ucf.query_top_level_collection(self.ucf.UCFin, 'input_sensors')
        i_list = []
        for sensor in in_sensors:
            i_list.append(sensor['name'])

        out_devices = self.ucf.query_top_level_collection(self.ucf.UCFout, 'output_devices')
        o_list = []
        for device in out_devices:
            o_list.append(device['name'])

        gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        g_list = []
        for gate in gates:
            # NOTE: below assumes that all gates in our UCFs are 'NOR' gates
            g_list.append(gate['group'])
        g_list = list(set(g_list))

        log.cf.info('\nListing available assignments from UCF: ')
        log.cf.info(i_list)
        log.cf.info(o_list)
        log.cf.info(g_list)

        circuit = GraphParser(self.rnl.inputs, self.rnl.outputs, self.rnl.gates)

        log.cf.info('\nNetlist de-construction: ')
        log.cf.info(circuit.inputs)
        log.cf.info(circuit.gates)
        log.cf.info(circuit.outputs)

        log.cf.info('\nNetlist requirements: ')
        i = len(self.rnl.inputs)
        o = len(self.rnl.outputs)
        g = len(self.rnl.gates)
        log.cf.info(f'need {i} inputs')
        log.cf.info(f'need {o} outputs')
        log.cf.info(f'need {g} gates')
        # NOTE: ^ This is the input to whatever algorithm to use

        # best_assignments = []
        if not self.exhaustive:
            best_assignments = self.simulated_annealing_assign(
                i_list, o_list, g_list, i, o, g, circuit, iter_)
        else:
            best_assignments = self.exhaustive_assign(
                i_list, o_list, g_list, i, o, g, circuit, iter_)

        print_centered('End of GATE ASSIGNMENT')
        log.cf.info('\n')

        return max(best_assignments, key=lambda x: x[0]) if len(
            best_assignments) > 0 else best_assignments

    def simulated_annealing_assign(self, i_list: list, o_list: list, g_list: list, i: int, o: int,
                                   g: int,
                                   netgraph: GraphParser, iter_: int) -> list:
        """
        Uses scipy's dual annealing func to efficiently find a regional optimum.
        (See notes on Dual Annealing below...)

        :param i_list: list of available inputs
        :param o_list: list of available outputs
        :param g_list: list of available gates
        :param i: int of required inputs
        :param o: int of required outputs
        :param g: int of required gates
        :param netgraph: GraphParser of circuit parameters
        :param iter_: int of total possible configurations
        :return: list: self.best_graphs: [(circuit_score, graph, tb, tb_labels)]
        """
        with threadpool_limits(limits=1, user_api='blas'):  # TODO: Needed?
            print_centered('Running SIMULATED ANNEALING gate-assignment algorithm...')
            i_perms, o_perms, g_perms = [], [], []
            # TODO: Optimize permutation arrays
            for i_perm in itertools.permutations(i_list, i):
                i_perms.append(i_perm)
            for o_perm in itertools.permutations(o_list, o):
                o_perms.append(o_perm)
            for g_perm in itertools.permutations(g_list, g):
                g_perms.append(g_perm)
            max_fun = iter_ if iter_ < self.total_iters else self.total_iters
            max_iter = max_fun

            # DUAL ANNEALING SCIPY FUNC
            def func(x):
                return self.prep_assign_for_scoring(x, (
                i_perms, o_perms, g_perms, netgraph, i, o, g, max_fun))

            lo = [0, 0, 0]
            hi = [len(i_perms), len(o_perms), len(g_perms)]
            # NOTE: Not possible to add integrality constraint; just round to int instead; adds only minor inefficiency
            bounds = scipy.optimize.Bounds(lo, hi,
                                           True)  # Alternatively: bounds = list(zip(lo, hi))
            # TODO: CK: Implement seed (test in simplified script; test other scipy func seeding)
            # TODO: CK: Implement toxicity check...

            ret = scipy.optimize.dual_annealing(func, bounds, maxfun=max_fun, maxiter=max_iter)
            """
            Dual Annealing: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html
            Dual Annealing combines Classical Simulated Annealing, Fast Simulated Annealing, and local search optimizations
            to improve upon the standard simulated annealing technique. The algorithm does not guarantee a global optimal 
            score but can find a good regional optimum in far less time than would be required by exhaustive search.
            
            Key Parameters:
            :param func:    Function of form func(x, *args) with return value that dual_annealing is attempting to optimize
            :param bounds:  Upper and lower bounds for each dimension/variable being passed into func
            :param maxiter: Max number of ~global searches (to identify neighborhoods with potential local maxima)
            :param max_fun: Max number of total function calls/circuit iterations, including local minimization searches
            :param no_local_search: Enable to function more like traditional simulated annealing
            Note: Additional parameters specified in URL above...
    
            :return OptimizeResult: Array including the solution input array, best score, number of iterations run, and a 
            message indicating the specific reason for termination, among additional attributes specified here...
            docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.OptimizeResult.html#scipy.optimize.OptimizeResult  
            """

            # TODO: CK: Capture multiple equivalent optimums
            # self.best_graphs = ret.x     # solution inputs (already stored in object attribute)
            # solution score (reverses inversion from prep_assign_for_scoring)
            self.best_score = -ret.fun
            # count = ret.nfev     # number of func executions
            # reason = ret.message # reason for termination
            log.cf.info(f'\n\nDONE!\n'
                        f'Completed: {self.iter_count:,}/{max_fun:,} iterations (out of {iter_:,} possible iterations)\n'
                        f'Best Score: {self.best_score}')

            # global mem_usage
            # mem_usage = memory_usage(-1, interval=.1, timeout=0.1)

        return self.best_graphs

    def exhaustive_assign(self, i_list: list, o_list: list, g_list: list, i: int, o: int, g: int,
                          netgraph: GraphParser, iter_: int) -> list:
        """
        Algorithm to check *all* possible permutations of inputs, gates, and outputs for this circuit.
        Depending on the number of possible iterations, this could take prohibitively long.
        Use simulated_annealing_assign for a far more efficient (though it does not guarantee the global optimum).

        :param i_list: list
        :param o_list: list
        :param g_list: list
        :param i: int
        :param o: int
        :param g: int
        :param netgraph: GraphParser
        :param iter_: int
        :return: list: self.best_graphs: [(circuit_score, graph, tb, tb_labels)]
        """
        print_centered('Running EXHAUSTIVE gate-assignment algorithm...')
        log.cf.info('Scoring potential gate assignments...')
        for I_perm in itertools.permutations(i_list, i):
            for O_perm in itertools.permutations(o_list, o):
                for G_perm in itertools.permutations(g_list, g):
                    self.prep_assign_for_scoring((I_perm, O_perm, G_perm),
                                                 (None, None, None, netgraph, i, o, g, iter_))
        if not self.verbose:
            log.cf.info('\n')
        log.cf.info(f'\nDONE!\nCounted: {self.iter_count:,} iterations')

        return self.best_graphs

    # def user_specified_assign(self, i_list: list, o_list: list, g_list: list, i: int, o: int, g: int,
    #                           netgraph: GraphParser, iter_: int) -> list:
    #     """
    #
    #     """
    #     print_centered('Running USER-SPECIFIED gate-assignment algorithm...')
    #     log.cf.info('Scoring potential gate assignments...')
    #
    #     for perm in perms:
    #         self.prep_assign_for_scoring()
    #
    #     self.prep_assign_for_scoring()
    #
    #     return self.best_graphs

    def prep_assign_for_scoring(self, x, args):
        """
        Prepares a specific iteration/configuration to be scored by score_circuit.

        :param x: Tuple of dimensions passed into func, including the following
            - i_perm: Specific inputs permutation to be tested
            - o_perm: Specific outputs permutation to be tested
            - g_perm: Specific gates permutation to be tested
            - netgraph:
            - i
        :param args: Tuple of additional arguments to be passed to func
            - i_perms: First dimension domain:  all permutations of inputs
            - o_perms: Second dimension domain: all permutations of outputs
            - g_perms: Third dimension domain:  all permutations of gates
            - i: Number of required inputs
            - o: Number of required outputs
            - g: Number of required gates
            - netgraph: Circuit parameters
            - iter: Number of total possible configurations
        :return: Best score (only returns score because of how dual_annealing functions; graph info in obj attributes)
        """

        (i_perm, o_perm, g_perm) = x
        (i_perms, o_perms, g_perms, netgraph, i, o, g, max_fun) = args
        # TODO: CK: Account for duplicates
        if i_perms and o_perms and g_perms:
            i_perm = i_perms[math.floor(i_perm)]
            o_perm = o_perms[math.floor(o_perm)]
            g_perm = g_perms[math.floor(g_perm)]

        # print('\ni_perm: \n', i_perm)
        # print('g_perm: \n', g_perm)
        # print('o_perm: \n', o_perm)

        # Ignore invalid cases where a type of CM is both an input and output (would create feedback)
        case_invalid = False
        # inputs = []
        # for input in i_perms[math.floor(x[0])]:
        #     input_short = input.removesuffix('_in')
        #     input_short = input_short.removesuffix('_input')
        #     inputs.append(input_short)
        # for output in o_perms[math.floor(x[1])]:
        #     output_short = output.removesuffix('_out')
        #     output_short = output_short.removesuffix('_output')
        #     if output_short in inputs:
        #         case_invalid = True
        #         break

        # Check if inputs, outputs, and gates are unique and the correct number
        if len(set(i_perm + o_perm + g_perm)) == i + o + g:
            self.iter_count += 1
            if case_invalid:
                return 0.0
            if self.print_iters:
                print_centered(f'beginning iteration {self.iter_count}:', also_logfile=False)

            # Output the combination
            def map_helper(l, c):
                return list(map(lambda x_, y: (x_, y), l, c))

            new_i = map_helper(i_perm, netgraph.inputs)
            new_g = map_helper(g_perm, netgraph.gates)
            new_o = map_helper(o_perm, netgraph.outputs)
            new_i = [Input(i[0], i[1].id) for i in new_i]
            new_o = [Output(o[0], o[1].id) for o in new_o]
            new_g = [Gate(g[0], g[1].gate_type, g[1].inputs, g[1].output)
                     for g in new_g]

            graph = AssignGraph(new_i, new_o,
                                new_g)  # NOTE: specific ins, gates, outs from annealing | exhaustive
            (circuit_score, tb, tb_labels) = self.score_circuit(graph)
            # NOTE: follow the circuit scoring functions

            block = '\u2588'  # str: █,   utf-8: '\u2588',   byte: b'\xe2\x96\x88'
            # block = '#'
            num_blocks = int(round(self.iter_count / max_fun, 2) * 50)
            ph_pb = '_' * 50
            format_cnt = format(self.iter_count, ',')
            format_itr = format(max_fun, ',')

            print(f'{ph_pb} #{format_cnt}/{format_itr} | Best: {round(self.best_score, 2)} | '
                  f'Current: {round(circuit_score, 2)}\r'
                  f'{num_blocks * block}', end='\r')

            if self.print_iters:
                print_centered(
                    f'end of iteration {self.iter_count} : intermediate circuit score = {circuit_score}',
                    also_logfile=False)

            # # Now write the CSV file if verbose
            # if self.verbose:
            #     with open((fp := f'{self.filepath}_all_scores.csv'), 'a+') as csvfile:
            #         csv_writer = csv.writer(csvfile)
            #         if os.stat(fp).st_size == 0:
            #             csv_writer.writerow(['Scores', 'Designs...'])
            #         csv_writer.writerow([circuit_score, graph])

            if circuit_score > self.best_score:
                self.best_score = circuit_score
                self.best_graphs = [(circuit_score, graph, tb, tb_labels)]
                log.f.info(
                    f'{ph_pb} #{format_cnt}/{format_itr} | Best Score: {self.best_score} | '
                    f'Current Score: {circuit_score}\r'
                    f'{num_blocks * block}')
            elif circuit_score == self.best_score:
                self.best_graphs.append((circuit_score, graph, tb, tb_labels))

        # Inverted because Dual Annealing designed to find minimum; should ONLY return score

        return -self.best_score

    def score_circuit(self, graph: AssignGraph):
        """
        Calculates the circuit score. Returns circuit_score, the core mapping from UCF. (See Pseudocode below).

        NOTE: Please ensure the UCF files follow the same format as those provided in the samples folder!

        NOTE: Use one gate from each group only! (graph.gates.name = group name)

        :param graph: AssignGraph
        :return: score: tuple[SupportsLessThan, list[list[int] | int], list[str]]
        """

        # print(graph.gates)

        '''
        Pseudocode:

        initialize traversal circuit()

        for each input:
            assign input function

        for each gate(group):
            find all gates in group
            for each gate in group:
                assign response function
                (basically find all individual gate permutations)

        for each output:
            assign output function

        create truth table of circuit

        if toxicity & cytometry in all gates:
            label circuit for extra tox and cyt plot evaluations
            (maybe ignore this part because they can just look in the UCF instead to find the plots)

        for each truth table combination:
            for each individual gate assignment:
                traverse circuit from inputs (input composition is mostly x1+x2)
                evaluate output
        '''

        # First, make sure that all inputs use the same 'sensor_response' function; this has to do with UCF formatting
        input_function_json = self.ucf.query_top_level_collection(self.ucf.UCFin, 'functions')
        input_model_names = [i.name + '_model' for i in graph.inputs]
        input_info = query_helper(self.ucf.query_top_level_collection(self.ucf.UCFin, 'models'),
                                  'name', input_model_names)
        input_functions = {c['name'][:-6]: c['functions'] for c in input_info}
        input_equations = input_functions.copy()
        for key, input in input_functions.items():
            input_equations[key] = {k: (e['equation']) for e in input_function_json for (k, f) in
                                    input.items()
                                    if (e['name'] == f)}
        input_params = {c['name'][:-6]: {p['name']: p['value'] for p in c['parameters']} for c in
                        input_info}

        if self.print_iters:
            debug_print(f'Assignment configuration: {repr(graph)}', False)
            print(f'INPUT parameters:')
            for p in input_params:
                print(f'{p} {input_params[p]}')
            print(
                f"input_response = {(funcs := next(iter(input_equations.values())))['response_function']}")
            if 'tandem_interference_factor' in funcs.keys():
                print(f"\ntandem_interference_factor = {funcs['tandem_interference_factor']}")
            print(f'\nParameters in sensor_response function json: \n{input_params}\n')

        main_function_json = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'functions')
        gate_groups = [(g.name, g.gate_type) for g in graph.gates]
        gates = self.ucf.query_top_level_collection(self.ucf.UCFmain, 'gates')
        gate_query = query_helper(gates, 'group', [g[0] for g in gate_groups])
        gate_ids = [(g['group'], g['name']) for g in gate_query]
        gate_id_names = [i[1] + '_model' for i in gate_ids]
        gate_info = query_helper(self.ucf.query_top_level_collection(self.ucf.UCFmain, 'models'),
                                 'name', gate_id_names)
        gate_functions = {c['name'][:-6]: c['functions'] for c in gate_info}
        gate_equations = gate_functions.copy()
        for key, input in gate_functions.items():
            gate_equations[key] = {k: (e['equation']) for e in main_function_json for (k, f) in
                                   input.items()
                                   if (e['name'] == f and 'equation' in e.keys())}
        gate_func_names = gate_info[0]['functions']
        gate_params = {gf['name'][:-6]: {g['name']: g['value'] for g in gf['parameters']} for gf in
                       gate_info}
        if self.print_iters:
            print(f'GATE parameters: ')
            for f in gate_params:
                print(f'{f} {gate_params[f]}')

        # gate_funcs = {}
        # for func_type, func_name in gate_func_names.items():
        #     if func_type not in ['toxicity', 'cytometry']:  # TODO: add cytometry and toxicity evaluation
        #         gate_funcs[func_type] = query_helper(main_function_json, 'name', [func_name])[0]['equation']

        # try:
        #     input_composition = query_helper(ucf_main_functions, 'name', ['linear_input_composition'])[0]
        # except Exception as e:
        #     raise Exception(f"UCF contains 'tandem' or no input_composition...") from e  # TODO: handle tandem?
        # hill_response_equation = gate_funcs['Hill_response']['equation'].replace('^', '**')  # substitute power operator
        # linear_input_composition = gate_funcs['linear_input_composition']['equation']
        # if self.print_iters:
        #     print(f'hill_response = {hill_response_equation}')
        #     print(f'linear_input_composition = {linear_input_composition}')
        #     print('\n')

        output_function_json = self.ucf.query_top_level_collection(self.ucf.UCFout, 'functions')
        output_function_str = output_function_json[0]['equation']
        output_names = [o.name for o in graph.outputs]
        output_model_names = [o + '_model' for o in output_names]
        output_jsons = query_helper(self.ucf.query_top_level_collection(self.ucf.UCFout, 'models'),
                                    'name',
                                    output_model_names)
        output_params = {o['name'][:-6]: {p['name']: p['value'] for p in o['parameters']} for o in
                         output_jsons}
        output_functions = {c['name'][:-6]: c['functions']['response_function'] for c in
                            output_jsons}
        output_equations = {k: (e['equation']) for e in output_function_json for (k, f) in
                            output_functions.items() if (e['name'] == f)}
        output_vars = {k: (e['variables']) for e in output_function_json for (k, f) in
                       output_functions.items() if (e['name'] == f)}

        if self.print_iters:
            print('OUTPUT parameters: ')
            for op in output_params:
                print(f'{op} {output_params[op]}')
            print(f'output_response = {output_equations}\n')

        # adding parameters to inputs
        for graph_input in graph.inputs:
            if all([repr(graph_input) in x for x in [input_params, input_equations]]):
                graph_input.add_eval_params(input_equations[repr(
                    graph_input)], input_params[repr(graph_input)])

        # adding parameters to outputs (NOTE: intermediate output nodes are technically treated as gates, not outputs)
        for graph_output in graph.outputs:
            if all([repr(graph_output) in x for x in [output_params, output_equations]]):
                graph_output.add_eval_params(output_equations[repr(graph_output)],
                                             output_params[repr(graph_output)],
                                             output_functions[repr(graph_output)],
                                             output_vars[repr(graph_output)])

        # adding parameters and individual gates to gates
        for (gate_group, gate_name) in gate_ids:
            gate_param = gate_params[gate_name]
            for graph_gate in graph.gates:
                if graph_gate.name == gate_group:
                    graph_gate.add_eval_params(gate_equations[gate_name], gate_name, gate_param)

        # NOTE: creating a truth table for each graph assignment
        num_inputs = len(graph.inputs)
        num_outputs = len(graph.outputs)
        num_gates = len(graph.gates)
        (truth_table, truth_table_labels) = generate_truth_table(num_inputs, num_gates, num_outputs,
                                                                 graph.inputs, graph.gates,
                                                                 graph.outputs)
        if self.print_iters:
            print('generating truth table...\n')

        # io_indexes = [i for i, x in enumerate(truth_table_labels) if x.split('_')[-1] == 'I/O']
        # io_names = ['_'.join(x.split('_')[:-1]) for x in truth_table_labels if x.split('_')[-1] == 'I/O']

        def get_tb_IO_index(node_name):
            """
            returns index/col num of column with label ending in '_I/O'

            :param node_name: str
            :return: int
            """
            return truth_table_labels.index(node_name + '_I/O')

        circuit_scores = []
        for r in range(len(truth_table)):
            if self.print_iters:
                print(f'row{r} {truth_table[r]}')

            for (input_name, input_onoff) in list(dict(zip(truth_table_labels[:num_inputs],
                                                           truth_table[r][:num_inputs])).items()):
                input_name = input_name[:input_name.rfind('_')]
                for graph_input in graph.inputs:
                    if repr(graph_input) == input_name:
                        # switch input on/off
                        graph_input.switch_onoff(input_onoff)
                        graph_input_idx = truth_table_labels.index(input_name)
                        truth_table[r][graph_input_idx] = graph_input.out_scores[
                            graph_input.score_in_use]

            def set_tb_IO(node_name, io_val):
                """
                Fills out truth table IO values

                :param node_name:
                :param io_val:
                """
                tb_index_ = get_tb_IO_index(node_name)
                truth_table[r][tb_index_] = io_val

            def get_tb_IO_val(node_name):
                """
                Uses get_tb_IO_index to return value of corresponding col.

                :param node_name: str
                :return: float
                """
                tb_index_ = get_tb_IO_index(node_name)
                return truth_table[r][tb_index_]

            def fill_truth_table_IO(graph_node):
                """
                TODO: docstring

                :param graph_node:
                """
                if type(graph_node) == Gate:
                    gate_inputs = graph.find_prev(graph_node)
                    gate_type = graph_node.gate_type
                    # gate_io = None
                    if gate_type == 'NOR':  # gate_type is either 'NOR' or 'NOT'
                        io_s = []
                        for gate_input in gate_inputs:  # should be exactly 2 inputs
                            input_io = get_tb_IO_val(repr(gate_input))
                            if input_io is None:
                                # this might happen if the gate_input is a gate
                                fill_truth_table_IO(gate_input)
                            input_io = get_tb_IO_val(repr(gate_input))
                            io_s.append(input_io)
                        if len(io_s) == 2 and sum(io_s) == 0:
                            gate_io = 1
                        else:
                            gate_io = 0
                    elif gate_type == 'NOT':  # (gate_type == 'NOT')
                        input_io = get_tb_IO_val(repr(gate_inputs))
                        if input_io is None:
                            fill_truth_table_IO(gate_inputs)
                        input_io = get_tb_IO_val(repr(gate_inputs))
                        if input_io == 0:
                            gate_io = 1
                        elif input_io == 1:
                            gate_io = 0
                        else:
                            raise RecursionError
                    # finally, update the truth table for this gate
                    set_tb_IO(repr(graph_node), gate_io)
                    graph_node.IO = gate_io
                elif type(graph_node) == Output:
                    input_gate = graph.find_prev(graph_node)
                    gate_io = get_tb_IO_val(repr(input_gate))
                    if gate_io is None:
                        fill_truth_table_IO(input_gate)
                    gate_io = get_tb_IO_val(repr(input_gate))
                    # output just carries the gate I/O
                    set_tb_IO(repr(graph_node), gate_io)
                    graph_node.IO = gate_io
                elif type(graph_node) == Input:
                    raise NameError(
                        'not suppose to recurse to input to fill truth table')
                else:
                    raise RecursionError

            for gout in graph.outputs:
                try:
                    fill_truth_table_IO(gout)
                except Exception as e_:
                    # FIXME: this happens for something like the sr_latch, it is not currently supported,
                    #  but with modifications to the truth table, this type of unstable could work
                    debug_print(
                        f'{self.verilog_name} has unsupported circuit configuration due to flip-flopping.\n'
                        f'{e_}')
                    print_table([truth_table_labels] + truth_table)
                    log.cf.info('\n')
                    raise RecursionError

            for graph_output in graph.outputs:
                output_name = graph_output.name
                graph_output_idx = truth_table_labels.index(output_name)
                if truth_table[r][graph_output_idx] is None:
                    output_score = graph.get_score(graph_output, verbose=self.verbose,
                                                   table_info={'table': truth_table,
                                                               'labels': truth_table_labels,
                                                               'r': r})[0]
                    truth_table[r][graph_output_idx] = output_score
                    circuit_scores.append((output_score, output_name))

            for graph_gate in graph.gates:
                graph_gate_idx = truth_table_labels.index(graph_gate.name)
                truth_table[r][graph_gate_idx] = graph_gate.best_score

            if self.print_iters:
                print(circuit_scores)
                print(truth_table_labels)
                print(f'row{r} {truth_table[r]}\n')

        # this part does this: for each output, find minOn/maxOff, and save output device score for this design
        # try:
        #   Min(On) / Max(Off)
        # except:
        #   either Max() ?
        truth_tested_output_values = {}
        for o in graph.outputs:
            tb_io_index = get_tb_IO_index(repr(o))
            tb_index = truth_table_labels.index(repr(o))
            truth_values = {0: [], 1: []}
            for r in range(len(truth_table)):
                o_io_val = truth_table[r][tb_io_index]
                truth_values[o_io_val].append(truth_table[r][tb_index])
            try:
                truth_tested_output_values[repr(o)] = min(
                    truth_values[1]) / max(truth_values[0])
            except Exception:  # TODO: improve exception handling...
                # this means that either all the rows in the output is ON or all OFF
                try:
                    truth_tested_output_values[repr(o)] = max(truth_values[0])
                except Exception:
                    truth_tested_output_values[repr(o)] = max(truth_values[1])

        graph_inputs_for_printing = list(zip(self.rnl.inputs, graph.inputs))
        graph_gates_for_printing = list(zip(self.rnl.gates, graph.gates))
        graph_outputs_for_printing = list(zip(self.rnl.outputs, graph.outputs))
        if self.print_iters:
            print('reconstructing netlist: ')
            for rnl_in, g_in in graph_inputs_for_printing:
                print(
                    f'{rnl_in} {str(g_in)} and max composition of {max(g_in.out_scores)}')
                # print(g_in.out_scores)
            for rnl_g, g_g in graph_gates_for_printing:
                print(f'{rnl_g} {str(g_g)}')
            for rnl_out, g_out in graph_outputs_for_printing:
                print(f'{rnl_out} {str(g_out)}')
            print('\n')

        truth_table_vis = f'{truth_table_labels}\n'
        for r in truth_table:
            truth_table_vis += str(r) + '\n'
        if self.print_iters:
            print(truth_table_vis)
            print(truth_tested_output_values)
            print('\n')
            print_table([truth_table_labels] + truth_table, False)
        # take the output columns of the truth table, and calculate the outputs

        # NOTE: **return the lower-scored output of the multiple outputs**
        score = min(truth_tested_output_values.values()), truth_table, truth_table_labels

        if self.print_iters:
            print('\nscore_circuit returns:')
            print(score)

        # NOTE: confirm intermediate output nodes are CMs...
        # for output in graph.outputs:
        #     if 'Hill_response' != output.func_name:  # TODO: What is appropriate CM detection?
        #         for gate in graph.gates:
        #             if output.id in gate.inputs:
        #                 score = 0.0, truth_table, truth_table_labels

        return score

    def __del__(self):

        log.cf.info('Cello object deleted...\n')
