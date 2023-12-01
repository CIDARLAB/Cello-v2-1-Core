module fulladder (input x, y, cin, output F);

	wire \$n6_0;
	wire \$n16_0;
	wire \$n14_0;
	wire \$n12_0;
	wire \$n13_0;
	wire \$n13_1;
	wire \$n10_0;
	wire \$n11_0;
	wire \$n11_1;
	wire \$n8_0;
	wire \$n7_0;
	wire \$n9_0;
	wire \$n9_1;

	nor (\$n16_0, x, \$n11_1);
	nor (F, \$n16_0, \$n13_1);
	nor (\$n10_0, cin, y);
	nor (\$n11_0, \$n10_0, \$n9_1);
	nor (\$n11_1, \$n10_0, \$n9_1);
	not (\$n8_0, x);
	not (\$n12_0, \$n11_0);
	not (\$n7_0, y);
	not (\$n6_0, cin);
	nor (\$n9_0, \$n6_0, \$n7_0);
	nor (\$n9_1, \$n6_0, \$n7_0);
	nor (\$n13_0, \$n12_0, \$n8_0);
	nor (\$n13_1, \$n12_0, \$n8_0);
	nor (\$n14_0, \$n13_0, \$n9_0);
	not (cout, \$n14_0);
	
	assign F = {cout, A};

endmodule
