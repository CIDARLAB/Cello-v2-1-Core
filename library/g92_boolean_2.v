module Main(t1, in91, out98);
  output out98;
  input t1, in91;  
  
  assign g92 = ~t1;
  assign g93 = t1 ~| in91;
  assign g94 = ~in91;
  assign g98 = g94 ~| g92;
  assign g104 = g93 ~| g98;

  assign out98 = g98;
  
  
  endmodule
