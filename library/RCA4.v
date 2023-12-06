`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 03/25/2021 06:51:14 PM
// Design Name: 
// Module Name: RCA4
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////

module RCA(
        input A, B, Cin,
        output S,
        output Cout
    );
    
    assign Cout = A*B + (A^B)*Cin;
    assign S = A^B^Cin;
        
endmodule

module RCA4(
    input [3:0]A, B,
    input Cin,
    output [3:0]S,
    output Cout
    );
    
    wire [2:0]C;
    
    RCA rca1(A[0], B[0], Cin, S[0], C[0]);
    RCA rca2(A[1], B[1], C[0], S[1], C[1]);
    RCA rca3(A[2], B[2], C[1], S[2], C[2]);
    RCA rca4(A[3], B[3], C[2], S[3], Cout);
    
endmodule
