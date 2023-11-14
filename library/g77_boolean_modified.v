module Main(a0, in76, sel, out);
  input a0, in76, sel;
  output out;
  
  wire g77, g78, g79, g80, temp_out;
  
  assign g77 = ~a0;
  assign g78 = a0 ~| in76;
  assign g79 = ~in76;
  assign g80 = g77 ~| g79;
  assign temp_out = g78 ~| g80;
  
  assign out = sel ? ~(temp_out) : temp_out;
endmodule

