module Main(m1,in67, out71, out91);
  output out71, out91;
  input m1, in67;  
  
  assign g68 = ~in67;
  assign g69 = in67 ~| m1;
  assign g70 = ~m1;
  assign out71 = g68 ~| g70;
  assign out91 = g69 ~| (g68 ~| g70);
  
  endmodule
