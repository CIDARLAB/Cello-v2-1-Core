module Main(a0, in76, out84);
  input a0, in76;
  output out84;

  
  assign g77 = ~a0;
  assign g78 = a0 ~| in76;
  assign g79 = ~in76;
  assign g80 = g77 ~| g79;
  
  assign out84 = g78 ~| g80;

endmodule

