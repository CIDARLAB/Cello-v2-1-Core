"""
Class to query, parse, and otherwise interface with the User Constraint Files (UCFs) specified by the user.

UCF Class: __count_collections(), __collection_names(), __parse_helpers(),
          list_collection_parameters(), query_top_level_collection()
"""

import os
from cello_helpers import *
import log


# Work in progress
class UCF:
    """

    """

    def __init__(self, filepath, ucf_file, in_file, out_file, cm_in_path, cm_out_path, cm_in_opt, cm_out_opt):
        self.filepath = filepath
        self.ucf_file = ucf_file
        self.in_file = in_file
        self.out_file = out_file
        self.cm_in_path = cm_in_path
        self.cm_out_path = cm_out_path
        self.cm_in_opt = cm_in_opt
        self.cm_out_opt = cm_out_opt
        self.name = ucf_file[:-4] if ucf_file.endswith('.UCF') else ucf_file  # CRIT: Fix
        (U, I, O) = self.__parse_helper()
        self.UCFmain = U
        self.UCFin = I
        self.UCFout = O
        self.valid = True if (
                self.UCFmain is not None and self.UCFin is not None and self.UCFout is not None) else False
        if self.valid:
            self.collection_count = {cName: self.__count_collection(cName) for cName in
                                     self.__collection_names(self.UCFmain)}  # Main UCF collection counts
        else:
            self.collection_count = {'broken UCF': 0}

    def __count_collection(self, c_name):
        internal_nodes = 0
        for c in self.UCFmain:
            if c['collection'] == c_name:
                internal_nodes += 1
        return internal_nodes

    @staticmethod
    def __collection_names(UCF_choice):
        return list(set([c['collection'] for c in UCF_choice]))

    def __parse_helper(self):
        # filepath = os.path.join(*self.filepath.split('/'))
        # # Communication Molecule filepaths
        u = os.path.join(self.filepath, self.ucf_file + '.json')
        i = os.path.join(self.filepath, self.in_file + '.json')
        o = os.path.join(self.filepath, self.out_file + '.json')
        paths = [u, i, o]
        out = []
        for f in paths:
            with open(f, 'r') as ucf:
                try:
                    ucf = json.load(ucf)

                    if self.cm_in_opt and f == i:
                        print('CM IN')
                        with open(self.cm_in_path, 'r') as comm_devices:
                            in_comm_devices = json.load(comm_devices)
                            ucf.extend(in_comm_devices)
                    if self.cm_out_opt and f == o:
                        print('CM OUT')
                        with open(self.cm_out_path, 'r') as comm_devices:
                            out_comm_devices = json.load(comm_devices)
                            ucf.extend(out_comm_devices)

                    out.append(ucf)
                except Exception as e:
                    debug_print(f'FAILED TO LOAD UCF {self.name}\nlocated at path: {f}')
                    debug_print(str(e))
                    # raise(Exception)
        if len(out) == 3:
            return tuple(out)
        else:
            if len(out) > 0:
                debug_print(f'Working UCF files in the {self.name} collection: ')
                for o in out:
                    try:
                        ucf_name = o[0]['collection']
                        print(f' - name at collection[0]: {ucf_name}')
                    except Exception as e:
                        debug_print(f'FAILED TO PRINT UCF file\ndump: {o}\n{e}')
                print()
            return None, None, None

    def __str__(self):
        # print only the first indexed enumeration to test seeing
        # return json.dumps(self.UCFmain[0], indent=4) + '\n\n'+ \
        #     json.dumps(self.UCFin[0], indent=4) + '\n\n' + \
        #     json.dumps(self.UCFout[0], indent=4)

        # print the name of the UCF only
        return self.UCFmain[0]['version']

    def list_collection_parameters(self, c_name):
        """
        Returns the list (set) of parameters found in a collection.

        :param c_name:
        :return:
        """
        params = []
        for c in self.UCFmain:
            if c['collection'] == c_name:
                params.append(list(c.keys()))
        params_set = set(tuple(x) for x in params)
        params = [list(x) for x in params_set]
        return params

    @staticmethod
    def query_top_level_collection(ucf, c_name):
        """
        Returns all collections with the specified name from the UCF.

        :param ucf:
        :param c_name:
        :return:
        """
        matches = []
        for c in ucf:
            if c['collection'] == c_name:
                matches.append(c)
        return matches
