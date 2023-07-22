"""
Class to query, parse, and otherwise interface with the User Constraint Files (UCFs) specified by the user.

UCF Class: __count_collections(), __collection_names(), __parse_helpers(),
          list_collection_parameters(), query_top_level_collection()
"""

import os
from cello_helpers import *


# Work in progress
class UCF:
    """

    """

    def __init__(self, filepath, name):
        (U, I, O) = self.__parse_helper(filepath, name)
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

    @staticmethod
    def __parse_helper(filepath, name):
        filepath = os.path.join(*filepath.split('/'))
        u = os.path.join(filepath, name + '.UCF.json')
        i = os.path.join(filepath, name + '.input.json')
        o = os.path.join(filepath, name + '.output.json')
        paths = [u, i, o]
        out = []
        for f in paths:
            with open(f, 'r') as ucf:
                try:
                    ucf = json.load(ucf)
                    out.append(ucf)
                except Exception as e:
                    debug_print(f'FAILED TO LOAD UCF {name}\nlocated at path: {f}')
                    debug_print(e, padding=False)
                    # raise(Exception)
        if len(out) == 3:
            return tuple(out)
        else:
            if len(out) > 0:
                debug_print(f'Working UCF files in the {name} collection: ')
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
