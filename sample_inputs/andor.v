module and_gate (a, b, c, out, out2);
    input a;
    input b;

    output out;
    output out2;

    assign out = a & b;
    assign out2 = a | c;

endmodule