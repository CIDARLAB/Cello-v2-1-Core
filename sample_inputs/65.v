module Main(in1, in2, out1);
  output out1;
  input in1, in2;  
  
  assign g1 = in1 ~| in2;
  assign g2 = in1 ~| g1;
  assign g3 = in2 ~| g1;
  assign g4 = g3 & g2;
  
  assign out1 = g4;
  
  endmodule
