module Main(in1, in2, out1, out2);
  output out1, out2;
  input in1, in2;  
  
  assign g1 = ~in1;
  assign g2 = in2 ~| in1;
  assign g3 = ~in2;
  assign g4 = g1 ~| g3;
  assign g5 = g4 ~| g2;
  assign g6 = ~g5;
  
  assign out1 = g6;
  assign out2 = g5;
  
  endmodule
