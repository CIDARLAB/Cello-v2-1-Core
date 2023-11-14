module Main(in1,in2, in3, out1);
  output out1;
  input in1, in2, in3;

  assign g1 = in1 ~| in2;
  assign g2 = in3 ~| g1;

  assign out1 = g2;

  endmodule