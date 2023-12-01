module Main(r1,r0, out26, out24, out25);
  output out24, out25, out26;
  input r1, r0;
//   wire g5, g6, g128, g129, g130;
  
  assign g5 = ~r1;
  assign g6 = ~r0;
  assign g17 = r0 ~| g5;
  assign g15 = g5 ~| g6;
  assign g16 = r1 ~| g6;
  
  assign out26 = ~g17;
  assign out24 = ~g15;
  assign out25 = ~g16;
  

endmodule



// module Main(in118,in126, ao_0);
//   output ao_0;
//   input in118, in126;
//  
//   assign ao_0 = ~((in126 ~| ~in118) ~| (in118 ~| ~in126));
//   
// 
// endmodule