module and_gate (a, b, c, out, out2);
    input a;
    input b;
    input c;

    output out;
    output out2;

    assign out = a & b & c;
    assign out2 = a | c;

endmodule