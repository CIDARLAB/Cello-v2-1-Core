module Main(
  input a,
  input b,
  output out1
);

  assign out1 = ~(a | b);

endmodule
