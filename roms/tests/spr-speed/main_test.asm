;* * * * *  Small-C/Plus z88dk * * * * *
;  Version: 23854-4d530b6eb7-20251002
;
;	Reconstructed for z80 Module Assembler
;
;	Module compile time: Thu Oct 29 13:45:28 2026


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
	C_LINE	282,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	286,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	289,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	297,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	328,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	330,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	331,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	362,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	363,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	373,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	374,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	410,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	411,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	412,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	415,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	416,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	417,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	420,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	422,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	428,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	436,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	437,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	532,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	533,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	534,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	535,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	536,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	537,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	538,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	544,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	545,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	546,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	547,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	548,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	552,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	553,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	554,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	555,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	556,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	557,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	558,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	562,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	566,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	567,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	568,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	569,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	570,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	571,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	572,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	580,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	589,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	595,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	596,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	599,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	600,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	601,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	602,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	610,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	611,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	612,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	613,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	614,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	620,"/home/alexey/Projects/vector-games/lib/v06.h"
	C_LINE	20,"main.c"
	C_LINE	0,"mario_old.inc"
	C_LINE	17,"mario_old.inc"
	SECTION	rodata_compiler
._mario1_l
	defb	3
	defb	4
	defb	32
	defb	10
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
	defb	12
	defb	12
	defb	12
	defb	15
	defb	15
	defb	15
	defb	31
	defb	31
	defb	17
	defb	31
	defb	31
	defb	16
	defb	1
	defb	127
	defb	127
	defb	127
	defb	255
	defb	255
	defb	255
	defb	63
	defb	48
	defb	63
	defb	31
	defb	20
	defb	31
	defb	127
	defb	116
	defb	127
	defb	255
	defb	128
	defb	255
	defb	255
	defb	130
	defb	255
	defb	127
	defb	71
	defb	127
	defb	2
	defb	63
	defb	60
	defb	63
	defb	31
	defb	16
	defb	31
	defb	15
	defb	15
	defb	15
	defb	31
	defb	17
	defb	31
	defb	63
	defb	32
	defb	63
	defb	63
	defb	32
	defb	63
	defb	127
	defb	113
	defb	127
	defb	127
	defb	95
	defb	127
	defb	3
	defb	127
	defb	89
	defb	127
	defb	127
	defb	127
	defb	127
	defb	63
	defb	63
	defb	63
	defb	63
	defb	63
	defb	63
	defb	31
	defb	31
	defb	31
	defb	7
	defb	7
	defb	4
	defb	15
	defb	15
	defb	8
	defb	15
	defb	15
	defb	15
	defb	4
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
	defb	96
	defb	96
	defb	96
	defb	224
	defb	160
	defb	224
	defb	224
	defb	32
	defb	224
	defb	240
	defb	48
	defb	240
	defb	5
	defb	248
	defb	184
	defb	104
	defb	248
	defb	248
	defb	200
	defb	252
	defb	252
	defb	228
	defb	252
	defb	124
	defb	252
	defb	252
	defb	100
	defb	252
	defb	252
	defb	228
	defb	252
	defb	252
	defb	68
	defb	252
	defb	248
	defb	8
	defb	248
	defb	6
	defb	240
	defb	48
	defb	240
	defb	248
	defb	120
	defb	248
	defb	248
	defb	248
	defb	200
	defb	252
	defb	252
	defb	132
	defb	252
	defb	252
	defb	132
	defb	252
	defb	252
	defb	132
	defb	255
	defb	255
	defb	15
	defb	255
	defb	252
	defb	27
	defb	7
	defb	255
	defb	248
	defb	255
	defb	255
	defb	253
	defb	254
	defb	255
	defb	255
	defb	254
	defb	249
	defb	249
	defb	249
	defb	240
	defb	240
	defb	240
	defb	240
	defb	240
	defb	16
	defb	240
	defb	240
	defb	16
	defb	240
	defb	240
	defb	240
	defb	10
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
	defb	192
	defb	192
	defb	192
	defb	11
	defb	224
	defb	224
	defb	96
	defb	240
	defb	176
	defb	112
	defb	248
	defb	24
	defb	248
	defb	248
	defb	56
	defb	200
	defb	248
	defb	248
	defb	136
	defb	248
	defb	248
	defb	152
	defb	112
	defb	112
	defb	112
	defb	0
	defb	0
	defb	0
	SECTION	code_compiler
	C_LINE	42,"mario_old.inc"
	SECTION	rodata_compiler
._mario2_l
	defb	3
	defb	4
	defb	32
	defb	10
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
	defb	12
	defb	12
	defb	12
	defb	15
	defb	11
	defb	15
	defb	15
	defb	15
	defb	8
	defb	15
	defb	15
	defb	8
	defb	1
	defb	63
	defb	63
	defb	63
	defb	127
	defb	127
	defb	127
	defb	63
	defb	48
	defb	63
	defb	31
	defb	26
	defb	31
	defb	63
	defb	58
	defb	63
	defb	127
	defb	64
	defb	127
	defb	127
	defb	65
	defb	127
	defb	255
	defb	231
	defb	255
	defb	2
	defb	63
	defb	62
	defb	63
	defb	15
	defb	8
	defb	15
	defb	7
	defb	7
	defb	7
	defb	47
	defb	47
	defb	44
	defb	127
	defb	95
	defb	121
	defb	127
	defb	94
	defb	115
	defb	63
	defb	62
	defb	51
	defb	63
	defb	45
	defb	63
	defb	3
	defb	63
	defb	44
	defb	63
	defb	63
	defb	63
	defb	63
	defb	127
	defb	127
	defb	127
	defb	255
	defb	255
	defb	159
	defb	254
	defb	254
	defb	142
	defb	124
	defb	124
	defb	68
	defb	60
	defb	60
	defb	36
	defb	24
	defb	24
	defb	24
	defb	4
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
	defb	48
	defb	48
	defb	48
	defb	112
	defb	80
	defb	112
	defb	240
	defb	144
	defb	240
	defb	240
	defb	144
	defb	112
	defb	5
	defb	248
	defb	216
	defb	56
	defb	252
	defb	252
	defb	196
	defb	252
	defb	124
	defb	228
	defb	254
	defb	62
	defb	254
	defb	254
	defb	50
	defb	254
	defb	254
	defb	114
	defb	254
	defb	254
	defb	34
	defb	254
	defb	252
	defb	132
	defb	252
	defb	6
	defb	248
	defb	24
	defb	248
	defb	252
	defb	60
	defb	252
	defb	254
	defb	254
	defb	226
	defb	254
	defb	254
	defb	226
	defb	255
	defb	31
	defb	241
	defb	255
	defb	15
	defb	249
	defb	255
	defb	15
	defb	249
	defb	255
	defb	31
	defb	243
	defb	7
	defb	255
	defb	254
	defb	255
	defb	255
	defb	254
	defb	255
	defb	255
	defb	255
	defb	255
	defb	254
	defb	254
	defb	250
	defb	254
	defb	254
	defb	250
	defb	126
	defb	126
	defb	114
	defb	252
	defb	252
	defb	132
	defb	248
	defb	248
	defb	248
	defb	10
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
	defb	224
	defb	224
	defb	224
	defb	248
	defb	216
	defb	56
	defb	11
	defb	252
	defb	220
	defb	44
	defb	252
	defb	220
	defb	36
	defb	252
	defb	156
	defb	100
	defb	252
	defb	252
	defb	204
	defb	56
	defb	56
	defb	56
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
	C_LINE	67,"mario_old.inc"
	SECTION	rodata_compiler
._mario3_l
	defb	3
	defb	4
	defb	32
	defb	10
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
	defb	24
	defb	24
	defb	31
	defb	23
	defb	31
	defb	31
	defb	23
	defb	24
	defb	15
	defb	15
	defb	8
	defb	1
	defb	63
	defb	63
	defb	63
	defb	127
	defb	127
	defb	127
	defb	63
	defb	48
	defb	63
	defb	31
	defb	21
	defb	31
	defb	31
	defb	21
	defb	31
	defb	63
	defb	32
	defb	63
	defb	63
	defb	32
	defb	63
	defb	127
	defb	115
	defb	127
	defb	2
	defb	31
	defb	31
	defb	31
	defb	15
	defb	8
	defb	15
	defb	111
	defb	111
	defb	111
	defb	255
	defb	159
	defb	249
	defb	255
	defb	191
	defb	241
	defb	255
	defb	191
	defb	227
	defb	127
	defb	127
	defb	103
	defb	127
	defb	89
	defb	127
	defb	3
	defb	255
	defb	249
	defb	159
	defb	255
	defb	255
	defb	143
	defb	255
	defb	255
	defb	143
	defb	255
	defb	255
	defb	143
	defb	248
	defb	248
	defb	200
	defb	112
	defb	112
	defb	112
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	0
	defb	4
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
	defb	28
	defb	28
	defb	28
	defb	188
	defb	164
	defb	188
	defb	252
	defb	196
	defb	124
	defb	252
	defb	196
	defb	60
	defb	5
	defb	252
	defb	228
	defb	28
	defb	252
	defb	252
	defb	196
	defb	252
	defb	60
	defb	244
	defb	254
	defb	30
	defb	254
	defb	254
	defb	26
	defb	254
	defb	255
	defb	57
	defb	255
	defb	255
	defb	145
	defb	255
	defb	254
	defb	194
	defb	254
	defb	6
	defb	252
	defb	12
	defb	252
	defb	248
	defb	56
	defb	248
	defb	252
	defb	252
	defb	196
	defb	254
	defb	254
	defb	130
	defb	255
	defb	255
	defb	113
	defb	255
	defb	143
	defb	249
	defb	255
	defb	7
	defb	253
	defb	255
	defb	7
	defb	255
	defb	7
	defb	255
	defb	140
	defb	255
	defb	255
	defb	254
	defb	243
	defb	255
	defb	255
	defb	251
	defb	255
	defb	255
	defb	249
	defb	255
	defb	255
	defb	249
	defb	31
	defb	31
	defb	25
	defb	6
	defb	6
	defb	6
	defb	0
	defb	0
	defb	0
	defb	10
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
	defb	252
	defb	252
	defb	252
	defb	254
	defb	206
	defb	54
	defb	11
	defb	254
	defb	206
	defb	50
	defb	254
	defb	206
	defb	50
	defb	254
	defb	206
	defb	54
	defb	252
	defb	252
	defb	252
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
	C_LINE	93,"mario_old.inc"
	SECTION	rodata_compiler
._mario_frames_old
	defw	_mario1_l + 0
	defw	_mario2_l + 0
	defw	_mario3_l + 0
	SECTION	code_compiler
	C_LINE	21,"main.c"
	C_LINE	25,"main.c"
	C_LINE	26,"main.c"
	C_LINE	27,"main.c"
	C_LINE	28,"main.c"
	C_LINE	29,"main.c"
	C_LINE	34,"main.c"
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
	C_LINE	42,"main.c"
	C_LINE	43,"main.c"
	C_LINE	44,"main.c"
	C_LINE	45,"main.c"
	C_LINE	50,"main.c"

; Function spr_frame flags 0x00000200 __smallc 
; void spr_frame()
	C_LINE	51,"main.c::spr_frame::0::0"
._spr_frame
	call	_timer_start
	ret


	C_LINE	60,"main.c::spr_frame::0::1"

; Function draw_sprite_old flags 0x00000200 __smallc 
; void draw_sprite_old(unsigned char x, unsigned int y, const unsigned char * spr)
; parameter 'const unsigned char * spr' at sp+2 size(2)
; parameter 'unsigned int y' at sp+4 size(2)
; parameter 'unsigned char x' at sp+6 size(1)
	C_LINE	61,"main.c::draw_sprite_old::0::1"
._draw_sprite_old
	pop	bc
	pop	hl
	push	hl
	push	bc
	ld	l,(hl)
	ld	h,0
	dec	sp
	ld	a,l
	pop	hl
	ld	l,a
	push	hl
	ld	hl,7	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	ld	a,l
	rrca
	rrca
	rrca
	and	31
	ld	l,a
	push	hl
	ld	h,l
	ld	l,0
	ld	a,224
	add	h
	ld	h,a
	push	hl
	ld	hl,9	;const
	add	hl,sp
	call	l_gint	;
	ld	de,255
	call	l_sub
	pop	de
	add	hl,de
	ld	(_rs_p0),hl
	ld	a,-32
	add	h
	ld	h,a
	ld	(_rs_p1),hl
	call	l_gint5sp	;
	ld	(_rs_spr),hl
	ld	hl,2	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	call	l_neg
	ld	a,l
	ld	(_rs_cols),a
	ld	hl,0	;const
	ld	a,l
	ld	(_rs_frac),a
	call	_mario_draw_sprite
	inc	sp
	pop	bc
	ret


	C_LINE	73,"main.c::draw_sprite_old::0::2"

; Function measure flags 0x00000200 __smallc 
; void measure()
	C_LINE	74,"main.c::measure::0::2"
._measure
	dec	sp
	pop	hl
	ld	l,0
	push	hl
	ld	hl,40	;const
	push	hl
	push	bc
	push	bc
	push	bc
	call	_v06_wait_frame
	ld	hl,3	;const
	add	hl,sp
	push	hl
	call	_timer_elapsed
	pop	de
	call	l_pint
	ld	hl,8	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	push	hl
	call	l_gint8sp	;
	push	hl
	ld	hl,(_mario_frames_old)
	push	hl
	call	_draw_sprite_old
	pop	bc
	pop	bc
	pop	bc
	ld	hl,1	;const
	add	hl,sp
	push	hl
	call	_timer_elapsed
	pop	de
	call	l_pint
	ld	hl,1	;const
	call	l_gintspsp	;
	call	l_gint5sp	;
	pop	de
	call	l_sub
	ld	(_bm_old_draw),hl
	call	_v06_wait_frame
	ld	hl,3	;const
	add	hl,sp
	push	hl
	call	_timer_elapsed
	pop	de
	call	l_pint
	ld	hl,0	;const
	add	hl,sp
	ld	(hl),0
	jp	i_9	;EOS
.i_7
	ld	hl,0	;const
	add	hl,sp
	inc	(hl)
.i_9
	pop	hl
	push	hl
	ld	a,l
	sub	3
	jp	nc,i_8	;
	ld	hl,8	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	push	hl
	call	l_gint8sp	;
	push	hl
	ld	hl,_mario_frames_old
	push	hl
	ld	hl,6	;const
	add	hl,sp
	ld	e,(hl)
	ld	d,0
	ld	hl,3	;const
	call	l_div_u
	ex	de,hl
	add	hl,hl
	pop	de
	add	hl,de
	call	l_gint	;
	push	hl
	call	_draw_sprite_old
	pop	bc
	pop	bc
	pop	bc
	jp	i_7	;EOS
.i_8
	ld	hl,1	;const
	add	hl,sp
	push	hl
	call	_timer_elapsed
	pop	de
	call	l_pint
	ld	hl,1	;const
	call	l_gintspsp	;
	call	l_gint5sp	;
	pop	de
	call	l_sub
	ld	(_bm_old_total),hl
	call	_v06_wait_frame
	ld	hl,3	;const
	add	hl,sp
	push	hl
	call	_timer_elapsed
	pop	de
	call	l_pint
	ld	hl,5	;const
	add	hl,sp
	ld	(hl),0
	jp	i_12	;EOS
.i_10
	ld	hl,5	;const
	add	hl,sp
	inc	(hl)
.i_12
	ld	hl,5	;const
	add	hl,sp
	ld	a,(hl)
	sub	3
	jp	nc,i_11	;
	ld	hl,8	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	push	hl
	call	l_gint8sp	;
	push	hl
	ld	hl,_mario_frames_old
	push	hl
	ld	hl,11	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,hl
	pop	de
	add	hl,de
	call	l_gint	;
	push	hl
	call	_draw_sprite_old
	pop	bc
	pop	bc
	pop	bc
	jp	i_10	;EOS
.i_11
	ld	hl,1	;const
	add	hl,sp
	push	hl
	call	_timer_elapsed
	pop	de
	call	l_pint
	ld	hl,1	;const
	call	l_gintspsp	;
	call	l_gint5sp	;
	pop	de
	call	l_sub
	ld	(_bm_old_anim),hl
	ld	hl,48879	;const
	ld	(_bm_magic),hl
	inc	sp
	pop	bc
	pop	bc
	pop	bc
	pop	bc
	ret


	C_LINE	108,"main.c::measure::0::3"

; Function main flags 0x00000000 __stdc 
; int main()
	C_LINE	109,"main.c::main::0::4"
._main
	dec	sp
	pop	hl
	ld	l,0
	push	hl
	push	bc
	dec	sp
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
	ld	hl,_spr_frame
	ld	(_frame_handler),hl
	call	_timer_start_sync
	ld	a,12
	ld	(_gfx_active_planes),a
	ld	hl,8	;const
	push	hl
	push	hl
	ld	hl,i_1+0
	push	hl
	ld	hl,4	;const
	push	hl
	call	_gfx_print
	ld	hl,8	;const
	push	hl
	ld	l,24
	push	hl
	ld	hl,i_1+11
	push	hl
	ld	hl,4	;const
	push	hl
	call	_gfx_print
	ld	hl,8	;const
	push	hl
	ld	l,32
	push	hl
	ld	hl,i_1+17
	push	hl
	ld	hl,4	;const
	push	hl
	call	_gfx_print
	ld	hl,8	;const
	push	hl
	ld	l,40
	push	hl
	ld	hl,i_1+24
	push	hl
	ld	hl,4	;const
	push	hl
	call	_gfx_print
	ld	hl,15	;const
	ld	a,l
	ld	(_gfx_active_planes),a
	call	_measure
	ld	hl,1	;const
	add	hl,sp
	ex	de,hl
	ld	hl,_frame_count
	call	l_pint
	ld	hl,0	;const
	add	hl,sp
	push	hl
	call	l_gint3sp	;
	ld	a,(hl)
	pop	de
	ld	(de),a
.i_16
	call	l_gint1sp	;
	ld	e,(hl)
	ld	d,0
	pop	hl
	push	hl
	ld	h,0
	call	l_eq
	jp	c,i_16	;EOS
.i_17
	ld	hl,0	;const
	add	hl,sp
	push	hl
	call	l_gint3sp	;
	ld	a,(hl)
	pop	de
	ld	(de),a
	ld	hl,0	;const
	push	hl
	ld	l,40
	push	hl
	ld	hl,_mario_frames_old
	push	hl
	ld	hl,9	;const
	add	hl,sp
	ld	l,(hl)
	ld	h,0
	add	hl,hl
	pop	de
	add	hl,de
	call	l_gint	;
	push	hl
	call	_draw_sprite_old
	pop	bc
	pop	bc
	pop	bc
	ld	hl,3	;const
	add	hl,sp
	push	hl
	ld	l,(hl)
	ld	h,0
	inc	hl
	ld	de,3
	ex	de,hl
	call	l_div_u
	ex	de,hl
	pop	de
	ld	a,l
	ld	(de),a
	jp	i_13	;EOS
.i_14
	ld	hl,0	;const
	pop	bc
	pop	bc
	ret


	SECTION	bss_compiler
	SECTION	code_compiler
; --- Start of Optimiser additions ---
	defc	i_13 = i_15
	defc	i_15 = i_16

	SECTION	rodata_compiler
.i_1
	defm	"Old engine"
	defb	0

	defm	"Draw:"
	defb	0

	defm	"Total:"
	defb	0

	defm	"Anim:"
	defb	0


; --- Start of Static Variables ---

	SECTION	bss_compiler
._rs_spr	defs	2
._rs_p0	defs	2
._rs_p1	defs	2
._rs_cols	defs	1
._rs_frac	defs	1
._bm_old_draw	defs	2
._bm_old_total	defs	2
._bm_old_anim	defs	2
._bm_magic	defs	2
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
	GLOBAL	_mario_draw_sprite
	GLOBAL	_rs_spr
	GLOBAL	_rs_p0
	GLOBAL	_rs_p1
	GLOBAL	_rs_cols
	GLOBAL	_rs_frac
	GLOBAL	_bm_old_draw
	GLOBAL	_bm_old_total
	GLOBAL	_bm_old_anim
	GLOBAL	_bm_magic
	GLOBAL	_main


; --- End of Scope Defns ---


; --- End of Compilation ---
