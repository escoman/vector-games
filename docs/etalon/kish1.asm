	.ORG	0
M0000H:	MVI	A, 88H
	OUT	00
	MVI	A, 81H
	OUT	04
	MVI	A, 0FFH
	OUT	03
	OUT	05
	OUT	06
	OUT	07
	MVI	A, 8
	STA	0DEF6H
	MVI	A, 0A8H
	LXI	B, 0040H
M001CH:	OUT	08
	SUB	C
	JNC	M001CH
	IN	01		;
	ANA	C		; выделить нажатие клавиши УС
	MOV	C,B
	JZ	M0048H		; если УС нажата - как ни в чем ни бывало
	XRA	A		; обнулить аккумулятор
	OUT	01		; выставить в порт 1 ноль
M002CH:	STAX	B		; очистить ОЗУ
	INX	B
	STAX	B
	INX	B
	CMP	C
	JNZ	M002CH
	CMP	B
	JMP	M0045H		; перепрыгнуть через прерывания
; подпрограмма обработки прерываний
M0038H:	LDA	0DEF6H
M003BH: DCR	A
	JNZ	M003BH
M003FH:	IN	01
	ANI	10H		; выделить бит чтения с магнитофона
	MOV	E, A
	RET

M0045H:	JNZ	M002CH
M0048H:	LXI	SP, 0DCF0H
	LXI	D, 55AAH
M004EH:	PUSH	D		; положить в стек DE
	POP	H		; взять из стека в HL
	MOV	A, L		; из L поместить в аккумулятор
	CMA			; инверсия аккумулятора
	CMP	H		; сравнить аккумулятор с H
	JNZ	M004EH		; если H<>L тогда переход
	LXI	D, 0009
M0059H:	MOV	H, B		; нарисовать загрузочную таблицу
	MOV	L, D
	CALL	M013EH
	DCR	L
	MVI	M, 0FFH
	DAD	D
	MVI	M, 0FFH
	INR	L
	MVI	M, 81H
	INR	B
	JNZ	M0059H
	MVI	H, 80H
	MVI	D, 2DH
	LXI	B, 080FH
M0072H:	XRA	A		; запрограммировать цветогенератор
	OUT	02
	EI
	HLT
	MOV	A, C
	OUT	02
	MOV	A, D
	OUT	0CH
	DCR	C
	MOV	A, C
	OUT	02
	MOV	A, D
	OUT	0CH
	DCR	C
	XCHG
	DCR	B
	JNZ	M0072H
	CALL	M009CH
M008DH:	EI		; разрешить прерывания
	HLT		; ожидать аппаратного прерывания 1/50 сек
	INR	C	;
	PUSH	B	;
	POP	B	;
	MOV	A, C	;
	ANI	08	; вкл/выкл светодиод
	ORI	02	; выключить реле
	OUT	01	; выставить данные на порт 1
	JMP	M008DH	;

M009CH:	CALL	M0172H
M009FH:	MOV	D, A
	ORA	A
	RAR
	MOV	E, A
	ADD	D
	MOV	H, A
	CALL	M0172H
	CMP	H
	JC	M009FH
	ADD	D
	STA	0DEF6H
	MVI	E, 0CH
M00B2H:	MVI	A, 08
	CALL	M01BFH
	CPI	55H
	JZ	M00C1H
	CPI	0AAH
	JNZ	M009CH
M00C1H:	DCR	E
	JNZ	M00B2H
M00C5H:	CALL	M019DH
	MOV	E, A
	MOV	A, M
	CPI	00
	JNZ	M00C5H
	LXI	H, 0DEF1H
	MOV	A, M
	DCX	H
	CMP	M
	JNZ	M009CH
	MOV	D, A
	DCX	H
	MOV	B, M
M00DBH:	CALL	M019DH
	PUSH	PSW
	MOV	A, M
	CPI	00
	JZ	M0118H
	ADD	A
	ADD	A
	ADD	A
	ADD	A
	ADD	A
	MOV	C, A
	POP	PSW
	INX	H
	MOV	A, M
	CMP	E
	JNZ	M00DBH
	PUSH	D
	PUSH	B
	INX	H
	LXI	D, 207EH
M00F8H:	MOV	A, M
	STAX	B
	LDAX	B
	XRA	M
	MOV	M, A
	INX	H
	INR	C
	DCR	D
	JNZ	M00F8H
	POP	B
	MOV	L, C
	MOV	H, B	;!!!
	CALL	M013EH
	MOV	M, E
	POP	D
	CALL	M012DH
	JZ	M00DBH
	MOV	A, D
	CPI	01
	JNZ	M00DBH
	RET

M0118H:	POP	PSW
	SUB	E
	JZ	M00DBH
	INR	A
	JNZ	M0000H	;  запуск сначала !!!!!!!!!!!!!!!!!!!!
	CALL	M012DH
	JZ	M0000H	;  запуск сначала !!!!!!!!!!!!!!!!!!!!
	DCR	E
	INR	B
	DCR	D
	JMP	M00DBH

M012DH:	MVI	L, 00
	MOV	H, B
	CALL	M013EH
M0133H:	MOV	A, M
	ANA	A
	RZ
	INX	H
	CPI	81H
	JNZ	M0133H
	ANA	A
	RET

M013EH:	PUSH	D
	MOV	A, L
	RLC
	RLC
	RLC
	MOV	L, A
	MOV	A, H
	RAR
	ANI	70H
	MOV	D, A
	RAR
	ADD	D
	ADD	L
	ADI	18H
	MOV	L, A
	MOV	A, H
	ANI	1FH
	ADI	0C0H
	MOV	H, A
	POP	D
	RET

M0157H:	PUSH	D
	RST	7
M0159H:	IN	01
	ANI	10H
	CMP	E
	JZ	M0159H
	MOV	E, A
	MVI	D, 01
M0164H:	IN	01
	ANI	10H
	INR	D
	CMP	E
	JZ	M0164H
	MOV	A, D
	ADD	A
	ADD	A
	POP	D
	RET

M0172H:	PUSH	H
	PUSH	D
M0174H:	CALL	M0157H
	MOV	B, A
	ORA	A
	RAR
	MOV	C, A
	LXI	H, 0000
	MVI	D, 20H
M0180H:	CALL	M0157H
	PUSH	D
	MVI	D, 00
	MOV	E, A
	DAD	D
	POP	D
	MOV	E, A
	SUB	B
	JNC	M0190H
	MOV	A, B
	SUB	E
M0190H:	CMP	C
	JNC	M0174H
	DCR	D
	JNZ	M0180H
	DAD	H
	MOV	A,H
	POP	D
	POP	H
	RET

M019DH:	PUSH	B
	LXI	H, 0DED0H
M01A1H:	PUSH	H
	LXI	B, 0023H
	MVI	A, 0FFH
M01A7H:	CALL	M01BFH
	MOV	M, A
	INX	H
	ADD	B
	MOV	B, A
	MVI	A, 08
	DCR	C
	JNZ	M01A7H
	DCX	H
	MOV	A, B
	SUB	M
	SUB	M
	MOV	A, M
	POP	H
	JNZ	M01A1H
	POP	B
	RET

M01BFH:	PUSH	B
	PUSH	D
	MVI	C, 00
	MOV	D, A
	CALL	M003FH
M01C7H:	IN	01
	ANI	10H
	CMP	E
	JZ	M01C7H
	RLC
	RLC
	RLC
	RLC
	MOV	A, C
	RAL
	MOV	C, A
	RST	7
	MOV	A, D
	ORA	A
	JP	M01F5H
	MOV	A, C
	CPI	0E6H
	JNZ	M01E9H
	XRA	A
	STA	0DEF4H
	JMP	M01F3H
M01E9H:	CPI	19H
	JNZ	M01C7H
	MVI	A, 0FFH
	STA	0DEF4H
M01F3H:	MVI	D, 09
M01F5H:	DCR	D
	JNZ	M01C7H
	LDA	0DEF4H
	XRA	C
	POP	D
	POP	B
	RET
	.END
	