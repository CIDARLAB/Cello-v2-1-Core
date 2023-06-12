'''
NETLIST class
input: netlist JSON from YOSYS output
(under development)
'''
import sys
sys.path.insert(0, 'utils/')  # links the utils folder to the search path
from cello_helpers import *


# NOTE: pass in a json initialized netlistJSON (dictionary)
class Netlist:
    def __init__(self, netlistJSON):
        self.__netlist = netlistJSON['modules']
        self.name = list(self.__netlist.keys())[0]
        self.__net_main = self.__netlist[self.name]
        self.__ports = self.__net_main['ports']
        self.__cells = self.__net_main['cells']
        self.__edges = self.__net_main['netnames']
        # important attributes below
        if self.is_valid_netlist():
            i, o = self.__sort_nodes(self.__ports)
            self.inputs = i
            self.outputs = o
            self.gates = self.__sort_gates(self.__cells)

    def __sort_nodes(self, ports):
        in_nodes = []
        out_nodes = []
        for p in ports.keys():
            node_name = p
            direction = ports[p]['direction']
            bits = ports[p]['bits']
            if len(bits) > 1:
                debug_print(f'ERROR: too many bits in \n{json.dumps(p, indent=4)}\n')
            bit = bits[0] # a bit is basically like the ID, only for uniqueness
            node = (node_name, bit)
            if direction == 'input':
                in_nodes.append(node)
            elif direction == 'output':
                out_nodes.append(node)
            else:
                raise ValueError('Invalid [in/out]put node')
        return (in_nodes, out_nodes)

    def __sort_gates(self, cells):
        gates = {}
        for c in cells.keys():
            partition = list(c.split('$'))
            gate_id = partition[-1] # uslesses except for uniqueness
            gate_type = cells[c]['type'].split('_')[1]
            gate = {gate_id:
                    {
                        'type': gate_type,
                        'inputs': {},
                        'output': {},
                    }
                    }
            dirns = cells[c]['port_directions']
            ctns = cells[c]['connections']
            inputs = []
            outputs = []
            for d in dirns.keys():
                inout = dirns[d]
                if inout == 'input':
                    inputs.append(d)
                else:
                    outputs.append(d)
            gate_inputs = []
            gate_outputs = []
            for c in ctns.keys():
                c_nodes = ctns[c][0]
                if c in inputs:
                    gate_inputs.append((c, c_nodes))
                else:
                    gate_outputs.append((c, c_nodes))
            for tup in gate_inputs:
                (node_name, edge_nos) = tup
                try:
                    gate[gate_id]['inputs'][node_name] += edge_nos
                except Exception as e:
                    gate[gate_id]['inputs'][node_name] = edge_nos
            for tup in gate_outputs:
                (node_name, edge_nos) = tup
                try:
                    gate[gate_id]['output'][node_name] += edge_nos
                except Exception as e:
                    gate[gate_id]['output'][node_name] = edge_nos
            # print(json.dumps(gate, indent=4))
            gates.update(gate)
        return gates

    def __str__(self):
        return (f"{self.name}: with \n"
                f"{len(self.inputs)} inputs,\n"
                f"{len(self.outputs)} ouputs.")

    # NOTE: IMPORTANT CELLO FEATURE
    def is_valid_netlist(self):
        
        # only support one circuit per Vrlg design
        if type(self.__net_main) != dict:
            return False
        
        # check IO bits (only support single bit ports)
        for port in self.__ports:
            bitarray = self.__ports[port]['bits']
            if len(bitarray) > 1:
                debug_print(f'failed to have single-bit IO in netlist \n{port}')
                return False
            
        # check each node aka gate (no param / attributes & 1-bit connections)
        for node in self.__cells:
            gate = self.__cells[node]

            try:
                gate_type = gate['type'].split('_')[-2]
                if gate_type not in ['NOT', 'NOR']:
                    debug_print(
                        f'Failed to use NOR/NOT gates, got {gate_type} instead.')
                    return False
            except Exception as e:
                debug_print('failed to read gate type ' +
                            gate['type'] + '\n' + e)
                return False

            params = gate['parameters']
            if len(params.items()) > 0:
                debug_print(
                    f'failed to us NOR/NOT gates, got parameters: \n{params}')
                return False

            attribs = gate['attributes']
            if len(attribs.items()) > 0:
                debug_print(
                    f'failed to us NOR/NOT gates, got attributes: \n{attribs}')
                return False

            dirctns = gate['port_directions']
            ctns = gate['connections']
            d_items = dirctns.items()
            c_items = ctns.items()
            if len(d_items) != len(c_items):
                debug_print(
                    f'got gate mismatch: \nport directions\n{d_items}\nconnections\n{c_items}')
                return False
            
            for bitarray in ctns.values():
                if len(bitarray) > 1:
                    debug_print(f'too many connections in a gate: \n{node}')
                    return False
            
            in_count = 0
            out_count = 0
            for d in dirctns.values():
                if d not in ['input', 'output']:
                    debug_print(f'got a non IO gate: \n{node}')
                    return False
                else:
                    if d == 'input':
                        in_count += 1
                    else:
                        out_count += 1
            # max 2 in and 1 out per gate
            if in_count > 2 or out_count > 1:
                debug_print(f'failed to have less than 2 in and 1 out for gate: \n{node}')
                return False
            
        # check if all ports are used in cells
        used_ports = set()
        for _, cell in self.__cells.items():
            for _, connection in cell['connections'].items():
                used_ports.update(connection)

        notused_ports = []
        for _, port in self.__ports.items():
            port_bit = port['bits'][0]
            if port_bit not in used_ports:
                notused_ports.append(port_bit)
               
        if len(notused_ports) > 0: 
            debug_print(f"Ports {notused_ports} not used in any cell (gate).", False)
            return False

        return True