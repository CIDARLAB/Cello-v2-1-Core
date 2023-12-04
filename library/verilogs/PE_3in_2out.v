module Main(in1,in2, in3, out1, out2);
  output out1, out2;
  input in1, in2, in3;

  assign g1 = ~in1;
  assign g2 = g1 ~| in2;
  assign g3 = ~g2;
  assign g4 = in3 ~| g3;

  assign out1 = g3;
  assign out2 = g4;

  endmodule