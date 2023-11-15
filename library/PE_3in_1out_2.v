module Main(in1,in2, in3, out1);
  output out1;
  input in1, in2, in3;

  assign g1 = ~in1;
  assign g2 = in1 ~| in2;
  assign g3 = g1 ~| in3;
  assign g4 = g3 ~| g2;

  assign out1 = g4;

  endmodule