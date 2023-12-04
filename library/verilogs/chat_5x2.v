module genetic_circuit (
    input wire a, b, c, d, e,
    output wire out1, out2
);

  wire not_a, not_b, not_e;
  wire and1, and2, and3;
  wire nor1;
  wire or1;

  // Inverters (NOT gates)
  not (not_a, a);
  not (not_b, b);
  not (not_e, e);

  // AND gates
  and (and1, not_a, b);
  and (and2, c, not_b);
  and (and3, d, not_e);

  // NOR gate
  nor (nor1, and1, and2);

  // OR gate
  or (or1, and3, nor1);

  // Assign outputs
  assign out1 = nor1;
  assign out2 = or1;

endmodule