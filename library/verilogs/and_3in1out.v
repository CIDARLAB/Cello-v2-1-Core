module and_gate (a, b, c, out);
    input a;
    input b;
    input c;

    output out;

    assign out = a & b & c;

endmodule