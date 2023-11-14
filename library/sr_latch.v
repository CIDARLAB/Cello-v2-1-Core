// file: sr_latch.v
// Using Verilog to describe our SR Latch
module sr_latch(
    input wire S, R,
    output wire Q, Q_not);

    assign Q     = ~(R | Q_not);
    assign Q_not = ~(S | Q);
endmodule
