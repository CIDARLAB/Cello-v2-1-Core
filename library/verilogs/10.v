module Main(in1, in2, out1, out2, out3);
  output out1, out2, out3;
  input in1, in2;  
  
  assign g1 = ~in1;
  assign g2 = ~in2;
  assign g3 = in2 ~| g1;
  assign g4 = g1 ~| g2;
  assign g5 = g2 ~| in1;
  assign g6 = ~g3;
  assign g7 = ~g4;
  assign g8 = ~g5;
  
  assign out1 = g6;
  assign out2 = g7;
  assign out3 = g8;
  
  endmodule
