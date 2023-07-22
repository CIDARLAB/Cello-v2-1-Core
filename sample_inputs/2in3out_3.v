module Main(
  input a,
  input b,
  output reg out3
);

  assign out3 = ~(a ^ b);
endmodule
