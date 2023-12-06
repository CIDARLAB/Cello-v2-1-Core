// module multiple_outputs (
//   input a,
//   input b,
//   output reg [7:0] out1,
//   output reg [3:0] out2
// );
  
//   assign out1 = a + b;
//   assign out2 = a - b;

// endmodule

module single_output (
  input a,
  input b,
  output reg [11:0] out
);

  wire [7:0] out1;
  wire [3:0] out2;
  multiple_outputs m_out (
    .a(a),
    .b(b),
    .out1(out1),
    .out2(out2)
  );

  assign out = {out2, out1};

endmodule
