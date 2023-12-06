module Main(in1,in2, in3, out1, out2);
  output out1, out2;
  input in1, in2, in3;

  assign g1 = in1 ~| in2;
  assign g2 = ~in2;
  assign g3 = in3 ~| g2;
  assign g4 = g1 ~| g3;

  assign out1 = g1;
  assign out2 = g4;

  endmodule