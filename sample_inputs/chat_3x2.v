module genetic_circuit (
    input wire a, b, c,
    output wire out1, out2
);

  wire not_a, not_b;
  wire and1, and2;
  wire nor1;
  wire or1;

  // Inverters (NOT gates)
  not (not_a, a);
  not (not_b, b);

  // AND gates
  and (and1, not_a, b);
  and (and2, c, not_b);

  // NOR gate
  nor (nor1, and1, and2);

  // OR gate
  or (or1, and1, and2);

  // Assign outputs
  assign out1 = nor1;
  assign out2 = or1;

endmodule
