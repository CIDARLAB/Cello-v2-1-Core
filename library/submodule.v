// N.B. - Place module definitions above those in which they are
// instantiated. Module `mysub` is instantiated in module `main`, so 
// `mysub` is defined before `main`.

// SUB module
module mysub(output out, input a, b); 
    and(out, a, b);
endmodule

// MAIN module
module main(output out, input a, b, c, d);
    wire w1, w2;
    mysub s1(w1, a, b); 
    mysub s2(w2, c, d); 
    and(out, w1, w2);
endmodule