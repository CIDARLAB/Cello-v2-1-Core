"""
Class to generate the final circuit design/part order.

"""


class DNADesign:
    """
    Object that generates DNA design (i.e. order of parts/dna sequences).
    Produces a csv of the part order. (Corresponds to v2.0 'dpl_dna_designs.csv'.)
    Relies heavily on the eugene.py object:
        ~ EugeneObject.structs_cas_dict{EugeneCassette{cassette name, inputs, outputs, components}}

    gen_seq()
    """

    def __init__(self, components, rules_device, rules_circuit):

        self.components = components
        self.rules_device = rules_device
        self.rules_circuit = rules_circuit

        # rules types: 'NOT', 'EQUALS', 'NEXTTO', 'CONTAINS', 'STARTSWITH', 'ENDSWITH', 'BEFORE', 'AFTER', 'ALL_FORWARD'

    def gen_seq(self) -> None:
        """
        Traverses all parts


        :return: None: creates csv
        """

        pass

