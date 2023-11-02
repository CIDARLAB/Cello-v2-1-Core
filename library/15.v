module Main(in1, in2, in3, out1, out2, out3);
  output out1, out2, out3;
  input in1, in2, in3;  
  
  assign g1 = ~in1;
  assign g2 = ~in2;
  assign g3 = g1 ~| in3;
  assign g4 = g1 ~| g2;
  
  assign out1 = g2;
  assign out2 = g3;
  assign out3 = g4;
  
  endmodule
