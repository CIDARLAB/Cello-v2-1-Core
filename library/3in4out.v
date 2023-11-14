module gene_circuit (input in1, in2, in3, output out1, out2, out3, out4);

assign out1 = (in1 & in2) | (in2 & in3);
assign out2 = (in1 & in2) ^ (in2 & in3);
assign out3 = (~in1 & in2) | (in2 & in3);
assign out4 = (in1 & in2) & (in2 & in3);

endmodule
