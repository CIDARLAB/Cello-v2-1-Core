module Main(in1, in2, out1);
  output out1;
  input in1, in2;  
  
  assign g1 = ~in2;
  assign g2 = g1 ~| in1;
  
  assign out1 = g2;
  
  endmodule
