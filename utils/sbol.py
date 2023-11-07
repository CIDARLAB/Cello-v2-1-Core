"""
Uses the following objects to construct the SBOL XML...
  - miniEugene part orders (for precedes constraints)
  # TODO: What about fenceposts?

  - sequences (for actual dna sequences)

SBOL/pySBOL3 Sources
  - https://github.com/SynBioDex/pySBOL3/tree/main
  - https://pysbol3.readthedocs.io/en/stable/getting_started.html
  - https://sbolstandard.org/docs/SBOL3.0.1.pdf

Example constraints syntax: https://github.com/SynBioDex/pySBOL3/blob/main/examples/circuit.py
# Wrap it together
circuit = sbol3.Component('circuit', sbol3.SBO_DNA)
circuit.roles.append(sbol3.SO_ENGINEERED_REGION)
ptet_sc = sbol3.SubComponent(ptet)
op1_sc = sbol3.SubComponent(op1)
utr1_sc = sbol3.SubComponent(utr1)
gfp_sc = sbol3.SubComponent(gfp)

# circuit.features can be set and appended to like any Python list
circuit.features = [ptet_sc, op1_sc]
circuit.features += [utr1_sc]
circuit.features.append(gfp_sc)
circuit.constraints = [sbol3.Constraint(sbol3.SBOL_PRECEDES, ptet_sc, op1_sc),
                       sbol3.Constraint(sbol3.SBOL_PRECEDES, op1_sc, utr1_sc),
                       sbol3.Constraint(sbol3.SBOL_PRECEDES, utr1_sc, gfp_sc)]

"""

import sbol3
import log


# For looking up ontologies
# import tyto
# print(tyto.SO.RBS)
# print(sbol3.SO_RBS)
# print(tyto.SO.terminator == sbol3.SO_RBS)


class SBOL:
    """
    SBOL object used to produce SBOL XML file.
    """

    def __init__(self, filepath, part_order, dna_seqs):

        self.filepath = filepath
        self.part_order = part_order
        self.dna_seqs = dna_seqs

        # print(f'\nFilepath: {self.filepath}\n\nPart Orders: {self.part_orders}\n\nSequences: {self.dna_seqs}\n\n')

    def generate_xml(self):
        """
        Primary SBOL3 roles/ontologies used: SO_PROMOTER, SO_RBS, SO_CDS, SO_TERMINATOR, SO_ENGINEERED_REGION
        TODO: SO_RBS?
        """

        doc = sbol3.Document()
        sbol3.set_namespace('http://cidarlab.org/cello/v2_1')
        circuit = sbol3.Component('circuit', sbol3.SBO_DNA, roles=[sbol3.SO_ENGINEERED_REGION])
        doc.add(circuit)
        # range_uri = 'https://cidarlab.org/cello/v2_1/range'

        # target_promoter = sbol3.Component('promoters/target_promoter', sbol3.SBO_DNA, roles=[sbol3.SO_PROMOTER])
        # doc.add(target_promoter)
        # target_promoter
        # target_promoter_seq = sbol3.Sequence('GFPSequence', elements='atgnnntaa', encoding=sbol3.IUPAC_DNA_ENCODING)
        # doc.add(target_promoter_seq)
        # target_promoter.sequences = [target_promoter_seq]

        # ptet = sbol3.Component('pTetR', sbol3.SBO_DNA, roles=[sbol3.SO_PROMOTER])
        # ptet_sc = sbol3.SubComponent(ptet)
        # circuit.constraints += [ptet_sc]

        components = {}
        subcomponents = {}
        sequences = {}
        landing_pads = {}
        ranges = {}
        locations = {}

        for part in self.dna_seqs.values():
            type = part.parts_type.lower()
            role = []
            if type in ['promoter', 'rbs', 'cds', 'terminator']:
                role = [f'sbol3.SO_{type.upper()}']
            name = part.parts_name.replace('-', '_')
            c_id = f'Component_{name}'
            s_id = f'Sequence_{name}'
            seq = part.parts_sequence

            components[c_id] = sbol3.Component(f'{type}/{c_id}', sbol3.SBO_DNA, roles=role)
            doc.add(components[c_id])

            # TODO: Correct Encoding?
            sequences[s_id] = sbol3.Sequence(f'{type}/{s_id}', elements=seq, encoding=sbol3.IUPAC_DNA_ENCODING)
            doc.add(sequences[s_id])
            components[c_id].sequences = [sequences[s_id]]

        # TODO: Get fenceposts/genetic_locations/landing_pads/nonce_pads

        start = 0
        end = 0
        prev = None
        prev_comp = None
        prev_c_id = None
        for part in self.part_order:
            name = part.replace('-', '_')
            c_id = f'Component_{name}'
            s_id = f'Sequence_{name}'

            if part.endswith('_NONCE_PAD'):
                start = 0
                end = 0
                lp_id = f'Landing_Pad_{name}'
                landing_pads[lp_id] = sbol3.Component(f'Landing_Pads/{lp_id}', sbol3.SBO_DNA)
                doc.add(landing_pads[lp_id])
            elif c_id in components.keys():
                # r_id = f'Range_{name}'
                # l_id = f'Location_{name}'
                # sc_id = f'SubComponent_{name}'
                # range_uri = f'http://cidarlab.org/cello/v2_1/{r_id}'
                # length = len(sequences[s_id].elements)
                # start = end + 1
                # end = start + length - 1
                # ranges[r_id] = sbol3.Range(sequences[s_id], start, end, identity=range_uri)
                # locations[l_id] = sbol3.Location(ranges[r_id])
                # sc_id = sbol3.SubComponent(locations=[ranges[r_id]])
                # sequences[s_id].features = ranges[r_id]
                # seq_feat = sbol3.SequenceFeature(ranges[r_id])

                # sc_id = f'SubComponent_{name}'
                # subcomponents[sc_id] = sbol3.SubComponent(components[c_id])
                # circuit.features = [subcomponents[sc_id]]

                if prev_c_id:
                    circuit.constraints.append(sbol3.Constraint(sbol3.SBOL_PRECEDES,
                                                                components[prev_c_id], components[c_id]))
                prev_c_id = c_id

                # if prev:
                #     sc_id = f'SubComponent_{name}'
                #     subcomponents[prev] = sbol3.SubComponent(components[prev_comp])
                #     subcomponents[sc_id] = sbol3.SubComponent(components[c_id])
                #     circuit.features = [subcomponents[sc_id]]
                #     circuit.constraints = [sbol3.Constraint(sbol3.SBOL_PRECEDES,
                #                                             subcomponents[prev], subcomponents[sc_id])]
                # # sequences[s_id].annotation = sbol3.TextProperty()
                # # create annotation
                # # add annotation
                # # create precedes constraint
                # # add precedes constraint
                # prev = f'SubComponent_{name}'
                # prev_comp = c_id

            # else:
            #     log.cf.error('Cannot find SBOL Component')
            #     raise Exception('Cannot find SBOL Component')

        log.cf.info('\n - SBOL files being generated...')
        log.cf.info(doc)
        doc.write(f'{self.filepath}_pySBOL3.nt', sbol3.RDF_XML)
