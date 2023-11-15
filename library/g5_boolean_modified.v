module Main(r1,r0, out);
  output out;
  input r1, r0;
  
  assign g5 = ~r1;
  assign g6 = ~r0;
  assign g17 = r0 ~| g5;
  assign g15 = g5 ~| g6;
  assign g16 = r1 ~| g6;

  assign out = g15 ~| (g16 ~| g17);
  // assign out = g15 ~| (g16 ~| g17)
  // assign out = (g15 ~| g16) ~| g17
  // assign out = (g15 ~| g17) ~| g16
  
endmodule



// module Main(r1,r0, sel, out);
//   output out;
//   input r1, r0;
  
//   assign g5 = ~r1;
//   assign g6 = ~r0;
//   assign g17 = r0 ~| g5;
//   assign g15 = g5 ~| g6;
//   assign g16 = r1 ~| g6;
  
//   assign out = sel ? ~g17 : ~g15;

// endmodule



// module Main(in118,in126, ao_0);
//   output ao_0;
//   input in118, in126;
 
//   assign ao_0 = ~((in126 ~| ~in118) ~| (in118 ~| ~in126));

// endmodule