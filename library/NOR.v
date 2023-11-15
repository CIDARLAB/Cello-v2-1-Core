module Main(in1, in2, out1);
  output out1;
  input in1, in2;  
  
  assign g1 = in1 ~| in2;
  
  
  assign out1 = g1;
  
  endmodule
  
 // Single Nor Gate
 // Total Gates: 33
 // Gates: 2, 4, 5, 8, 21, 22, 24, 25, 26, 27, 28, 30, 33, 34, 35, 38, 39, 41, 42, 43, 44, 45, 46, 49, 51, 53, 54, 55, 56, 57, 59, 60, 66
