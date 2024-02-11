module Main(in1,in2, in3, out1, out2);
  output out1, out2;
  input in1, in2, in3;  
  
  assign g1 = in1 ~| in2;
  assign g2 = in3 ~| g1;
  
  assign out1 = g2;
  assign out2 = g1;
  
  endmodule
