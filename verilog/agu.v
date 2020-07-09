/**
 * Address Generation Unit (AGU)
 */

/**** Module ****/
module agu( clk,
            clr,
            step,
            l0,
			l1,
			l2,
			j0,
			j1,
			j2,
			j3,
            addr_out,
            z0_out,
            z1_out,
            z2_out
);
           
parameter BWADDR    = 21;             /* Bitwidth of Address */
parameter BWLENGTH  = 8;


// Ports
input  wire                         clk;			    // Clock
input  wire                         clr;                // Clear
input  wire                         step;               // Step
input  wire [      BWADDR-1 : 0]    j0;					// Address jump: dimension 0
input  wire [      BWADDR-1 : 0]    j1;					// Address jump: dimension 1
input  wire [      BWADDR-1 : 0]    j2;					// Address jump: dimension 2
input  wire [      BWADDR-1 : 0]    j3;					// Address jump: dimension 3
input  wire [    BWLENGTH-1 : 0]    l0;					// Length: dimension 0
input  wire [    BWLENGTH-1 : 0]    l1;					// Length: dimension 1
input  wire [    BWLENGTH-1 : 0]    l2;					// Length: dimension 2
output reg  [      BWADDR-1 : 0]    addr_out;   		// Address generated
output wire                         z0_out;             // Signals when jump length 0 counter is 0
output wire                         z1_out;             // Signals when jump length 1 counter is 0
output wire                         z2_out;             // Signals when jump length 2 counter is 0


/* Local wires */
wire                            z0;
wire                            z1;
wire                            z2;



/* Local registers */
reg        [    BWLENGTH-1 : 0] i0 = 0;
reg        [    BWLENGTH-1 : 0] i1 = 0;
reg        [    BWLENGTH-1 : 0] i2 = 0;



//
// Wire Assignments
//

// zN signals are checks for zero on the iN counters
assign z0 = i0 == 0;
assign z1 = i1 == 0;
assign z2 = i2 == 0;

// jumpedN signals indicate when jumps happen
assign z0_out = step & z0;
assign z1_out = step & z1;
assign z2_out = step & z2;


// Index decrement & Address Bump logic
always @(posedge clk) begin
    if (clr) begin
        i0 <= l0;
        i1 <= l1;
        i2 <= l2;
        addr_out <= 0;
    end else if (step) begin
        if (z0 && z1 && z2) begin
            addr_out <= addr_out+j3;
            i0       <= l0;
            i1       <= l1;
            i2       <= l2;
        end else if(z0 && z1) begin
            addr_out <= addr_out+j2;
            i0       <= l0;
            i1       <= l1;
            i2       <= i2 - 1;
        end else if(z0) begin
            addr_out <= addr_out+j1;
            i0       <= l0;
            i1       <= i1 - 1;
        end else begin
            addr_out <= addr_out+j0;
            i0       <= i0 - 1;
        end
    end
end



/* Module end */
endmodule
