module mux4to1 (input a, b, c, d, sel, output y);
    assign y = (sel == 0) ? a : (sel == 1) : b : (sel == 2) ? c : d;
endmodule