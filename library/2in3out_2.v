module Main(
  input a,
  input b,
  output reg out2
);

  assign out2 = ~(a & b);
endmodule
