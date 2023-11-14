module Main(a0, in76, out81);
  input a0, in76;
  output out81;
  
  
  assign g77 = ~a0;
  assign g78 = a0 ~| in76;
  assign g79 = ~in76;
  assign g80 = g77 ~| g79;

  assign out81 = g78 ~| g80;

endmodule

