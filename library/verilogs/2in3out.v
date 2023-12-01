module multiple_outputs (
  input a,
  input b,
  output reg out1,
  output reg out2,
  output reg out3
);

  assign out1 = ~(a | b);
  assign out2 = ~(a & b);
  assign out3 = ~(a ^ b);

endmodule
