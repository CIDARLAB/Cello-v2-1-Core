module struct(output x, input a, b, c);
    wire w1, w2, w3, w4, w5; 
    not (w1, c);
    not (w5, b);
    not (w4, a);
    nor (w3, w4, w5); 
    not (w2, w3); 
    nor (x, w1, w2);
endmodule