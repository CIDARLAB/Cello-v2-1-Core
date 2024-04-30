/*
This file contains example verilog code.
The circuit represented below can be converted to a genetic circuit by the Cello program.
You may use either structural or behavioral verilog.  Comment or remove the unused form.
*/


// Structural form

module and_gate (in_A, in_B, out);

    input in_A;
    input in_B;

    output out;

    and(out, in_A, in_B);

endmodule



// Behavioral form
/*
module and_gate (output reg out, input in_A, in_B);

	always @ (in_A or in_B) begin
	
		if (in_A == 1'b1 & in_B == 1'b1) begin
			out = 1'b1;
		end
		else 
			out = 1'b0; 
			
	end
	
endmodule
*/
