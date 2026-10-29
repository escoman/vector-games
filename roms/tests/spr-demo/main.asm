;* * * * *  Small-C/Plus z88dk * * * * *
;  Version: 23854-4d530b6eb7-20251002
;
;	Reconstructed for z80 Module Assembler
;
;	Module compile time: Thu Oct 29 21:15:53 2026


	C_LINE	0,"main.c"

	MODULE	main_c


	INCLUDE "z80_crt0.hdr"


	EXTERN	saved_hl
	C_LINE	0,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	48,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	49,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	56,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	57,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	58,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	62,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	95,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	101,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	104,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	107,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	114,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	128,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	134,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	135,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	136,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	139,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	140,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	141,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	142,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	146,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	147,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	148,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	154,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	155,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	158,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	159,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	162,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	165,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	167,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	171,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	173,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	177,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	190,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	191,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	217,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	218,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	219,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	220,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	221,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	222,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	223,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	224,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	225,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	226,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	227,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	228,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	229,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	252,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	262,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	263,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	264,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	271,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	272,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	273,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	297,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	298,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	300,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	310,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	314,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	317,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	325,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	356,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	358,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	359,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	390,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	391,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	401,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	402,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	438,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	439,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	440,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	443,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	444,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	445,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	448,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	450,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	456,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	464,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	465,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	560,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	561,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	562,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	563,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	564,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	565,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	566,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	572,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	573,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	574,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	575,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	576,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	580,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	581,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	582,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	583,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	584,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	585,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	586,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	590,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	594,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	595,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	596,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	597,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	598,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	599,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	600,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	608,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	617,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	623,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	624,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	627,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	628,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	629,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	630,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	638,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	639,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	640,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	641,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	642,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	648,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	25,"main.c"
	C_LINE	0,"spr.inc"
	C_LINE	18,"spr.inc"
	SECTION	rodata_compiler
._inv_flat_0
	defb	12
	defb	3
	defb	24
	defb	8
	defb	3
	defb	1
	defb	3
	defb	1
	defb	7
	defb	7
	defb	128
	defb	201
	defb	255
	defb	255
	defb	255
	defb	255
	defb	127
	defb	7
	defb	6
	defb	128
	defb	192
	defb	224
	defb	192
	defb	128
	defb	128
	defb	5
	defb	19
	defb	1
	defb	3
	defb	3
	defb	7
	defb	7
	defb	7
	defb	15
	defb	7
	defb	7
	defb	7
	defb	3
	defb	3
	defb	1
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	0
	defb	24
	defb	36
	defb	36
	defb	36
	defb	44
	defb	127
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	0
	defb	0
	defb	0
	defb	255
	defb	255
	defb	203
	defb	195
	defb	195
	defb	195
	defb	195
	defb	5
	defb	19
	defb	192
	defb	224
	defb	224
	defb	240
	defb	240
	defb	240
	defb	248
	defb	240
	defb	240
	defb	240
	defb	224
	defb	224
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	SECTION	code_compiler
	C_LINE	29,"spr.inc"
	SECTION	rodata_compiler
._inv_flat_1
	defb	12
	defb	3
	defb	24
	defb	8
	defb	3
	defb	1
	defb	3
	defb	1
	defb	7
	defb	7
	defb	128
	defb	201
	defb	255
	defb	255
	defb	255
	defb	255
	defb	127
	defb	7
	defb	6
	defb	128
	defb	192
	defb	224
	defb	192
	defb	128
	defb	128
	defb	5
	defb	19
	defb	1
	defb	3
	defb	3
	defb	7
	defb	7
	defb	7
	defb	15
	defb	7
	defb	7
	defb	7
	defb	3
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	0
	defb	24
	defb	36
	defb	36
	defb	36
	defb	44
	defb	127
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	0
	defb	0
	defb	129
	defb	255
	defb	255
	defb	137
	defb	129
	defb	129
	defb	129
	defb	129
	defb	5
	defb	19
	defb	192
	defb	224
	defb	224
	defb	240
	defb	240
	defb	240
	defb	248
	defb	240
	defb	240
	defb	240
	defb	224
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	SECTION	code_compiler
	C_LINE	40,"spr.inc"
	SECTION	rodata_compiler
._inv_flat_2
	defb	12
	defb	3
	defb	24
	defb	8
	defb	3
	defb	1
	defb	3
	defb	1
	defb	7
	defb	7
	defb	128
	defb	201
	defb	255
	defb	255
	defb	255
	defb	255
	defb	127
	defb	7
	defb	6
	defb	128
	defb	192
	defb	224
	defb	192
	defb	128
	defb	128
	defb	5
	defb	19
	defb	1
	defb	3
	defb	3
	defb	7
	defb	7
	defb	7
	defb	15
	defb	7
	defb	7
	defb	7
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	7
	defb	0
	defb	24
	defb	36
	defb	36
	defb	36
	defb	44
	defb	127
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	0
	defb	0
	defb	0
	defb	255
	defb	255
	defb	203
	defb	195
	defb	195
	defb	195
	defb	231
	defb	5
	defb	19
	defb	192
	defb	224
	defb	224
	defb	240
	defb	240
	defb	240
	defb	248
	defb	240
	defb	240
	defb	240
	defb	224
	defb	224
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	defb	224
	SECTION	code_compiler
	C_LINE	51,"spr.inc"
	SECTION	rodata_compiler
._inv_mask_0
	defb	124
	defb	3
	defb	24
	defb	5
	defb	19
	defb	0
	defb	24
	defb	5
	defb	19
	defb	254
	defb	252
	defb	252
	defb	248
	defb	248
	defb	248
	defb	240
	defb	248
	defb	248
	defb	248
	defb	252
	defb	252
	defb	254
	defb	252
	defb	252
	defb	252
	defb	252
	defb	252
	defb	252
	defb	219
	defb	219
	defb	219
	defb	211
	defb	128
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	255
	defb	255
	defb	255
	defb	0
	defb	0
	defb	52
	defb	60
	defb	60
	defb	60
	defb	60
	defb	63
	defb	31
	defb	31
	defb	15
	defb	15
	defb	15
	defb	7
	defb	15
	defb	15
	defb	15
	defb	31
	defb	31
	defb	63
	defb	63
	defb	63
	defb	63
	defb	63
	defb	63
	defb	63
	defb	0
	defb	0
	defb	0
	defb	1
	defb	3
	defb	1
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	128
	defb	201
	defb	255
	defb	255
	defb	255
	defb	255
	defb	127
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	128
	defb	192
	defb	224
	defb	192
	defb	128
	defb	128
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	1
	defb	3
	defb	3
	defb	7
	defb	7
	defb	7
	defb	15
	defb	7
	defb	7
	defb	7
	defb	3
	defb	3
	defb	1
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	36
	defb	36
	defb	36
	defb	44
	defb	127
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	0
	defb	0
	defb	0
	defb	255
	defb	255
	defb	203
	defb	195
	defb	195
	defb	195
	defb	195
	defb	192
	defb	224
	defb	224
	defb	240
	defb	240
	defb	240
	defb	248
	defb	240
	defb	240
	defb	240
	defb	224
	defb	224
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	SECTION	code_compiler
	C_LINE	71,"spr.inc"
	SECTION	rodata_compiler
._inv_mask_1
	defb	124
	defb	3
	defb	24
	defb	5
	defb	19
	defb	0
	defb	24
	defb	5
	defb	19
	defb	254
	defb	252
	defb	252
	defb	248
	defb	248
	defb	248
	defb	240
	defb	248
	defb	248
	defb	248
	defb	252
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	219
	defb	219
	defb	219
	defb	211
	defb	128
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	255
	defb	255
	defb	126
	defb	0
	defb	0
	defb	118
	defb	126
	defb	126
	defb	126
	defb	126
	defb	63
	defb	31
	defb	31
	defb	15
	defb	15
	defb	15
	defb	7
	defb	15
	defb	15
	defb	15
	defb	31
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	0
	defb	0
	defb	0
	defb	1
	defb	3
	defb	1
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	128
	defb	201
	defb	255
	defb	255
	defb	255
	defb	255
	defb	127
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	128
	defb	192
	defb	224
	defb	192
	defb	128
	defb	128
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	1
	defb	3
	defb	3
	defb	7
	defb	7
	defb	7
	defb	15
	defb	7
	defb	7
	defb	7
	defb	3
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	15
	defb	36
	defb	36
	defb	36
	defb	44
	defb	127
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	0
	defb	0
	defb	129
	defb	255
	defb	255
	defb	137
	defb	129
	defb	129
	defb	129
	defb	129
	defb	192
	defb	224
	defb	224
	defb	240
	defb	240
	defb	240
	defb	248
	defb	240
	defb	240
	defb	240
	defb	224
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	SECTION	code_compiler
	C_LINE	91,"spr.inc"
	SECTION	rodata_compiler
._inv_mask_2
	defb	124
	defb	3
	defb	24
	defb	5
	defb	19
	defb	0
	defb	24
	defb	5
	defb	19
	defb	254
	defb	252
	defb	252
	defb	248
	defb	248
	defb	248
	defb	240
	defb	248
	defb	248
	defb	248
	defb	252
	defb	252
	defb	252
	defb	252
	defb	252
	defb	252
	defb	252
	defb	252
	defb	248
	defb	219
	defb	219
	defb	219
	defb	211
	defb	128
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	255
	defb	255
	defb	255
	defb	0
	defb	0
	defb	52
	defb	60
	defb	60
	defb	60
	defb	24
	defb	63
	defb	31
	defb	31
	defb	15
	defb	15
	defb	15
	defb	7
	defb	15
	defb	15
	defb	15
	defb	31
	defb	31
	defb	63
	defb	63
	defb	63
	defb	63
	defb	63
	defb	63
	defb	31
	defb	0
	defb	0
	defb	0
	defb	1
	defb	3
	defb	1
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	128
	defb	201
	defb	255
	defb	255
	defb	255
	defb	255
	defb	127
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	128
	defb	192
	defb	224
	defb	192
	defb	128
	defb	128
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	1
	defb	3
	defb	3
	defb	7
	defb	7
	defb	7
	defb	15
	defb	7
	defb	7
	defb	7
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	3
	defb	7
	defb	36
	defb	36
	defb	36
	defb	44
	defb	127
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	255
	defb	0
	defb	0
	defb	0
	defb	255
	defb	255
	defb	203
	defb	195
	defb	195
	defb	195
	defb	231
	defb	192
	defb	224
	defb	224
	defb	240
	defb	240
	defb	240
	defb	248
	defb	240
	defb	240
	defb	240
	defb	224
	defb	224
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	defb	192
	defb	224
	SECTION	code_compiler
	C_LINE	111,"spr.inc"
	SECTION	rodata_compiler
._inv_frames_flat
	defw	_inv_flat_0 + 0
	defw	_inv_flat_1 + 0
	defw	_inv_flat_2 + 0
	SECTION	code_compiler
	C_LINE	115,"spr.inc"
	SECTION	rodata_compiler
._inv_frames_mask
	defw	_inv_mask_0 + 0
	defw	_inv_mask_1 + 0
	defw	_inv_mask_2 + 0
	SECTION	code_compiler
	C_LINE	119,"spr.inc"
	SECTION	rodata_compiler
._inv_erase
	defb	12
	defb	3
	defb	24
	defb	0
	defb	24
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	24
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	24
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	24
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	24
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	24
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	SECTION	code_compiler
	C_LINE	26,"main.c"
	C_LINE	42,"main.c"
	SECTION	data_compiler
._pal16
	defb	235
	defb	7
	defb	247
	defb	0
	defb	255
	defb	255
	defb	255
	defb	255
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	SECTION	code_compiler
	C_LINE	57,"main.c"

; Function draw_checker flags 0x00000200 __smallc 
; void draw_checker(unsigned char x0, unsigned char y0, unsigned char w, unsigned char h)
; parameter 'unsigned char h' at sp+2 size(1)
; parameter 'unsigned char w' at sp+4 size(1)
; parameter 'unsigned char y0' at sp+6 size(1)
; parameter 'unsigned char x0' at sp+8 size(1)
	C_LINE	58,"main.c::draw_checker::0::0"
._draw_checker
	push	bc
	ld	hl,1	;const
	add	hl,sp
	ld	(hl),0
	jp	i_14	;EOS
.i_12
	ld	hl,1	;const
	add	hl,sp
	inc	(hl)
.i_14
	pop	hl
	push	hl
	ld	e,h
	ld	d,0
	ld	hl,6	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,e
	sub	l
	ld	a,d
	sbc	h
	jp	nc,i_13	;
	ld	hl,0	;const
	add	hl,sp
	ld	(hl),0
	jp	i_17	;EOS
.i_15
	ld	hl,0	;const
	add	hl,sp
	inc	(hl)
.i_17
	pop	hl
	push	hl
	ld	h,0
	ex	de,hl
	ld	hl,4	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,e
	sub	l
	ld	a,d
	sbc	h
	jp	nc,i_16	;
	ld	hl,57344	;const
	push	hl
	ld	hl,10	;const
	add	hl,sp
	ld	e,(hl)
	ld	d,0
	ld	hl,2	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,de
	ld	de,255
	call	l_sub
	push	hl
	ld	hl,14	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,l
	rrca
	rrca
	rrca
	and	31
	ld	l,a
	ex	de,hl
	ld	hl,5	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,de
	ld	h,l
	ld	l,0
	pop	de
	add	hl,de
	pop	de
	add	hl,de
	push	hl
	ld	hl,10	;const
	add	hl,sp
	ld	e,(hl)
	ld	d,0
	ld	hl,2	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,de
	ld	a,l
	rrca
	rrca
	rrca
	and	31
	ld	l,a
	ex	de,hl
	ld	hl,3	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,de
	ld	a,l
	and	1
	jp	z,i_18	;
	ld	hl,255	;const
	jp	i_19	;
.i_18
	ld	hl,0	;const
.i_19
	pop	de
	ld	a,l
	ld	(de),a
	jp	i_15	;EOS
.i_13
	pop	bc
	ret


	C_LINE	67,"main.c::draw_checker::0::1"

; Function draw_stripes flags 0x00000200 __smallc 
; void draw_stripes(unsigned char x0, unsigned char y0, unsigned char w, unsigned char h)
; parameter 'unsigned char h' at sp+2 size(1)
; parameter 'unsigned char w' at sp+4 size(1)
; parameter 'unsigned char y0' at sp+6 size(1)
; parameter 'unsigned char x0' at sp+8 size(1)
	C_LINE	68,"main.c::draw_stripes::0::1"
._draw_stripes
	push	bc
	ld	hl,1	;const
	add	hl,sp
	ld	(hl),0
	jp	i_22	;EOS
.i_20
	ld	hl,1	;const
	add	hl,sp
	inc	(hl)
.i_22
	pop	hl
	push	hl
	ld	e,h
	ld	d,0
	ld	hl,6	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,e
	sub	l
	ld	a,d
	sbc	h
	jp	nc,i_21	;
	ld	hl,0	;const
	add	hl,sp
	ld	(hl),0
	jp	i_25	;EOS
.i_23
	ld	hl,0	;const
	add	hl,sp
	inc	(hl)
.i_25
	pop	hl
	push	hl
	ld	h,0
	ex	de,hl
	ld	hl,4	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,e
	sub	l
	ld	a,d
	sbc	h
	jp	nc,i_24	;
	ld	hl,49152	;const
	push	hl
	ld	hl,10	;const
	add	hl,sp
	ld	e,(hl)
	ld	d,0
	ld	hl,2	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,de
	ld	de,255
	call	l_sub
	push	hl
	ld	hl,14	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,l
	rrca
	rrca
	rrca
	and	31
	ld	l,a
	ex	de,hl
	ld	hl,5	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,de
	ld	h,l
	ld	l,0
	pop	de
	add	hl,de
	pop	de
	add	hl,de
	ld	(hl),204
	jp	i_23	;EOS
.i_21
	pop	bc
	ret


	C_LINE	75,"main.c::draw_stripes::0::2"

; Function main flags 0x00000000 __stdc 
; int main()
	C_LINE	75,"main.c::main::0::3"
._main
	ld	hl,766
	push	hl
	dec	sp
	pop	hl
	ld	l,16
	push	hl
	dec	sp
	ld	hl,26624
	push	hl
	ld	hl,0	;const
	push	hl
	call	_gfx_set_mode
	ld	hl,_pal16
	ex	(sp),hl
	call	_gfx_set_palette
	pop	bc
	ld	hl,15	;const
	push	hl
	ld	l,0
	push	hl
	call	_gfx_fill_planes
	call	_spr_init
	ld	hl,16	;const
	push	hl
	ld	l,40
	push	hl
	ld	hl,6	;const
	push	hl
	ld	l,48
	push	hl
	call	_draw_checker
	pop	bc
	pop	bc
	pop	bc
	pop	bc
	ld	hl,80	;const
	push	hl
	ld	l,112
	push	hl
	ld	hl,6	;const
	push	hl
	ld	l,48
	push	hl
	call	_draw_stripes
	pop	bc
	pop	bc
	pop	bc
	pop	bc
	ld	a,12
	ld	(_gfx_active_planes),a
	ld	hl,8	;const
	push	hl
	ld	l,1
	push	hl
	ld	hl,i_1+0
	push	hl
	ld	hl,4	;const
	push	hl
	call	_gfx_print
	ld	hl,2	;const
	push	hl
	ld	l,4
	push	hl
	ld	de,i_1+26
	push	de
	push	hl
	call	_gfx_print
	ld	hl,10	;const
	push	hl
	ld	l,13
	push	hl
	ld	hl,i_1+50
	push	hl
	ld	hl,4	;const
	push	hl
	call	_gfx_print
	ld	a,15
	ld	(_gfx_active_planes),a
	ld	hl,2	;const
	add	hl,sp
	push	hl
	dec	hl
	ld	a,(hl)
	pop	de
	ld	(de),a
.i_28
	pop	hl
	push	hl
	ld	h,0
	ld	a,l
	rrca
	rrca
	and	63
	ld	l,a
	ld	de,3
	ex	de,hl
	call	l_div_u
	ex	de,hl
	ld	h,0
	dec	sp
	ld	a,l
	pop	hl
	ld	l,a
	push	hl
	call	_gfx_next_frame
	ld	hl,16	;const
	push	hl
	ld	l,40
	push	hl
	ld	hl,6	;const
	push	hl
	ld	l,48
	push	hl
	call	_draw_checker
	pop	bc
	pop	bc
	pop	bc
	pop	bc
	ld	hl,4	;const
	add	hl,sp
	push	hl
	ld	l,(hl)
	ld	h,0
	push	hl
	ld	hl,10	;const
	add	hl,sp
	call	l_gchar
	pop	de
	add	hl,de
	pop	de
	ld	a,l
	ld	(de),a
	ld	hl,4	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,16
	sub	l
	ccf
	jp	c,i_30	;
	ld	hl,4	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,l
	sub	40
	ccf
	jp	nc,i_29	;
.i_30
	ld	hl,6	;const
	add	hl,sp
	push	hl
	ld	a,(hl)
	neg
	pop	de
	ld	(de),a
.i_29
	ld	hl,4	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	push	hl
	ld	hl,52	;const
	push	hl
	ld	hl,_inv_frames_mask
	push	hl
	ld	hl,6	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,hl
	pop	de
	add	hl,de
	call	l_gint	;
	push	hl
	call	_spr_blit_mask
	ld	hl,2	;const
	add	hl,sp
	push	hl
	ld	l,(hl)
	ld	h,0
	push	hl
	ld	hl,9	;const
	add	hl,sp
	call	l_gchar
	pop	de
	add	hl,de
	pop	de
	ld	a,l
	ld	(de),a
	ld	hl,2	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,80
	sub	l
	ccf
	jp	c,i_33	;
	ld	hl,2	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,l
	sub	104
	ccf
	jp	nc,i_32	;
.i_33
	ld	hl,5	;const
	add	hl,sp
	push	hl
	ld	a,(hl)
	neg
	pop	de
	ld	(de),a
.i_32
	pop	hl
	push	hl
	ld	l,h
	ld	h,0
	ld	a,l
	and	a
	jp	z,ASMPC+4
	scf
	jp	nc,i_35	;
	ld	hl,3	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	push	hl
	ld	hl,124	;const
	push	hl
	ld	hl,_inv_erase
	push	hl
	call	_spr_blit
.i_35
	ld	hl,2	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	push	hl
	ld	hl,124	;const
	push	hl
	ld	hl,_inv_frames_flat
	push	hl
	ld	hl,6	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,hl
	pop	de
	add	hl,de
	call	l_gint	;
	push	hl
	call	_spr_blit
	ld	hl,3	;const
	add	hl,sp
	ex	de,hl
	ld	hl,2	;const
	add	hl,sp
	ld	a,(hl)
	ld	(de),a
	ld	hl,1	;const
	add	hl,sp
	inc	(hl)
	ld	l,(hl)
	ld	h,0
	dec	l
	inc	sp
	jp	i_26	;EOS
.i_27
	ld	hl,0	;const
	pop	bc
	pop	bc
	pop	bc
	ret


	SECTION	bss_compiler
	SECTION	code_compiler
; --- Start of Optimiser additions ---
	defc	i_26 = i_28
	defc	i_16 = i_12
	defc	i_24 = i_20

	SECTION	rodata_compiler
.i_1
	defm	"SPR-DEMO: LIB SPR KERNELS"
	defb	0

	defm	"spr_blit_mask: no erase"
	defb	0

	defm	"spr_blit: erase+draw"
	defb	0


; --- Start of Static Variables ---

	SECTION	bss_compiler
	SECTION	code_compiler


; --- Start of Scope Defns ---

	GLOBAL	_v06_out
	GLOBAL	_v06_in
	GLOBAL	_frame_count
	GLOBAL	_irq_active
	GLOBAL	_frame_handler
	GLOBAL	_v06_wait_frame
	GLOBAL	_timer_start
	GLOBAL	_timer_start_sync
	GLOBAL	_timer_read
	GLOBAL	_timer_elapsed
	GLOBAL	_timer_wait
	GLOBAL	_gfx_modes
	GLOBAL	_gfx_current_mode
	GLOBAL	_gfx_active_planes
	GLOBAL	_gfx_set_mode
	GLOBAL	_gfx_clear
	GLOBAL	_gfx_fill_planes
	GLOBAL	_gfx_fill_stride
	GLOBAL	_gfx_set_palette
	GLOBAL	_gfx_set_bmp_palette
	GLOBAL	_gfx_set_black_palette
	GLOBAL	_gfx_fade_in
	GLOBAL	_gfx_fade_out
	GLOBAL	_gfx_set_scroll
	GLOBAL	_gfx_scroll_row
	GLOBAL	_gfx_next_frame
	GLOBAL	_gfx_put_char
	GLOBAL	_gfx_print
	GLOBAL	_gfx_put_char_512
	GLOBAL	_gfx_print_512
	GLOBAL	_gfx_print_512t
	GLOBAL	_gfx_plane_or
	GLOBAL	_gfx_plane_andn
	GLOBAL	_gfx_dblbuf_init
	GLOBAL	_gfx_dblbuf_present
	GLOBAL	_gfx_dblbuf_show
	GLOBAL	_gfx_dblbuf_set_planes
	GLOBAL	_gfx_dblbuf_copy_ab
	GLOBAL	_gfx_dblbuf_copy_ba
	GLOBAL	_gfx_dblbuf_isr
	GLOBAL	_gfx_dblbuf_front
	GLOBAL	_gfx_dblbuf_back
	GLOBAL	_gfx_dblbuf_front_pal
	GLOBAL	_gfx_dblbuf_back_pal
	GLOBAL	_gfx_dblbuf_invalidate
	GLOBAL	_gfx_dblbuf_set_front
	GLOBAL	_gfx_font_8x8
	GLOBAL	_gfx_font_16x8
	GLOBAL	_gfx_font_thin
	GLOBAL	_gfx_select_font
	GLOBAL	_gfx_select_font_512
	GLOBAL	_gfx_select_font_512t
	GLOBAL	_spr_init
	GLOBAL	_spr_blit
	GLOBAL	_spr_blit_mask
	GLOBAL	_gfx_rle_expand
	GLOBAL	_gfx_rle_expand_512
	GLOBAL	_gfx_lz_expand
	GLOBAL	_zx0_decompress
	GLOBAL	_heap_top
	GLOBAL	_heap_alloc
	GLOBAL	_heap_avail
	GLOBAL	_v06_div_tab
	GLOBAL	_v06_ay_period_tab
	GLOBAL	_vi53_set_channel
	GLOBAL	_vi53_set_channel_m0
	GLOBAL	_ay_write
	GLOBAL	_ay_set_r7
	GLOBAL	_ay_mixer_init
	GLOBAL	_ay_set_tone_period
	GLOBAL	_ay_note_off
	GLOBAL	_ay_mute_all
	GLOBAL	_ay_set_envelope
	GLOBAL	_ay_set_fixed_volume
	GLOBAL	_sound_init
	GLOBAL	_sound_silence
	GLOBAL	_sound_set_data
	GLOBAL	_sound_set_tempo
	GLOBAL	_sound_set_loop
	GLOBAL	_sound_start
	GLOBAL	_sound_stop
	GLOBAL	_sound_is_playing
	GLOBAL	_sound_tick
	GLOBAL	_drum_route_tape
	GLOBAL	_drum_route_ay
	GLOBAL	_drum_init
	GLOBAL	_drum_tick
	GLOBAL	_drum_mute
	GLOBAL	_drum_kick
	GLOBAL	_drum_snare
	GLOBAL	_drum_hat_c
	GLOBAL	_drum_hat_o
	GLOBAL	_drum_tom
	GLOBAL	_drum_clap
	GLOBAL	_drum_rim
	GLOBAL	_drum_sample_play
	GLOBAL	_drum_tape_step
	GLOBAL	_drum_tape_generate
	GLOBAL	_drum_tape_mode_frame
	GLOBAL	_drum_tape_mode_manual
	GLOBAL	_drum_tape_mode_manual_env
	GLOBAL	_drum_tape_running
	GLOBAL	_drum_tape_set_steps_per_tick
	GLOBAL	_sfx_init
	GLOBAL	_sfx_set_channel_mask
	GLOBAL	_sfx_play
	GLOBAL	_sfx_stop_all
	GLOBAL	_sfx_busy
	GLOBAL	_sfx_tick
	GLOBAL	_kbd_scan
	GLOBAL	_kbd_scan_now
	GLOBAL	_kbd_read
	GLOBAL	_kbd_wait_key
	GLOBAL	_kbd_is_down
	GLOBAL	_kbd_rows
	GLOBAL	_main


; --- End of Scope Defns ---


; --- End of Compilation ---
