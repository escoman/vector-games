; Every byte of the ROM window is emitted exactly once: instruction,
; RDB data region, or explicit gap_ region.  This is what the build
; consumes; code/code.asm and data/data.asm are read-only views.

	jmp	label_0100
; Uncovered ROM bytes — neither code nor an RDB object
gap_0003:
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,0C3h,00h,0Eh
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,23h,07h,94h,07h
	defb	95h,06h,0FBh,09h,0B6h,06h,67h,06h
	defb	0E4h,05h,1Bh,01h,00h

label_0100:
        defb    0F3h,031h,0FFh,000h,03Eh,0C3h,032h,000h
        defb    000h,032h,038h,000h,021h,000h,001h,022h
        defb    001h,000h,021h,000h,00Eh,022h,039h,000h
        defb    0CDh,073h,005h,021h,0E1h,011h,036h,0C3h
        defb    023h,036h,040h,023h,036h,012h,021h,0CAh
        defb    014h,036h,0C9h,0CDh,07Ch,014h,021h,000h
        defb    00Dh,0CDh,0D8h,011h,021h,0E1h,011h,036h
        defb    0FEh,023h,036h,01Ch,023h,036h,0CCh,021h
        defb    0CAh,014h,036h,0CDh,001h,050h,08Ch,021h
        defb    072h,00Eh,0CDh,082h,005h,001h,040h,08Ch
        defb    021h,07Bh,00Eh,0CDh,082h,005h,021h,084h
        defb    00Eh,001h,030h,0A9h,0CDh,082h,005h,02Ah
        defb    0F6h,00Dh,001h,02Eh,092h,0CDh,008h,00Fh
        defb    021h,08Eh,00Eh,001h,020h,0CCh,0CDh,082h
        defb    005h,021h,0F8h,00Dh,001h,020h,0EFh,0CDh
        defb    065h,005h
lbl_017a:
; Диспетчер перехода между экранами (меню). Живой факт Stage 5: цикл CALL func_get_key(0x0F15); ORA A; JZ 0x018B (ждать клавишу), затем CPI по кодам: 0x11→JZ 0x02F6 (1.START), 0x12→JZ 0x0FA5 (2.LOAD), 0x13→JZ 0x020A (3.PASS), иначе JMP 0x018B. Расположен в exec-области bootstrap после рендера заставки.
        defb    0CDh,020h,005h,0FEh,03Fh,0C2h,07Ah,001h
        defb    0CDh,028h,005h,021h,091h,00Eh,0CDh,045h
        defb    00Fh
func_menu_dispatcher:
        defb    0CDh,015h,00Fh,0B7h,0CAh,08Bh,001h,0FEh
        defb    011h,0CAh,0F6h,002h,0FEh,012h,0CAh,0A5h
        defb    00Fh,0FEh,013h,0CAh,00Ah,002h,0C3h,08Bh
        defb    001h
lbl_01a4:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,028h,005h,0CDh,0D0h,00Dh,021h,0AEh
        defb    00Eh,0CDh,045h,00Fh,0FBh,03Eh,080h,076h
gap_01B4:
	defb	3Dh,0C2h,0B3h,01h,0CDh,28h,05h,0C3h
	defb	00h,10h

label_01BE:
	call	func_0528
	lxi	h,0ebbh
label_01C4:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,045h,00Fh,001h,028h,0CCh,000h,000h
        defb    01Eh,000h,021h,0F8h,00Ch,0CDh,055h,002h
        defb    076h
gap_01D5:
	defb	76h,0B7h,0CAh,0D1h,01h,0FEh,03h,0CAh
	defb	0FBh,01h,0FEh,02h,0C8h,76h,76h,0FEh
	defb	07h,0DAh,0D1h,01h,57h,7Bh,0FEh,07h
	defb	0CAh,0D1h,01h,7Ah,0C6h,20h,0CDh,14h
	defb	24h,1Ch,04h,0C3h,49h,02h,7Bh,0B7h
	defb	0CAh,0D1h,01h,05h,3Eh,25h,0CDh,14h
	defb	24h,1Dh,0C3h,7Dh,0Fh

; Пункт меню 3.PASS (код клавиши 0x13): цель JZ из func_menu_dispatcher@0x019E. Экран пароля/прохождения (Stage 8).
; screen_role: Пункт меню 3.PASS — экран пароля/прохождения (password passes). Как данные — Stage 8.
label_screen_pass:
	call	label_01BE
	mvi	d,00h
	lxi	b,264dh
label_0212:
	lxi	h,0cf8h
	push	d
lbl_0216:
        defb    00Ah,0BEh,0C2h,038h,002h,003h,023h,01Dh
        defb    0C2h,016h,002h,0D1h,0C3h,08Dh,00Fh
lbl_0225:
	lxi	b,0680h
	mov	a,d
label_0229:
	ora	a
	jz	lbl_0232
	dad	b
	dcr	a
	jmp	label_0229
lbl_0232:
	shld	1423h
	jmp	label_0305
lbl_0238:
	pop	d
lbl_0239:
	ldax	b
	inx	b
	ora	a
	jnz	lbl_0239
	ldax	b
	cpi	0ffh
	jz	lbl_025e
	inr	d
	jmp	label_0212
; Uncovered ROM bytes — neither code nor an RDB object
gap_0249:
	defb	7Ah,0C6h,20h,77h,23h,0C3h,0D1h,01h
	defb	2Bh,0C3h,0D1h,01h

; Верхний игровой цикл (frame loop): по цензу вызывает 0x0520/0x0528/0x0565/0x0582 (задержки/тайминг), 0x0DD0 (blob, ложный callee), 0x0F08/0x0F15/0x0F45 (видео-клубок), 0x11D8 (big logic). Тело 0x0255..0x031F — цикл с CALL-последовательностью; сигнатуры внутри могут быть рассинхронены (границы точнить Stage 3 CFG).
func_0255:
	hlt
; Uncovered ROM bytes — neither code nor an RDB object
gap_0256:
	defb	76h,76h,76h,76h,0CDh,15h,0Fh,0C9h

lbl_025e:
	call	func_0528
	lxi	h,0ecdh
label_0264:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,045h,00Fh,03Eh,050h,076h
gap_026A:
	defb	3Dh,0C2h,69h,02h,0CDh,28h,05h,0C3h
	defb	44h,01h,2Ah,0F6h,0Dh,0EBh,2Ah,0DFh
	defb	24h,7Ch,0BAh,0DAh,00h,01h,7Dh,0BBh
	defb	0DAh,00h,01h,2Ah,0DFh,24h,22h,0F6h
	defb	0Dh,0C3h,0A6h,02h

label_028E:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,0D0h,00Dh,021h,0D9h,00Eh,0CDh,045h
        defb    00Fh,0FBh,03Eh,040h,076h
gap_029B:
	defb	3Dh,0C2h,9Ah,02h,0CDh,0D0h,0Dh,0FBh
	defb	0C3h,74h,02h,0F3h,21h,00h,0Eh,22h
	defb	39h,00h,0FBh,21h,80h,0Ch,0CDh,45h
	defb	0Fh,21h,0F8h,0Dh,0Eh,07h,36h,25h
	defb	2Ch,0Dh,0C2h,0B9h,02h,21h,0F8h,0Dh
	defb	1Eh,00h,01h,70h,0ACh,31h,0FFh,00h
	defb	0CDh,0D1h,01h,21h,0F8h,0Dh,11h,0E9h
	defb	0Eh,06h,07h,1Ah,0BEh,0C2h,00h,01h
	defb	23h,13h,05h,0C2h,0D6h,02h,0AFh,32h
	defb	0A2h,1Eh,0C3h,00h,01h

label_02E8:
	mov	a,d
label_02E9:
; Пункт меню 1.START (код клавиши 0x11): цель JZ из func_menu_dispatcher@0x0194. Путь входа в игру (через 0x01A4 → рендер/HLD-выдержка → JMP 0x1000 func_game_main).
        defb    0B7h,0CAh,0A4h,001h,0F5h,0CDh,03Dh,026h
        defb    0F1h,03Dh,0C3h,0E9h,002h
label_screen_start:
	lxi	h,264ch
	shld	264ah
	lxi	h,5700h
	shld	1423h
	jmp	lbl_01a4
label_0305:
	lxi	h,264ch
	shld	264ah
	jmp	label_0313
label_030E:
	call	func_text_walk_speak
	ei
	ret
label_0313:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0AFh,032h,047h,00Eh,0C3h,0E8h,002h
gap_031A:
	defb	00h,00h,00h,00h,00h,00h

func_0320:
	push	b
	push	d
	push	h
	lhld	033fh
	mov	a,h
	rlc
	rlc
	rlc
	ani	0f8h
	add	h
	mov	b,a
	mov	a,l
	rlc
	rlc
	ani	0fch
	add	l
	add	l
	sbb	b
	mov	h,l
	mov	l,a
	shld	033fh
	pop	h
	pop	d
	pop	b
	ret
; Uncovered ROM bytes — neither code nor an RDB object
gap_033F:
	defb	93h,93h,0C9h

func_0342:
	push	b
	push	h
	mov	a,h
	ani	07h
	mov	b,a
	mov	a,h
	rrc
	rrc
	rrc
	ani	1fh
	adi	0a0h
	mov	h,a
	mvi	c,80h
	mov	a,b
	ora	a
	jz	lbl_035f
lbl_0358:
	mov	a,c
	rrc
	mov	c,a
	dcr	b
	jnz	lbl_0358
lbl_035f:
	mov	a,m
	xra	c
	mov	m,a
	pop	h
	pop	b
	ret
label_0365:
	call	func_036c
	call	func_03f7
	ret
func_036c:
	lda	0436h
	ora	a
	rz
	mov	c,a
	lxi	h,7a30h
lbl_0375:
	push	b
	push	h
	mov	c,m
	inx	h
	mov	b,m
	inx	h
	mov	e,m
	inx	h
	mov	d,m
	inx	h
	mov	a,m
	inx	h
	mov	h,m
	mov	l,a
	call	func_0342
	mov	a,e
	cmp	b
	cz	label_03BD
	inr	e
	mov	a,c
	ora	a
	jz	lbl_0393
	dcr	l
	dcr	l
lbl_0393:
	inr	l
	mov	a,c
	ora	a
	jz	lbl_039f
	mov	a,b
	cpi	07h
	jz	lbl_03db
lbl_039f:
	call	func_0342
	shld	0434h
	pop	h
	mov	m,c
	inx	h
	mov	m,b
	inx	h
	mov	m,e
	inx	h
	mov	m,d
	xchg
	lhld	0434h
	xchg
	inx	h
	mov	m,e
	inx	h
	mov	m,d
	inx	h
	pop	b
label_03B8:
	dcr	c
	jnz	lbl_0375
	ret
label_03BD:
	mov	a,d
	ora	a
	jz	lbl_03c6
	dcr	h
	dcr	h
	dcr	h
	dcr	h
lbl_03c6:
	inr	h
	inr	h
	mov	a,c
	ora	a
	jnz	lbl_03d4
	dcr	b
	cz	label_03D8
	mvi	e,0ffh
	ret
lbl_03d4:
	inr	b
	mvi	e,0ffh
	ret
label_03D8:
	mvi	c,01h
	ret
lbl_03db:
	lxi	h,0436h
	dcr	m
	pop	h
	push	h
	lxi	d,0006h
	dad	d
	xchg
	pop	h
	push	h
	mvi	b,0b4h
lbl_03ea:
	ldax	d
	mov	m,a
	inx	h
	inx	d
	dcr	b
	jnz	lbl_03ea
	pop	h
	pop	b
	jmp	label_03B8
func_03f7:
	call	func_0320
	ani	03h
	cpi	01h
	rnz
	lda	0436h
	cpi	1eh
	rnc
	inr	a
	sta	0436h
	dcr	a
	add	a
	mov	c,a
	add	a
	add	c
	lxi	h,7a30h
	add	l
	mov	l,a
	mvi	m,00h
	inx	h
	call	func_0320
	ani	07h
	adi	03h
	mov	m,a
	inx	h
	mvi	m,00h
	inx	h
	call	func_0320
	ani	01h
	mov	m,a
	inx	h
	mvi	m,1eh
	inx	h
	mvi	m,88h
	lxi	h,881eh
	jmp	func_0342
; Uncovered ROM bytes — neither code nor an RDB object
gap_0434:
	defb	1Fh,88h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,0CDh,65h,03h,0FBh
	defb	76h,0C3h,15h,0Fh,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h

func_0520:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,030h,005h,0C3h,015h,00Fh
gap_0526:
	defb	01h,00h

; Тайминг-хелпер (8 call-in из frame-цикла): короткая подпрограмма 0x0528..0x052F, выровненная дизассемблировка даёт POP B/JMP 03B8 — хвост стековой рамки; вероятный wait/vsync-твик. Точное назначение — Stage 3 (по coverage).
func_0528:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,046h,005h,0C3h,021h,00Fh
gap_052E:
	defb	00h,0C9h

func_0530:
	lhld	0526h
	mov	a,h
	ora	l
	jz	lbl_053d
	dcx	h
	shld	0526h
	ret
lbl_053d:
        defb    0CDh,010h,00Bh,022h,026h,005h,0C3h,065h
        defb    003h
func_0546:
	lxi	h,7a30h
	lda	0436h
	ora	a
	rz
	mov	c,a
lbl_054f:
	inx	h
	inx	h
	inx	h
	inx	h
	mov	e,m
	inx	h
	mov	d,m
	inx	h
	xchg
	call	func_0342
	xchg
	dcr	c
	jnz	lbl_054f
	xra	a
	sta	0436h
	ret
func_0565:
	xra	a
	sta	0436h
	jmp	label_030E
func_056c:
	mov	a,m
	stax	b
	inr	c
	stax	b
	nop
	dcx	h
	ret
; Вызыватель речи заставки (exec). Живой факт Stage 5: bootstrap 0x0100 делает CALL 0x0573. Тело: CALL 0DD0 (палитра/beam); LXI H,0600 (буфер фразы); CALL 0660 (func_speak_start) → произносит «GRU DIL SOFT PREDLAGAET NOWEJSIE…» (ГРУ Дил Софт предлагает…); возврат 0x057C; LXI H,09D0; JMP 05E1 (вторая фраза + очистка буфера STA 0600). Момент речи #1 = титр/заставка.
func_title_speech_caller:
; Обходчик строки с речью (exec). MOV A,M; ORA A; RZ (терминатор 0x00); INX H; CALL 0x058D; INR B; JMP 0x0582. Вызывается из bootstrap (0x014A/0x0153/0x015C/0x016E) на экранных скриптах 0x0E72/0x0E7B/0x0E84. Диспетчер 0x058D посимвольно вызывает speech (CALL 0660 @ 0x05A6) — момент речи #2 = меню (буквы/цифры ODIN/DWA/TRI, табл. 0x09C3).
        defb    0CDh,0D0h,00Dh,021h,000h,006h,0CDh,060h
        defb    006h,021h,0D0h,009h,0C3h,0E1h,005h
func_text_walk_speak:
	mov	a,m
	ora	a
	rz
	inx	h
	call	func_058d
	inr	b
	jmp	func_text_walk_speak
; Посимвольный диспетчер речи меню (exec 0x058D). Уточн. Stage 5: вызывается из func_text_walk_speak@0x0582 (CALL 0x058D @ 0x0586) на каждом символе экранного скрипта; внутри делает CALL 0x0660 (триггер речи 0x0663) → произносит букву/цифру (таблица 0x09C3 = ODIN/DWA/TRI). Это момент речи #2 (меню). Прежняя Stage-3 гипотеза «frame-тайминг» снята: CALL-внутрь-0x0660 — это обращение к движку речи, а не ложная сигнатура.
func_058d:
	push	psw
	push	b
	push	d
	push	h
	cpi	31h
	cz	label_05C6
	cpi	32h
	cz	label_05CC
	cpi	33h
	cz	label_05D2
	lxi	h,05feh
	mov	m,a
	push	psw
	push	b
	call	label_phrase_SOFT
	pop	b
	pop	psw
	sui	24h
	mov	l,a
	mvi	h,00h
	dad	h
	dad	h
	dad	h
	lxi	d,2700h
	dad	d
	mvi	e,08h
lbl_05b9:
	mov	a,m
	stax	b
	dcx	h
	inr	c
	dcr	e
	jnz	lbl_05b9
	pop	h
	pop	d
	jmp	label_05DD
label_05C6:
	lxi	h,09c3h
	jmp	label_05D5
label_05CC:
	lxi	h,09c8h
	jmp	label_05D5
label_05D2:
	lxi	h,09cch
label_05D5:
	push	psw
	push	b
	call	label_phrase_SOFT
	pop	b
	pop	psw
	ret
label_05DD:
	pop	b
	pop	psw
	ei
	ret
label_05E1:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,060h,006h,03Eh,000h,032h,000h,006h
        defb    0C3h,0D0h,00Dh
gap_05EC:
	defb	03h,0D3h,0Ch,1Bh,7Ah,0B3h,0C2h,0E7h
	defb	05h,0C3h,0D0h,0Dh,00h,00h,00h,00h
	defb	00h,00h,59h,00h

; str_voice: речевая фраза заставки (exec-буфер 0x0600, момент речи #1). Транслит (разделитель — пробел, НЕ '%'): «GRU DIL SOFT PREDLAGAET NOWEJSIE PROGRAMMY K WEKTOR NOL SEST… C PISITE NAM PO ADRESU» → «ГРУ Дил Софт предлагает новейшие программы к Вектор-06… пишите нам по адресу». В ROM-файле источник на 0x065A (блок speech −0x59 relocation → exec 0x0600). Произносится func_speak_engine (Stage 7).
str_voice_title:
	defb	00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_0601:
	defb	47h,52h,55h,20h,20h,44h,49h,4Ch
	defb	20h,20h,53h,4Fh,46h,54h,20h,20h
	defb	50h,52h,45h,44h,4Ch,41h,47h,41h
	defb	45h,54h,20h,20h,4Eh,4Fh,57h,45h
	defb	4Ah,53h,49h,45h,20h,20h,50h,52h
	defb	4Fh,47h,52h,41h,4Dh,4Dh,59h,20h
	defb	20h,4Bh,20h,20h,57h,45h,4Bh,54h
	defb	4Fh,52h,20h,20h,4Eh,4Fh,4Ch,20h
	defb	20h,53h,45h,53h,54h,58h,20h,43h
	defb	20h,20h,50h,49h,53h,49h,54h,45h
	defb	20h,4Eh,41h,4Dh,20h,50h,4Fh,20h
	defb	41h

; Демо-фраза синтезатора речи (translit, 94B): 'GRU DIL SOFT PREDLAGAET NOWEJSIE PROGRAMMY K WEKTOR NOL SESTX C PISITE NAM PO ADRESU'; терминатор (00h) в 0x06B8 (после 'ADRESU' идут 10 09 04 00 = NOP/DAD B/INR B/NOP, затем DI-вход). Адреса 0x0660/0x0663/0x0669/0x06C3 внутри строки — НЕ код: ранние Stage-2 функции по этим адресам были фантомами (исправлено в этом проходе). Ветки речи (CALL 0x0669; цели 0x069B/0x0686/0x068C/0x0690/0x0697/0x06FD/0x06DC, JMP 0x066B) прилетают в область строки — аномалию разрешать трейсингом в Stage 7 (см. func_speak_walker).
str_speak_demo:
	defb	44h,52h,45h,53h,55h,00h

label_phrase_SOFT:
	nop
	nop
	nop
; Триггер речи: DI (глушит прерывания на время бит-бэнга — критично для постоянного периода PDM) → CALL func_speak_string → RET. Вход: HL = указатель на translit-строку (0-терминатор).
label_str_in_0663:
	di
	call	label_call_target_in_str
	nop
	ret
; Обходчик строки текст→речь: посимвольно читает (HL), классифицирует translit-буквы ('A'..'Z', спец 'C'/'H'/'''), ремап ADI 1Ah; паузы по '.',' ,',' ' через DE=0x8000/0x4000 + func_voice_delay; на букву — CALL func_speak_phoneme. Конец по 0 (ORA A/RZ). B=0xBBh — стартовая высота тона.
label_call_target_in_str:
	mvi	b,0bbh
label_066B:
	mov	a,b
	mov	c,b
	mov	b,m
	ora	a
	rz
	mov	a,c
	cpi	41h
	jm	lbl_069b
	cpi	5bh
	jp	lbl_069b
	cpi	43h
	mov	a,b
	jnz	lbl_0686
	cpi	48h
	jz	lbl_068c
lbl_0686:
	cpi	27h
	mov	a,c
	jnz	lbl_0690
lbl_068c:
	adi	1ah
	mvi	b,0bbh
lbl_0690:
	push	b
	push	h
	call	label_phoneme_call_tgt
	pop	h
	pop	b
label_0697:
	inx	h
	jmp	label_066B
lbl_069b:
	lxi	d,0000h
	cpi	2eh
	nop
	nop
	nop
	lxi	d,8000h
	cpi	2ch
	jz	lbl_06b3
	lxi	d,4000h
	cpi	20h
	jnz	lbl_06b9
lbl_06b3:
	call	func_speak_start
	jmp	label_0697
lbl_06b9:
	jmp	label_0697
; ВХОД речи (факт, abs-адреси): DI (0x06BC) → CALL 0x0669 (0x06BD) → NOP → RET (0x06C1). DI глушит прерывания на всё время бит-бэнга PDM (критично для постоянного периода). Колл-входы из дампа: 0x070C (пауза), 0x0718 (delay-цикл), 0x0779 (emit) — все внутри речевого региона; внешних CALL в ROM-области нет — вход в речь выполняется из RAM-области после распаковки (Stage 3+). Цель CALL 0x0669 лежит в str_speak_demo: слайд по строке 1-байтовыми NOP/MOV до RET 0x06C1; явный смысл не установлен (аномалия, Stage 7 трейсинг).
; called_from: unpacked RAM @0xEE00 (1.26M fetches runtime; not in ROM)
; exec_addr: 0x0663 (file 0x06BC − 0x59; boot self-relocation)
; interrupts: disabled (DI) for IRQ-free PDM busy-loop
; params: in=HL: pointer to phrase string (ASCII, 0x00-terminated). DI; CALL walker; NOP; RET. No register return. Caller (exec 0x0573): CALL 0DD0; LXI H,0x0600; CALL 0x0660.
; phrase_buffer_lead: exec buffer: [0x0600]=0x00 lead, [0x0601]='GRU DIL SOFT...'. HL passed = 0x0600 (points at the 0x00). Walker RZs on 0x00 -> either a 0x00-terminated phrase stored at 0x0601 or a silent/status tick call. Resolve in Stage 7.
; relocation: Speech engine + caller block stored in ROM at exec_addr + 0x59; boot copies down to exec_addr (no operand fixup — operands already target exec addresses). This explains Stage-2 'branch targets land inside string' anomaly: correct in exec space, false at file addr.
; role: speech_entry (DI; CALL walker; RET)
; speech_metering: busy-loop при IFF=0: DI на входе (0x0663 exec), в всей речевой цепочке (file 0x06BC..0x0790) НЕТ ни одного EI (проверено побайтово); ISR VBlank не может тикать речь
; speech_step: шаг = софтверный счётчик: LDA 0733 / DCR A / JNZ (exec 0x0706-0x070C; в ROM-файле паттерн 3A 33 07 3D C2 09 07 на 0x078C); ВИ53 (порты 08-0B) и счётчик луча (IN 02) в цикле эмита не используются
func_speak_start:
	dcx	d
	mov	a,d
	ora	e
	jnz	func_speak_start
; Обходчик строки текст→речь (тело 0x06C2..0x0712, 0x0715..0x071B — вложенный delay). Старт: B=0xBB — высота тона; чтение (HL); конец строки по 00h (ORA A/RZ 0x06C8). Классификация литер: CPI 41h 'A'..JM / CPI 5Bh '['..JP / 'C' / 'H' / 27h — спец-коды управляемой интонации/пауз; ремап букв ADI 1Ah; на литеру — CALL 0x06C3 (цель внутри пролога обходчика — аномалия, вероятная реальная цель = декодер func_speak_phoneme@0x071C). Паузы: '.'→DE=0x0000, ','→LXI D,8000, ' '→LXI D,4000 + func_voice_delay. Петля: INX H / JMP 0x066B (цель в str_speak_demo — аномалия, штатная петля должна возвращаться к чтению символа).
; exec_addr: 0x0669 (file 0x06C2 − 0x59)
; params: in=HL: string cursor; reads [HL] (MOV B,M), advances INX H. terminator: [HL]==0 -> ORA A/RZ (petle-style RET-after-terminator). B=0xBB pitch seed (internal, not input). Pauses set DE for '.'=0000 ','=8000 ' '=4000.
; pause_table: '.'=DE 0000, ','=8000, ' '=4000
; phrase_queue: буфер-очередь 0x0600: вызовы из кадрового цикла (exec 0x0579 LXI H,0600; 0x05E1) синтезируют фразу целиком блокирующим вызовом, затем MVI A,00 / STA 0600 (exec 0x05E4-0x05E9) очищает очередь
; pitch_reg: B=0x0BB (MVI B,BB; MOV B,M)
; role: phrase_iterator (walks str_speak_demo)
func_speak_walker:
	ret
; func_speak_phoneme — декодер фонемы + PDM-эмиттер (ядро голоса, EXEC 0x06C3; на диске twin 0x071C). Вход: A=raw ASCII charcode (из обходчика). Двойная индексация: (1) LXI B,06F7; HL=0x06F7+A → data_speak_char_index → смещение; (2) LXI B,076C; HL=0x076C+смещение → data_speak_codes → дескриптор. Разбор: ANI 0F=длительность C; RLC×3/ANI 07 = номер плоскости; ANI 80 = флаг. LXI D,0935+plane → B=data_speak_plane_lengths (число бит). LXI D,082E+RAL → бит-плоскость data_pdm_planes; ANA M / MVI A,80 → OUT 00 (0x00/0x01). Период бита: LDA 0733/DCR/JNZ (var_voice_period). Курсор сэмпла LHLD 0734 (var_voice_bufptr). RESOLVED: «аномалии» Stage 3 (ветки в строку) были артефактом разбора в FILE-адресах; в EXEC-пространстве всё связно (подтверждено живым stepping 'D'@0x09D1).
label_phoneme_call_tgt:
	lxi	b,06f7h
	mov	l,a
	mvi	h,00h
	dad	b
	lxi	b,076ch
	mov	l,m
	mvi	h,00h
	dad	b
label_06D1:
	mov	a,m
	ani	0fh
	mov	c,a
	inx	h
	mov	a,m
	ani	80h
	ora	c
	mov	c,a
	dcx	h
lbl_06dc:
        defb    07Eh,007h,007h,007h,0E6h,007h,0E5h,0CAh
        defb    01Bh,007h,011h,035h,009h,06Fh,026h,000h
        defb    019h,046h,0E1h,023h,07Eh,02Bh,0E5h,017h
        defb    011h,02Eh,008h,06Fh,026h,000h,019h,03Eh
        defb    080h
lbl_06fd:
	push	psw
	ana	m
	jz	lbl_0704
	mvi	a,01h
lbl_0704:
        defb    0D3h,000h,03Ah,033h,007h
lbl_0709:
        defb    03Dh,0C2h,009h,007h,0F1h,005h,0CAh,01Bh
        defb    007h,0B7h,00Fh,0D2h,0FDh,006h,023h,0C3h
        defb    0FDh,006h
lbl_071b:
; Счётчикsoftware-delay PDM-бита (LDA 0733/DCR/JNZ в func_speak_phoneme). Задаёт каденс бита-бэнга (~40 T-c на OUT 00h → ~37 кГц при такте машины). Косвенно = частота дискретизации речи.
        defb    02Ah,034h,007h,0EBh,0AFh,0CDh,0BCh,006h
        defb    00Dh,079h,0E6h,00Fh,0E1h,0C2h,0DCh,006h
        defb    079h,017h,0D8h,023h,023h,0C3h,0D1h,006h
var_voice_period:
; Курсор буфера сэмплов речи (LHLD 0734 в хвосте func_speak_phoneme, 0x071B). Указывает на текущую позицию в data_pdm_planes при побитовом выводе.
        defb    010h
var_voice_bufptr:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    000h,002h
gap_0736:
; Таблица-индексатор символ→смещение (exec). Операнд base=0x06F7; реальные литеры A..Z лежат на 0x0738+ (низкие control-коды никогда не индексируются — обходчик divertит '.'/','/' ' на паузы). Значения = смещения в articulogram data_speak_codes. A=0,B=2,C=6,D=10,E=14,F=16,G=18,H=22,I=26,J=28,K=34,L=38,M=42,N=46,O=50,P=52,Q=56,R=66,S=72,T=74,U=78,V=80,W=80,X=86,Y=26,Z=92. Дубли V=W=80, Y=I=26 = слитые фонемы транслита. Индекс = raw ASCII charcode (живой stepping: 'D'=0x44 → 0x073B → 10 → table2 0x0776).
        defb    060h,0EEh
data_speak_char_index:
; Последовательность артикулограмм-дескрипторов (exec base 0x076C). Индекс = смещение из data_speak_char_index. Единица читается func_speak_phoneme по 2 байта: byte0 — low-nibble=длительность (ANI 0F → C), bits4-6=номер бит-плоскости сэмпла (RLC×3/ANI 07), bit7=флаг; byte1 bit7=флаг продолжения пары. Чтение пар до терминатора (JZ 0x071B при plane#==0). Плоскость → длина из data_speak_plane_lengths, биты → data_pdm_planes. Пример 'D': offset 10 → 0x0776: 34 19 | 31 E0 | …
        defb    000h,002h,006h,00Ah,00Eh,010h,012h,016h
        defb    01Ah,01Ch,022h,026h,02Ah,02Eh,032h,034h
        defb    038h,042h,048h,04Ah,04Eh,050h,050h,056h
        defb    01Ah,05Ch,064h,066h,070h,074h,07Ah,07Ch
        defb    0C2h,084h,086h,0C2h,0C2h,0C2h,088h,08Ch
        defb    092h,094h,0C2h,09Eh,0A6h,0A8h,0AEh,0B0h
        defb    0C2h,0C2h,086h,0BCh
data_speak_codes:
; data_pdm_planes — база бит-плоскостей PDM-сэмплов (EXEC 0x082E..0x0934, ~262B высокоэнтропийных данных). Индекс: LXI D,082E + смещение(RAL из дескриптора) → ANA M (маска MVI A,80) → OUT 00 значением 0x00/0x01. Каждый бит плоскости = один такт PDM-бит-бэнга; период задаёт var_voice_period@0x0733 (~40 T-с → ~37 кГц). Это носитель звучания (форм-фактор units) — декодер выбирает плоскость по номеру из data_speak_codes.
        defb    036h,081h,034h,019h,031h,0ABh,018h,019h
        defb    091h,0C3h,034h,019h,031h,0E0h,036h,084h
        defb    092h,0E3h,035h,019h,051h,09Ch,031h,031h
        defb    034h,096h,036h,087h,033h,03Ah,032h,03Dh
        defb    032h,0C0h,018h,019h,051h,09Ch,033h,022h
        defb    031h,0B1h,031h,031h,036h,0A5h,031h,031h
        defb    036h,0A8h,036h,08Ah,018h,019h,031h,0ABh
        defb    018h,019h,051h,01Ch,034h,031h,032h,034h
        defb    032h,0B7h,022h,010h,013h,019h,021h,0AEh
        defb    092h,0C3h,018h,019h,031h,0E0h,036h,08Dh
        defb    034h,031h,032h,034h,032h,0B7h,018h,019h
        defb    071h,01Ch,092h,0C3h,032h,031h,032h,043h
        defb    032h,044h,032h,0C5h,03Fh,081h,034h,019h
        defb    031h,02Bh,033h,03Ah,032h,03Dh,032h,0C0h
        defb    018h,019h,091h,0D3h,033h,019h,071h,06Dh
        defb    032h,093h,03Eh,084h,092h,063h,033h,03Ah
        defb    032h,03Dh,032h,0C0h,092h,0F3h,03Eh,087h
        defb    031h,031h,036h,025h,031h,031h,035h,025h
        defb    032h,093h,03Eh,08Ah,018h,019h,031h,02Bh
        defb    033h,03Ah,032h,03Dh,032h,0C0h,013h,019h
        defb    032h,060h,013h,019h,071h,0DDh,092h,0D3h
        defb    018h,019h,071h,06Dh,032h,093h,03Eh,08Dh
        defb    034h,031h,032h,034h,032h,037h,033h,03Ah
        defb    032h,03Dh,032h,0C0h,032h,053h,032h,054h
        defb    032h,0D5h
data_pdm_planes:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    01Ah
gap_082F:
; Заголовок бит-плоскостей (exec): длины/число итераций эмита на единицу. Байты 00 2E 5A 5E FE (plane0..4). Читается как LXI D,0935 + plane# → MOV B,M = счётчик внутреннего цикла эмита (0x06ED). plane#==0 → конец фонемы (JZ 0x071B). Плотная упаковка: сразу за заголовком (0x093A) стартуют строки-фразы (область 0x098D/0x09C3).
        defb    099h,0E1h,0C3h,0E1h,0C7h,08Fh,00Fh,0F8h
        defb    003h,00Fh,007h,0C1h,0E3h,0FFh,040h,017h
        defb    0FFh,000h,003h,0F8h,07Ch,0C1h,0F1h,0F8h
        defb    003h,0FEh,000h,07Fh,0FCh,000h,003h,0F8h
        defb    00Fh,009h,0F1h,0FEh,003h,0EFh,040h,017h
        defb    0FFh,000h,003h,0E1h,05Ch,035h,0C5h,0AAh
        defb    035h,000h,000h,000h,000h,000h,000h,03Eh
        defb    08Eh,038h,073h,0CFh,0F8h,078h,0C3h,0DFh
        defb    01Ch,0F1h,0C7h,0FEh,003h,0C0h,0FFh,000h
        defb    000h,0FFh,0F8h,000h,07Fh,0F8h,003h,0FFh
        defb    0F0h,001h,0FFh,0E0h,003h,0AAh,0CAh,05Ah
        defb    0D5h,021h,03Dh,0FEh,01Fh,0F8h,000h,000h
        defb    01Fh,0FFh,0FCh,020h,000h,000h,003h,0FFh
        defb    0FFh,008h,079h,000h,002h,0FFh,0E1h,0C7h
        defb    01Fh,0E0h,003h,0FFh,0D0h,001h,0FFh,00Ch
        defb    003h,07Fh,001h,0FAh,05Fh,0C0h,007h,0F8h
        defb    00Fh,0C0h,0FFh,000h,042h,0AAh,0A5h,055h
        defb    05Ah,0AAh,0AAh,05Ah,0A5h,05Ah,0AAh,055h
        defb    055h,0AAh,0AAh,0A5h,055h,0AAh,05Ah,0AAh
        defb    0A5h,055h,0AAh,0AAh,0A5h,055h,0AAh,0AAh
        defb    055h,0A5h,0A5h,0AAh,0A5h,0B7h,066h,06Ch
        defb    0D8h,0F9h,0B3h,06Ch,0ADh,037h,037h,066h
        defb    0FCh,09Bh,087h,0F6h,0C0h,0D3h,0B6h,060h
        defb    0F7h,0F7h,03Eh,04Dh,0FBh,0FEh,05Dh,0B7h
        defb    0DEh,046h,0F6h,096h,0B4h,04Fh,0AAh,0A9h
        defb    055h,0AAh,0AAh,0A5h,069h,059h,09Ah,06Ah
        defb    095h,055h,095h,055h,06Ah,0A5h,055h,0A9h
        defb    04Dh,066h,06Ah,092h,0ECh,0A5h,055h,0D2h
        defb    096h,055h,0A2h,0BAh,0CDh,000h,066h,099h
        defb    0CCh,067h,031h,08Eh,066h,039h,0A6h,06Bh
        defb    019h,066h,059h,0C6h,071h,009h,067h,019h
        defb    0CBh,001h,071h,0CCh,073h,019h,099h,0CCh
        defb    0C6h,067h,019h,09Ah,0C6h,059h
data_speak_plane_lengths:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    000h,02Eh,05Ah,05Eh,0FEh
gap_093A:
; str_voice: речевая фраза (транслит, space-разделитель): «JSEM HLAS VAS'EHO POC'I'TAC'E SPEKTRUM» → ≈ «Йэм глас Вашэго почтачье Спектрум» («Я слыхал голос Вашего почерка, Спектрум»). Хедер записи 2E 5A 5E FE перед текстом. Озвучка движком речи (Stage 7).
        defb    04Ah,053h,045h,04Dh,020h,048h,04Ch,041h
        defb    053h,020h,056h,041h,053h,027h,045h,048h
        defb    04Fh,020h,050h,04Fh,043h,027h,049h,027h
        defb    054h,041h,043h,027h,045h,020h,053h,050h
        defb    045h,04Bh,054h,052h,055h,04Dh,000h,045h
        defb    053h,054h,049h,020h,044h,056h,041h,020h
        defb    053h,054h,04Fh,020h,044h,056h,041h,044h
        defb    043h,041h,054h,058h,020h,020h,047h,04Fh
        defb    052h,04Fh,044h,020h,042h,04Fh,052h,049h
        defb    053h,04Fh,056h,020h,020h,050h,041h,056h
        defb    04Ch,04Fh,057h
str_voice_098d:
; Uncovered ROM bytes — neither code nor an RDB object
        defm "A SEMNADCATX  PODOVDITE MINUTOHKU  POVALUJ"
gap_09B7:
; str_voice: речевая фраза (транслит): «ESTI DVA STO DVADCATX GOROD BORISOV PAVLOWA SEMNADCATX PODOVDITE MINUTOHKU POVALUJSTA» → «[в]от два сто двадцать, город Борисов Павлова семнадцать, подождите минутку, пожалуйста». str_voice_* — речь (Stage 7).
        defb    053h
str_voice_09b8:
; Uncovered ROM bytes — neither code nor an RDB object
        defm "TA        "
        defb    000h
        defm "ODIN"
        defb    000h
        defm "DWA"
        defb    000h
        defm "TRI"
        defb    000h
        defm "DIL SOFT PREDLAGAET NOWYE IGRY K WEKTOR NOL SEST C  PISITE PO ADR"
gap_0A11:
; str_voice: речевая фраза (транслит): «DIL SOFT PREDLAGAET NOWYE IGRY K WEKTOR NOL SEST C PISITE PO ADRESU DWESTE DWADCAT NOL SEMDESUAT ODIN ABANEBENTNYJ IASIK SESDESUAT ODIN» → «Дил Софт предлагает новые игры к Вектор-06… пишите по адресу 220-01-71 абонентский ящик 71». str_voice_* — речь (Stage 7).
        defb    045h,053h,055h,020h,020h,044h,057h,045h
        defb    053h,054h,045h,020h,044h,057h,041h,044h
        defb    043h,041h
str_voice_0a23:
; Видео-конвейер верхнего уровня: единственный вызов func_0B1E (0x0A60..0x0A?? хвост), плюс CALL 0x0DD0 (blob-ложный) и 0x0F45 (video_frame_out). По сути прослойка frame-цикла (0x0255) → big-модуль 0x0B1E. Границы уточнить Stage 3.
        defm "T NOL SEMDESUAT ODIN ABANEBENTNYJ IASIK SESDESUAT ODIN"
        defb    000h,000h,000h,000h,000h,000h,000h
func_0a60:
        defb    000h,000h,000h,0D5h,0CDh,0D0h,00Dh,0D1h
        defb    001h,0F8h,00Ch,0C9h
lbl_0a6c:
        defb    0CDh,01Eh,00Bh,021h,000h,080h
lbl_0a72:
        defb    07Eh,0EEh,0A5h,077h,023h,07Ch,0FEh,0A1h
        defb    0C2h,072h,00Ah,021h,000h,000h,011h,002h
        defb    080h,006h,000h
lbl_0a85:
        defb    01Ah,04Fh,009h,013h,07Ah,0FEh,0A1h,0C2h
        defb    085h,00Ah,0EBh,02Ah,000h,080h,07Dh,093h
        defb    07Ch,09Ah,0B7h,0C2h,0CEh,00Ah,021h,002h
        defb    080h,011h,04Ch,026h
lbl_0aa1:
        defb    07Eh,012h,023h,013h,0FEh,026h,0C2h,0A1h
        defb    00Ah,021h,080h,080h,011h,000h,057h
lbl_0ab0:
        defb    07Eh,012h,013h,023h,07Ch,0FEh,0A1h,0C2h
        defb    0B0h,00Ah,0CDh,0D0h,00Dh,021h,0C9h,00Ch
label_0AC0:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,045h,00Fh,0FBh,03Eh,080h,076h
gap_0AC7:
        defb    03Dh,0C2h,0C6h,00Ah,0C3h,000h,001h
lbl_0ace:
        defb    0CDh,0D0h,00Dh,021h,0D1h,00Ch,0C3h,0C0h
        defb    00Ah
label_0AD7:
        defb    02Ah,04Ah,026h
lbl_0ada:
        defb    07Eh,0FEh,026h,0CAh,0E9h,00Ah,023h,0B7h
        defb    0C2h,0DAh,00Ah,022h,04Ah,026h,0C9h
lbl_0ae9:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0F3h,031h,0F0h,000h,021h,000h,00Eh,022h
        defb    039h,000h,0CDh,0D0h,00Dh,021h,0E2h,00Ch
        defb    0CDh,045h,00Fh,021h,040h,00Ch,0CDh,045h
        defb    00Fh,001h,000h,003h,0FBh,076h
gap_0B07:
        defb    00Bh,078h,0B1h,0C2h,005h,00Bh,0C3h,08Eh
        defb    002h
func_0b10:
; Big-модуль 0x0B1E..0x0DCF (~700B, вызывается 1x из 0x0A60): по цензу OUT 0/2/3/12h + IN 2 + LDA 4200 + STA 0E47 — похоже на второй видеовывод/скролл (режим 512?) + запись управляющего слова в 0E47 (страницы/банки?). Сигнатуры из линейного дампа — candidates на рассинхрон; разметка Stage 3.
        defb    02Ah,07Eh,00Ch,023h,022h,07Eh,00Ch,026h
        defb    000h,07Dh,0E6h,03Fh,06Fh,0C9h
func_0b1e:
        defb    021h,000h,080h,022h,007h,07Ah,0C3h,0A0h
        defb    079h
label_0B27:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    07Ah,0FEh,003h,0DAh,025h,002h,0CDh,028h
        defb    005h,021h,030h,00Ch,0C3h,064h,002h
gap_0B36:
; str_screen: экранный текст (транслит/ASCII, разделитель слов '%'): «THE%FEDERATION%WILL%REWARD» → «Федерация вознаградит». Хедер записи display-list 70 E3 (позиция/команда). Рендерится func_display_list_interp@0x11D8 → func_render_glyph@0x114D (data_glyph_block@0x3780).
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
str_screen_0b96:
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_0BB2:
	defb	00h,00h,00h

; str_screen: экранный текст (% -разделитель): «ENTER%<FREEMAN>%IN%HISCORE» → «Введите <FREEMAN> в таблицу рекордов». Хедер записи 60 A3. str_screen_* — вывод на экран (func_display_list_interp@0x11D8).
str_screen_0bb5:
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_0BCF:
	defb	00h,00h,00h,00h,00h,00h,00h,00h

; str_screen: экранный текст (% -разделитель): «PLEASE%ENTER%YOUR%NAME» → «Пожалуйста, введите Ваше имя» (ввод имени в таблицу рекордов). В том же блоке 0x0B96..0x0C40: «NO%DRIVE%A», «ENTER%LEVEL%NAME», «NOT %…». func_display_list_interp@0x11D8.
str_screen_0bd7:
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_0BEE:
; str_screen: экранный текст (% -разделитель): «CONGRATULATIONS%%» → «Поздравляем» (двойной %% = пустое слово/конец). func_display_list_interp@0x11D8.
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,040h,0ACh,04Eh,04Fh,025h,047h
        defb    04Fh,054h,04Fh
str_screen_0c39:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    000h,0FFh,000h,000h,000h,000h,000h
        defm "p"
        defb    0E3h
        defm "THE%FEDER"
gap_0C4B:
; Ранний ревиз: это НЕ data-blob. runtime-доказательство (raster_events + mem-map 0x0D00 fetch=227718): код на 0x0DDC/0x0DDE/0x0DE0 выполняет OUT в палитрные порты 0x0C-0x0F в середине кадра (строки 59-65) — racing-the-beam effect. Требует CFG-ревизии в Stage 3.
; called_by_speech_path: exec 0x0573 (runtime caller) issues CALL 0x0DD0 immediately before LXI H,0600; CALL speech — init/output routine coupled to speech start
; ei_tail: в хвосте блока (file 0x0F2A, 0x0F3E) есть EI — разрешение прерываний после речевого/кадрового критичного участка
; io_ports: 0x0C-0x0F palette writes (raster_events: lines 59-65, ~48 v_cycle spacing)
; runtime_role: beam-race raster code (NOT a data blob): PCs 0x0DDC/0x0DDE/0x0DE0 emit OUT to palette ports mid-frame
; watchpoint_block: 0x0D00 blk fetch 227718 (hot executable)
        defb    041h,054h,049h,04Fh,04Eh,025h,057h,049h
        defb    04Ch,04Ch,025h,052h,045h,057h,041h,052h
        defb    044h,000h,060h,0A3h,045h,04Eh,054h,045h
        defb    052h,025h,03Ch,046h,052h,045h,045h,04Dh
        defb    041h,04Eh,03Eh,025h,049h,04Eh,025h,048h
        defb    049h,053h,043h,04Fh,052h,045h,000h,0FFh
        defb    044h,000h,0FFh,00Dh,000h,080h,0E5h,050h
        defb    04Ch,045h,041h,053h,045h,025h,045h,04Eh
        defb    054h,045h,052h,025h,059h,04Fh,055h,052h
        defb    025h,04Eh,041h,04Dh,045h,000h,0FFh,038h
        defb    0ECh,04Eh,04Fh,025h,044h,052h,049h,056h
        defb    045h,025h,041h,000h,0FFh,040h,088h,045h
        defb    04Eh,054h,045h,052h,025h,04Ch,045h,056h
        defb    045h,04Ch,025h,04Eh,041h,04Dh,045h,000h
        defb    0FFh,030h,0CBh,04Eh,04Fh,054h,025h,046h
        defb    04Fh,055h,04Eh,044h,000h,0FFh,040h,0CFh
        defb    04Fh,04Bh,045h,059h,000h,0FFh,030h,0AAh
        defb    04Ch,04Fh,041h,044h,049h,04Eh,047h,025h
        defb    045h,052h,052h,04Fh,052h,000h,0FFh,080h
        defb    0CAh,043h,04Fh,04Eh,047h,052h,041h,054h
        defb    055h,04Ch,041h,054h,049h,04Fh,04Eh,053h
        defb    025h,025h,000h,0FFh,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,011h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,00Fh,013h,00Bh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,033h,013h,013h
        defb    00Bh,0A5h,0A5h,0A5h,0A5h,083h,084h,0A5h
        defb    0A5h,0A5h,034h,013h,013h,079h,079h,079h
        defb    079h,079h,047h,0A5h,0A5h,059h,0A5h,035h
        defb    013h,013h,00Ch,0A5h,0A5h,0A5h,0A5h,077h
        defb    0A5h,063h,05Ah,06Ch,036h,013h,013h,00Eh
        defb    0A5h,0A5h,0A5h,0A5h,077h,0A5h,064h,05Bh
        defb    06Dh,035h,013h,013h,00Bh,0A5h,0A5h,0A5h
        defb    0A5h,077h,0A5h,065h,05Ch,0A5h,033h,013h
        defb    013h,07Fh,0A5h,0A5h,0A5h,0A5h,077h,0A5h
        defb    066h,05Dh,0A5h,035h,013h,013h,080h,0A5h
        defb    0A5h,0A5h,0A5h,077h,0A5h,067h,05Eh,0A5h
        defb    034h,013h,013h,081h,0A5h,0A5h,0A5h,0A5h
        defb    077h,0A5h,068h,05Fh,0A5h,036h,013h,013h
        defb    00Bh,0A5h,0A5h,0A5h,0A5h,077h,0A5h,069h
        defb    060h,0A5h,036h,013h,013h,00Eh,0A5h,0A5h
        defb    0A5h,0A5h,077h,0A5h,06Ah,061h,06Eh,033h
        defb    013h,013h,079h,079h,079h,079h,079h,048h
        defb    0A5h,0A5h,0A5h,06Fh,034h,013h,013h,00Ch
        defb    0A5h,0A5h,0A5h,0A5h,082h,085h,0A5h,0A5h
        defb    0A5h,035h,013h,013h,00Dh,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,036h,013h
        defb    012h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,010h
label_blob_0DD0:
        defb    0F3h,00Eh,080h
lbl_0dd3:
        defb    011h,00Fh,010h
lbl_0dd6:
        defb    07Bh,0D3h,002h,0AFh,0D3h,00Ch,0D3h,00Ch
        defb    0D3h,00Ch,01Dh,015h,0C2h,0D6h,00Dh,00Dh
        defb    0C2h,0D3h,00Dh,021h,000h,080h,0AFh
lbl_0ded:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    077h,023h,0BCh,0C2h,0EDh,00Dh,0C9h
gap_0DF4:
; ISR VBlank (RST 7). Живой факт Stage 4: boot патчит вектор 0x0038 на JMP 0E00; код ISR живёт в RAM (файл ROM по 0x0E00 — мусор, как и речевой блок: файл != exec после распаковки). int_events: ровно 1 прерывание/кадр, всегда vector 0x0038, raster_line=0, v_cycle_in_line 188-236. Тело: PUSH PSW/B/D/H → sweep луча (OUT 02 со счётчиком + 6×OUT 0C из таблицы 0x0E71) → OUT 00,8A → гонка IN 02/CPI FF с OUT 03 → CALL 0E57 (OUT 00,88; OUT 02,00) → POP → EI RET. Речь НЕ тикает отсюда: речевой блок работает при IFF=0.
; interrupt_vector: 0x0038 (RST 7), boot-patched JMP 0E00
; isr_io_ports: OUT 0x02 (счётчик луча), OUT 0x0C ×6 (палитра/гонка), OUT 0x03, IN 0x02 (poll), OUT 0x00 (0x8A/0x88 — строб на кадр)
; source: RAM-resident unpacked stub (в ROM-файле по 0x0E00 — данные; паттерн как у речевого блока −0x59)
; tick_rate: 1 interrupt per frame (50 Гц); int_events 729/729 кадров, raster_line=0
        defb    000h,000h,00Ah,000h,048h,045h,057h,053h
        defb    04Fh,04Eh,000h,000h
func_irq_vblank_isr:
        defb    0F5h,0C5h,0D5h,0E5h,021h,071h,00Eh,011h
        defb    00Fh,010h
label_0E0A:
        defb    07Bh,0D3h,002h,07Eh,0D3h,00Ch,0D3h,00Ch
        defb    0D3h,00Ch,0D3h,00Ch,0D3h,00Ch,0D3h,00Ch
        defb    02Bh,01Dh,015h,0C2h,00Ah,00Eh,03Eh,08Ah
        defb    0D3h,000h,011h,000h,008h,001h,008h,0FEh
label_0E2A:
        defb    078h,0D3h,003h,0DBh,002h,0FEh,0FFh,0C2h
        defb    048h,00Eh,07Bh,082h,05Fh,078h,007h,047h
        defb    00Dh,0C2h,02Ah,00Eh
label_0E3E:
; RAM-переменная залаченной клавиши. Пишется обработчиком опроса, читается/сбрасывается func_get_key@0x0F15 (LDA 0E47; ...; XRA A; STA 0E47). 0 = клавиша не нажата.
        defb    0CDh,057h,00Eh,0E1h,0D1h,0C1h,0F1h,0FBh
        defb    0C9h
var_key_latch:
        defb    011h
label_0E48:
        defb    01Fh,0D2h,050h,00Eh,01Ch,0C3h,048h,00Eh
label_0E50:
        defb    07Bh,032h,047h,00Eh,0C3h,03Eh,00Eh
label_0E57:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    03Eh,088h,0D3h,000h,0AFh,0D3h,002h,02Fh
        defb    0D3h,003h,0C9h
gap_0E62:
        defb    040h,0D6h,0F4h,0D0h,07Fh,086h,016h,036h
        defb    093h,0C5h,022h,0C0h,002h,098h,052h,0ADh
        defb    044h,049h,04Ch,025h,053h,04Fh,046h,054h
        defb    000h,025h,04Dh,049h,04Eh,053h,04Bh,025h
        defb    025h,000h,048h,049h,025h,053h,043h,04Fh
        defb    052h,045h,03Ah,000h,042h,059h,000h,048h
        defb    08Ch,031h,02Eh,053h,054h,041h,052h,054h
        defb    000h,038h,0ACh,032h,02Eh,04Ch,04Fh,041h
        defb    044h,000h,028h,0CCh,033h,02Eh,050h,041h
        defb    053h,053h,000h,0FFh,080h,0ACh,047h,045h
        defb    054h,025h,052h,045h,041h,044h,059h,000h
        defb    0FFh,040h,0E9h,045h,04Eh,054h,045h,052h
        defb    025h,050h,041h,053h,053h,057h,04Fh,052h
        defb    044h,000h,0FFh,038h,0ACh,046h,055h,043h
        defb    04Bh,025h,04Fh,046h,046h,000h,0FFh,080h
        defb    0CBh,059h,04Fh,055h,025h,041h,052h,045h
        defb    025h,044h,045h,041h,044h,000h,0FFh,046h
        defb    052h,045h,045h,04Dh,041h,04Eh,045h,025h
        defb    045h,04Eh,054h,045h,052h,025h,059h,04Fh
        defb    055h,052h,025h,04Eh,041h,04Dh
label_0F00:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    036h,000h,0C3h,0D7h,00Ah
gap_0F05:
        defb    02Ah,098h,024h
func_0f08:
; Чтение клавиатуры: LDA 0x0E47 (залatchенная клавиша, пишет ISR/аппаратный опрос); ORA A; RZ (нет клавиши → A=0); иначе XRA A; STA 0x0E47 (сброс latch); RET с кодом в A. Коды меню: 0x11/0x12/0x13 = 1/2/3.
; key_latch_var: 0x0E47 (RAM; 0 = нет клавиши; ненулевое = код, сбрасывается после чтения)
        defb    0CDh,03Eh,024h,02Ah,098h,024h,044h,04Dh
        defb    03Eh,030h,0C3h,014h,024h
func_get_key:
        defb    03Ah,047h,00Eh,0B7h,0C8h,0F5h,0AFh,032h
        defb    047h,00Eh,0F1h,0C9h
label_0F21:
        defb    021h,060h,088h,016h,040h
label_0F26:
        defb    0E5h,01Eh,004h
lbl_0f29:
        defb    0E5h,006h,010h
lbl_0f2c:
; Точка HLT главного цикла ожидания: int_events показывают was_halt=true, ret_pc=0x0F3D на каждом кадре — CPU спит до VBlank (RST 7 → JMP 0E00). Доказательство из live-трассы Stage 4.
        defb    036h,000h,024h,005h,0C2h,02Ch,00Fh,0E1h
        defb    001h,000h,020h,009h,01Dh,0C2h,029h,00Fh
        defb    076h
label_idle_hlt:
; Видеовывод кадра (бит-бэнг ПИА, CFG-выровнено @0x0F45). Сохраняет BC/DE/HL/PSW; HL=10C1 (таблица строки, RAM), DE=0F0F — счётчик 15 итераций; цикл: OUT 02h (=E, номер строки/бордюр PB), OUT 0Ch (M — данные строки), DCX H, OUT 0Dh, DCR E, OUT 0Eh, OUT 0Fh, JNZ 101B — стробирование С-порта ПИА (сдвиг-регистр). Хвост: MVI A,8Ah/OUT 00h — КС ПИА (режим клавиатуры, V06_CW_KEYSCAN), серии OUT 03h FE/FD/FB + IN 02h/CMA/STA 11CE..11CF — опрос луча/строки через порт A. Связан с func_0F5B/func_1065 (CALL из хвоста 0x0F90/0x0F93) и с речью (OUT 00h 88h в 0x0F88 — КС ПИА, не звук). Точная раскладка 512-режима = Stage 7.
; io_ports: 0x02(PB border/mode), 0x0C-0x0F(palette bit-bang), IN 0x02(beam)
; video_rows: 15-iteration OUT sweep; table HL=0x10C1; keyscan CW=0x8A
; watchpoint_vram: 0xDC00 blk (W 202314/R 178310) framebuffer
        defb    000h,0E1h,02Dh,015h,0C2h,026h,00Fh,0C9h
func_video_frame_out:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    04Eh,023h,046h,023h,0CDh,082h,005h,023h
        defb    07Eh,0FEh,0FFh,0C8h,0C3h,045h,00Fh
gap_0F54:
        defb    02Ch,07Eh,0A9h,077h,0E1h,0C1h,0C9h
label_0F5B:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,072h,00Fh,021h,0BAh,010h,07Eh,03Ch
        defb    0F6h,0C0h,077h,0C9h
gap_0F67:
        defb    00Ah,0B7h,0C2h,05Eh,002h,021h,000h,057h
        defb    0C3h,025h,002h
label_0F72:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,09Eh,010h,021h,0B3h,010h,07Eh,0EEh
        defb    019h,077h,0C9h
gap_0F7D:
        defb    077h,02Bh,0C3h,0D1h,001h,025h,023h,01Ch
        defb    07Bh,0FEh,007h,0C2h,081h,00Fh,0D1h,0C9h
label_0F8D:
; Поллинг таймера КР580ВИ53 (каналы = порты 08h/09h по v06.h; OUT 08/09 в теле по цензу, CFG-граница ~0x0F9C подтверждена хвостом предшественника POP PSW..RET). Чтение LDA 10AD (флаг таймера), счётчик DCR M на 10B2, при обнулении — CALL 1091 (перезарка ВИ53) + LHLD 10B0 (деление 16 бит). Используется кадровым циклом (вызван из 0E00-области по цензу — под сомнением выравнивания, уточнить Stage 3 CFG).
; stage4_note: Под вопросом как VI53: живой io_trace (10000 событий, ~76 кадров) показывает НОЛЬ обращений к портам 08h-0Bh; в ISR 0x0E00 тоже. Тело читает LDA 10AD/DCR M 10B2/LHLD 10B0 — RAM-переменные.possible misclassification, пересмотреть карту портов в Stage 5/7
        defb    000h,00Ah,0FEh,025h,0C2h,05Eh,002h,021h
        defb    000h,057h,0C3h,027h,00Bh
func_vi53_timer_poll:
; Пункт меню 2.LOAD (код клавиши 0x12): цель JZ из func_menu_dispatcher@0x0199. Экран загрузки/пароля (данные пароля — Stage 8).
; screen_role: Пункт меню 2.LOAD — экран загрузки. Как данные (пароль/проходы) — Stage 8.
        defb    03Eh,00Bh,0D3h,019h,04Fh,0E3h,0E3h,0DBh
        defb    019h,0B9h,0C9h
label_screen_load:
        defb    0CDh,028h,005h,0CDh,09Ah,00Fh,0CAh,0B4h
        defb    00Fh,021h,09Ah,00Ch,0C3h,064h,002h
lbl_0fb4:
        defb    021h,0A8h,00Ch,0CDh,0C4h,001h,0CDh,060h
        defb    00Ah,021h,080h,077h,036h,000h,023h,016h
        defb    008h
lbl_0fc5:
        defb    00Ah,077h,003h,023h,015h,01Dh,0C2h,0C5h
        defb    00Fh
lbl_0fce:
        defb    036h,020h,023h,015h,0C2h,0CEh,00Fh,036h
        defb    04Ch,023h,036h,045h,023h,036h,056h,00Eh
        defb    020h
lbl_0fdf:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    036h,000h,023h,00Dh,0C2h,0DFh,00Fh,0CDh
        defb    020h,079h,03Ah,011h,07Ah,0B7h,0C2h,06Ch
        defb    00Ah,0CDh,0D0h,00Dh,0FBh,021h,0BCh,00Ch
        defb    0C3h,0C0h,00Ah
gap_0FFA:
; Точка входа главного цикла игры (exec 0x1000). Живой факт Stage 5: путь START (0x01A4) после рендера и HLT-выдержки делает JMP 0x1000. Горячий блок по memory_access_map во время игры: 0x1700 (fetch 6.77M — внутренний цикл/растер), 0x1100 (2.55M), 0x1400/0x1500/0x1000. Код игры в RAM-области 0x1000..0x2500 (после распаковки). HUD: LEVEL/FIRE/SCORE/LIFE/STAGE. Подробный разбор цикла/спрайтов — вне scope Stage 5.
; hot_block: memory_access_map во время игры: 0x1700 (fetch 6.77M — внутренний цикл/растер), 0x1100 (2.55M), 0x1400/0x1500/0x1000. Игровой код в RAM 0x1000..0x2500 после распаковки.
; hud_vars_note: HUD (SCORE/LIFE/STAGE/LEVEL/FIRE) выводится через func_video_frame_out@0x0F45 (в пути START: LXI H,0EAE; CALL 0F45). Точные адреса var_score/var_lives/var_stage — вне scope Stage 5 (поверхностно); разбор рендера экрана/текста → Stage 6.
        defb    046h,055h,043h,04Bh,000h,000h
func_game_main:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0F3h,021h,011h,010h,022h,039h,000h,0FBh
        defb    076h
gap_1009:
        defb    076h,076h,0C3h,0EDh,013h
lbl_100e:
; Не вход функции (бывш. func_frame_out_512 — ложное имя линейного прохода): 0x1011 попадает в середину вычислителя адресов (0x1019 PUSH PSW / RRC / ANI 03 / RRC x3 / ANI 1F / ADD B / … / LXI D,4EB0 / DAD / RET) — распаковка (x,y) → адрес строки экранного буфера (512x256: D7/100h — page-банки, умножения сдвигом). Реальный хост-видеовывод = func_video_frame_out@0x0F45. Граница функции ≈0x100D..0x1019 — уточнить Stage 3 CFG. 0x0F61 JNZ 101B прыгает внутрь этого вычислителя (общий трек бит-плоскостей).
        defb    0C3h,08Eh,002h
label_scr512_addr_calc:
        defb    0E5h,0D5h,0C5h,0F5h,021h,0C1h,010h,011h
        defb    00Fh,00Fh
label_101B:
        defb    07Bh,0D3h,002h,07Eh,0D3h,00Ch,02Bh,0D3h
        defb    00Dh,01Dh,0D3h,00Eh,0D3h,00Fh,015h,0C2h
        defb    01Bh,010h,03Eh,08Ah,0D3h,000h,03Eh,0FEh
        defb    0D3h,003h,0DBh,002h,02Fh,032h,0CEh,011h
        defb    03Eh,0FDh,0D3h,003h,0DBh,002h,02Fh,032h
        defb    0CFh,011h,03Eh,0FBh,0D3h,003h,0DBh,002h
        defb    02Fh,032h,0D0h,011h,03Eh,088h,0D3h,000h
        defb    0AFh,0D3h,002h,02Fh,0D3h,003h,0CDh,065h
        defb    010h,0CDh,05Bh,00Fh,0F1h,0C1h,0D1h,0E1h
        defb    0FBh,0C9h
label_1065:
        defb    03Ah,0ADh,010h,0B7h,0C8h,021h,0B2h,010h
        defb    035h,0C0h,0EBh,0CDh,091h,010h,02Ah,0B0h
        defb    010h,07Eh,0B7h,0CAh,089h,010h,012h,023h
        defb    05Eh,023h,056h,023h,022h,0B0h,010h,0EBh
        defb    022h,0AEh,010h,0C9h
label_1089:
        defb    0AFh,032h,0ADh,010h,0CDh,091h,010h,0C9h
label_1091:
        defb    03Eh,0B6h,0D3h,008h,03Eh,076h,0D3h,008h
        defb    03Eh,036h,0D3h,008h,0C9h
label_109E:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    03Ah,0ADh,010h,0B7h,0C8h,02Ah,0AEh,010h
        defb    07Dh,0D3h,009h,07Ch,0D3h,009h,0C9h
gap_10AD:
        defb    000h,000h,000h,000h,000h,040h,0D6h,0F4h
        defb    0D0h,093h,086h,016h,036h,0E5h,0C5h,022h
        defb    0C0h,002h,098h,052h,0ADh,000h
func_10c3:
        defb    0F5h,07Ah,00Fh,0E6h,003h,04Fh,07Ah,00Fh
        defb    00Fh,00Fh,0E6h,01Fh,080h,057h,0F1h,087h
        defb    087h,081h,0D5h,06Fh,026h,000h,029h,029h
        defb    029h,029h,011h,0B0h,04Eh,019h,0D1h,0C9h
func_10e3:
        defb    0F5h,07Ah,00Fh,0E6h,003h,04Fh,07Ah,00Fh
        defb    00Fh,00Fh,0E6h,01Fh,080h,057h,0F1h,087h
        defb    087h,081h,0D5h,06Fh,026h,000h,029h,029h
        defb    029h,029h,054h,05Dh,029h,019h,011h,0A0h
        defb    02Ah,019h,0D1h,0C9h
func_1107:
        defb    0F3h,0C5h,0D5h,0E5h,0CDh,0E3h,010h,0EBh
        defb    001h,010h,003h,0CDh,01Ah,011h,0E1h,0D1h
        defb    0C1h,0FBh,0C9h
func_111a:
        defb    07Dh,081h,06Fh,0C5h,0EBh,001h,0F8h,0FFh
        defb    009h,0EBh,0C1h
lbl_1125:
        defb    0C5h
lbl_1126:
        defb    01Ah,0AEh,077h,013h,024h,005h,0C2h,026h
        defb    011h,0C1h,07Ch,090h,067h,02Dh,00Dh,0C2h
        defb    025h,011h,0C9h
func_1139:
        defb    0C5h
lbl_113a:
; Рендер одного глифа экранного шрифта (Stage 6). Вход: A = код символа. Адрес глифа = A*32 + 0x3780 (`MOV L,A; MVI H,00; DAD H` ×5 = ×32; `LXI D,3780; DAD D`) → data_glyph_block. Затем адрес в VRAM из курсора (`ANI 1F; ADI A0` — плоскости 0xA000/0x8000) и копирование (`LXI B,0210; CALL 0x111A`). ПРЕЖНЯЯ Stage-3 подпись «клавиатурный диспетчер, CPI 93/97..» ошибочна: эта CPI-цепочка принадлежит func_display_list_interp@0x11D8; сюда A приходит уже как код символа из цикла 0x1241.
        defb    01Ah,0AEh,077h,024h,013h,005h,0C2h,03Ah
        defb    011h,0C1h,07Ch,090h,067h,02Ch,00Dh,0C2h
        defb    039h,011h,0C9h
func_render_glyph:
        defb    000h,0C5h,0D5h,0E5h,0F5h,06Fh,026h,000h
        defb    029h,029h,029h,029h,029h,0D5h,011h,080h
        defb    037h,019h,0D1h,07Ah,0E6h,01Fh,0C6h,0A0h
        defb    057h,07Bh,0E6h,01Fh,087h,087h,087h,05Fh
        defb    0EBh,001h,010h,002h,0CDh,01Ah,011h,0F1h
        defb    0E1h,0D1h,0C1h,000h,0C9h
func_117a:
        defb    0F3h,0C5h,0D5h,0E5h,0EBh,006h,010h,0CDh
        defb    080h,01Eh,0EBh,03Eh,00Ah,0CDh,08Fh,011h
        defb    0E1h,0D1h,0C1h,0FBh,0C9h
func_118f:
        defb    0F3h,0C5h,0D5h,0E5h,0EBh,006h,080h,0CDh
        defb    0C3h,010h,001h,008h,002h,0EBh,0CDh,039h
        defb    011h,0E1h,0D1h,0C1h,0FBh,0C9h
func_11a5:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0F3h,0C5h,0D5h,0E5h,0F5h,006h,002h,0CDh
        defb    0A9h,01Eh,0F1h,06Fh,026h,000h,029h,029h
        defb    029h,029h,029h,0D5h,011h,080h,037h,019h
        defb    0D1h,07Ah,0F6h,0A0h,057h,0EBh,001h,010h
        defb    002h,0CDh,01Ah,011h,0E1h,0D1h,0C1h,0FBh
        defb    0C9h
gap_11CE:
        defb    000h,000h,000h,000h,054h,000h,057h
func_11d5:
; Интерпретатор экранного display-list (рендер текста/графики). Живой факт Stage 6: цикл 0x11E0 `MOV A,M` читает байт скрипта; цепочка CPI/CZ — управляющие коды: 1C/1F→0x12D9, 3D→0x1303, 45/46→0x1328, 27/31→0x134F, 51→0x1388, 91→0x13C2, A6→0x13AA, 26/2F→0x1270, 93/97→0x12A4, A7→0x1276, A8/A9/AA→0x13C6 (координаты/атрибуты/спец-команды). Обычный печатный символ (в т.ч. '%') → 0x1240 `INX H; CALL func_render_glyph@0x114D`. Вызывается из bootstrap (CALL 0x11D8) на экранных скриптах 0x0E72/0x0E7B/0x0E84.
        defb    02Ah,0D1h,011h
func_display_list_interp:
        defb    011h,000h,000h,006h,010h
lbl_11dd:
        defb    00Eh,00Dh,0D5h
lbl_11e0:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    07Eh,0FEh,01Ch,0CCh,0D9h,012h,0FEh,01Fh
        defb    0CCh,0D9h,012h,0FEh,03Dh,0CCh,003h,013h
        defb    0FEh,045h,0CCh,028h,013h,0FEh,046h,0CCh
        defb    028h,013h,0FEh,027h,0CCh,04Fh,013h,0FEh
        defb    031h,0CCh,04Fh,013h,0FEh,051h,0CCh,088h
        defb    013h,0FEh,091h,0CCh,0C2h,013h,0FEh,0A6h
        defb    0CCh,0AAh,013h,0FEh,026h,0CCh,070h,012h
        defb    0FEh,02Fh,0CCh,070h,012h,0FEh,093h,0CCh
        defb    0A4h,012h,0FEh,097h,0CCh,0A4h,012h,0FEh
        defb    0A7h,0CCh,076h,012h,0FEh,0A8h,0CCh,0C6h
        defb    013h,0FEh,0A9h,0CCh,0C6h,013h,0FEh,0AAh
        defb    0CCh,0C6h,013h,0FEh,0ABh,0CCh,0C6h,013h
        defb    023h,0CDh,04Dh,011h,01Ch,01Ch,00Dh,0C2h
        defb    0E0h,011h,0D1h,014h,014h,005h,0C2h,0DDh
        defb    011h,0C9h
gap_1252:
        defb    021h,000h,0A0h,00Eh,010h,006h,020h,0E5h
        defb    036h,0FFh,0E5h,07Dh,0D6h,020h,06Fh,036h
        defb    0FFh,0E1h,024h,005h,0C2h,05Ah,012h,0E1h
        defb    02Ch,00Dh,0C2h,057h,012h,0C9h
label_1270:
        defb    0EBh,022h,045h,01Bh,0EBh,0C9h
label_1276:
        defb    0F5h,0C5h,0D5h,0E5h,021h,09Fh,01Fh,034h
        defb    07Eh,03Dh,04Fh,087h,081h,02Ah,0A0h,01Fh
        defb    085h,06Fh,036h,000h,023h,0EBh,07Dh,087h
        defb    087h,087h,06Fh,012h,013h,07Ch,087h,087h
        defb    087h,067h,012h,0AFh,0CDh,03Bh,016h,0E1h
        defb    0D1h,0C1h,0F1h,03Eh,0A5h,0C9h
label_12A4:
        defb    0F5h,0C5h,0D5h,0E5h,001h,000h,0F8h,0FEh
        defb    093h,0CAh,0B3h,012h,001h,001h,018h
lbl_12b3:
        defb    021h,0B5h,01Eh,034h,07Eh,03Dh,0C5h,04Fh
        defb    087h,081h,02Ah,0B6h,01Eh,085h,06Fh,0C1h
        defb    071h,023h,0EBh,07Dh,087h,087h,087h,0C6h
        defb    004h,012h,013h,07Ch,087h,087h,087h,080h
        defb    012h,0E1h,0D1h,0C1h,0F1h,0C9h
label_12D9:
        defb    0F5h,0C5h,0D5h,0E5h,006h,001h,0FEh,01Fh
        defb    0CAh,0E6h,012h,006h,000h
lbl_12e6:
        defb    021h,047h,01Bh,034h,07Eh,03Dh,087h,087h
        defb    02Ah,048h,01Bh,085h,06Fh,036h,000h,023h
        defb    070h,023h,0EBh,07Dh,012h,013h,07Ch,012h
        defb    0E1h,0D1h,0C1h,0F1h,0C9h
label_1303:
        defb    0F5h,0C5h,0D5h,0E5h,021h,09Ah,01Bh,034h
        defb    07Eh,03Dh,087h,087h,02Ah,09Bh,01Bh,085h
        defb    06Fh,036h,000h,023h,036h,000h,023h,0EBh
        defb    07Dh,087h,087h,087h,012h,013h,07Ch,012h
        defb    0E1h,0D1h,0C1h,0F1h,0C9h
label_1328:
        defb    0F5h,0C5h,0D5h,0E5h,0D6h,045h,047h,021h
        defb    021h,01Ch,034h,07Eh,03Dh,087h,087h,02Ah
        defb    022h,01Ch,085h,06Fh,036h,000h,023h,070h
        defb    023h,0EBh,07Dh,087h,087h,087h,012h,013h
        defb    07Ch,012h,0E1h,0D1h,0C1h,0F1h,0C9h
label_134F:
        defb    0F5h,0C5h,0D5h,0E5h,001h,010h,002h,0FEh
        defb    027h,0CAh,05Eh,013h,001h,0F8h,000h
lbl_135e:
        defb    021h,012h,01Dh,034h,07Eh,03Dh,0C5h,04Fh
        defb    087h,081h,0C1h,02Ah,013h,01Dh,085h,06Fh
        defb    070h,023h,0EBh,07Dh,087h,087h,087h,081h
        defb    012h,013h,078h,087h,047h,07Ch,090h,087h
        defb    087h,087h,0C6h,004h,012h,0E1h,0D1h,0C1h
        defb    0F1h,0C9h
label_1388:
        defb    0F5h,0C5h,0D5h,0E5h,021h,001h,01Eh,034h
        defb    07Eh,03Dh,087h,087h,02Ah,002h,01Eh,085h
        defb    06Fh,036h,000h,023h,036h,000h,023h,0EBh
        defb    07Dh,012h,013h,07Ch,012h,0E1h,0D1h,0C1h
        defb    0F1h,0C9h
label_13AA:
        defb    0C5h,0D5h,0E5h,07Ah,087h,087h,087h,057h
        defb    07Bh,087h,087h,087h,05Fh,0EBh,022h,01Dh
        defb    016h,0E1h,0D1h,0C1h,03Eh,0A5h,077h,0C9h
label_13C2:
        defb    03Eh,0A5h,077h,0C9h
label_13C6:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0F5h,0C5h,0D5h,0E5h,021h,0B2h,022h,034h
        defb    0D6h,0A8h,047h,07Eh,03Dh,04Fh,087h,081h
        defb    02Ah,0B3h,022h,085h,06Fh,070h,023h,07Bh
        defb    087h,087h,087h,077h,023h,07Ah,087h,087h
        defb    087h,077h,0E1h,0D1h,0C1h,0F1h,0C9h
gap_13ED:
        defb    0F3h,021h,000h,080h,001h,000h,000h,071h
        defb    023h,07Ch,0B8h,0C2h,0F4h,013h,031h,0FFh
        defb    000h,0FBh,03Eh,006h,032h,0E1h,024h,03Eh
        defb    005h,032h,0E4h,024h,032h,0E3h,024h,021h
        defb    000h,000h,022h,0DFh,024h,000h,000h,000h
        defb    000h,000h,000h,0AFh,032h,0E2h,024h,021h
        defb    000h,054h,022h,0D1h,011h,021h,000h,057h
        defb    022h,0D3h,011h,0CDh,0DFh,025h,0CDh,03Dh
        defb    026h,0AFh,032h,01Fh,016h,032h,0F4h,018h
        defb    032h,0F5h,018h
label_1438:
        defb    032h,016h,025h,032h,0F6h,018h,032h,047h
        defb    01Bh,032h,09Ah,01Bh,032h,021h,01Ch,032h
        defb    012h,01Dh,032h,017h,01Dh,032h,001h,01Eh
        defb    032h,0B5h,01Eh,032h,00Ch,01Fh,032h,09Fh
        defb    01Fh,032h,0FDh,020h,032h,0F5h,018h,032h
        defb    0B2h,022h,032h,00Ch,023h,0CDh,0CCh,025h
        defb    03Eh,001h,032h,089h,025h,021h,0C8h,000h
        defb    022h,08Ah,025h,02Ah,04Ah,026h,001h,0F0h
        defb    0A7h,0CDh,033h,024h
func_147c:
        defb    021h,000h,055h,022h,0F7h,018h,021h,020h
        defb    055h,022h,048h,01Bh,021h,040h,055h,022h
        defb    09Bh,01Bh,021h,060h,055h,022h,022h,01Ch
        defb    021h,080h,055h,022h,013h,01Dh,021h,0C0h
        defb    055h,022h,018h,01Dh,021h,0A0h,055h,022h
        defb    002h,01Eh,021h,000h,056h,022h,0B6h,01Eh
        defb    021h,020h,056h,022h,00Dh,01Fh,021h,040h
        defb    056h,022h,0A0h,01Fh,021h,060h,056h,022h
        defb    0FBh,020h,021h,080h,056h,022h,0B3h,022h
        defb    021h,0A0h,056h,022h,00Dh,023h,0CDh,0D5h
        defb    011h,0CDh,022h,016h,0CDh,0E5h,024h,0CDh
        defb    045h,025h
label_14D6:
        defb    0CDh,011h,015h,0CDh,0DEh,019h,0CDh,04Ah
        defb    01Bh,0CDh,09Fh,01Bh,0CDh,026h,01Ch,0CDh
        defb    01Ah,01Dh,0CDh,066h,01Dh,0CDh,006h,01Eh
        defb    0CDh,0BAh,01Eh,0CDh,011h,01Fh,0CDh,0A4h
        defb    01Fh,0CDh,000h,021h,0CDh,0B7h,022h,0CDh
        defb    011h,023h,0DBh,001h,0E6h,040h,0CAh,00Eh
        defb    010h,03Ah,0F5h,018h,0B7h,0C4h,0B2h,01Ah
        defb    0C3h,0D6h,014h
func_1511:
        defb    03Ah,09Bh,015h,0B7h,0CAh,01Dh,015h,03Dh
        defb    032h,09Bh,015h,0C9h
lbl_151d:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    03Eh,005h,032h,09Bh,015h,0CDh,08Eh,025h
        defb    03Ah,0D0h,011h,0FEh,002h,0CCh,080h,025h
        defb    0FEh,004h,0CCh,080h,025h,03Ah,0CFh,011h
        defb    0FEh,002h,0CCh,080h,025h,0FEh,004h,0CCh
        defb    080h,025h,03Ah,0CEh,011h,04Fh,0E6h,002h
        defb    0FEh,002h,0CAh,0F9h,018h,079h,0E6h,008h
        defb    0FEh,008h,0C5h,0CCh,069h,019h,0C1h,079h
        defb    0E6h,030h,0FEh,030h,0CAh,011h,016h,079h
        defb    0E6h,060h,0FEh,060h,0CAh,017h,016h,079h
        defb    0E6h,010h,0FEh,010h,0CAh,09Ch,015h,079h
        defb    0E6h,020h,0FEh,020h,0CAh,0EBh,015h,079h
        defb    0E6h,040h,0FEh,040h,0CAh,0C2h,015h,02Ah
        defb    01Dh,016h,02Dh,07Dh,0FEh,008h,0DAh,0ADh
        defb    022h,0CDh,057h,017h,0C2h,006h,018h,0CDh
        defb    0CDh,01Ah,0CDh,022h,016h,022h,01Dh,016h
        defb    0CDh,0CDh,01Ah,0C3h,022h,016h
gap_159B:
        defb    005h
func_159c:
        defb    02Ah,01Dh,016h,025h,025h,07Ch,0FEh,008h
        defb    0DAh,09Eh,022h,0CDh,06Fh,017h,0C2h,006h
        defb    018h,0CDh,0CDh,01Ah,0CDh,022h,016h,024h
        defb    022h,01Dh,016h,03Eh,001h,032h,01Fh,016h
        defb    0CDh,0CDh,01Ah,0C3h,022h,016h
func_15c2:
        defb    02Ah,01Dh,016h,07Ch,0C6h,010h,067h,0FEh
        defb    0F8h,0D2h,0A3h,022h,0CDh,06Fh,017h,0C2h
        defb    006h,018h,0CDh,022h,016h,0CDh,0CDh,01Ah
        defb    02Ah,01Dh,016h,024h,0AFh,032h,01Fh,016h
        defb    022h,01Dh,016h,0CDh,0CDh,01Ah,0C3h,022h
        defb    016h
lbl_15eb:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    02Ah,01Dh,016h,07Dh,0C6h,010h,06Fh,0FEh
        defb    0C8h,0D2h,0A8h,022h,0CDh,057h,017h,0C2h
        defb    006h,018h,0CDh,022h,016h,0CDh,0CDh,01Ah
        defb    02Ah,01Dh,016h,02Ch,022h,01Dh,016h,0CDh
        defb    0CDh,01Ah,0C3h,022h,016h
gap_1610:
        defb    0C9h
lbl_1611:
        defb    0CDh,09Ch,015h,0C3h,0EBh,015h
lbl_1617:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,0C2h,015h,0C3h,0EBh,015h
gap_161D:
        defb    0A0h,010h,000h,09Fh,010h
func_1622:
        defb    0C5h,0E5h,0D5h,02Ah,01Dh,016h,0EBh,03Ah
        defb    01Fh,016h,006h,0C0h,0CDh,007h,011h,03Ah
        defb    0F4h,018h,0B7h,0CAh,09Ch,016h,0C3h,093h
        defb    016h
func_163b:
        defb    0F3h,0C5h,0E5h,0D5h,0EBh,0F5h,006h,010h
        defb    0CDh,080h,01Eh,0F1h,0C6h,002h,006h,0C0h
        defb    0CDh,007h,011h,0D1h,0E1h,0C1h,0FBh,0C9h
func_1653:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0F3h,0C5h,0D5h,0E5h,0F5h,006h,010h,0CDh
        defb    080h,01Eh,0F1h,0C6h,00Ch,006h,0E0h,0CDh
        defb    007h,011h,0E1h,0D1h,0C1h,0FBh,0C9h
gap_166A:
        defb    0F3h,0C5h,0D5h,0E5h,0C6h,008h,006h,0C0h
        defb    0CDh,007h,011h,0E1h,0D1h,0C1h,0FBh,0C9h
func_167a:
        defb    02Ah,01Dh,016h,07Ch,0C6h,010h,067h,03Ah
        defb    01Fh,016h,04Fh,0B7h,0C2h,08Dh,016h,07Ch
        defb    0D6h,020h,067h
lbl_168d:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    079h,0C6h,006h,0C9h
gap_1691:
        defb    000h,000h
label_1693:
        defb    0CDh,07Ah,016h,0EBh,006h,0C0h,0CDh,007h
        defb    011h
lbl_169c:
        defb    0D1h,0E1h,0C1h,0C9h
label_16A0:
        defb    011h,005h,000h,0CDh,071h,025h,02Ah,0D1h
        defb    011h,006h,0D0h
lbl_16ab:
        defb    07Eh,0FEh,026h,0CCh,0E6h,016h,0FEh,027h
        defb    0CCh,0E6h,016h,0FEh,028h,0CCh,0E6h,016h
        defb    0FEh,029h,0CCh,0E6h,016h,023h,005h,0C2h
        defb    0ABh,016h,02Ah,045h,01Bh,0EBh,03Eh,026h
        defb    0CDh,04Dh,011h,014h,014h,03Ch,0CDh,04Dh
        defb    011h,01Dh,01Dh,03Ch,03Ch,0CDh,04Dh,011h
        defb    03Dh,015h,015h,0CDh,04Dh,011h,0AFh,032h
        defb    012h,01Dh,0C9h
label_16E6:
        defb    036h,0A5h,0C9h
label_16E9:
        defb    011h,005h,000h,0CDh,071h,025h,02Ah,0D1h
        defb    011h,006h,0D0h
lbl_16f4:
        defb    07Eh,0FEh,02Fh,0CCh,0E6h,016h,0FEh,030h
        defb    0CCh,0E6h,016h,0FEh,031h,0CCh,0E6h,016h
        defb    0FEh,032h,0CCh,0E6h,016h,023h,005h,0C2h
        defb    0F4h,016h,02Ah,045h,01Bh,0EBh,03Eh,02Fh
        defb    0CDh,04Dh,011h,014h,014h,03Ch,0CDh,04Dh
        defb    011h,01Dh,01Dh,03Ch,03Ch,0CDh,04Dh,011h
        defb    015h,015h,03Dh,0CDh,04Dh,011h,0AFh,032h
        defb    012h,01Dh,0C9h
label_172F:
        defb    011h,003h,000h,0CDh,071h,025h,02Ah,0D1h
        defb    011h,006h,0D0h
lbl_173a:
        defb    07Eh,0FEh,051h,0CCh,0E6h,016h,0FEh,052h
        defb    0CCh,0E6h,016h,023h,005h,0C2h,03Ah,017h
        defb    02Ah,002h,01Eh,0EBh,0EBh,0CDh,028h,01Eh
        defb    0AFh,032h,001h,01Eh,0C9h
func_1757:
        defb    0C5h,0D5h,0E5h,00Eh,010h
label_175C:
        defb    016h,000h
lbl_175e:
        defb    0E5h,0CDh,087h,017h,0E1h,0B2h,057h,024h
        defb    00Dh,0C2h,05Eh,017h,0E1h,0D1h,0C1h,0B7h
        defb    0C9h
func_176f:
        defb    0C5h,0D5h,0E5h,00Eh,010h
label_1774:
        defb    016h,000h
lbl_1776:
        defb    0E5h,0CDh,087h,017h,0E1h,0B2h,057h,02Ch
        defb    00Dh,0C2h,076h,017h,0E1h,0D1h,0C1h,0B7h
        defb    0C9h
func_1787:
        defb    07Ch,0E6h,007h,01Eh,080h
label_178C:
        defb    0B7h,0CAh,099h,017h,0F5h,07Bh,00Fh,05Fh
        defb    0F1h,03Dh,0C3h,08Ch,017h
lbl_1799:
        defb    07Ch,0E6h,0F8h,0B7h,01Fh,0B7h,01Fh,0B7h
        defb    01Fh,0C6h,0A0h,067h,07Eh,0A3h,0C9h
func_17a8:
        defb    0C5h,0D5h,0E5h,07Ch,0C6h,0A0h,067h,001h
        defb    000h,008h
lbl_17b2:
        defb    07Eh,0B1h,04Fh,02Ch,005h,0C2h,0B2h,017h
        defb    0E1h,0D1h,079h,0B7h,0C1h,0C9h
func_17c0:
        defb    0C5h,00Eh,008h,0CDh,0C8h,017h,0C1h,0C9h
func_17c8:
        defb    0C5h,0D5h,0E5h,0C3h,05Ch,017h
func_17ce:
        defb    0C5h,00Eh,008h,0CDh,0D6h,017h,0C1h,0C9h
func_17d6:
        defb    0C5h,0D5h,0E5h,0C3h,074h,017h
func_17dc:
        defb    07Dh,0E6h,0F0h,00Fh,00Fh,00Fh,00Fh,04Fh
        defb    07Ch,0E6h,0F0h,00Fh,00Fh,00Fh,00Fh,067h
        defb    021h,000h,000h,011h,00Dh,000h
label_17F2:
        defb    0B7h,0CAh,0FBh,017h,019h,03Dh,0C3h,0F2h
        defb    017h
lbl_17fb:
        defb    0E5h,02Ah,0D1h,011h,0EBh,0E1h,019h,006h
        defb    000h,009h,0C9h
lbl_1806:
        defb    022h,020h,016h,0CDh,0DCh,017h,04Eh,07Eh
        defb    0FEh,070h,0CCh,064h,018h,0FEh,076h,0CCh
        defb    0D0h,018h,0FEh,075h,0CCh,0AFh,018h,0FEh
        defb    08Bh,0CCh,099h,018h,0FEh,071h,0CCh,083h
        defb    018h,0FEh,072h,0CCh,083h,018h,0FEh,073h
        defb    0CCh,083h,018h,0FEh,074h,0CCh,083h,018h
        defb    0C9h
func_1837:
        defb    036h,0A5h,02Ah,020h,016h,07Ch,00Fh,00Fh
        defb    00Fh,0E6h,01Eh,0C6h,0A0h,057h,07Dh,00Fh
        defb    00Fh,00Fh,0E6h,01Eh,05Fh,079h,0CDh,04Dh
        defb    011h,0C9h
func_1851:
        defb    036h,0A5h,07Ah,0E6h,01Eh,0C6h,0A0h,057h
        defb    07Bh,00Fh,00Fh,00Fh,0E6h,01Eh,05Fh,079h
        defb    0C3h,04Dh,011h
label_1864:
        defb    0CDh,037h,018h,011h,001h,000h,0CDh,071h
        defb    025h,021h,033h,026h,0CDh,0F1h,025h,03Ah
        defb    0F4h,018h,0B7h,0C0h,03Eh,001h,032h,0F4h
        defb    018h,0C5h,0D5h,0E5h,0C3h,093h,016h
label_1883:
        defb    0F5h,0CDh,037h,018h,0F1h,0D6h,070h,05Fh
        defb    016h,000h,0CDh,071h,025h,021h,015h,026h
        defb    0CDh,0F1h,025h,0C3h,045h,025h
label_1899:
        defb    0CDh,037h,018h,011h,00Ah,000h,0CDh,071h
        defb    025h,021h,033h,026h,0CDh,0F1h,025h,021h
        defb    0E1h,024h,034h,0C3h,045h,025h
label_18AF:
        defb    0CDh,037h,018h,011h,004h,000h,0CDh,071h
        defb    025h,021h,0E3h,024h,011h,0E4h,024h,03Ah
        defb    016h,025h,0B7h,0CAh,0C6h,018h,0EBh
lbl_18c6:
        defb    034h,021h,033h,026h,0CDh,0F1h,025h,0C3h
        defb    017h,025h
label_18D0:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,037h,018h,021h,033h,026h,0CDh,0F1h
        defb    025h,011h,002h,000h,0CDh,071h,025h,03Ah
        defb    0F5h,018h,0B7h,0C0h,03Eh,001h,032h,0F5h
        defb    018h,03Dh,032h,082h,01Ah,032h,083h,01Ah
        defb    0CDh,0CDh,01Ah,0C9h
gap_18F4:
        defb    000h,000h,000h,000h,055h
lbl_18f9:
        defb    03Ah,016h,025h,0B7h,0CAh,01Bh,019h,03Ah
        defb    089h,025h,0B7h,0C0h,021h,0E4h,024h,07Eh
        defb    0B7h,0C8h,035h,0CDh,017h,025h,03Eh,001h
        defb    032h,089h,025h,021h,02Ch,001h,022h,08Ah
        defb    025h,0C9h
lbl_191b:
        defb    03Ah,0FDh,020h,0B7h,0C0h,021h,0E3h,024h
        defb    07Eh,0B7h,0C8h,035h,0CDh,017h,025h,021h
        defb    0C2h,001h,022h,0FEh,020h,03Eh,001h,032h
        defb    0FDh,020h,00Eh,004h,03Eh,001h,006h,001h
        defb    02Ah,01Dh,016h,0EBh,02Ah,0FBh,020h
lbl_1942:
        defb    072h,023h,073h,023h,077h,023h,070h,023h
        defb    0F5h,0E5h,0D5h,0C5h,0EBh,025h,025h,025h
        defb    025h,0CDh,091h,020h,0C1h,0D1h,0E1h,0F1h
        defb    014h,014h,014h,014h,02Fh,0F5h,078h,02Fh
        defb    047h,0F1h,00Dh,0C2h,042h,019h,0C9h
label_1969:
        defb    03Ah,0F4h,018h,0B7h,0CAh,0A5h,019h,0CDh
        defb    0A5h,019h,03Ah,01Fh,016h,0F5h,02Ah,01Dh
        defb    016h,0E5h,07Ch,0C6h,010h,067h,03Ah,01Fh
        defb    016h,0B7h,0C2h,08Ah,019h,07Ch,0D6h,020h
        defb    067h
lbl_198a:
        defb    07Dh,0C6h,00Ah,06Fh,022h,01Dh,016h,03Ah
        defb    01Fh,016h,0EEh,001h,032h,01Fh,016h,0CDh
        defb    0A5h,019h,0E1h,022h,01Dh,016h,0F1h,032h
        defb    01Fh,016h,0C9h
func_19a5:
        defb    03Ah,0F6h,018h,0FEh,003h,0C8h,03Ch,032h
        defb    0F6h,018h,03Dh,04Fh,087h,081h,02Ah,0F7h
        defb    018h,085h,06Fh,0EBh,03Ah,01Fh,016h,012h
        defb    013h,02Ah,01Dh,016h,0B7h,0C2h,0C9h,019h
        defb    07Ch,0C6h,018h,067h
lbl_19c9:
        defb    07Dh,012h,013h,07Ch,0D6h,008h,067h,012h
        defb    03Ah,01Fh,016h,0CDh,08Fh,011h,021h,0FFh
        defb    025h,0CDh,0F1h,025h,0C9h
func_19de:
        defb    02Ah,040h,01Ah,07Ch,0B5h,0CAh,0EBh,019h
        defb    02Bh,022h,040h,01Ah,0C9h
lbl_19eb:
        defb    021h,001h,000h,022h,040h,01Ah,03Ah,0F6h
        defb    018h,0B7h,0C8h,04Fh,02Ah,0F7h,018h
label_19FA:
        defb    0E5h,046h,023h,07Eh,023h,066h,06Fh,078h
        defb    0CDh,08Fh,011h,0EBh,0E1h,0E5h,07Eh,046h
        defb    0EBh,0B7h,0CAh,02Fh,01Ah,025h,025h,0CDh
        defb    0CEh,017h,0C2h,042h,01Ah
label_1A17:
        defb    02Dh,0CDh,0CEh,017h,0C2h,042h,01Ah,078h
        defb    0CDh,08Fh,011h,0EBh,0E1h,023h,073h,023h
        defb    072h,023h
label_1A29:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    00Dh,0C8h,0C3h,0FAh,019h
gap_1A2E:
        defb    0C9h
lbl_1a2f:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0E5h,07Ch,0C6h,00Ah,067h,0CDh,0CEh,017h
        defb    0E1h,0C2h,042h,01Ah,024h,024h,0C3h,017h
        defb    01Ah
gap_1A40:
        defb    001h,000h
lbl_1a42:
        defb    0CDh,060h,01Ah,021h,0F6h,018h,035h,0E1h
        defb    0E5h,0E5h,023h,023h,023h,054h,05Dh,0E1h
        defb    006h,014h
lbl_1a54:
        defb    01Ah,077h,013h,023h,005h,0C2h,054h,01Ah
        defb    0E1h,0C3h,029h,01Ah
func_1a60:
        defb    0C5h,0E5h,054h,05Dh,0D5h,0CDh,0DCh,017h
        defb    0D1h,07Eh,04Eh,0FEh,018h,0CCh,073h,01Ah
        defb    0E1h,0C1h,0C9h
label_1A73:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    07Ah,00Fh,00Fh,00Fh,057h,0CDh,051h,018h
        defb    011h,001h,000h,0CDh,071h,025h,0C9h
gap_1A82:
        defb    000h,000h
func_1a84:
        defb    02Ah,01Dh,016h,011h,0E0h,000h,03Ah,082h
        defb    01Ah,0E6h,003h,0B7h,0CAh,0DBh,01Ah,011h
        defb    000h,0E0h,03Dh,0CAh,0E7h,01Ah,011h,020h
        defb    000h,03Dh,0CAh,0F1h,01Ah,011h,000h,020h
        defb    019h,00Ah,094h,02Fh,03Ch,067h,00Ah,095h
        defb    02Fh,03Ch,06Fh,0C3h,0FAh,01Ah
label_1AB2:
        defb    001h,083h,01Ah,0CDh,084h,01Ah,021h,083h
        defb    01Ah,034h,07Eh,0FEh,020h,0CCh,0C8h,01Ah
        defb    001h,083h,01Ah,0C3h,084h,01Ah
label_1AC8:
        defb    036h,000h,02Bh,034h,0C9h
func_1acd:
        defb    03Ah,0F5h,018h,0B7h,0C8h,0E5h,001h,083h
        defb    01Ah,0CDh,084h,01Ah,0E1h,0C9h
lbl_1adb:
        defb    019h,00Ah,094h,02Fh,03Ch,067h,00Ah,085h
        defb    06Fh,0C3h,0FAh,01Ah
lbl_1ae7:
        defb    019h,00Ah,084h,067h,00Ah,085h,06Fh,0C3h
        defb    0FAh,01Ah
lbl_1af1:
        defb    019h,00Ah,084h,067h,00Ah,095h,02Fh,03Ch
        defb    06Fh
label_1AFA:
        defb    0C5h,0D5h,0E5h,03Eh,010h,006h,0C0h,022h
        defb    043h,01Bh,0EBh,0CDh,007h,011h,0EBh
label_1B09:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,0DCh,017h,07Eh,0FEh,026h,0CCh,0A0h
        defb    016h,0FEh,027h,0CCh,0A0h,016h,0FEh,028h
        defb    0CCh,0A0h,016h,0FEh,029h,0CCh,0A0h,016h
        defb    0FEh,02Fh,0CCh,0E9h,016h,0FEh,030h,0CCh
        defb    0E9h,016h,0FEh,031h,0CCh,0E9h,016h,0FEh
        defb    032h,0CCh,0E9h,016h,0FEh,051h,0CCh,02Fh
        defb    017h,0FEh,052h,0CCh,02Fh,017h,0E1h,0D1h
        defb    0C1h,0C9h
gap_1B43:
        defb    000h,000h,000h,000h,000h,020h,055h
func_1b4a:
        defb    02Ah,096h,01Bh,07Ch,0B5h,0CAh,057h,01Bh
        defb    02Bh,022h,096h,01Bh,0C9h
lbl_1b57:
        defb    021h,01Eh,000h,022h,096h,01Bh,03Ah,047h
        defb    01Bh,0B7h,0C8h,04Fh,02Ah,048h,01Bh
label_1B66:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0E5h,046h,023h,07Eh,05Eh,087h,083h,080h
        defb    0C6h,01Ch,023h,05Eh,023h,056h,0CDh,04Dh
        defb    011h,0E1h,07Eh,03Ch,0FEh,003h,0CCh,098h
        defb    01Bh,077h,047h,023h,07Eh,05Eh,087h,083h
        defb    080h,0C6h,01Ch,023h,05Eh,023h,056h,0CDh
        defb    04Dh,011h,023h,00Dh,0C8h,0C3h,066h,01Bh
gap_1B96:
        defb    001h,000h
label_1B98:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0AFh,0C9h
gap_1B9A:
        defb    000h,040h,055h,00Dh,000h
func_1b9f:
        defb    02Ah,09Dh,01Bh,07Ch,0B5h,0CAh,0ACh,01Bh
        defb    02Bh,022h,09Dh,01Bh,0C9h
lbl_1bac:
        defb    021h,00Fh,000h,022h,09Dh,01Bh,03Ah,09Ah
        defb    01Bh,0B7h,0C8h,04Fh,02Ah,09Bh,01Bh,0C3h
        defb    0DBh,01Bh
func_1bbe:
        defb    0E5h,023h,07Eh,0F5h,0C6h,03Dh,023h,05Eh
        defb    023h,056h,0CDh,0A5h,011h,0F1h,0C6h,041h
        defb    047h,0D5h,07Bh,0C6h,030h,05Fh,078h,0CDh
        defb    0A5h,011h,0D1h,0E1h,0C9h
lbl_1bdb:
        defb    0CDh,0BEh,01Bh,023h,07Eh,03Ch,0E6h,003h
        defb    077h,02Bh,07Eh,0B7h,0C2h,00Dh,01Ch,0D5h
        defb    07Bh,0D6h,008h,05Fh,0EBh,0CDh,0A8h,017h
        defb    0EBh,0D1h,01Dh
label_1BF6:
        defb    0B7h,0C4h,01Ch,01Ch,023h,023h,073h,023h
        defb    023h,0E5h,02Bh,02Bh,02Bh,02Bh,0CDh,0BEh
        defb    01Bh,0E1h,00Dh,0C2h,0DBh,01Bh,0C9h
lbl_1c0d:
        defb    0D5h,07Bh,0C6h,040h,05Fh,0EBh,0CDh,0A8h
        defb    017h,0EBh,0D1h,01Ch,0C3h,0F6h,01Bh
label_1C1C:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    07Eh,0EEh,001h,077h,0C9h
gap_1C21:
        defb    000h,060h,055h,00Dh,000h
func_1c26:
        defb    02Ah,024h,01Ch,07Ch,0B5h,0CAh,033h,01Ch
        defb    02Bh,022h,024h,01Ch,0C9h
lbl_1c33:
        defb    021h,00Fh,000h,022h,024h,01Ch,03Ah,021h
        defb    01Ch,0B7h,0C8h,04Fh,0C5h,02Ah,01Dh,016h
        defb    07Ch,00Fh,00Fh,00Fh,0E6h,01Fh,047h,02Ah
        defb    022h,01Ch
lbl_1c4d:
        defb    023h,023h,023h,07Eh,0B8h,0CCh,0B9h,01Ch
        defb    03Ch,0B8h,023h,00Dh,0C2h,04Dh,01Ch,0C1h
        defb    02Ah,022h,01Ch
label_1C60:
        defb    07Eh,0B7h,0CAh,0B2h,01Ch,0FAh,0B2h,01Ch
        defb    023h,07Eh,0C6h,045h,047h,07Eh,023h,05Eh
        defb    023h,056h,0CDh,0C7h,01Ch,0B7h,0C2h,09Ah
        defb    01Ch,0D5h,07Bh,0C6h,010h,05Fh,0EBh,0CDh
        defb    0A8h,017h,0EBh,0D1h,0C2h,0CEh,01Ch,0CDh
        defb    0D6h,01Ch,0C2h,0CEh,01Ch,01Ch
label_1C8E:
        defb    02Bh,073h,023h,023h,0CDh,0C7h,01Ch
label_1C95:
        defb    00Dh,0C8h,0C3h,060h,01Ch
lbl_1c9a:
        defb    0D5h,07Bh,0D6h,008h,05Fh,0EBh,0CDh,0A8h
        defb    017h,0EBh,0D1h,0C2h,0CEh,01Ch,0CDh,0D6h
        defb    01Ch,0C2h,0CEh,01Ch,01Dh,0C3h,08Eh,01Ch
lbl_1cb2:
        defb    023h,023h,023h,023h,0C3h,095h,01Ch
label_1CB9:
        defb    02Bh,02Bh,02Bh,07Eh,0B7h,0C2h,0C3h,01Ch
        defb    036h,001h
lbl_1cc3:
        defb    023h,023h,023h,0C9h
func_1cc7:
        defb    0F5h,078h,0CDh,0A5h,011h,0F1h,0C9h
lbl_1cce:
        defb    0E5h,02Bh,02Bh,02Bh,036h,0FFh,0E1h,0C9h
func_1cd6:
        defb    0D5h,0C5h,0E5h,03Ah,0F6h,018h,0B7h,0CAh
        defb    003h,01Dh,04Fh,02Ah,0F7h,018h
lbl_1ce4:
        defb    023h,07Eh,093h,0F2h,0ECh,01Ch,02Fh,03Ch
lbl_1cec:
        defb    0FEh,008h,0D2h,00Eh,01Dh,023h,07Eh,092h
        defb    0F2h,0F9h,01Ch,02Fh,03Ch
lbl_1cf9:
        defb    0FEh,004h,0DAh,009h,01Dh
label_1CFE:
        defb    023h,00Dh,0C2h,0E4h,01Ch
lbl_1d03:
        defb    0AFh
label_1D04:
        defb    0B7h,0E1h,0C1h,0D1h,0C9h
lbl_1d09:
        defb    03Eh,001h,0C3h,004h,01Dh
lbl_1d0e:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    023h,0C3h,0FEh,01Ch
gap_1D12:
        defb    000h,080h,055h,0ECh,001h,000h,0C0h,055h
func_1d1a:
        defb    02Ah,015h,01Dh,07Ch,0B5h,0CAh,027h,01Dh
        defb    02Bh,022h,015h,01Dh,0C9h
lbl_1d27:
        defb    0CDh,081h,01Fh,06Fh,026h,001h,022h,015h
        defb    01Dh,03Ah,012h,01Dh,0B7h,0C8h,02Ah,013h
        defb    01Dh,046h,023h,05Eh,023h,056h,0CDh,041h
        defb    01Dh,0C9h
func_1d41:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    03Ah,017h,01Dh,0FEh,00Dh,0C8h,03Ch,032h
        defb    017h,01Dh,03Dh,04Fh,087h,081h,02Ah,018h
        defb    01Dh,085h,06Fh,070h,023h,073h,023h,072h
        defb    0EBh,0CDh,07Ah,011h,021h,029h,026h,0CDh
        defb    0F1h,025h,0C9h
gap_1D64:
        defb    008h,000h
func_1d66:
        defb    02Ah,064h,01Dh,07Ch,0B5h,0CAh,073h,01Dh
        defb    02Bh,022h,064h,01Dh,0C9h
lbl_1d73:
        defb    021h,014h,000h,022h,064h,01Dh,03Ah,017h
        defb    01Dh,0B7h,0C8h,04Fh,02Ah,018h,01Dh
label_1D82:
        defb    046h,023h,05Eh,023h,056h,0EBh,0CDh,07Ah
        defb    011h,0EBh,0E5h,02Ah,01Dh,016h,07Ch,0BAh
        defb    0DAh,0A8h,01Dh,0D5h,0E5h,0EBh,07Ch,0C6h
        defb    009h,067h,0CDh,0C0h,017h,0E1h,0D1h,0C2h
        defb    0E6h,01Dh,014h,0C3h,0B1h,01Dh
lbl_1da8:
        defb    015h,0EBh,0CDh,0C0h,017h,0EBh,0C2h,0E6h
        defb    01Dh
label_1DB1:
        defb    07Dh,0BBh,0DAh,0C9h,01Dh,0D5h,0E5h,07Bh
        defb    0C6h,009h,05Fh,0EBh,0CDh,0CEh,017h,0E1h
        defb    0D1h,0C2h,0E6h,01Dh,01Ch,0C3h,0D2h,01Dh
lbl_1dc9:
        defb    01Dh,0EBh,0CDh,0CEh,017h,0EBh,0C2h,0E6h
        defb    01Dh
label_1DD2:
        defb    0E1h,0CDh,0E0h,01Dh,02Bh,073h,023h,072h
        defb    023h,00Dh,0C8h,0C3h,082h,01Dh
func_1de0:
        defb    0EBh,0CDh,07Ah,011h,0EBh,0C9h
lbl_1de6:
        defb    0E1h,03Ah,017h,01Dh,03Dh,032h,017h,01Dh
        defb    0E5h,023h,05Dh,054h,02Bh,02Bh,02Bh,006h
        defb    028h
lbl_1df7:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    01Ah,077h,013h,023h,005h,0C2h,0F7h,01Dh
        defb    0E1h,0C9h
gap_1E01:
        defb    000h,0A0h,055h,0D5h,000h
func_1e06:
        defb    02Ah,004h,01Eh,07Ch,0B5h,0CAh,013h,01Eh
        defb    02Bh,022h,004h,01Eh,0C9h
lbl_1e13:
        defb    0CDh,081h,01Fh,06Fh,026h,000h,022h,004h
        defb    01Eh,03Ah,001h,01Eh,0B7h,0C8h,04Fh,02Ah
        defb    002h,01Eh,0C3h,03Dh,01Eh
func_1e28:
        defb    0E5h,023h,07Eh,087h,0C6h,051h,023h,05Eh
        defb    023h,056h,0CDh,04Dh,011h,014h,014h,03Ch
        defb    0CDh,04Dh,011h,0E1h,0C9h
label_1E3D:
        defb    0CDh,028h,01Eh,07Eh,023h,0B7h,0CAh,04Fh
        defb    01Eh,035h,07Eh,0B7h,0CCh,063h,01Eh,0C3h
        defb    056h,01Eh
lbl_1e4f:
        defb    034h,07Eh,0FEh,003h,0CCh,05Bh,01Eh
label_1E56:
        defb    02Bh,0CDh,028h,01Eh,0C9h
label_1E5B:
        defb    02Bh,036h,001h,023h,0CDh,06Ah,01Eh,0C9h
label_1E63:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    02Bh,036h,000h,023h,0C9h
gap_1E68:
        defb    000h,000h
func_1e6a:
        defb    0E5h,07Bh,087h,087h,087h,0D6h,00Ch,05Fh
        defb    023h,07Ah,03Dh,087h,087h,087h,0C6h,004h
        defb    057h,0CDh,041h,01Dh,0E1h,0C9h
func_1e80:
        defb    02Ah,01Dh,016h,07Ch
label_1E84:
        defb    092h,0F2h,08Ah,01Eh,02Fh,03Ch
lbl_1e8a:
        defb    0B8h,0D0h,07Dh,093h,0F2h,093h,01Eh,02Fh
        defb    03Ch
lbl_1e93:
        defb    0FEh,010h,0D0h,03Ah,089h,025h,0B7h,0C0h
        defb    0F3h,031h,0FFh,000h,021h,0E1h,024h,035h
        defb    0FAh,00Eh,010h,0C3h,076h,022h
func_1ea9:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    02Ah,01Dh,016h,07Ch,00Fh,00Fh,00Fh,0E6h
        defb    01Fh,0C3h,084h,01Eh
gap_1EB5:
        defb    000h,000h,056h,04Ch,000h
func_1eba:
        defb    02Ah,0B8h,01Eh,07Ch,0B5h,0CAh,0C7h,01Eh
        defb    02Bh,022h,0B8h,01Eh,0C9h
lbl_1ec7:
        defb    0CDh,081h,01Fh,06Fh,0CDh,081h,01Fh,0E6h
        defb    003h,067h,022h,0B8h,01Eh,03Ah,0B5h,01Eh
        defb    0B7h,0C8h,04Fh,02Ah,0B6h,01Eh
label_1EDD:
        defb    046h,023h,05Eh,023h,056h,0CDh,0EBh,01Eh
        defb    023h,00Dh,0C8h,0C3h,0DDh,01Eh
func_1eeb:
        defb    0E5h,0C5h,021h,00Ch,01Fh,07Eh,0FEh,005h
        defb    0CAh,009h,01Fh,034h,07Eh,03Dh,04Fh,087h
        defb    081h,02Ah,00Dh,01Fh,085h,06Fh,070h,023h
        defb    073h,023h,072h,0CDh,0E0h,01Dh
lbl_1f09:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0C1h,0E1h,0C9h
gap_1F0C:
        defb    000h,020h,056h,006h,000h
func_1f11:
        defb    02Ah,00Fh,01Fh,07Ch,0B5h,0CAh,01Eh,01Fh
        defb    02Bh,022h,00Fh,01Fh,0C9h
lbl_1f1e:
        defb    021h,00Ah,000h,022h,00Fh,01Fh,03Ah,00Ch
        defb    01Fh,0B7h,0C8h,04Fh,02Ah,00Dh,01Fh
label_1F2D:
        defb    0E5h,023h,05Eh,023h,056h,0CDh,0E0h,01Dh
        defb    0E1h,07Eh,0B7h,0C2h,051h,01Fh,015h,0EBh
        defb    0CDh,0CEh,017h,0EBh,0C2h,064h,01Fh
label_1F44:
        defb    023h,073h,023h,072h,023h,0CDh,0E0h,01Dh
        defb    00Dh,0C8h,0C3h,02Dh,01Fh
lbl_1f51:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0D5h,07Ah,0C6h,009h,057h,0EBh,0CDh,0CEh
        defb    017h,0EBh,0D1h,0C2h,064h,01Fh,014h,0C3h
        defb    044h,01Fh
gap_1F63:
        defb    0C9h
lbl_1f64:
        defb    03Ah,00Ch,01Fh,03Dh,032h,00Ch,01Fh,0E5h
        defb    023h,023h,023h,054h,05Dh,0E1h,0E5h,006h
        defb    014h
lbl_1f75:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    01Ah,077h,013h,023h,005h,0C2h,075h,01Fh
        defb    0E1h,0C9h
gap_1F7F:
        defb    0FCh,0F7h
func_1f81:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0C5h,0E5h,02Ah,07Fh,01Fh,07Ch,007h,007h
        defb    007h,0E6h,0F8h,084h,047h,07Dh,007h,007h
        defb    0E6h,03Fh,085h,085h,098h,065h,06Fh,022h
        defb    07Fh,01Fh,0E1h,0C1h,0C9h
gap_1F9E:
        defb    0C9h,000h,040h,056h,000h,000h
func_1fa4:
        defb    02Ah,0A2h,01Fh,07Ch,0B5h,0CAh,0B1h,01Fh
        defb    02Bh,022h,0A2h,01Fh,0C9h
lbl_1fb1:
        defb    021h,005h,000h,022h,0A2h,01Fh,03Ah,09Fh
        defb    01Fh,0B7h,0C8h,04Fh,02Ah,0A0h,01Fh
label_1FC0:
        defb    0E5h,07Eh,023h,05Eh,023h,056h,0EBh,0CDh
        defb    07Ah,020h,0EBh,0E1h,07Eh,0B7h,0CAh,004h
        defb    020h,03Dh,0CAh,026h,020h,03Dh,0CAh,048h
        defb    020h,0C3h,05Bh,020h
func_1fdc:
        defb    0D5h,01Dh,0EBh,0CDh,057h,017h,0EBh,0D1h
        defb    0C0h,01Dh,0AFh,0C9h
label_1FE8:
        defb    07Eh,023h,073h,023h,072h,023h,0EBh,0CDh
        defb    07Ah,020h,0EBh,00Dh,0C8h,0C3h,0C0h,01Fh
func_1ff8:
        defb    0D5h,015h,0EBh,0CDh,06Fh,017h,0EBh,0D1h
        defb    0C0h,015h,0AFh,0C9h
lbl_2004:
        defb    0CDh,0DCh,01Fh,006h,003h,0B7h,0CAh,076h
        defb    020h,0CDh,0F8h,01Fh,0B7h,0C2h,06Eh,020h
        defb    0C3h,0E8h,01Fh
func_2017:
        defb    0D5h,07Bh,0C6h,010h,05Fh,0EBh,0CDh,057h
        defb    017h,0EBh,0D1h,0C0h,01Ch,0AFh,0C9h
lbl_2026:
        defb    0CDh,0F8h,01Fh,006h,000h,0B7h,0CAh,076h
        defb    020h,0CDh,017h,020h,0B7h,0C2h,06Eh,020h
        defb    0C3h,0E8h,01Fh
func_2039:
        defb    0D5h,07Ah,0C6h,010h,057h,0EBh,0CDh,06Fh
        defb    017h,0EBh,0D1h,0C0h,014h,0AFh,0C9h
lbl_2048:
        defb    0CDh,017h,020h,006h,001h,0B7h,0CAh,076h
        defb    020h,0CDh,039h,020h,0B7h,0C2h,06Eh,020h
        defb    0C3h,0E8h,01Fh
label_205B:
        defb    0CDh,039h,020h,006h,002h,0B7h,0CAh,076h
        defb    020h,0CDh,0DCh,01Fh,0B7h,0C2h,06Eh,020h
        defb    0C3h,0E8h,01Fh
lbl_206e:
        defb    07Eh,03Ch,0E6h,003h,077h,0C3h,0E8h,01Fh
lbl_2076:
        defb    070h,0C3h,0E8h,01Fh
func_207a:
        defb    0FEh,001h,0CAh,087h,020h,0FEh,003h,0CAh
        defb    08Ch,020h
label_2084:
        defb    0C3h,03Bh,016h
lbl_2087:
        defb    03Eh,003h,0C3h,084h,020h
lbl_208c:
        defb    03Eh,001h,0C3h,084h,020h
func_2091:
        defb    0C5h,0CDh,0BBh,020h,0E5h,011h,0CCh,020h
        defb    006h,004h
lbl_209b:
        defb    01Ah,013h,06Fh,026h,000h,079h
lbl_20a1:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    029h,03Dh,0C2h,0A1h,020h,0EBh,0E3h,07Ah
        defb    0AEh,077h,024h,07Bh,0AEh,077h,025h,02Dh
        defb    0E3h,0EBh,005h,0C2h,09Bh,020h,0E1h,0C1h
        defb    0C9h
gap_20BA:
	defb	0C9h

func_20bb:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    07Ch,0E6h,007h,02Fh,0C6h,009h,04Fh,07Ch
        defb    01Fh,01Fh,01Fh,0E6h,01Fh,0C6h,080h,067h
        defb    0C9h
gap_20CC:
        defb    006h,00Fh,00Fh,006h,000h,000h
func_20d2:
        defb    021h,000h,0A0h,06Bh,079h,0B7h,01Fh,0B7h
        defb    01Fh,0B7h,01Fh,084h,067h,079h,0E6h,007h
        defb    047h,078h,0B7h,0CAh,0F3h,020h,07Eh,048h
lbl_20ea:
        defb    0B7h,017h,00Dh,0C2h,0EAh,020h,0C3h,0F4h
        defb    020h
lbl_20f3:
        defb    07Eh
label_20F4:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0E6h,080h,0B7h,0C8h,03Eh,001h,0C9h
gap_20FB:
        defb    060h,056h,000h,000h,000h
func_2100:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    02Ah,0D0h,020h,07Ch,0B5h,0CAh,011h,021h
        defb    02Bh,022h,0D0h,020h,0C9h
gap_210D:
        defb    000h,000h,001h,001h
lbl_2111:
        defb    021h,005h,000h,022h,0D0h,020h,03Ah,0FDh
        defb    020h,0B7h,0C8h,00Eh,004h,02Ah,0FEh,020h
        defb    07Ch,0B5h,0CAh,069h,021h,02Bh,022h,0FEh
        defb    020h,02Ah,0FBh,020h
label_212D:
        defb    0C5h,0D5h,0E5h,079h,03Dh,087h,087h,085h
        defb    06Fh,07Eh,032h,00Dh,021h,023h,07Eh,032h
        defb    00Eh,021h,023h,07Eh,032h,00Fh,021h,023h
        defb    07Eh,032h,010h,021h,0E5h,0CDh,08Ah,021h
        defb    0E1h,03Ah,010h,021h,077h,02Bh,03Ah,00Fh
        defb    021h,077h,02Bh,03Ah,00Eh,021h,077h,02Bh
        defb    03Ah,00Dh,021h,077h,0E1h,0D1h,0C1h,00Dh
        defb    0C8h,0C3h,02Dh,021h
lbl_2169:
        defb    02Ah,0FBh,020h
lbl_216c:
        defb    0C5h,0D5h,0E5h,07Eh,023h,06Eh,03Dh,03Dh
        defb    03Dh,03Dh,067h,0CDh,091h,020h,0E1h,0D1h
        defb    0C1h,023h,023h,023h,023h,00Dh,0C2h,06Ch
        defb    021h,0AFh,032h,0FDh,020h,0C9h
func_218a:
        defb    021h,00Dh,021h,04Eh,023h,05Eh,03Ah,00Fh
        defb    021h,0FEh,0FFh,0CAh,0ACh,021h,01Dh,00Ch
        defb    00Ch,00Ch,00Ch,0CDh,0D2h,020h,0B7h,0CAh
        defb    0ACh,021h,03Eh,0FFh,032h,00Fh,021h,0CDh
        defb    03Eh,022h
lbl_21ac:
        defb    021h,00Dh,021h,04Eh,023h,05Eh,01Ch,03Ah
        defb    010h,021h,0FEh,0FFh,0CAh,0CBh,021h,00Ch
        defb    0CDh,0D2h,020h,0B7h,0CAh,0CBh,021h,03Eh
        defb    0FFh,032h,010h,021h,0CDh,03Eh,022h
lbl_21cb:
        defb    021h,00Dh,021h,04Eh,023h,05Eh,01Dh,00Dh
        defb    03Ah,00Fh,021h,0FEh,001h,0CAh,0EAh,021h
        defb    0CDh,0D2h,020h,0B7h,0CAh,0EAh,021h,03Eh
        defb    001h,032h,00Fh,021h,0CDh,03Eh,022h
lbl_21ea:
        defb    021h,00Dh,021h,04Eh,023h,05Eh,01Dh,01Dh
        defb    01Dh,01Dh,00Ch,03Ah,010h,021h,0FEh,001h
        defb    0CAh,00Ch,022h,0CDh,0D2h,020h,0B7h,0CAh
        defb    00Ch,022h,03Eh,001h,032h,010h,021h,0CDh
        defb    03Eh,022h
lbl_220c:
        defb    021h,00Dh,021h,07Eh,023h,06Eh,067h,025h
        defb    025h,025h,025h,0CDh,091h,020h,03Ah,00Dh
        defb    021h,021h,00Fh,021h,086h,032h,00Dh,021h
        defb    04Fh,03Ah,00Eh,021h,023h,086h,032h,00Eh
        defb    021h,06Fh,061h,025h,025h,025h,025h,0E5h
        defb    0CDh,091h,020h,0E1h,0C5h,0D5h,0E5h,0C3h
        defb    009h,01Bh
func_223e:
        defb    021h,01Fh,026h,0C3h,0F1h,025h
label_2244:
        defb    0F3h,02Ah,01Dh,016h,0D6h,0A8h,0B7h,0CAh
        defb    08Ah,022h,03Dh,0CAh,08Fh,022h,03Dh,0CAh
        defb    094h,022h,03Dh,0CAh,099h,022h
label_225A:
        defb    022h,01Dh,016h,02Ah,0D3h,011h,011h,0D0h
        defb    000h,019h,022h,0D3h,011h,0CDh,0DFh,025h
        defb    021h,0E2h,024h,034h,07Eh,0E6h,008h,0FEh
        defb    008h,0CCh,000h,00Fh
label_2276:
        defb    021h,000h,080h,00Eh,000h
lbl_227b:
        defb    071h,023h,07Ch,0FEh,000h,0C2h,07Bh,022h
        defb    031h,0FFh,000h,0AFh,0C3h,038h,014h
lbl_228a:
        defb    026h,0E0h,0C3h,05Ah,022h
lbl_228f:
        defb    026h,010h,0C3h,05Ah,022h
lbl_2294:
        defb    02Eh,010h,0C3h,05Ah,022h
lbl_2299:
        defb    02Eh,0B0h,0C3h,05Ah,022h
lbl_229e:
        defb    03Eh,0A8h,0C3h,044h,022h
lbl_22a3:
        defb    03Eh,0A9h,0C3h,044h,022h
lbl_22a8:
        defb    03Eh,0AAh,0C3h,044h,022h
lbl_22ad:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    03Eh,0ABh,0C3h,044h,022h
gap_22B2:
        defb    003h,080h,056h,0BEh,001h
func_22b7:
        defb    02Ah,0B5h,022h,07Ch,0B5h,0CAh,0C4h,022h
        defb    02Bh,022h,0B5h,022h,0C9h
lbl_22c4:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0CDh,081h,01Fh,06Fh,0CDh,081h,01Fh,0E6h
        defb    001h,067h,022h,0B5h,022h,03Ah,0B2h,022h
        defb    0B7h,0C8h,04Fh,0CDh,081h,01Fh,0E6h,003h
        defb    0B9h,0D0h,04Fh,087h,081h,02Ah,0B3h,022h
        defb    085h,06Fh,046h,023h,05Eh,023h,056h,021h
        defb    00Ch,023h,07Eh,0FEh,005h,0C8h,034h,07Eh
        defb    03Dh,087h,087h,02Ah,00Dh,023h,085h,06Fh
        defb    070h,023h,0CDh,081h,01Fh,0E6h,003h,077h
        defb    023h,073h,023h,072h,0CDh,053h,016h,0C9h
gap_230C:
        defb    002h,0A0h,056h,000h,000h
func_2311:
        defb    02Ah,00Fh,023h,07Ch,0B5h,0CAh,01Eh,023h
        defb    02Bh,022h,00Fh,023h,0C9h
lbl_231e:
        defb    021h,005h,000h,022h,00Fh,023h,03Ah,00Ch
        defb    023h,0B7h,0C8h,04Fh,02Ah,00Dh,023h
label_232D:
        defb    0E5h,023h,07Eh,023h,05Eh,023h,056h,0CDh
        defb    053h,016h,0E1h,0E5h,07Eh,0B7h,0CAh,06Dh
        defb    023h,03Dh,0CAh,07Fh,023h,03Dh,0CAh,08Eh
        defb    023h,0D5h,07Bh,0C6h,010h,05Fh,0EBh,0CDh
        defb    057h,017h,0EBh,0D1h,0C2h,0A4h,023h,01Ch
label_2355:
        defb    0CDh,0C0h,023h,0B7h,0CAh,09Dh,023h,0E1h
        defb    023h,07Eh,046h,023h,073h,023h,072h,0CDh
        defb    053h,016h,023h
label_2368:
        defb    00Dh,0C8h,0C3h,02Dh,023h
lbl_236d:
        defb    0D5h,07Ah,0C6h,010h,057h,0EBh,0CDh,06Fh
        defb    017h,0EBh,0D1h,0C2h,0A4h,023h,014h,0C3h
        defb    055h,023h
lbl_237f:
        defb    0D5h,015h,0EBh,0CDh,06Fh,017h,0EBh,0D1h
        defb    0C2h,0A4h,023h,015h,0C3h,055h,023h
lbl_238e:
        defb    0D5h,01Dh,0EBh,0CDh,057h,017h,0EBh,0D1h
        defb    0C2h,0A4h,023h,01Dh,0C3h,055h,023h
lbl_239d:
        defb    058h,016h,000h,013h,0CDh,071h,025h
lbl_23a4:
        defb    021h,00Ch,023h,035h,0E1h,0E5h,023h,023h
        defb    023h,023h,054h,05Dh,0E1h,0E5h,006h,01Fh
lbl_23b4:
        defb    01Ah,077h,013h,023h,005h,0C2h,0B4h,023h
        defb    0E1h,0C3h,068h,023h
func_23c0:
        defb    03Ah,0F6h,018h,02Ah,0F7h,018h,047h,004h
label_23C8:
        defb    005h,0CAh,0D8h,023h,023h,0CDh,0F4h,023h
        defb    0B7h,0CAh,012h,024h,023h,0C3h,0C8h,023h
lbl_23d8:
        defb    02Ah,0FBh,020h,03Ah,0F5h,018h,0B7h,0CAh
        defb    00Fh,024h,0C5h,0CDh,07Ah,016h,0C1h,021h
        defb    043h,01Bh,0CDh,0F4h,023h,0B7h,0CAh,012h
        defb    024h,0C3h,00Fh,024h
func_23f4:
        defb    07Bh,096h,0F2h,0FBh,023h,02Fh,03Ch
lbl_23fb:
        defb    0FEh,010h,0D2h,00Fh,024h,023h,07Ah,096h
        defb    0F2h,008h,024h,02Fh,03Ch
lbl_2408:
        defb    0FEh,00Ch,0D2h,00Fh,024h,0AFh,0C9h
lbl_240f:
        defb    03Eh,001h,0C9h
lbl_2412:
        defb    0AFh,0C9h
func_2414:
        defb    0F5h,0C5h,0D5h,0E5h,0D6h,024h,06Fh,026h
        defb    000h,029h,029h,029h,011h,000h,027h,019h
        defb    01Eh,008h
lbl_2426:
        defb    0CDh,06Ch,005h,00Ch,01Dh,0C2h,026h,024h
        defb    0E1h,0D1h,0C1h,0F1h,0C9h
func_2433:
        defb    07Eh,0B7h,0C8h,023h,0CDh,014h,024h,004h
        defb    0C3h,033h,024h
func_243e:
        defb    0E5h,060h,069h,022h,098h,024h,006h,085h
        defb    021h,08Eh,024h
lbl_2449:
        defb    05Eh,023h,056h,023h,0E3h,00Eh,030h
label_2450:
        defb    07Dh,093h,06Fh,07Ch,09Ah,067h,0DAh,05Dh
        defb    024h,00Ch,0C3h,050h,024h
lbl_245d:
        defb    019h,078h,0B7h,0F2h,074h,024h,0F5h,079h
        defb    0FEh,030h,0CAh,07Bh,024h,0CDh,09Ah,024h
        defb    0F1h,0E6h,07Fh,047h,0C3h,087h,024h
lbl_2474:
        defb    079h,0CDh,09Ah,024h,0C3h,087h,024h
lbl_247b:
        defb    0F1h,0E6h,07Fh,0FEh,001h,0C2h,087h,024h
        defb    047h,0C3h,074h,024h
lbl_2487:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0E3h,005h,0C2h,049h,024h,0E1h,0C9h
gap_248E:
        defb    010h,027h,0E8h,003h,064h,000h,00Ah,000h
        defb    001h,000h,0E0h,0DEh
func_249a:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0C5h,0D5h,0E5h,02Ah,098h,024h,044h,079h
        defb    04Dh,0CDh,014h,024h,004h,060h,069h,022h
        defb    098h,024h,0E1h,0D1h,0C1h,0C9h
gap_24B0:
        defb    053h,043h,04Fh,052h,045h,03Ah,000h,04Ch
        defb    049h,046h,045h,03Ah,000h,053h,054h,041h
        defb    047h,045h,03Ah,000h,04Ch,045h,056h,045h
        defb    04Ch,03Ah,000h,053h,048h,049h,045h,04Ch
        defb    044h,000h,042h,04Fh,055h,04Eh,043h,045h
        defb    000h,046h,049h,052h,045h,03Ah,000h,000h
        defb    000h,003h,000h,005h,005h
func_24e5:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    021h,0B0h,024h,001h,0E0h,0C0h,0CDh,033h
        defb    024h,021h,0B7h,024h,001h,0E0h,0CCh,0CDh
        defb    033h,024h,021h,0BDh,024h,001h,0E0h,0D7h
        defb    0CDh,033h,024h,021h,0C4h,024h,001h,0F0h
        defb    0A1h,0CDh,033h,024h,021h,0D9h,024h,001h
        defb    0F0h,0B0h,0CDh,033h,024h,0CDh,017h,025h
        defb    0C9h
gap_2516:
        defb    000h
func_2517:
        defb    03Ah,016h,025h,011h,0D2h,024h,021h,0CBh
        defb    024h,0B7h,0C2h,025h,025h,0EBh
lbl_2525:
        defb    001h,0F0h,0B5h,0CDh,033h,024h,03Ah,0E3h
        defb    024h,06Fh,026h,000h,03Ah,0E4h,024h,05Fh
        defb    016h,000h,03Ah,016h,025h,0B7h,0CAh,03Fh
        defb    025h,0EBh
lbl_253f:
        defb    001h,0F0h,0BCh,0C3h,03Eh,024h
func_2545:
        defb    02Ah,0DFh,024h,001h,0E0h,0C6h,0CDh,03Eh
        defb    024h,02Ah,098h,024h,044h,04Dh,03Eh,030h
        defb    0CDh,014h,024h,03Ah,0E1h,024h,06Fh,026h
        defb    000h,001h,0E0h,0D1h,0CDh,03Eh,024h,03Ah
        defb    0E2h,024h,06Fh,026h,000h,001h,0E0h,0DDh
        defb    0CDh,03Eh,024h,0C9h
func_2571:
        defb    0C5h,0E5h,02Ah,0DFh,024h,019h,022h,0DFh
        defb    024h,0CDh,045h,025h,0E1h,0C1h,0C9h
label_2580:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0B7h,01Fh,03Dh,032h,016h,025h,0C3h,017h
        defb    025h
gap_2589:
        defb    000h,000h,000h,004h,000h
func_258e:
        defb    03Ah,089h,025h,0B7h,0C8h,02Ah,08Ah,025h
        defb    07Ch,0B5h,0CAh,0CCh,025h,02Bh,022h,08Ah
        defb    025h,02Ah,08Ch,025h,07Ch,0B5h,0CAh,0ACh
        defb    025h,02Bh,022h,08Ch,025h,0C9h
lbl_25ac:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    021h,005h,000h,022h,08Ch,025h,021h,0B4h
        defb    010h,07Eh,0EEh,0E0h,077h,0C3h,0CAh,025h
gap_25BC:
        defb    007h,077h,021h,0BDh,010h,07Eh,0EEh,007h
        defb    077h,023h,07Eh,0EEh,007h,077h
label_25CA:
        defb    0FBh,0C9h
func_25cc:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0AFh,032h,089h,025h,021h,0B4h,010h,036h
        defb    0F4h,0C9h
gap_25D6:
        defb    023h,071h,021h,0BDh,010h,071h,023h,071h
        defb    0C9h
func_25df:
        defb    02Ah,0D1h,011h,0EBh,02Ah,0D3h,011h,006h
        defb    0D0h
lbl_25e8:
        defb    07Eh,012h,013h,023h,005h,0C2h,0E8h,025h
        defb    0C9h
func_25f1:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    0F3h,022h,0B0h,010h,03Eh,001h,032h,0ADh
        defb    010h,032h,0B2h,010h,0FBh,0C9h
gap_25FF:
; НЕ ФУНКЦИЯ (конверт function->Data этим проходом): раздутый range 0x263D..0x77FF (~20 KiB) — packer-архив/таблицы исходной ROM (закодированные игровые данные, распаковываются stub'ом 0xEE00 в RAM). Линейный дамп внутри области даёт ложные OUT/IN/CALL-сигнатуры (в т.ч. ложные «OUT микшера») и ложные функции 0x7800+ (область за концом ROM 0x6B00 = пустая RAM). Точная разметка = Stage 3+ (coverage-трассировка).
        defb    001h,000h,00Ah,001h,000h,008h,001h,032h
        defb    007h,001h,000h,001h,001h,000h,004h,001h
        defb    000h,002h,001h,000h,001h,000h,001h,000h
        defb    014h,001h,000h,01Bh,001h,000h,002h,000h
        defb    001h,000h,002h,002h,000h,006h,001h,000h
        defb    001h,000h,001h,000h,032h,002h,000h,03Ch
        defb    001h,000h,014h,000h,001h,000h,004h,001h
        defb    000h,002h,001h,000h,005h,000h
data_blob_263d:
        defb    02Ah,04Ah,026h
lbl_2640:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    07Eh,023h,0B7h,0C2h,040h,026h,022h,04Ah
        defb    026h,0C9h
gap_264A:
; data_password_table: таблица паролей/имён уровней экрана 3.PASS (exec 0x264D). Строки: "START" (0x264D), "ROOM%%" (0x2653), "KISS%%" (0x265A), "LEFT%%" (0x2661), "CLEAR%%" (0x2668). Каждая запись 0-терминирована, разделитель '%' (0x25). Используется обработчиком screen_pass@0x020A (LXI B,264D @0x020F).
        defb    04Dh,026h,000h
data_password_table:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    053h,054h,041h,052h,054h,000h,052h,04Fh
        defb    04Fh,04Dh,025h,025h,000h,04Bh,049h,053h
        defb    053h,025h,025h,000h,04Ch,045h,046h,054h
        defb    025h,025h,000h,043h,04Ch,045h,041h,052h
        defb    025h,026h,026h,000h
gap_2671:
; Блок глифов экранного шрифта (base). Stage 6: func_render_glyph@0x114D берёт глиф как charcode*32 + 0x3780; шаг 32 байта = 4 бит-плоскости × 8 строк (8×8, 4-битный цвет V06). Шрифт транслитный ASCII, код 0x25 '%' = разделитель слов (пробел). glyph_scan(.rom,0x3780,stride 0x20): регулярный массив 32-байтных глифов (ink>0 по всему блоку, повторов в 0x00..0x0F нет). Точный порядок бит/плоскостей (column-major/инверсия) — рендер-деталь, Stage 7/8. Попадания strings_scan «koi8-мусор» 0x35xx/0x3Axx/0x43xx–0x45xx — это растровые глифы, ошибочно принятые за текст.
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    008h,010h,000h,000h,000h,000h,000h,000h
        defb    01Ch,010h,010h,010h,010h,01Ch,000h,000h
        defb    038h,008h,008h,008h,008h,038h,000h,0FFh
        defb    081h,0BDh,0A1h,0A1h,0BDh,081h,0FFh,000h
        defb    000h,008h,008h,03Eh,008h,008h,000h,000h
        defb    000h,000h,000h,000h,008h,008h,010h,000h
        defb    000h,000h,07Eh,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,018h,000h,000h
        defb    002h,004h,008h,010h,020h,040h,000h,000h
        defb    07Eh,046h,04Ah,052h,062h,07Eh,000h,000h
        defb    010h,030h,010h,010h,010h,07Ch,000h,000h
        defb    07Eh,002h,07Eh,040h,040h,07Eh,000h,000h
        defb    07Eh,002h,03Ch,002h,002h,07Eh,000h,000h
        defb    042h,042h,07Eh,002h,002h,002h,000h,000h
        defb    07Eh,040h,07Eh,002h,002h,07Eh,000h,000h
        defb    07Eh,040h,07Eh,042h,042h,07Eh,000h,000h
        defb    07Eh,002h,002h,002h,002h,002h,000h,000h
        defb    07Eh,042h,07Eh,042h,042h,07Eh,000h,000h
        defb    07Eh,042h,042h,07Eh,002h,002h,000h,000h
        defb    000h,000h,038h,038h,000h,038h,038h,000h
        defb    000h,038h,038h,000h,038h,038h,070h,000h
        defb    01Ch,038h,070h,0E0h,070h,038h,01Ch,000h
        defb    000h,0FEh,000h,000h,0FEh,000h,000h,000h
        defb    070h,038h,01Ch,00Eh,01Ch,038h,070h,000h
        defb    07Ch,0E6h,00Ch,038h,038h,000h,038h,000h
        defb    07Ch,0E6h,0EEh,0EAh,0EEh,0E0h,07Ch,000h
        defb    07Eh,042h,07Eh,042h,042h,042h,000h,000h
        defb    07Eh,042h,07Ch,042h,042h,07Eh,000h,000h
        defb    07Eh,040h,040h,040h,040h,07Eh,000h,000h
        defb    07Ch,042h,042h,042h,042h,07Eh,000h,000h
        defb    07Eh,040h,07Eh,040h,040h,07Eh,000h,000h
        defb    07Eh,040h,07Eh,040h,040h,040h,000h,000h
        defb    07Eh,042h,040h,046h,042h,07Eh,000h,000h
        defb    042h,042h,07Eh,042h,042h,042h,000h,000h
        defb    07Ch,010h,010h,010h,010h,07Ch,000h,000h
        defb    07Ch,010h,010h,010h,010h,070h,000h,000h
        defb    044h,048h,070h,048h,044h,044h,000h,000h
        defb    040h,040h,040h,040h,040h,07Ch,000h,000h
        defb    042h,066h,05Ah,042h,042h,042h,000h,000h
        defb    042h,062h,052h,04Ah,046h,042h,000h,000h
        defb    07Eh,042h,042h,042h,042h,07Eh,000h,000h
        defb    07Eh,042h,042h,07Eh,040h,040h,000h,000h
        defb    07Eh,042h,042h,042h,044h,07Ah,000h,000h
        defb    07Eh,042h,07Eh,048h,044h,042h,000h,000h
        defb    07Eh,040h,07Eh,002h,002h,07Eh,000h,000h
        defb    07Ch,010h,010h,010h,010h,010h,000h,000h
        defb    042h,042h,042h,042h,042h,07Eh,000h,000h
        defb    042h,042h,042h,042h,024h,018h,000h,000h
        defb    042h,042h,042h,05Ah,066h,042h,000h,000h
        defb    042h,024h,018h,018h,024h,042h,000h,000h
        defb    044h,028h,010h,010h,010h,010h,000h,000h
        defb    07Eh,004h,008h,010h,020h,07Eh,000h,00Eh
        defb    03Eh,07Eh,0FEh,000h,0FFh,07Fh,00Fh,0C0h
        defb    050h,0ACh,055h,000h,0FFh,0FCh,0E0h,000h
        defb    077h,0EFh,05Fh,000h,07Bh,0FBh,07Bh,000h
        defb    0C0h,0BAh,000h,000h,000h,06Ah,000h,000h
        defb    040h,020h,010h,008h,004h,002h,001h,000h
        defb    002h,004h,008h,010h,020h,040h,000h,000h
        defb    002h,03Ch,01Ch,00Ch,024h,040h,000h,080h
        defb    040h,03Ch,038h,030h,024h,002h,000h,000h
        defb    000h,000h,000h,07Fh,000h,000h,000h,000h
        defb    000h,060h,078h,07Eh,078h,060h,000h,000h
        defb    007h,00Fh,018h,032h,036h,036h,034h,000h
        defb    0C0h,0E0h,030h,018h,018h,018h,018h,034h
        defb    030h,030h,030h,018h,00Fh,007h,000h,018h
        defb    058h,058h,098h,030h,0E0h,0C0h,000h,01Fh
        defb    005h,005h,005h,002h,002h,001h,000h,0FFh
        defb    084h,084h,084h,0C8h,0C8h,010h,0E0h,001h
        defb    002h,002h,004h,004h,005h,01Fh,000h,010h
        defb    008h,008h,044h,0E4h,0F4h,0FFh,000h,000h
        defb    000h,000h,000h,00Ch,03Ch,0FCh,0FCh,00Ch
        defb    03Ch,0FCh,0FCh,0FCh,0FCh,0FCh,0FCh,000h
        defb    000h,000h,000h,00Ch,03Ch,0FCh,000h,00Ch
        defb    03Ch,0FCh,0FCh,0FCh,0FCh,0FCh,000h,0FCh
        defb    0FCh,0FCh,0FCh,0FCh,0FCh,0FCh,000h,0FCh
        defb    0FCh,0FCh,0FCh,0FCh,0FCh,0FCh,000h,00Eh
        defb    03Eh,05Eh,06Eh,0F6h,0FAh,0FCh,000h,000h
        defb    0FFh,000h,0FFh,0AAh,055h,000h,000h,070h
        defb    07Ch,07Ah,076h,06Fh,05Fh,03Fh,000h,000h
        defb    0FCh,0FAh,0F6h,06Eh,05Eh,03Eh,00Eh,000h
        defb    000h,0FFh,000h,0FFh,055h,0AAh,000h,000h
        defb    03Fh,05Fh,06Fh,076h,07Ah,07Ch,070h,05Ah
        defb    05Ch,05Ah,05Ch,05Ah,05Ch,05Ah,05Ch,07Eh
        defb    040h,04Ah,054h,04Ah,054h,04Ah,054h,000h
        defb    034h,038h,034h,038h,034h,038h,034h,038h
        defb    034h,038h,034h,028h,014h,028h,000h,07Eh
        defb    040h,04Ah,054h,04Ah,054h,04Ah,054h,000h
        defb    0BFh,000h,05Fh,0AAh,055h,000h,000h,000h
        defb    000h,0BFh,000h,0AFh,055h,0AAh,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,00Eh
        defb    0C0h,000h,03Eh,050h,000h,07Eh,0ACh,000h
        defb    0FEh,055h,000h,000h,000h,000h,0FFh,0FFh
        defb    000h,07Fh,0FCh,000h,00Fh,0E0h,000h,000h
        defb    000h,000h,077h,0C0h,000h,0EFh,0BAh,000h
        defb    05Fh,000h,000h,000h,000h,000h,07Bh,000h
        defb    000h,0FBh,06Ah,000h,07Bh,000h,000h,003h
        defb    0B0h,000h,00Fh,094h,000h,01Fh,0ABh,000h
        defb    03Fh,095h,040h,000h,000h,000h,03Fh,0FFh
        defb    0C0h,01Fh,0FFh,000h,003h,0F8h,000h,000h
        defb    000h,000h,01Dh,0F0h,000h,03Bh,0EEh,080h
        defb    017h,0C0h,000h,000h,000h,000h,01Eh,0C0h
        defb    000h,03Eh,0DAh,080h,01Eh,0C0h,000h,000h
        defb    0ECh,000h,003h,0E5h,000h,007h,0EAh,0C0h
        defb    00Fh,0E5h,050h,000h,000h,000h,00Fh,0FFh
        defb    0F0h,007h,0FFh,0C0h,000h,0FEh,000h,000h
        defb    000h,000h,007h,07Ch,000h,00Eh,0FBh,0A0h
        defb    005h,0F0h,000h,000h,000h,000h,007h,0B0h
        defb    000h,00Fh,0B6h,0A0h,007h,0B0h,000h,000h
        defb    03Bh,000h,000h,0F9h,040h,001h,0FAh,0B0h
        defb    003h,0F9h,054h,000h,000h,000h,003h,0FFh
        defb    0FCh,001h,0FFh,0F0h,000h,03Fh,080h,000h
        defb    000h,000h,001h,0DFh,000h,003h,0BEh,0E8h
        defb    001h,07Ch,000h,000h,000h,000h,001h,0ECh
        defb    000h,003h,0EDh,0A8h,001h,0ECh,000h,003h
        defb    070h,000h,00Ah,07Ch,000h,035h,07Eh,000h
        defb    0AAh,07Fh,000h,000h,000h,000h,0FFh,0FFh
        defb    000h,03Fh,0FEh,000h,007h,0F0h,000h,000h
        defb    000h,000h,003h,0EEh,000h,05Dh,0F7h,000h
        defb    000h,0FAh,000h,000h,000h,000h,000h,0DEh
        defb    000h,056h,0DFh,000h,000h,0DEh,000h,000h
        defb    0DCh,000h,002h,09Fh,000h,00Dh,05Fh,080h
        defb    02Ah,09Fh,0C0h,000h,000h,000h,03Fh,0FFh
        defb    0C0h,00Fh,0FFh,080h,001h,0FCh,000h,000h
        defb    000h,000h,000h,0FBh,080h,017h,07Dh,0C0h
        defb    000h,03Eh,080h,000h,000h,000h,000h,037h
        defb    080h,015h,0B7h,0C0h,000h,037h,080h,000h
        defb    037h,000h,000h,0A7h,0C0h,003h,057h,0E0h
        defb    00Ah,0A7h,0F0h,000h,000h,000h,00Fh,0FFh
        defb    0F0h,003h,0FFh,0E0h,000h,07Fh,000h,000h
        defb    000h,000h,000h,03Eh,0E0h,005h,0DFh,070h
        defb    000h,00Fh,0A0h,000h,000h,000h,000h,00Dh
        defb    0E0h,005h,06Dh,0F0h,000h,00Dh,0E0h,000h
        defb    00Dh,0C0h,000h,029h,0F0h,000h,0D5h,0F8h
        defb    002h,0A9h,0FCh,000h,000h,000h,003h,0FFh
        defb    0FCh,000h,0FFh,0F8h,000h,01Fh,0C0h,000h
        defb    000h,000h,000h,00Fh,0B8h,001h,077h,0DCh
        defb    000h,003h,0E8h,000h,000h,000h,000h,003h
        defb    078h,001h,05Bh,07Ch,000h,003h,078h,007h
        defb    0E0h,000h,01Fh,0E8h,000h,03Fh,0F4h,000h
        defb    07Fh,0EAh,000h,07Fh,0D6h,000h,09Fh,0E9h
        defb    000h,0E7h,0A7h,000h,0F8h,01Fh,000h,0FFh
        defb    0FFh,000h,03Ch,03Ch,000h,0DBh,0DBh,000h
        defb    0DBh,0DBh,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,001h
        defb    0F8h,000h,007h,0FAh,000h,00Fh,0FDh,000h
        defb    01Fh,0FAh,080h,01Fh,0F5h,080h,027h,0FAh
        defb    040h,039h,0E9h,0C0h,03Eh,007h,0C0h,00Fh
        defb    0FFh,0C0h,037h,00Fh,000h,036h,0F6h,0C0h
        defb    006h,0F6h,0C0h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    07Eh,000h,001h,0FEh,080h,003h,0FFh,040h
        defb    007h,0FEh,0A0h,007h,0FDh,060h,009h,0FEh
        defb    090h,00Eh,07Ah,070h,00Fh,081h,0F0h,00Fh
        defb    0C3h,0F0h,003h,0BDh,0C0h,00Dh,0BDh,0B0h
        defb    00Dh,081h,0B0h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    01Fh,080h,000h,07Fh,0A0h,000h,0FFh,0D0h
        defb    001h,0FFh,0A8h,001h,0FFh,058h,002h,07Fh
        defb    0A4h,003h,09Eh,09Ch,003h,0E0h,07Ch,003h
        defb    0FFh,0F0h,000h,0F0h,0ECh,003h,06Fh,06Ch
        defb    003h,06Fh,060h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,007h
        defb    0B0h,000h,01Bh,0B0h,000h,03Bh,0C0h,000h
        defb    07Dh,0F0h,000h,07Dh,0F0h,000h,0FEh,0C0h
        defb    000h,0FEh,0B0h,000h,0FEh,0B0h,000h,0FEh
        defb    0B0h,000h,0FCh,0B0h,000h,0F6h,0C0h,000h
        defb    029h,0F0h,000h,055h,0F0h,000h,02Bh,0C0h
        defb    000h,01Bh,0B0h,000h,007h,0B0h,000h,001h
        defb    0ECh,000h,006h,0ECh,000h,00Eh,0F0h,000h
        defb    01Fh,07Ch,000h,01Fh,07Ch,000h,03Fh,0B0h
        defb    000h,03Fh,0ACh,000h,03Fh,0ACh,000h,03Fh
        defb    0ACh,000h,03Fh,02Ch,000h,03Dh,0B0h,000h
        defb    00Ah,07Ch,000h,015h,07Ch,000h,00Ah,0F0h
        defb    000h,006h,0ECh,000h,001h,0ECh,000h,000h
        defb    07Bh,000h,001h,0BBh,000h,003h,0BCh,000h
        defb    007h,0DFh,000h,007h,0DFh,000h,00Fh,0ECh
        defb    000h,00Fh,0EBh,000h,00Fh,0EBh,000h,00Fh
        defb    0EBh,000h,00Fh,0CBh,000h,00Fh,06Ch,000h
        defb    002h,09Fh,000h,005h,05Fh,000h,002h,0BCh
        defb    000h,001h,0BBh,000h,000h,07Bh,000h,000h
        defb    01Eh,0C0h,000h,06Eh,0C0h,000h,0EFh,000h
        defb    001h,0F7h,0C0h,001h,0F7h,0C0h,003h,0FBh
        defb    000h,003h,0FAh,0C0h,003h,0FAh,0C0h,003h
        defb    0FAh,0C0h,003h,0F2h,0C0h,003h,0DBh,000h
        defb    000h,0A7h,0C0h,001h,057h,0C0h,000h,0AFh
        defb    000h,000h,06Eh,0C0h,000h,01Eh,0C0h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,0DBh,0DBh,000h,0DBh,0DBh
        defb    000h,03Ch,03Ch,000h,0FFh,0FFh,000h,0F8h
        defb    01Fh,000h,0E7h,0A7h,000h,09Fh,0E9h,000h
        defb    07Fh,0D6h,000h,07Fh,0EAh,000h,03Fh,0F4h
        defb    000h,01Fh,0E8h,000h,007h,0E0h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,006h,0F6h,0C0h,036h,0F6h
        defb    0C0h,037h,00Fh,000h,00Fh,0FFh,0C0h,03Eh
        defb    007h,0C0h,039h,0E9h,0C0h,027h,0FAh,040h
        defb    01Fh,0F5h,080h,01Fh,0FAh,080h,00Fh,0FDh
        defb    000h,007h,0FAh,000h,001h,0F8h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,00Dh,081h,0B0h,00Dh,0BDh
        defb    0B0h,003h,0BDh,0C0h,00Fh,0C3h,0F0h,00Fh
        defb    081h,0F0h,00Eh,07Ah,070h,009h,0FEh,090h
        defb    007h,0FDh,060h,007h,0FEh,0A0h,003h,0FFh
        defb    040h,001h,0FEh,080h,000h,07Eh,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,003h,06Fh,060h,003h,06Fh
        defb    06Ch,000h,0F0h,0ECh,003h,0FFh,0F0h,003h
        defb    0E0h,07Ch,003h,09Eh,09Ch,002h,07Fh,0A4h
        defb    001h,0FFh,058h,001h,0FFh,0A8h,000h,0FFh
        defb    0D0h,000h,07Fh,0A0h,000h,01Fh,080h,00Dh
        defb    0E0h,000h,00Dh,0D8h,000h,003h,0DCh,000h
        defb    00Fh,0BEh,000h,00Fh,0BEh,000h,003h,07Fh
        defb    000h,00Dh,07Fh,000h,00Dh,07Fh,000h,00Dh
        defb    07Fh,000h,00Dh,03Fh,000h,003h,06Fh,000h
        defb    00Fh,094h,000h,00Fh,0AAh,000h,003h,0D4h
        defb    000h,00Dh,0D8h,000h,00Dh,0E0h,000h,003h
        defb    078h,000h,003h,076h,000h,000h,0F7h,000h
        defb    003h,0EFh,080h,003h,0EFh,080h,000h,0DFh
        defb    0C0h,003h,05Fh,0C0h,003h,05Fh,0C0h,003h
        defb    05Fh,0C0h,003h,04Fh,0C0h,000h,0DBh,0C0h
        defb    003h,0E5h,000h,003h,0EAh,080h,000h,0F5h
        defb    000h,003h,076h,000h,003h,078h,000h,000h
        defb    0DEh,000h,000h,0DDh,080h,000h,03Dh,0C0h
        defb    000h,0FBh,0E0h,000h,0FBh,0E0h,000h,037h
        defb    0F0h,000h,0D7h,0F0h,000h,0D7h,0F0h,000h
        defb    0D7h,0F0h,000h,0D3h,0F0h,000h,036h,0F0h
        defb    000h,0F9h,040h,000h,0FAh,0A0h,000h,03Dh
        defb    040h,000h,0DDh,080h,000h,0DEh,000h,000h
        defb    037h,080h,000h,037h,060h,000h,00Fh,070h
        defb    000h,03Eh,0F8h,000h,03Eh,0F8h,000h,00Dh
        defb    0FCh,000h,035h,0FCh,000h,035h,0FCh,000h
        defb    035h,0FCh,000h,034h,0FCh,000h,00Dh,0BCh
        defb    000h,03Eh,050h,000h,03Eh,0A8h,000h,00Fh
        defb    050h,000h,037h,060h,000h,037h,080h,000h
        defb    050h,000h,000h,022h,000h,003h,005h,000h
        defb    007h,056h,000h,0BBh,076h,000h,007h,056h
        defb    000h,003h,005h,000h,000h,022h,000h,000h
        defb    050h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    014h,000h,000h,01Ch,080h,000h,0C9h,040h
        defb    001h,0C1h,080h,02Eh,0D5h,080h,001h,0DDh
        defb    080h,000h,0D5h,040h,000h,000h,080h,000h
        defb    01Ch,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,005h,020h,000h,037h,050h
        defb    000h,075h,060h,00Bh,0B0h,060h,000h,075h
        defb    060h,000h,037h,050h,000h,005h,020h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    001h,0C0h,000h,000h,008h,000h,00Dh,054h
        defb    000h,01Dh,0D8h,002h,0EDh,058h,000h,01Ch
        defb    018h,000h,00Ch,094h,000h,001h,0C8h,000h
        defb    001h,040h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,00Eh
        defb    000h,000h,040h,000h,000h,0AAh,0C0h,000h
        defb    06Eh,0E0h,000h,06Ah,0DDh,000h,060h,0E0h
        defb    000h,0A4h,0C0h,000h,04Eh,000h,000h,00Ah
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,012h,080h,000h,02Bh,0B0h,000h
        defb    01Ah,0B8h,000h,018h,037h,040h,01Ah,0B8h
        defb    000h,02Bh,0B0h,000h,012h,080h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    0A0h,000h,004h,0E0h,000h,00Ah,04Ch,000h
        defb    006h,00Eh,000h,006h,0ADh,0D0h,006h,0EEh
        defb    000h,00Ah,0ACh,000h,004h,000h,000h,000h
        defb    0E0h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    028h,000h,001h,010h,000h,002h,083h,000h
        defb    001h,0ABh,080h,001h,0BBh,074h,001h,0ABh
        defb    080h,002h,083h,000h,001h,010h,000h,000h
        defb    028h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,007h
        defb    000h,000h,01Eh,0C0h,000h,01Fh,0CAh,000h
        defb    02Fh,0DDh,000h,0FEh,03Ah,000h,0FEh,0FDh
        defb    000h,078h,0FAh,000h,002h,0FAh,000h,0F6h
        defb    078h,000h,0FFh,063h,000h,0FFh,06Eh,000h
        defb    0BCh,00Bh,000h,073h,0BDh,000h,00Fh,0BAh
        defb    000h,03Dh,0B4h,000h,03Ah,01Ch,000h,001h
        defb    0C0h,000h,007h,0B0h,000h,007h,0F2h,080h
        defb    00Bh,0F7h,040h,03Fh,08Eh,080h,03Fh,0BFh
        defb    040h,01Eh,03Eh,080h,000h,0BEh,080h,03Dh
        defb    09Eh,000h,03Fh,0D8h,0C0h,03Fh,0DBh,080h
        defb    02Fh,002h,0C0h,01Ch,0EFh,040h,003h,0EEh
        defb    080h,00Fh,06Dh,000h,00Eh,087h,000h,000h
        defb    070h,000h,001h,0ECh,000h,001h,0FCh,0A0h
        defb    002h,0FDh,0D0h,00Fh,0E3h,0A0h,00Fh,0EFh
        defb    0D0h,007h,08Fh,0A0h,000h,02Fh,0A0h,00Fh
        defb    067h,080h,00Fh,0F6h,030h,00Fh,0F6h,0E0h
        defb    00Bh,0C0h,0B0h,007h,03Bh,0D0h,000h,0FBh
        defb    0A0h,003h,0DBh,040h,003h,0A1h,0C0h,000h
        defb    01Ch,000h,000h,07Bh,000h,000h,07Fh,028h
        defb    000h,0BFh,074h,003h,0F8h,0E8h,003h,0FBh
        defb    0F4h,001h,0E3h,0E8h,000h,00Bh,0E8h,003h
        defb    0D9h,0E0h,003h,0FDh,08Ch,003h,0FDh,0B8h
        defb    002h,0F0h,02Ch,001h,0CEh,0F4h,000h,03Eh
        defb    0E8h,000h,0F6h,0D0h,000h,0E8h,070h,005h
        defb    000h,000h,01Eh,0C0h,000h,01Bh,0CAh,000h
        defb    02Dh,04Dh,000h,0B0h,02Ah,000h,094h,02Dh
        defb    000h,078h,01Ah,000h,000h,00Ah,000h,0F0h
        defb    010h,000h,0A8h,003h,000h,0D4h,02Ah,000h
        defb    0ACh,00Bh,000h,072h,0B5h,000h,00Bh,08Ah
        defb    000h,035h,0B4h,000h,02Ah,01Ch,000h,001h
        defb    040h,000h,007h,0B0h,000h,006h,0F2h,080h
        defb    00Bh,053h,040h,02Ch,00Ah,080h,025h,00Bh
        defb    040h,01Eh,006h,080h,000h,002h,080h,03Ch
        defb    004h,000h,02Ah,000h,0C0h,035h,00Ah,080h
        defb    02Bh,002h,0C0h,01Ch,0ADh,040h,002h,0E2h
        defb    080h,00Dh,06Dh,000h,00Ah,087h,000h,000h
        defb    050h,000h,001h,0ECh,000h,001h,0BCh,0A0h
        defb    002h,0D4h,0D0h,00Bh,002h,0A0h,009h,042h
        defb    0D0h,007h,081h,0A0h,000h,000h,0A0h,00Fh
        defb    001h,000h,00Ah,080h,030h,00Dh,042h,0A0h
        defb    00Ah,0C0h,0B0h,007h,02Bh,050h,000h,0B8h
        defb    0A0h,003h,05Bh,040h,002h,0A1h,0C0h,000h
        defb    014h,000h,000h,07Bh,000h,000h,06Fh,028h
        defb    000h,0B5h,034h,002h,0C0h,0A8h,002h,050h
        defb    0B4h,001h,0E0h,068h,000h,000h,028h,003h
        defb    0C0h,040h,002h,0A0h,00Ch,003h,050h,0A8h
        defb    002h,0B0h,02Ch,001h,0CAh,0D4h,000h,02Eh
        defb    028h,000h,0D6h,0D0h,000h,0A8h,070h,007h
        defb    000h,000h,016h,0C0h,000h,010h,00Ah,000h
        defb    021h,01Dh,000h,0E8h,00Ah,000h,0E0h,011h
        defb    000h,020h,002h,000h,000h,00Ah,000h,0C0h
        defb    000h,000h,0D0h,001h,000h,0C0h,024h,000h
        defb    0A4h,003h,000h,070h,005h,000h,008h,02Ah
        defb    000h,039h,0B4h,000h,03Ah,01Ch,000h,001h
        defb    0C0h,000h,005h,0B0h,000h,004h,002h,080h
        defb    008h,047h,040h,03Ah,002h,080h,038h,004h
        defb    040h,008h,000h,080h,000h,002h,080h,030h
        defb    000h,000h,034h,000h,040h,030h,009h,000h
        defb    029h,000h,0C0h,01Ch,001h,040h,002h,00Ah
        defb    080h,00Eh,06Dh,000h,00Eh,087h,000h,000h
        defb    070h,000h,001h,06Ch,000h,001h,000h,0A0h
        defb    002h,011h,0D0h,00Eh,080h,0A0h,00Eh,001h
        defb    010h,002h,000h,020h,000h,000h,0A0h,00Ch
        defb    000h,000h,00Dh,000h,010h,00Ch,002h,040h
        defb    00Ah,040h,030h,007h,000h,050h,000h,082h
        defb    0A0h,003h,09Bh,040h,003h,0A1h,0C0h,000h
        defb    01Ch,000h,000h,05Bh,000h,000h,040h,028h
        defb    000h,084h,074h,003h,0A0h,028h,003h,080h
        defb    044h,000h,080h,008h,000h,000h,028h,003h
        defb    000h,000h,003h,040h,004h,003h,000h,090h
        defb    002h,090h,00Ch,001h,0C0h,014h,000h,020h
        defb    0A8h,000h,0E6h,0D0h,000h,0E8h,070h,002h
        defb    000h,000h,004h,040h,000h,020h,008h,000h
        defb    001h,002h,000h,008h,008h,000h,0A0h,000h
        defb    000h,000h,002h,000h,000h,000h,000h,080h
        defb    001h,000h,000h,004h,000h,080h,001h,000h
        defb    000h,000h,000h,050h,002h,000h,008h,020h
        defb    000h,020h,084h,000h,00Ah,010h,000h,000h
        defb    080h,000h,001h,010h,000h,008h,002h,000h
        defb    000h,040h,080h,002h,002h,000h,028h,000h
        defb    000h,000h,000h,080h,000h,000h,000h,020h
        defb    000h,040h,000h,001h,000h,020h,000h,040h
        defb    000h,000h,000h,014h,000h,080h,002h,008h
        defb    000h,008h,021h,000h,002h,084h,000h,000h
        defb    020h,000h,000h,044h,000h,002h,000h,080h
        defb    000h,010h,020h,000h,080h,080h,00Ah,000h
        defb    000h,000h,000h,020h,000h,000h,000h,008h
        defb    000h,010h,000h,000h,040h,008h,000h,010h
        defb    000h,000h,000h,005h,000h,020h,000h,082h
        defb    000h,002h,008h,040h,000h,0A1h,000h,000h
        defb    008h,000h,000h,011h,000h,000h,080h,020h
        defb    000h,004h,008h,000h,020h,020h,002h,080h
        defb    000h,000h,000h,008h,000h,000h,000h,002h
        defb    000h,004h,000h,000h,010h,002h,000h,004h
        defb    000h,000h,000h,001h,040h,008h,000h,020h
        defb    080h,000h,082h,010h,000h,028h,040h,003h
        defb    0C0h,000h,00Fh,0D0h,000h,01Fh,0E8h,000h
        defb    03Fh,0D4h,000h,07Fh,0AAh,000h,000h,000h
        defb    000h,0DCh,0E7h,000h,0DCh,0E7h,000h,0DCh
        defb    0E7h,000h,000h,000h,000h,07Fh,0EAh,000h
        defb    0FFh,055h,000h,000h,000h,000h,07Bh,0DAh
        defb    000h,000h,000h,000h,019h,098h,000h,000h
        defb    0F0h,000h,003h,0F4h,000h,007h,0FAh,000h
        defb    00Fh,0F5h,000h,01Fh,0EAh,080h,000h,000h
        defb    000h,02Eh,073h,080h,02Eh,073h,080h,02Eh
        defb    073h,080h,000h,000h,000h,01Fh,0FAh,080h
        defb    03Fh,0D5h,040h,000h,000h,000h,01Eh,0F6h
        defb    080h,000h,000h,000h,00Ch,063h,000h,000h
        defb    03Ch,000h,000h,0FDh,000h,001h,0FEh,080h
        defb    003h,0FDh,040h,007h,0FAh,0A0h,000h,000h
        defb    000h,007h,039h,0D0h,007h,039h,0D0h,007h
        defb    039h,0D0h,000h,000h,000h,007h,0FEh,0A0h
        defb    00Fh,0F5h,050h,000h,000h,000h,00Fh,03Ch
        defb    0D0h,000h,000h,000h,006h,018h,060h,000h
        defb    00Fh,000h,000h,03Fh,040h,000h,07Fh,0A0h
        defb    000h,0FFh,050h,001h,0FEh,0A8h,000h,000h
        defb    000h,003h,09Ch,0ECh,003h,09Ch,0ECh,003h
        defb    09Ch,0ECh,000h,000h,000h,001h,0FFh,0A8h
        defb    003h,0FDh,054h,000h,000h,000h,001h,0EFh
        defb    068h,000h,000h,000h,000h,0C6h,030h,005h
        defb    0A0h,000h,01Dh,0B8h,000h,03Dh,0B4h,000h
        defb    07Dh,0BAh,000h,07Dh,0BAh,000h,0FDh,0B5h
        defb    000h,0FDh,0BBh,000h,003h,0C0h,000h,07Fh
        defb    0EAh,000h,000h,000h,000h,07Fh,0EAh,000h
        defb    0FFh,0F5h,000h,000h,000h,000h,03Fh,0D4h
        defb    000h,00Fh,0D0h,000h,003h,040h,000h,001h
        defb    068h,000h,007h,06Eh,000h,00Fh,06Dh,000h
        defb    01Fh,06Eh,080h,01Fh,06Eh,080h,03Fh,06Dh
        defb    040h,03Fh,06Eh,0C0h,000h,0F0h,000h,01Fh
        defb    0FAh,080h,000h,000h,000h,01Fh,0FAh,080h
        defb    03Fh,0FDh,040h,000h,000h,000h,00Fh,0F5h
        defb    000h,003h,0F4h,000h,000h,0D0h,000h,000h
        defb    05Ah,000h,001h,0DBh,080h,003h,0DBh,040h
        defb    007h,0DBh,0A0h,007h,0DBh,0A0h,00Fh,0DBh
        defb    050h,00Fh,0DBh,0B0h,000h,03Ch,000h,007h
        defb    0FEh,0A0h,000h,000h,000h,007h,0FEh,0A0h
        defb    00Fh,0FFh,050h,000h,000h,000h,003h,0FDh
        defb    040h,000h,0FDh,000h,000h,034h,000h,000h
        defb    016h,080h,000h,076h,0E0h,000h,0F6h,0D0h
        defb    001h,0F6h,0E8h,001h,0F6h,0E8h,003h,0F6h
        defb    0D4h,003h,0F6h,0ECh,000h,00Fh,000h,001h
        defb    0FFh,0A8h,000h,000h,000h,001h,0FFh,0A8h
        defb    003h,0FFh,0D4h,000h,000h,000h,000h,0FFh
        defb    050h,000h,03Fh,040h,000h,00Dh,000h,007h
        defb    0A0h,000h,01Fh,0E8h,000h,03Fh,0D4h,000h
        defb    07Fh,0EAh,000h,07Fh,0D6h,000h,0FFh,0E9h
        defb    000h,0FFh,0D5h,000h,000h,000h,000h,02Fh
        defb    0D4h,000h,04Fh,0D2h,000h,080h,001h,000h
        defb    087h,0A1h,000h,080h,001h,000h,091h,089h
        defb    000h,063h,0C6h,000h,033h,0CCh,000h,001h
        defb    0E8h,000h,007h,0FAh,000h,00Fh,0F5h,000h
        defb    01Fh,0FAh,080h,01Fh,0F5h,080h,03Fh,0FAh
        defb    040h,03Fh,0F5h,040h,000h,000h,000h,00Bh
        defb    0F5h,000h,013h,0F4h,080h,020h,000h,040h
        defb    021h,0E8h,040h,020h,000h,040h,012h,064h
        defb    080h,00Ch,0F3h,000h,006h,0F6h,000h,000h
        defb    07Ah,000h,001h,0FEh,080h,003h,0FDh,040h
        defb    007h,0FEh,0A0h,007h,0FDh,060h,00Fh,0FEh
        defb    090h,00Fh,0FDh,050h,000h,000h,000h,002h
        defb    0FDh,040h,004h,0FDh,020h,008h,000h,010h
        defb    008h,07Ah,010h,004h,000h,020h,002h,05Ah
        defb    040h,001h,0BDh,080h,000h,0FFh,000h,000h
        defb    01Eh,080h,000h,07Fh,0A0h,000h,0FFh,050h
        defb    001h,0FFh,0A8h,001h,0FFh,058h,003h,0FFh
        defb    0A4h,003h,0FFh,054h,000h,000h,000h,000h
        defb    0BFh,050h,001h,03Fh,048h,002h,000h,004h
        defb    002h,01Eh,084h,002h,000h,004h,001h,026h
        defb    048h,000h,0CFh,030h,000h,06Fh,060h,005h
        defb    0A0h,000h,01Dh,0B8h,000h,03Dh,0B4h,000h
        defb    07Dh,0BAh,000h,07Dh,0BAh,000h,0FDh,0B5h
        defb    000h,0FDh,0BBh,000h,003h,0C0h,000h,03Fh
        defb    0FCh,000h,03Fh,0FCh,000h,00Eh,070h,000h
        defb    055h,0AAh,000h,0BBh,0DDh,000h,0BBh,0DAh
        defb    000h,0BBh,0DDh,000h,051h,08Ah,000h,001h
        defb    068h,000h,007h,06Eh,000h,00Fh,06Dh,000h
        defb    01Fh,06Eh,080h,01Fh,06Eh,080h,03Fh,06Dh
        defb    040h,03Fh,06Eh,0C0h,000h,0F0h,000h,00Fh
        defb    0FFh,000h,00Fh,0FFh,000h,003h,09Ch,000h
        defb    015h,06Ah,080h,02Eh,0F7h,040h,02Eh,0F6h
        defb    080h,02Eh,0F7h,040h,014h,062h,080h,000h
        defb    05Ah,000h,001h,0DBh,080h,003h,0DBh,040h
        defb    007h,0DBh,0A0h,007h,0DBh,0A0h,00Fh,0DBh
        defb    050h,00Fh,0DBh,0B0h,000h,03Ch,000h,003h
        defb    0FFh,0C0h,003h,0FFh,0C0h,000h,0E7h,000h
        defb    005h,05Ah,0A0h,00Bh,0BDh,0D0h,00Bh,0BDh
        defb    0A0h,00Bh,0BDh,0D0h,005h,018h,0A0h,000h
        defb    016h,080h,000h,076h,0E0h,000h,0F6h,0D0h
        defb    001h,0F6h,0E8h,001h,0F6h,0E8h,003h,0F6h
        defb    0D4h,003h,0F6h,0ECh,000h,00Fh,000h,000h
        defb    0FFh,0F0h,000h,0FFh,0F0h,000h,039h,0C0h
        defb    001h,056h,0A8h,002h,0EFh,074h,002h,0EFh
        defb    068h,002h,0EFh,074h,001h,046h,028h,081h
        defb    002h,000h,06Dh,06Ch,000h,04Bh,0A4h,000h
        defb    01Ch,070h,000h,07Fh,0FCh,000h,05Eh,0F4h
        defb    000h,02Dh,068h,000h,0EDh,06Eh,000h,02Dh
        defb    068h,000h,05Eh,0F4h,000h,07Fh,0FCh,000h
        defb    01Ch,070h,000h,04Bh,0A4h,000h,06Dh,06Ch
        defb    000h,081h,002h,000h,000h,000h,000h,020h
        defb    040h,080h,01Bh,05Bh,000h,012h,0E9h,000h
        defb    007h,01Ch,000h,01Fh,0FFh,000h,017h,0BDh
        defb    000h,00Bh,05Ah,000h,03Bh,05Bh,080h,00Bh
        defb    05Ah,000h,017h,0BDh,000h,01Fh,0FFh,000h
        defb    007h,01Ch,000h,012h,0E9h,000h,01Bh,05Bh
        defb    000h,020h,040h,080h,000h,000h,000h,008h
        defb    010h,020h,006h,0D6h,0C0h,004h,0BAh,040h
        defb    001h,0C7h,000h,007h,0FFh,0C0h,005h,0EFh
        defb    040h,002h,0D6h,080h,00Eh,0D6h,0E0h,002h
        defb    0D6h,080h,005h,0EFh,040h,007h,0FFh,0C0h
        defb    001h,0C7h,000h,004h,0BAh,040h,006h,0D6h
        defb    0C0h,008h,010h,020h,000h,000h,000h,002h
        defb    004h,008h,001h,0B5h,0B0h,001h,02Eh,090h
        defb    000h,071h,0C0h,001h,0FFh,0F0h,001h,07Bh
        defb    0D0h,000h,0B5h,0A0h,003h,0B5h,0B8h,000h
        defb    0B5h,0A0h,001h,07Bh,0D0h,001h,0FFh,0F0h
        defb    000h,071h,0C0h,001h,02Eh,090h,001h,0B5h
        defb    0B0h,002h,004h,008h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,0C1h
        defb    093h,0F5h,08Bh,039h,0A3h,093h,086h
data_glyph_block:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    043h
gap_3781:
; data_sprites_base: кандидат на базу спрайтовых данных (exec 0x4000). Структурированные байт-паттерны: симметричные последовательности (220/231), битовые маски (3/128, 7/64, 7/128). Возможно, 8x8 или 16x16 пиксельные спрайты врагов/объектов. Глубокий разбор вне scope Stage 8 (минимально).
        defb    03Eh,08Eh,078h,03Ch,080h,0F0h,0C7h,0C8h
        defb    0CFh,01Dh,0DCh,04Eh,099h,086h,01Ah,01Bh
        defb    059h,07Bh,01Ch,0E1h,08Fh,0C9h,0A3h,0C9h
        defb    0A3h,0E5h,093h,070h,0C7h,03Ah,0FEh,018h
        defb    038h,09Dh,002h,01Ch,040h,0F8h,01Fh,0E4h
        defb    0BBh,00Eh,030h,026h,032h,04Bh,01Ch,01Bh
        defb    0AEh,039h,086h,0F1h,0A3h,0C5h,083h,0C5h
        defb    0A3h,0F1h,087h,038h,0DEh,05Ah,0D8h,098h
        defb    062h,059h,070h,03Bh,0B8h,0F3h,013h,0E3h
        defb    00Fh,001h,03Ch,09Eh,070h,07Ch,0C2h,061h
        defb    0C8h,0C9h,09Ch,0D1h,08Fh,0C5h,0A3h,0C5h
        defb    0A3h,0D1h,08Fh,061h,09Ch,075h,0D9h,038h
        defb    0D2h,04Ch,061h,00Ch,070h,0DCh,027h,0F8h
        defb    01Fh,002h,038h,040h,0BAh,01Ch,018h,07Fh
        defb    05Ch,0E3h,00Eh,0C1h,0A7h,0C9h,083h,0C1h
        defb    083h,0E5h,08Fh,07Bh,01Ch,01Bh,059h,086h
        defb    018h,04Eh,099h,01Dh,0DCh,0C8h,0CFh,0F0h
        defb    0C7h,03Ch,080h,08Eh,079h,043h,03Eh,093h
        defb    086h,039h,093h,0F1h,0ABh,0C1h,083h,000h
        defb    001h,000h,001h,000h,003h,000h,006h,000h
        defb    006h,000h,000h,000h,01Dh,000h,01Dh,000h
        defb    000h,000h,03Bh,000h,077h,000h,077h,018h
        defb    077h,000h,077h,034h,077h,07Ah,03Bh,000h
        defb    000h,0B6h,0AAh,07Fh,0FDh,0EFh,0FEh,0FFh
        defb    0AAh,000h,000h,0DFh,0FFh,0FFh,0FFh,000h
        defb    000h,0BFh,0F5h,0FFh,0FEh,07Fh,0FDh,0FFh
        defb    0FEh,0FFh,0FDh,07Fh,0FAh,0DFh,055h,080h
        defb    000h,080h,000h,040h,000h,020h,000h,0A0h
        defb    000h,000h,000h,048h,000h,0A8h,000h,000h
        defb    000h,054h,000h,0AAh,000h,054h,000h,0AAh
        defb    018h,054h,000h,0AAh,034h,054h,07Ah,000h
        defb    000h,06Dh,0FAh,0DFh,0FDh,0DBh,0FAh,0DFh
        defb    0FDh,0DBh,0FAh,0DFh,0FDh,0DBh,0FAh,0DFh
        defb    0FDh,0DBh,0FAh,0DFh,0FDh,0DBh,0FAh,0DFh
        defb    0FDh,0DBh,0FAh,0DFh,0F5h,06Dh,0AAh,030h
        defb    008h,036h,064h,034h,048h,034h,044h,030h
        defb    008h,036h,064h,034h,048h,034h,044h,030h
        defb    008h,036h,064h,034h,048h,034h,044h,030h
        defb    008h,036h,064h,034h,048h,034h,044h,06Dh
        defb    0FAh,0DFh,0FDh,0DBh,0FAh,0DFh,0FDh,0DBh
        defb    0FAh,0DFh,0FDh,0DBh,0FAh,0DFh,0FDh,0DBh
        defb    0FAh,0DFh,0FDh,0DBh,0FAh,0DFh,0FDh,0DBh
        defb    0FAh,0DFh,0F5h,06Dh,0AAh,000h,000h,080h
        defb    000h,040h,000h,040h,000h,020h,0C0h,020h
        defb    020h,020h,010h,060h,000h,060h,00Fh,060h
        defb    030h,060h,066h,0C0h,0C6h,0C0h,0C6h,0C1h
        defb    083h,0C5h,0A3h,0D1h,08Bh,0C1h,083h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,018h,008h,004h,010h,002h,062h
        defb    022h,061h,003h,0C9h,093h,0C1h,083h,080h
        defb    000h,080h,000h,080h,000h,040h,000h,040h
        defb    000h,060h,0E0h,027h,080h,00Ch,000h,018h
        defb    000h,030h,000h,036h,008h,063h,004h,06Bh
        defb    006h,0C1h,0A3h,0D5h,093h,0C1h,083h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,001h,008h
        defb    081h,085h,012h,091h,003h,0C1h,0A3h,000h
        defb    006h,000h,03Eh,000h,07Ch,001h,0BEh,003h
        defb    0BCh,007h,0DEh,007h,0DCh,00Fh,0EAh,00Fh
        defb    0ECh,017h,0F2h,019h,0F4h,03Eh,0FAh,03Fh
        defb    03Ah,07Fh,0DCh,07Fh,0E4h,000h,000h,060h
        defb    000h,07Ch,000h,07Eh,000h,07Dh,080h,07Dh
        defb    040h,07Bh,0A0h,07Bh,0E0h,077h,0D0h,077h
        defb    0F0h,06Fh,0E8h,06Fh,098h,05Fh,074h,05Ch
        defb    0F4h,03Bh,0FAh,027h,0EAh,000h,000h,000h
        defb    000h,0FFh,0F8h,0FFh,0E6h,07Fh,09Ch,07Eh
        defb    07Ch,079h,0FAh,027h,0F6h,01Fh,0F4h,017h
        defb    0EEh,00Bh,0DCh,006h,0DAh,001h,0FCh,000h
        defb    066h,000h,018h,000h,006h,000h,000h,000h
        defb    000h,01Fh,0FFh,067h,0FFh,039h,0FEh,03Eh
        defb    07Eh,05Fh,09Eh,06Fh,0E4h,06Fh,0F8h,077h
        defb    0E8h,07Bh,0D0h,07Bh,060h,03Dh,080h,066h
        defb    000h,018h,000h,060h,000h,000h,000h,000h
        defb    000h,0FFh,0FFh,055h,055h,000h,000h,0FFh
        defb    0FFh,0BFh,0FDh,0E0h,007h,0E5h,057h,0E2h
        defb    0AFh,0E5h,057h,0BFh,0FDh,0FFh,0FFh,000h
        defb    000h,0FFh,0FFh,055h,055h,000h,000h,04Fh
        defb    0F4h,06Bh,0D6h,04Fh,0F4h,06Ch,036h,04Ch
        defb    034h,06Dh,076h,04Ch,0B4h,06Dh,076h,04Ch
        defb    0B4h,06Dh,076h,04Ch,0B4h,06Dh,076h,04Ch
        defb    0B4h,06Fh,0F6h,04Bh,0D4h,06Fh,0F6h,007h
        defb    080h,01Fh,07Fh,03Fh,07Fh,07Fh,06Fh,07Fh
        defb    07Fh,0FFh,07Fh,0FFh,07Fh,0FFh,07Fh,0FFh
        defb    07Fh,0FFh,07Fh,0FFh,07Fh,07Fh,07Fh,07Fh
        defb    06Fh,03Fh,02Ah,01Fh,055h,007h,080h,001h
        defb    0E0h,0FAh,0F8h,0FCh,0FCh,0EAh,0FEh,0FCh
        defb    0FEh,0FAh,0FDh,0F4h,0FEh,0FAh,0FDh,0F4h
        defb    0FEh,0FAh,0FDh,0F4h,0FDh,0EAh,0F6h,054h
        defb    0EAh,0AAh,0F4h,054h,0C8h,001h,0A0h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,041h
        defb    082h,007h,0E0h,060h,006h,06Fh,0F6h,06Fh
        defb    0F6h,060h,006h,007h,0E0h,041h,082h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,007h
        defb    0E0h,01Fh,0F8h,03Ch,03Ch,070h,00Eh,00Ch
        defb    030h,0EAh,057h,0C6h,0E2h,0C1h,0C3h,0C3h
        defb    082h,0C7h,063h,0EAh,057h,00Ch,030h,070h
        defb    00Eh,03Ch,034h,01Fh,0E8h,006h,0A0h,000h
        defb    000h,000h,0FEh,001h,002h,002h,078h,07Ah
        defb    07Ah,04Bh,000h,073h,0FEh,073h,0FCh,073h
        defb    0FAh,06Bh,0D4h,043h,002h,06Ah,078h,002h
        defb    07Ah,001h,000h,000h,0AAh,000h,000h,000h
        defb    000h,0FFh,0FFh,000h,000h,033h,033h,000h
        defb    000h,0FFh,0FFh,0FFh,0FFh,0FFh,0FFh,0FFh
        defb    0FFh,0AAh,0AAh,055h,055h,000h,000h,033h
        defb    033h,000h,000h,0AAh,0AAh,000h,000h,000h
        defb    000h,07Fh,000h,040h,080h,05Eh,040h,05Eh
        defb    05Eh,040h,0D2h,07Eh,09Ch,07Fh,05Ah,07Eh
        defb    09Ch,075h,05Ah,040h,090h,05Eh,05Ah,05Eh
        defb    040h,040h,080h,055h,000h,000h,000h,00Fh
        defb    0D0h,02Fh,0E4h,02Fh,0D4h,02Fh,0E4h,00Fh
        defb    0D0h,000h,000h,007h,0A0h,007h,0C0h,007h
        defb    0A0h,000h,000h,001h,080h,001h,080h,000h
        defb    000h,003h,040h,003h,080h,003h,040h,00Fh
        defb    0D0h,06Fh,0E6h,06Fh,0D6h,06Fh,0E6h,00Fh
        defb    0D0h,000h,000h,007h,0A0h,007h,0C0h,007h
        defb    0A0h,000h,000h,001h,080h,000h,000h,003h
        defb    040h,003h,080h,003h,040h,000h,000h,00Fh
        defb    0D0h,0EFh,0E7h,0EFh,0D7h,0EFh,0E7h,00Fh
        defb    0D0h,000h,000h,007h,0A0h,007h,0C0h,007h
        defb    0A0h,000h,000h,000h,000h,003h,040h,003h
        defb    080h,003h,040h,000h,000h,000h,000h,003h
        defb    040h,003h,080h,003h,040h,000h,000h,001h
        defb    080h,001h,080h,000h,000h,007h,0A0h,007h
        defb    0C0h,007h,0A0h,000h,000h,00Fh,0D0h,02Fh
        defb    0E4h,02Fh,0D4h,02Fh,0E4h,00Fh,0D0h,000h
        defb    000h,003h,040h,003h,080h,003h,040h,000h
        defb    000h,001h,080h,000h,000h,007h,0A0h,007h
        defb    0C0h,007h,0A0h,000h,000h,00Fh,0D0h,06Fh
        defb    0E6h,06Fh,0D6h,06Fh,0E6h,00Fh,0D0h,000h
        defb    000h,000h,000h,003h,040h,003h,080h,003h
        defb    040h,000h,000h,000h,000h,007h,0A0h,007h
        defb    0C0h,007h,0A0h,000h,000h,00Fh,0D0h,0EFh
        defb    0E7h,0EFh,0D7h,0EFh,0E7h,00Fh,0D0h,001h
        defb    0E0h,002h,0D0h,00Fh,070h,01Fh,064h,01Ch
        defb    052h,033h,0D2h,031h,0A1h,064h,001h,064h
        defb    001h,044h,001h,042h,002h,043h,002h,081h
        defb    086h,000h,0CCh,000h,058h,000h,038h,000h
        defb    001h,000h,001h,000h,002h,000h,00Ch,000h
        defb    078h,017h,0C0h,031h,000h,039h,000h,014h
        defb    000h,02Ah,000h,014h,000h,001h,000h,010h
        defb    080h,008h,080h,008h,080h,004h,040h,000h
        defb    068h,000h,050h,000h,0E0h,000h,0D0h,001h
        defb    0E0h,001h,0D0h,002h,0A8h,003h,051h,007h
        defb    0ABh,007h,0D3h,00Bh,0E9h,01Dh,0D5h,01Dh
        defb    0A8h,03Ah,0EBh,066h,0D7h,0C1h,003h,004h
        defb    040h,004h,040h,00Ch,040h,008h,080h,019h
        defb    080h,033h,000h,0C6h,000h,0AAh,000h,0D4h
        defb    000h,0A8h,000h,0DAh,000h,0A7h,000h,09Dh
        defb    000h,03Eh,080h,0C3h,020h,078h,055h,006h
        defb    05Ah,019h,06Dh,021h,06Dh,041h,06Dh,043h
        defb    06Dh,086h,0EDh,0DDh,0DDh,073h,0DBh,00Fh
        defb    03Bh,0FCh,0F7h,063h,0EEh,01Fh,09Eh,0FCh
        defb    07Dh,033h,0FBh,08Fh,0E7h,07Fh,01Eh,000h
        defb    000h,000h,000h,080h,000h,0A0h,000h,0A0h
        defb    000h,0A0h,000h,0B0h,000h,0B0h,000h,070h
        defb    000h,068h,000h,068h,000h,0E8h,000h,0D0h
        defb    000h,0D8h,000h,030h,000h,0D0h,000h,000h
        defb    0FDh,01Fh,0E3h,007h,09Fh,000h,074h,000h
        defb    003h,000h,03Fh,000h,03Fh,000h,01Eh,000h
        defb    00Fh,000h,000h,000h,01Fh,000h,01Fh,000h
        defb    00Fh,000h,073h,001h,07Ch,0DFh,0ADh,0A0h
        defb    000h,040h,000h,080h,000h,040h,000h,080h
        defb    000h,040h,000h,080h,000h,080h,000h,021h
        defb    0F0h,0D3h,00Ch,0A3h,086h,0D5h,0FCh,0A2h
        defb    0D0h,095h,020h,02Ah,0C8h,055h,0B7h,07Bh
        defb    0FFh,0FDh,0BFh,0FEh,0FFh,0FFh,07Fh,0FFh
        defb    0B7h,0FFh,0DFh,07Fh,0EFh,000h,007h,07Fh
        defb    0AAh,0FFh,0F5h,0FFh,0FAh,07Fh,0F4h,077h
        defb    0FAh,03Bh,0F4h,01Ch,0D8h,007h,0E0h,0F1h
        defb    054h,0D8h,0AAh,0FCh,055h,0FEh,02Ah,0FBh
        defb    015h,0FFh,08Ah,081h,0C4h,060h,0E0h,0C0h
        defb    070h,090h,038h,038h,05Ch,078h,0EEh,035h
        defb    067h,00Eh,0A2h,00Fh,040h,00Fh,0A0h,017h
        defb    0D0h,03Bh,0D0h,01Dh,0E8h,000h,0D8h,000h
        defb    034h,000h,00Eh,000h,006h,000h,001h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,0FFh
        defb    0FEh,080h,000h,0BBh,0BAh,0A2h,020h,0A2h
        defb    022h,080h,000h,0BBh,0BAh,0A2h,020h,0A2h
        defb    022h,080h,000h,0BBh,0BAh,0A2h,020h,0A2h
        defb    022h,080h,000h,0AAh,0AAh,000h,000h,0FFh
        defb    0FEh,080h,000h,0BFh,0FAh,0A0h,000h,0AAh
        defb    0AAh,0A5h,050h,0AAh,0AAh,0A5h,050h,0AAh
        defb    0AAh,0A5h,050h,0AAh,0AAh,0A5h,050h,0AAh
        defb    0AAh,080h,000h,0AAh,0AAh,000h,000h,0DFh
        defb    0ADh,001h,07Ch,000h,073h,000h,00Fh,000h
        defb    01Fh,000h,01Fh,000h,000h,000h,00Fh,000h
        defb    01Eh,000h,03Fh,000h,03Fh,000h,003h,000h
        defb    074h,007h,09Fh,01Fh,0E3h,000h,0FDh,055h
        defb    0B7h,02Ah,0C8h,095h,020h,0A2h,0D0h,0D5h
        defb    0FCh,0A3h,086h,0D3h,00Ch,021h,0F0h,080h
        defb    000h,080h,000h,040h,000h,080h,000h,040h
        defb    000h,080h,000h,040h,000h,0A0h,000h,07Fh
        defb    01Eh,08Fh,0E7h,033h,0FBh,0FCh,07Dh,01Fh
        defb    09Eh,063h,0EEh,0FCh,0F7h,00Fh,03Bh,073h
        defb    0DBh,0DDh,0DDh,086h,0EDh,043h,06Dh,041h
        defb    06Dh,021h,06Dh,019h,06Dh,006h,05Ah,0D0h
        defb    000h,030h,000h,0D8h,000h,0D0h,000h,0E8h
        defb    000h,068h,000h,068h,000h,070h,000h,0B0h
        defb    000h,0B0h,000h,0A0h,000h,0A0h,000h,0A0h
        defb    000h,080h,000h,000h,000h,000h,000h,0C1h
        defb    083h,0D1h,08Bh,0C5h,0A3h,0C1h,083h,0C0h
        defb    0C6h,0C0h,0C6h,060h,066h,060h,030h,060h
        defb    00Fh,060h,000h,020h,010h,020h,020h,020h
        defb    0C0h,040h,000h,040h,000h,080h,000h,0C1h
        defb    083h,0C9h,093h,061h,003h,062h,022h,010h
        defb    002h,008h,004h,000h,018h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,0C1h
        defb    083h,0D5h,093h,0C1h,0A3h,06Bh,006h,063h
        defb    004h,036h,008h,030h,000h,018h,000h,00Ch
        defb    000h,027h,080h,060h,0E0h,040h,000h,040h
        defb    000h,080h,000h,080h,000h,080h,000h,0C1h
        defb    0A3h,091h,003h,085h,012h,008h,081h,000h
        defb    001h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,063h,08Eh,0E6h
        defb    0DBh,066h,0DBh,066h,0DBh,066h,0DBh,066h
        defb    0DBh,066h,0DBh,066h,0DBh,066h,0DBh,0F3h
        defb    08Eh,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,063h,0CEh,0F3h
        defb    01Bh,0B3h,01Bh,033h,01Bh,033h,09Bh,060h
        defb    0DBh,0C0h,0DBh,0C0h,0DBh,0C2h,0DBh,0F1h
        defb    08Eh,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,0F3h,08Eh,0C6h
        defb    0DBh,0C6h,0DBh,0C6h,0DBh,0E6h,0DBh,036h
        defb    0DBh,036h,0DBh,036h,0DBh,0B6h,0DBh,0E3h
        defb    08Eh,000h,000h,000h,000h,000h,000h,06Fh
        defb    0DAh,06Fh,0F4h,06Fh,0DAh,06Fh,0F4h,06Fh
        defb    0DAh,06Fh,0F4h,06Fh,0DAh,06Fh,0F4h,06Fh
        defb    0DAh,06Fh,0F4h,06Fh,0DAh,06Fh,0F4h,06Fh
        defb    0DAh,06Fh,0F4h,06Fh,0DAh,06Fh,0F4h,080h
        defb    001h,0D5h,055h,0DAh,0ABh,000h,000h,06Dh
        defb    05Ah,06Eh,0B4h,06Fh,05Ah,06Eh,0B4h,06Fh
        defb    05Ah,06Fh,0B4h,06Fh,05Ah,06Fh,0B4h,06Fh
        defb    0DAh,06Fh,0B4h,06Fh,0DAh,06Fh,0F4h,06Fh
        defb    0F4h,06Fh,0DAh,06Fh,0B4h,06Fh,0DAh,06Fh
        defb    0B4h,06Fh,05Ah,06Fh,0B4h,06Fh,05Ah,06Eh
        defb    0B4h,06Fh,05Ah,06Eh,0B4h,06Dh,05Ah,000h
        defb    000h,0DAh,0ABh,0D5h,055h,080h,001h,035h
        defb    054h,07Fh,0EAh,000h,000h,0DCh,0E7h,0DCh
        defb    0E7h,0DCh,0E7h,000h,000h,06Fh,0EAh,06Fh
        defb    0F6h,000h,000h,02Fh,0D4h,037h,0ECh,05Bh
        defb    0DAh,04Fh,056h,033h,0CCh,080h,001h,035h
        defb    054h,07Fh,0EAh,000h,000h,0B9h,0CEh,0B9h
        defb    0CEh,0B9h,0CEh,000h,000h,06Fh,0EAh,06Fh
        defb    0F6h,000h,000h,02Fh,0D4h,037h,0ECh,05Bh
        defb    0DAh,04Fh,056h,033h,0CCh,080h,001h,035h
        defb    054h,07Fh,0EAh,000h,000h,073h,09Dh,073h
        defb    09Dh,073h,09Dh,000h,000h,06Fh,0EAh,06Fh
        defb    0F6h,000h,000h,02Fh,0D4h,037h,0ECh,05Bh
        defb    0DAh,04Fh,056h,033h,0CCh,080h,001h,035h
        defb    054h,07Fh,0EAh,000h,000h,0E7h,03Bh,0E7h
        defb    03Bh,0E7h,03Bh,000h,000h,06Fh,0EAh,06Fh
        defb    0F6h,000h,000h,02Fh,0D4h,037h,0ECh,05Bh
        defb    0DAh,04Fh,056h,033h,0CCh,080h,001h,080h
        defb    001h,033h,0CCh,04Fh,056h,05Bh,0DAh,037h
        defb    0ECh,02Fh,0D4h,000h,000h,06Fh,0F6h,06Fh
        defb    0EAh,000h,000h,0E7h,03Bh,0E7h,03Bh,0E7h
        defb    03Bh,000h,000h,07Fh,0EAh,035h,054h,080h
        defb    001h,033h,0CCh,04Fh,056h,05Bh,0DAh,037h
        defb    0ECh,02Fh,0D4h,000h,000h,06Fh,0F6h,06Fh
        defb    0EAh,000h,000h,073h,09Dh,073h,09Dh,073h
        defb    09Dh,000h,000h,07Fh,0EAh,035h,054h,080h
        defb    001h,033h,0CCh,04Fh,056h,05Bh,0DAh,037h
        defb    0ECh,02Fh,0D4h,000h,000h,06Fh,0F6h,06Fh
        defb    0EAh,000h,000h,0B9h,0CEh,0B9h,0CEh,0B9h
        defb    0CEh,000h,000h,07Fh,0EAh,035h,054h,080h
        defb    001h,033h,0CCh,04Fh,056h,05Bh,0DAh
data_sprites_base:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    037h
gap_4001:
; Фантом (конверт function->label этим проходом): 0x7800.. — за концом ROM (0x6B00 байт, последний nonzero в 0x6AFF) = пустая RAM, дамп — одни NOP. Все метки label_phantom_78xx — то же. Возникли в раннем Stage-2 из линейного дампа (рассинхрон) + ветвей внутри data_blob_263d. Реальный код их не вызывает (CALL-подобные последовательности внутри архива — ложные).
        defb    0ECh,02Fh,0D4h,000h,000h,06Fh,0F6h,06Fh
        defb    0EAh,000h,000h,0DCh,0E7h,0DCh,0E7h,0DCh
        defb    0E7h,000h,000h,07Fh,0EAh,035h,054h,001h
        defb    000h,000h,000h,003h,080h,003h,080h,000h
        defb    000h,003h,080h,007h,040h,007h,080h,007h
        defb    040h,007h,080h,007h,040h,010h,010h,017h
        defb    0D0h,03Bh,0B8h,07Bh,0BCh,079h,03Ch,079h
        defb    03Ch,07Bh,0BCh,03Bh,0B8h,017h,0D0h,010h
        defb    010h,007h,040h,007h,080h,007h,040h,007h
        defb    080h,007h,040h,003h,080h,000h,000h,003h
        defb    080h,003h,080h,000h,000h,001h,000h,000h
        defb    000h,00Fh,0FEh,03Fh,07Eh,03Fh,07Eh,07Fh
        defb    0BEh,07Fh,0DCh,07Fh,0DAh,07Fh,0ECh,01Fh
        defb    0E2h,067h,0F4h,079h,0FAh,07Eh,078h,07Fh
        defb    094h,07Fh,0A6h,07Dh,058h,000h,000h,000h
        defb    000h,07Eh,0F0h,07Eh,0FCh,07Dh,0FCh,07Dh
        defb    0FEh,07Bh,0FCh,07Bh,0FAh,077h,0FCh,077h
        defb    0F2h,06Fh,0ECh,06Fh,09Ah,05Eh,074h,05Ch
        defb    0FAh,033h,0F4h,027h,0AAh,000h,000h,000h
        defb    000h,055h,0E4h,02Fh,0CCh,05Fh,03Ah,02Eh
        defb    07Ah,059h,0F6h,037h,0F6h,04Fh,0ECh,03Fh
        defb    0EEh,05Fh,0DCh,03Fh,0DAh,07Fh,0BCh,03Fh
        defb    0BAh,03Fh,074h,00Fh,06Ah,000h,000h,000h
        defb    000h,01Fh,0FEh,067h,0FEh,039h,0FEh,01Eh
        defb    07Eh,05Fh,09Ch,06Fh,0E6h,067h,0F8h,077h
        defb    0FEh,07Bh,0FCh,07Bh,0FAh,07Dh,0FCh,07Eh
        defb    0FAh,07Eh,0F4h,07Fh,068h,000h,000h,000h
        defb    000h,0DFh,0FFh,0DFh,0FFh,0DFh,0FFh,000h
        defb    000h,06Fh,0FFh,06Fh,0FFh,06Fh,0FFh,000h
        defb    000h,01Bh,0FFh,01Bh,0FFh,01Bh,0FFh,01Bh
        defb    0FFh,01Bh,0FFh,01Bh,0FFh,01Bh,0FFh,000h
        defb    000h,0FDh,055h,0FEh,0AAh,0FDh,055h,000h
        defb    000h,0FEh,0AAh,0FDh,054h,0FEh,0AAh,000h
        defb    000h,0FEh,0A8h,0FDh,050h,0FEh,0A8h,0FDh
        defb    050h,0FAh,0A8h,0F5h,050h,0AAh,0A8h,0EEh
        defb    0FFh,0EFh,0FFh,0EEh,0FFh,0EFh,0FFh,076h
        defb    0FFh,077h,0FFh,03Bh,07Fh,000h,000h,00Dh
        defb    0DFh,00Dh,0FFh,00Dh,0DFh,00Dh,0FFh,00Dh
        defb    0DFh,00Dh,0FFh,00Dh,0DFh,00Dh,0FFh,0EAh
        defb    0ABh,0F5h,055h,0FAh,0AAh,0F5h,055h,0FAh
        defb    0AAh,0F5h,056h,0EAh,0A8h,000h,000h,055h
        defb    050h,0AAh,0A0h,0D5h,050h,0EAh,0A0h,0D5h
        defb    050h,0EAh,0A0h,0D5h,050h,0EAh,0A0h,00Dh
        defb    0DFh,00Dh,0FFh,00Dh,0DFh,00Dh,0FFh,00Dh
        defb    0DFh,00Dh,0FFh,00Dh,0DFh,000h,000h,037h
        defb    07Fh,037h,0FFh,037h,07Fh,000h,000h,0EEh
        defb    0FFh,0EFh,0FFh,0EEh,0FFh,000h,000h,0D5h
        defb    050h,0EAh,0A0h,0D5h,050h,0EAh,0A0h,0D5h
        defb    050h,0AAh,0A0h,055h,050h,000h,000h,0D5h
        defb    054h,0EAh,0A8h,0F5h,054h,000h,000h,0F5h
        defb    055h,0FAh,0AAh,0F5h,055h,000h,000h,0FFh
        defb    07Fh,0FFh,05Fh,0FFh,07Fh,0FFh,07Fh,07Fh
        defb    07Fh,07Fh,07Fh,07Fh,07Fh,03Fh,07Fh,03Fh
        defb    07Fh,01Fh,07Fh,00Fh,07Fh,007h,07Fh,003h
        defb    07Fh,001h,05Fh,000h,07Fh,000h,00Fh,0FEh
        defb    0ABh,0FAh,0D5h,0FEh,0AAh,0FEh,0D5h,0FEh
        defb    0AAh,0FEh,0D4h,0FEh,0AAh,0FEh,0D4h,0FEh
        defb    094h,0FEh,0A8h,0FEh,0D0h,0FEh,0A0h,0FEh
        defb    0C0h,0FAh,080h,0FEh,000h,0F0h,000h,0FFh
        defb    054h,0FFh,02Bh,0FFh,057h,0FFh,000h,07Fh
        defb    07Fh,07Fh,05Fh,07Fh,07Fh,03Fh,07Fh,03Fh
        defb    07Fh,01Fh,07Fh,00Fh,07Fh,007h,07Fh,003h
        defb    07Fh,001h,07Fh,000h,07Fh,000h,00Fh,014h
        defb    0ABh,0CAh,0D5h,0E4h,0AAh,000h,0D5h,0FEh
        defb    0AAh,0FAh,0D4h,0FEh,0AAh,0FEh,0D4h,0FEh
        defb    094h,0FEh,0A8h,0FEh,0D0h,0FEh,0A0h,0FEh
        defb    0C0h,0FEh,080h,0FEh,000h,0F0h,000h,0FFh
        defb    054h,0FFh,02Bh,0FFh,057h,0FFh,024h,07Fh
        defb    048h,07Fh,028h,07Fh,048h,03Fh,000h,03Fh
        defb    07Fh,01Fh,05Fh,00Fh,07Fh,007h,07Fh,003h
        defb    07Fh,001h,07Fh,000h,07Fh,000h,00Fh,014h
        defb    0ABh,0CAh,0D5h,0E4h,0AAh,022h,0D5h,010h
        defb    0AAh,012h,0D4h,010h,0AAh,000h,0D4h,0FEh
        defb    094h,0FAh,0A8h,0FEh,0D0h,0FEh,0A0h,0FEh
        defb    0C0h,0FEh,080h,0FEh,000h,0F0h,000h,0FFh
        defb    054h,0FFh,02Bh,0FFh,057h,0FFh,024h,07Fh
        defb    048h,07Fh,028h,07Fh,048h,03Fh,028h,03Fh
        defb    044h,01Fh,023h,00Fh,054h,007h,000h,003h
        defb    07Fh,001h,05Fh,000h,07Fh,000h,00Fh,014h
        defb    0ABh,0CAh,0D5h,0E4h,0AAh,022h,0D5h,010h
        defb    0AAh,012h,0D4h,010h,0AAh,012h,0D4h,020h
        defb    094h,0C2h,0A8h,004h,0D0h,000h,0A0h,0FEh
        defb    0C0h,0FAh,080h,0FEh,000h,0F0h,000h,0FFh
        defb    0FFh,07Fh,0FFh,03Fh,0FFh,01Fh,0FFh,00Fh
        defb    0FFh,007h,0E0h,003h,0F0h,001h,0F8h,000h
        defb    0FCh,000h,07Eh,000h,03Fh,000h,01Fh,000h
        defb    00Fh,000h,007h,000h,003h,000h,001h,0FFh
        defb    0DFh,0FFh,0BFh,0FFh,01Fh,0FEh,00Fh,0FCh
        defb    00Fh,000h,00Fh,000h,00Fh,000h,00Fh,000h
        defb    00Fh,000h,00Fh,000h,00Fh,080h,00Fh,0C0h
        defb    00Fh,0E0h,00Fh,0F0h,00Fh,0F8h,00Fh,0F0h
        defb    03Fh,0E0h,07Fh,0C0h,0FFh,081h,0F8h,083h
        defb    0F0h,087h,0E0h,08Fh,0FFh,09Fh,0FFh,0BFh
        defb    0FFh,0BEh,00Fh,0BCh,01Fh,0B8h,03Fh,0BFh
        defb    0FFh,0BFh,0FFh,0BFh,0FFh,0BFh,0FEh,0F8h
        defb    001h,0FCh,003h,0FEh,007h,03Fh,00Fh,07Eh
        defb    01Fh,0FCh,03Fh,0F8h,07Fh,0F0h,0FFh,0C1h
        defb    0FFh,0E3h,0F0h,0F7h,0E0h,0EFh,0C0h,0DFh
        defb    0FFh,0BFh,0FFh,07Fh,0FFh,0FFh,0FFh,0FFh
        defb    0FBh,0FFh,0F7h,0FFh,0EFh,0FFh,0DFh,080h
        defb    03Fh,000h,07Eh,0FEh,0FFh,0FDh,0FFh,0FBh
        defb    0FFh,007h,0FFh,00Fh,0CFh,01Fh,087h,0FFh
        defb    003h,0FEh,001h,0FCh,000h,0F8h,000h,0FFh
        defb    080h,0FFh,0C1h,0FFh,0E3h,083h,0F7h,007h
        defb    0EFh,00Fh,0DFh,0FFh,0BFh,0FFh,07Eh,0FEh
        defb    0FCh,081h,0F8h,0C3h,0F0h,0E7h,0E0h,0FFh
        defb    0C1h,0FFh,083h,0FFh,007h,07Eh,00Fh,0FFh
        defb    0E0h,0FFh,0F0h,0FFh,0F8h,0E0h,0FDh,0C1h
        defb    0FBh,083h,0F7h,007h,0EFh,00Fh,0DFh,01Fh
        defb    0BFh,03Fh,07Eh,07Eh,0FCh,0FDh,0F8h,0FBh
        defb    0FFh,0F1h,0FFh,0E0h,0FFh,0C0h,07Fh,03Fh
        defb    0F8h,07Fh,0FCh,0FFh,0FEh,0F8h,03Fh,0F0h
        defb    07Eh,0E0h,0FDh,0C1h,0FBh,083h,0F7h,007h
        defb    0EFh,00Fh,0DFh,01Fh,0BFh,03Fh,07Eh,0FEh
        defb    0FDh,0FDh,0FBh,0FBh,0F7h,0F7h,0EFh,00Fh
        defb    0CFh,01Fh,08Fh,03Fh,04Fh,07Eh,0EFh,001h
        defb    0FFh,0FBh,0FFh,0F7h,0FFh,0EFh,0DFh,0DFh
        defb    08Fh,0BFh,00Fh,07Eh,00Fh,0FCh,00Fh,0FFh
        defb    0FFh,0FFh,0FFh,0FFh,0FFh,0FFh,0FFh,080h
        defb    000h,080h,000h,080h,000h,080h,000h,080h
        defb    000h,080h,000h,080h,000h,080h,000h,080h
        defb    000h,080h,000h,080h,000h,080h,000h,080h
        defb    000h,080h,000h,080h,000h,080h,000h,0FFh
        defb    0EFh,07Fh,0EFh,03Fh,0EFh,01Fh,0EFh,00Fh
        defb    0EFh,007h,0EFh,003h,0EFh,001h,0EFh,000h
        defb    00Fh,000h,07Fh,000h,03Fh,000h,01Fh,000h
        defb    00Fh,000h,007h,000h,003h,000h,001h,080h
        defb    000h,080h,000h,080h,000h,080h,000h,080h
        defb    000h,083h,0EDh,087h,0DBh,083h,036h,086h
        defb    07Dh,08Ch,0FBh,099h,0B6h,0B3h,06Fh,0A6h
        defb    0DEh,080h,000h,080h,000h,080h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,0BCh,00Fh,078h,01Eh,0C0h,030h,0E0h
        defb    07Bh,0C0h,0F6h,001h,08Dh,003h,01Bh,006h
        defb    031h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,06Eh,036h,0DFh,06Dh,036h,0D8h,061h
        defb    0F1h,0D3h,063h,0B6h,0C6h,0EDh,08Ch,0DBh
        defb    019h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,0FBh,071h,0F6h,0FBh,0C1h,0B6h,09Bh
        defb    06Ch,036h,0DAh,06Dh,0B6h,0DBh,07Ch,0B6h
        defb    038h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,0C0h,031h,0E0h,07Fh,0C0h,0D6h,001h
        defb    08Dh,003h,01Bh,006h,036h,00Ch,06Dh,018h
        defb    0DBh,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,0BCh,0E3h,07Dh,0F6h,0DBh,06Dh,0B6h
        defb    01Fh,0ECh,03Eh,0D8h,06Dh,0BEh,0DBh,01Dh
        defb    0B6h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,06Dh,0C7h,0DBh,0EFh,086h,0D8h,06Dh
        defb    0BCh,0DBh,078h,0B6h,0C0h,06Dh,0E0h,0DBh
        defb    0C0h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,080h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,07Fh
        defb    0E0h,03Fh,0C0h,01Fh,080h,00Fh,0C0h,007h
        defb    0E0h,003h,0F0h,001h,0F8h,000h,01Dh,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,0FFh,0C0h,07Fh,080h,03Fh
        defb    000h,07Eh,000h,0FCh,000h,0F8h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,00Fh,000h,00Fh,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,0E0h,000h,0C0h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,050h,000h
        defb    022h,003h,005h,007h,056h,0BBh,076h,007h
        defb    056h,003h,005h,000h,022h,000h,050h,003h
        defb    0C0h,00Fh,0F0h,01Ch,038h,03Bh,01Ch,037h
        defb    00Ch,036h,00Ch,034h,004h,034h,008h,030h
        defb    004h,034h,008h,030h,004h,030h,008h,038h
        defb    014h,01Ch,028h,00Eh,0D0h,003h,040h,003h
        defb    0C0h,007h,0E0h,00Fh,0F0h,00Ch,030h,019h
        defb    018h,01Bh,018h,01Bh,018h,01Ah,008h,018h
        defb    010h,01Ah,008h,018h,010h,018h,008h,00Ch
        defb    030h,00Fh,050h,007h,0A0h,003h,040h,001h
        defb    080h,003h,0C0h,007h,0E0h,00Eh,070h,01Ch
        defb    038h,039h,01Ch,073h,00Eh,0E7h,007h,0E0h
        defb    005h,070h,00Ah,038h,014h,01Ch,028h,00Eh
        defb    050h,006h,0A0h,003h,040h,001h,080h,001h
        defb    080h,003h,040h,007h,0A0h,00Fh,050h,01Fh
        defb    0A8h,03Fh,054h,07Fh,0AAh,0FFh,055h,0AAh
        defb    001h,055h,002h,02Ah,004h,015h,008h,00Ah
        defb    010h,005h,020h,002h,040h,001h,080h,00Fh
        defb    0D0h,008h,010h,000h,000h,017h,0E8h,02Fh
        defb    0F4h,02Fh,0E8h,02Fh,0D4h,000h,000h,05Fh
        defb    0EAh,05Fh,0F4h,05Fh,0EAh,05Fh,0F4h,05Fh
        defb    0EAh,05Fh,0F4h,05Fh,0EAh,02Fh,0D4h,000h
        defb    000h,081h,002h,06Dh,06Ch,04Bh,0A4h,01Ch
        defb    070h,07Fh,0FCh,05Eh,0F4h,02Dh,068h,0EDh
        defb    06Eh,02Dh,068h,05Eh,0F4h,07Fh,0FCh,01Ch
        defb    070h,04Bh,0A4h,06Dh,06Ch,081h,002h,000h
        defb    000h,0FFh,0FFh,03Fh,0FFh,055h,055h,000h
        defb    000h,0AAh,0AAh,055h,055h,0AAh,0AAh,055h
        defb    055h,0AAh,0AAh,055h,055h,000h,000h,0FFh
        defb    0FFh,03Fh,0FFh,055h,055h,000h,000h,07Fh
        defb    0FEh,07Fh,0FCh,060h,006h,06Dh,0B4h,069h
        defb    026h,069h,024h,060h,006h,06Fh,0F4h,06Ch
        defb    006h,060h,004h,06Dh,0B6h,069h,024h,069h
        defb    026h,060h,004h,07Fh,0FEh,055h,054h,072h
        defb    0AEh,065h,04Ch,072h,0AEh,065h,04Ch,072h
        defb    0AEh,065h,04Ch,072h,0AEh,065h,04Ch,072h
        defb    0AEh,065h,04Ch,072h,0AEh,065h,04Ch,072h
        defb    0AEh,065h,04Ch,052h,0AAh,045h,048h,000h
        defb    000h,07Eh,0F8h,09Bh,0F5h,0C7h,0FEh,070h
        defb    07Dh,0FFh,06Eh,07Fh,01Dh,0EFh,07Eh,0FEh
        defb    0FDh,0BFh,0FEh,07Fh,0FDh,0DDh,0F4h,0FFh
        defb    0F9h,06Fh,0FEh,0BFh,0FDh,0FDh,0FEh,0BFh
        defb    0FDh,0DDh,0FAh,0FBh,0FDh,07Fh,0FAh,01Fh
        defb    0FCh,06Eh,0F8h,0FFh,0F5h,0F9h,0FAh,0EFh
        defb    0FDh,0BFh,0FAh,07Bh,0FCh,0FFh,0FAh,09Fh
        defb    0FDh,07Fh,0FAh,0FBh,0FDh,0BFh,0FAh,0BFh
        defb    0DDh,0DFh,0FAh,0FFh,0F5h,077h,0EAh,0BFh
        defb    0FCh,0EFh,0FAh,0F8h,0FCh,0FFh,0BAh,0AFh
        defb    0F9h,0FFh,0FAh,07Eh,0FDh,07Fh,0FAh,09Fh
        defb    0F5h,0FFh,0EAh,0F7h,0FDh,07Fh,0FAh,0EFh
        defb    0FDh,07Eh,0F8h,09Bh,0F5h,0C7h,0FEh,070h
        defb    07Dh,0FFh,06Eh,07Fh,01Dh,0EFh,07Eh,0FEh
        defb    0FDh,0BFh,0FEh,07Fh,0FDh,0DDh,0F4h,0FFh
        defb    0F9h,06Fh,0FEh,0BFh,0FDh,0FDh,0FEh,0BFh
        defb    0DDh,0DFh,0FAh,0FFh,0F5h,077h,0EAh,0BFh
        defb    0FCh,0EFh,0FAh,0F8h,0FCh,0FFh,0BAh,0AFh
        defb    0F9h,0FFh,0FAh,07Eh,0FDh,07Fh,0FAh,09Fh
        defb    0F5h,0FFh,0EAh,0F4h,00Dh,000h,000h,000h
        defb    000h,000h,000h,000h,001h,000h,003h,000h
        defb    006h,000h,004h,000h,004h,000h,00Ch,000h
        defb    039h,000h,033h,000h,0F7h,003h,0F6h,007h
        defb    09Eh,03Eh,07Ah,07Dh,0E6h,0E1h,0C3h,000h
        defb    000h,0A0h,002h,090h,012h,02Ah,046h,060h
        defb    05Bh,072h,00Dh,06Eh,0F5h,0E6h,0E6h,0C6h
        defb    066h,00Ch,063h,05Dh,071h,018h,065h,030h
        defb    0E3h,065h,0CBh,0D1h,0A3h,0C1h,083h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,080h,000h,0C0h,000h,060h
        defb    000h,030h,000h,0BEh,000h,09Ah,000h,09Bh
        defb    060h,070h,0FCh,06Ah,0C7h,0C0h,0D3h,000h
        defb    000h,0FFh,0FFh,07Fh,0F5h,000h,000h,00Fh
        defb    0C0h,000h,000h,007h,080h,003h,000h,0C3h
        defb    000h,0C3h,000h,0DDh,000h,0CEh,000h,0D7h
        defb    000h,0DFh,000h,0C0h,000h,0C0h,000h,000h
        defb    000h,0FFh,0FFh,055h,056h,000h,000h,003h
        defb    0F0h,000h,000h,001h,0E0h,000h,0C0h,000h
        defb    0C3h,000h,0C2h,000h,0BBh,000h,072h,000h
        defb    0EBh,000h,0FAh,000h,003h,000h,002h,007h
        defb    000h,01Fh,078h,03Fh,034h,07Fh,07Ah,07Fh
        defb    034h,0FFh,07Ah,0FFh,034h,0FEh,07Ah,000h
        defb    034h,045h,07Ah,06Fh,0F4h,06Fh,0FAh,06Fh
        defb    0F4h,06Fh,0FAh,06Fh,0F4h,06Fh,0FAh,000h
        defb    0E0h,02Eh,0F8h,06Eh,0FCh,06Eh,0FEh,06Eh
        defb    0FEh,06Eh,0FFh,06Eh,0FFh,06Eh,07Fh,06Eh
        defb    000h,06Eh,0AAh,06Fh,0D4h,06Fh,0EAh,06Fh
        defb    0F4h,06Fh,0EAh,06Fh,0F4h,06Fh,0EAh,06Fh
        defb    0F4h,06Fh,0EAh,06Fh,0F4h,06Fh,0EAh,06Fh
        defb    0F4h,06Fh,0EAh,06Fh,0F4h,06Fh,0EAh,06Fh
        defb    0F4h,06Fh,0EAh,06Fh,0F4h,06Fh,0EAh,06Fh
        defb    0F4h,06Fh,0EAh,06Fh,0F4h,06Fh,0EAh,000h
        defb    000h,0FFh,0FFh,080h,000h,095h,055h,0AAh
        defb    0AAh,095h,055h,0AAh,0AAh,095h,055h,0AAh
        defb    0AAh,095h,055h,0AAh,0AAh,095h,055h,0AAh
        defb    0AAh,095h,055h,0AAh,0AAh,095h,055h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    01Fh,000h,000h,000h,03Fh,000h,000h,000h
        defb    07Fh,000h,07Fh,000h,070h,000h,078h,000h
        defb    07Ch,000h,07Eh,000h,0FFh,01Fh,0FDh,000h
        defb    000h,000h,000h,000h,000h,000h,000h,0A8h
        defb    000h,000h,000h,0D4h,000h,000h,000h,0EAh
        defb    000h,0F4h,000h,00Ah,000h,014h,000h,02Ah
        defb    000h,074h,000h,0EAh,000h,055h,0F8h,000h
        defb    000h,0FFh,0FDh,0F3h,0CAh,0F3h,0CDh,0F3h
        defb    0CAh,0E1h,0CDh,0DEh,0CAh,0E1h,0CDh,0F3h
        defb    0CAh,0F3h,085h,0F3h,07Ah,0F3h,085h,0F3h
        defb    0CAh,0F3h,0C5h,0FFh,0EAh,000h,000h,00Eh
        defb    0C0h,03Eh,050h,07Eh,0ACh,0FEh,055h,000h
        defb    000h,0FFh,0FFh,07Fh,0FCh,00Fh,0E0h,000h
        defb    000h,077h,0C0h,0EFh,0BAh,05Fh,000h,000h
        defb    000h,07Bh,000h,0FBh,06Ah,07Bh,000h,006h
        defb    0E0h,01Fh,0F8h,03Eh,0F4h,07Fh,0FAh,000h
        defb    000h,0FEh,0FDh,0FFh,0FAh,0FDh,0F5h,0F7h
        defb    0FAh,05Fh,0F5h,0FFh,0EAh,000h,000h,07Fh
        defb    0EAh,03Fh,0D4h,01Fh,068h,006h,0A0h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,007h
        defb    0E0h,004h,020h,070h,00Ah,075h,06Ch,072h
        defb    0AAh,070h,00Eh,004h,020h,006h,0A0h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,003h,0C0h,001h,080h,000h,000h,007h
        defb    0E0h,004h,020h,070h,00Ah,075h,06Ch,072h
        defb    0AAh,070h,00Eh,004h,020h,006h,0A0h,000h
        defb    000h,001h,080h,003h,0C0h,000h,000h,000h
        defb    000h,003h,040h,003h,080h,003h,040h,000h
        defb    000h,00Dh,0B0h,009h,000h,009h,090h,009h
        defb    000h,009h,090h,00Dh,030h,000h,000h,003h
        defb    040h,003h,080h,003h,040h,000h,000h,037h
        defb    0F4h,06Fh,0FAh,06Fh,0FAh,06Fh,0F4h,06Fh
        defb    0FAh,06Fh,0F4h,040h,002h,037h,0F4h,037h
        defb    0E8h,037h,0F4h,037h,0E8h,037h,0F4h,037h
        defb    0E8h,037h,0F4h,037h,0E8h,037h,0F4h,037h
        defb    0E8h,037h,0F4h,037h,0E8h,037h,0F4h,037h
        defb    0E8h,037h,0F4h,037h,0E8h,037h,0F4h,037h
        defb    0E8h,037h,0D4h,037h,0E8h,037h,0D4h,037h
        defb    0E8h,037h,0D4h,037h,0A8h,037h,054h,000h
        defb    000h,0DFh,0FFh,0DFh,0F5h,000h,000h,077h
        defb    0EAh,000h,000h,01Bh,0E8h,01Bh,0F0h,01Bh
        defb    0E8h,01Bh,0F0h,01Bh,0E8h,01Bh,0F0h,01Bh
        defb    0E8h,000h,000h,077h,0EAh,0EFh,055h,04Fh
        defb    0F4h,0F3h,0F9h,03Ch,0F5h,0CFh,039h,073h
        defb    0CCh,028h,0F0h,035h,03Ch,02Ah,08Fh,035h
        defb    057h,02Ah,0ABh,035h,053h,06Ah,0ABh,0D5h
        defb    053h,000h,000h,0FFh,0FFh,03Fh,0FCh,000h
        defb    000h,080h,000h,0B0h,000h,0B8h,000h,078h
        defb    000h,020h,000h,00Ch,000h,03Ch,000h,05Ch
        defb    000h,060h,000h,078h,000h,070h,000h,040h
        defb    000h,000h,000h,000h,000h,000h,000h,0C0h
        defb    003h,0FFh,0FFh,000h,000h,06Fh,0F6h,04Bh
        defb    0D4h,06Fh,0F6h,04Fh,0F4h,06Fh,0F6h,04Fh
        defb    0F4h,06Fh,0F6h,04Fh,0F4h,06Fh,0F6h,04Fh
        defb    0F4h,06Bh,0D6h,04Fh,0F4h,06Fh,0F6h,000h
        defb    000h,000h,001h,000h,00Dh,000h,01Dh,000h
        defb    01Eh,000h,004h,000h,030h,000h,03Ch,000h
        defb    03Ah,000h,006h,000h,01Eh,000h,00Eh,000h
        defb    002h,000h,000h,000h,000h,000h,000h,02Fh
        defb    0F2h,09Fh,0CFh,0AFh,03Ch,09Ch,0F3h,033h
        defb    0CEh,00Fh,014h,03Ch,0ACh,0F1h,054h,0EAh
        defb    0ACh,0D5h,054h,0CAh,0ACh,0D5h,056h,0CAh
        defb    0ABh,000h,000h,0FFh,0FFh,03Fh,0FCh,06Fh
        defb    0F6h,04Fh,0F4h,06Bh,0D6h,04Fh,0F4h,06Fh
        defb    0F6h,04Fh,0F4h,06Fh,0F6h,04Fh,0F4h,06Fh
        defb    0F6h,04Fh,0F4h,06Fh,0F6h,04Bh,0D4h,06Fh
        defb    0F6h,000h,000h,0FFh,0FFh,0C0h,003h,000h
        defb    000h,07Fh,0FFh,05Fh,0FFh,060h,000h,060h
        defb    003h,060h,00Ch,06Ch,030h,063h,000h,060h
        defb    0C0h,06Ch,030h,060h,00Ch,060h,003h,060h
        defb    000h,05Fh,0FFh,055h,055h,000h,000h,000h
        defb    000h,0FFh,0FFh,0FFh,0FFh,000h,000h,0C0h
        defb    003h,030h,00Ch,00Ch,030h,003h,000h,000h
        defb    0C0h,00Ch,030h,030h,00Ch,0C0h,003h,000h
        defb    000h,0FFh,0FFh,055h,055h,000h,000h,000h
        defb    000h,0FFh,0FEh,0FFh,0FAh,000h,006h,0C0h
        defb    006h,030h,006h,00Ch,034h,000h,0C6h,003h
        defb    004h,00Ch,032h,030h,004h,0C0h,002h,000h
        defb    004h,0FFh,0FAh,055h,054h,000h,000h,000h
        defb    000h,07Fh,0FEh,05Fh,0F8h,060h,006h,062h
        defb    044h,062h,046h,061h,004h,061h,006h,060h
        defb    084h,060h,086h,062h,044h,062h,046h,064h
        defb    024h,064h,026h,068h,014h,068h,016h,068h
        defb    014h,068h,016h,064h,024h,064h,026h,062h
        defb    044h,062h,046h,061h,004h,061h,006h,060h
        defb    084h,060h,086h,062h,044h,062h,046h,064h
        defb    024h,064h,026h,068h,014h,068h,016h,068h
        defb    014h,068h,016h,064h,024h,064h,026h,062h
        defb    044h,062h,046h,060h,084h,060h,086h,061h
        defb    004h,061h,006h,062h,044h,062h,046h,060h
        defb    004h,05Fh,0AAh,07Dh,054h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    001h,000h,001h,000h,001h,000h,000h,000h
        defb    000h,000h,004h,000h,008h,000h,010h,000h
        defb    010h,000h,020h,000h,020h,000h,020h,020h
        defb    000h,040h,000h,080h,000h,080h,000h,008h
        defb    000h,004h,000h,002h,000h,083h,000h,0C1h
        defb    000h,041h,000h,061h,000h,021h,000h,032h
        defb    000h,018h,000h,00Ch,000h,034h,000h,000h
        defb    020h,000h,013h,000h,01Ah,000h,00Ch,000h
        defb    036h,000h,076h,000h,063h,000h,0C3h,000h
        defb    0C3h,000h,0C6h,000h,0AEh,000h,0E4h,000h
        defb    0D0h,000h,068h,000h,074h,000h,0BDh,0C6h
        defb    000h,006h,000h,002h,000h,003h,000h,002h
        defb    000h,003h,000h,002h,000h,007h,000h,006h
        defb    000h,00Dh,000h,00Ah,000h,01Eh,000h,034h
        defb    000h,07Ch,000h,0E8h,000h,0F0h,000h,003h
        defb    0BBh,00Fh,0D7h,01Fh,0EFh,01Fh,0EFh,03Fh
        defb    09Fh,03Fh,03Fh,03Eh,07Fh,01Eh,0FFh,01Ah
        defb    0FEh,00Dh,07Dh,00Bh,0BEh,007h,0BDh,00Fh
        defb    0B2h,01Fh,069h,07Eh,016h,0E8h,0C0h,0D0h
        defb    000h,0F3h,000h,0A5h,0C0h,0A9h,0A0h,0D7h
        defb    050h,08Fh,0A0h,057h,0D0h,04Fh,0E8h,04Fh
        defb    0D0h,0ABh,0E8h,0A5h,0D0h,052h,0E8h,0A9h
        defb    090h,054h,060h,0AAh,090h,041h,05Ah,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,004h,0C0h
        defb    000h,0E0h,000h,014h,000h,077h,000h,014h
        defb    000h,0E0h,000h,0C0h,000h,000h,000h,030h
        defb    000h,038h,000h,005h,000h,01Dh,0C0h,005h
        defb    000h,038h,000h,030h,000h,000h,000h,00Ch
        defb    000h,00Eh,000h,001h,040h,007h,070h,001h
        defb    040h,00Eh,000h,00Ch,000h,000h,000h,003h
        defb    000h,003h,080h,000h,050h,001h,0DCh,000h
        defb    050h,003h,080h,003h,000h,000h,000h,000h
        defb    000h,003h,000h,007h,000h,028h,000h,0EEh
        defb    000h,028h,000h,007h,000h,003h,000h,000h
        defb    000h,000h,0C0h,001h,0C0h,00Ah,000h,03Bh
        defb    080h,00Ah,000h,001h,0C0h,000h,0C0h,000h
        defb    000h,000h,030h,000h,070h,002h,080h,00Eh
        defb    0E0h,002h,080h,000h,070h,000h,030h,000h
        defb    000h,000h,00Ch,000h,01Ch,000h,0A0h,003h
        defb    0B8h,000h,0A0h,000h,01Ch,000h,00Ch,01Dh
        defb    010h,07Bh,084h,07Eh,0A1h,0FDh,048h,0FEh
        defb    081h,0FDh,050h,03Ah,082h,035h,008h,007h
        defb    040h,05Eh,0E2h,01Fh,0A0h,0BFh,054h,03Fh
        defb    0A0h,03Fh,052h,00Eh,0A4h,02Dh,040h,001h
        defb    0D4h,027h,0B8h,007h,0E9h,04Fh,0D4h,00Fh
        defb    0E8h,02Fh,0D5h,003h,0A8h,003h,050h,000h
        defb    074h,045h,0EEh,011h,0FAh,003h,0F5h,0ABh
        defb    0FAh,003h,0F5h,008h,0EAh,012h,0D4h,008h
        defb    000h,049h,000h,01Ch,000h,0FFh,080h,01Ch
        defb    000h,01Ch,000h,049h,000h,008h,000h,002h
        defb    000h,012h,040h,017h,040h,02Dh,0A0h,007h
        defb    000h,007h,080h,012h,040h,002h,000h,000h
        defb    080h,006h,090h,001h,0C0h,00Eh,0D8h,001h
        defb    080h,003h,0C8h,004h,090h,000h,080h,000h
        defb    020h,001h,028h,000h,070h,003h,0EEh,000h
        defb    030h,001h,074h,000h,020h,000h,020h,018h
        defb    000h,042h,000h,018h,000h,0BDh,000h,0BDh
        defb    000h,018h,000h,042h,000h,018h,000h,006h
        defb    000h,010h,080h,006h,000h,02Fh,040h,02Fh
        defb    040h,006h,000h,010h,080h,006h,000h,001h
        defb    080h,004h,020h,001h,080h,00Bh,0D0h,00Bh
        defb    0D0h,001h,080h,004h,020h,001h,080h,000h
        defb    060h,001h,008h,000h,060h,002h,0F4h,002h
        defb    0F4h,000h,060h,001h,008h,000h,060h,03Ch
        defb    000h,04Eh,000h,0BFh,000h,0BFh,000h,0FFh
        defb    000h,0FFh,000h,07Eh,000h,03Ch,000h,00Fh
        defb    000h,013h,080h,02Fh,0C0h,02Fh,0C0h,03Fh
        defb    0C0h,03Fh,0C0h,01Fh,080h,00Fh,000h,000h
        defb    000h,003h,0C0h,006h,0E0h,005h,0E0h,007h
        defb    0E0h,007h,0E0h,003h,0C0h,000h,000h,000h
        defb    000h,000h,0F0h,001h,0B8h,001h,078h,001h
        defb    0F8h,001h,0F8h,000h,0F0h,000h,000h,014h
        defb    000h,040h,000h,015h,000h,088h,000h,054h
        defb    000h,081h,000h,024h,000h,008h,000h,005h
        defb    000h,010h,000h,005h,040h,022h,000h,015h
        defb    000h,020h,040h,009h,000h,002h,000h,001h
        defb    040h,004h,000h,001h,050h,008h,080h,005h
        defb    040h,008h,010h,002h,040h,000h,080h,000h
        defb    050h,001h,000h,000h,054h,002h,020h,001h
        defb    050h,002h,004h,000h,090h,000h,020h,010h
        defb    000h,004h,000h,028h,000h,052h,000h,008h
        defb    000h,050h,000h,004h,000h,000h,000h,004h
        defb    000h,001h,000h,00Ah,000h,014h,080h,002h
        defb    000h,014h,000h,001h,000h,000h,000h,001h
        defb    000h,000h,040h,002h,080h,005h,020h,000h
        defb    080h,005h,000h,000h,040h,000h,000h,000h
        defb    040h,000h,010h,000h,0A0h,001h,048h,000h
        defb    020h,001h,040h,000h,010h,000h,000h,000h
        defb    000h,008h,000h,000h,000h,02Ah,000h,010h
        defb    000h,008h,000h,000h,000h,000h,000h,000h
        defb    000h,002h,000h,000h,000h,00Ah,080h,004h
        defb    000h,002h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,080h,000h,000h,002h,0A0h,001h
        defb    000h,000h,080h,000h,000h,000h,000h,000h
        defb    000h,000h,020h,000h,000h,000h,0A8h,000h
        defb    040h,000h,020h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,03Eh
        defb    000h,041h,000h,09Ch,000h,0A2h,000h,0AAh
        defb    000h,092h,000h,042h,000h,03Ch,000h,00Fh
        defb    000h,010h,080h,026h,040h,029h,040h,025h
        defb    040h,021h,040h,01Eh,040h,000h,080h,003h
        defb    0C0h,004h,020h,004h,090h,005h,050h,004h
        defb    050h,003h,090h,008h,020h,007h,0C0h,001h
        defb    000h,002h,078h,002h,084h,002h,0A4h,002h
        defb    094h,002h,064h,001h,008h,000h,0F0h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,08Ch
        defb    08Ch,08Ch,08Ch,08Ch,08Ch,08Ch,08Ch,08Ch
        defb    08Ch,08Ch,08Ch,08Ch,08Ch,08Ch,08Ch,08Ch
        defb    08Ch,08Ch,04Fh,0FEh,006h,016h,04Fh,0FEh
        defb    04Fh,0FEh,0B4h,0FFh,04Dh,0FFh,05Fh,015h
        defb    07Eh,00Ah,070h,0FFh,05Fh,015h,00Ch,001h
        defb    05Fh,015h,05Fh,015h,037h,00Ch,08Ch,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,013h
        defb    004h,000h,003h,001h,002h,013h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,013h,003h,002h,004h
        defb    000h,003h,013h,0A5h,0A5h,013h,048h,0A5h
        defb    0A5h,013h,002h,001h,003h,001h,004h,013h
        defb    0A5h,0A5h,013h,0ABh,0A5h,0A5h,013h,001h
        defb    000h,002h,002h,000h,013h,0A5h,0A5h,013h
        defb    0ABh,0A5h,0A5h,013h,000h,004h,001h,003h
        defb    001h,013h,0A5h,0A5h,013h,0ABh,0A5h,0A5h
        defb    013h,004h,003h,000h,004h,002h,013h,0A5h
        defb    0A5h,013h,047h,0A5h,0A5h,013h,003h,002h
        defb    004h,000h,003h,013h,0A5h,0A5h,013h,013h
        defb    0A5h,0A5h,013h,002h,001h,003h,000h,004h
        defb    013h,0A5h,0A5h,013h,013h,0A5h,0A5h,013h
        defb    001h,000h,002h,001h,000h,013h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,013h,000h,004h,003h
        defb    002h,001h,013h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,04Ah,014h,014h,014h,014h,014h,048h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,003h
        defb    000h,040h,003h,000h,050h,003h,000h,060h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,003h
        defb    003h,017h,060h,003h,000h,006h,060h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,013h
        defb    004h,000h,003h,001h,002h,013h,0A6h,0A5h
        defb    013h,013h,0A5h,0A5h,013h,003h,002h,004h
        defb    000h,003h,013h,0A5h,0A5h,013h,048h,0A5h
        defb    0A5h,013h,002h,001h,003h,001h,004h,013h
        defb    0A5h,0A5h,013h,0ABh,0A5h,0A5h,013h,001h
        defb    000h,002h,002h,000h,013h,0A5h,0A5h,013h
        defb    0ABh,0A5h,0A5h,013h,000h,004h,001h,003h
        defb    001h,013h,0A5h,0A5h,013h,0ABh,0A5h,0A5h
        defb    013h,004h,003h,000h,004h,002h,013h,0A5h
        defb    0A5h,013h,047h,0A5h,0A5h,013h,003h,002h
        defb    004h,000h,003h,013h,0A5h,0A5h,013h,013h
        defb    0A5h,0A5h,013h,002h,001h,003h,000h,004h
        defb    013h,0A5h,0A5h,013h,013h,0A5h,0A5h,013h
        defb    001h,000h,002h,001h,000h,013h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,013h,000h,004h,003h
        defb    002h,001h,013h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,04Ah,014h,014h,014h,014h,014h,048h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,049h,014h,014h,014h,047h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,013h,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,013h,0A5h,0A5h,0A5h,013h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    013h,08Bh,0A5h,0A5h,013h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,0A5h,0A5h,013h,0A5h,0A5h
        defb    0A5h,04Ah,014h,014h,014h,014h,013h,013h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,047h
        defb    0A9h,0A9h,0A9h,049h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,004h,000h,001h
        defb    002h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,003h,002h,003h,003h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,002h
        defb    001h,004h,004h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,001h,000h,000h,000h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,000h,004h,001h,001h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,004h,003h
        defb    002h,002h,013h,01Fh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,003h,002h,003h,003h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    002h,001h,004h,004h,013h,01Fh,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,001h,000h,000h
        defb    000h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,000h,003h,002h,001h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,014h,014h
        defb    014h,014h,014h,048h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,0ABh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    0ABh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,0ABh,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,00Fh,0A8h
        defb    0A8h,0A8h,0A5h,00Fh,013h,0A5h,0A5h,013h
        defb    002h,001h,000h,013h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,070h,0A5h,013h,003h,003h,004h
        defb    013h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,013h,004h,002h,000h,013h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,013h,000h
        defb    001h,001h,013h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,012h,014h,014h,014h,010h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    0A5h,0A5h,011h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,013h,013h,0A5h,0A5h,013h
        defb    002h,001h,000h,004h,003h,002h,001h,000h
        defb    013h,013h,0A5h,0A5h,013h,003h,004h,000h
        defb    001h,002h,003h,004h,000h,013h,013h,0A5h
        defb    0A5h,012h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,049h,014h,014h,014h,047h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,013h,000h
        defb    001h,000h,013h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,013h,004h,002h,004h,013h
        defb    071h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    013h,003h,003h,003h,013h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,0A5h,0A5h,013h,002h,003h
        defb    002h,013h,072h,0A5h,0A5h,0A5h,013h,013h
        defb    0A5h,0A5h,013h,001h,003h,001h,013h,0A5h
        defb    0A5h,0A5h,0A5h,013h,010h,0A5h,0A5h,013h
        defb    000h,000h,000h,013h,073h,0A5h,0A5h,0A5h
        defb    013h,0ABh,0A5h,0A5h,013h,004h,000h,004h
        defb    013h,0A5h,0A5h,0A5h,0A5h,013h,0ABh,0A5h
        defb    0A5h,013h,003h,001h,003h,013h,074h,0A5h
        defb    0A5h,0A5h,013h,0ABh,0A5h,0A5h,013h,002h
        defb    001h,002h,013h,0A5h,0A5h,0A5h,0A5h,013h
        defb    00Fh,0A5h,0A5h,013h,001h,002h,001h,013h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    013h,000h,002h,000h,013h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,010h,0A8h,0A8h,0A8h,012h,014h
        defb    014h,014h,014h,00Fh,013h,000h,00Bh,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,033h,002h,000h,002h
        defb    013h,013h,001h,00Ch,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,034h,001h,001h,001h,013h,013h,002h
        defb    00Ch,0A5h,0A5h,0A5h,0A5h,0A5h,034h,000h
        defb    002h,000h,013h,013h,003h,00Ch,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,035h,004h,003h,004h,013h
        defb    013h,004h,00Eh,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    035h,003h,004h,003h,013h,013h,000h,00Eh
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,036h,002h,000h
        defb    002h,013h,013h,001h,00Dh,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,036h,001h,001h,001h,013h,013h
        defb    002h,00Ch,0A5h,0A5h,0A5h,0A5h,0A5h,033h
        defb    000h,002h,000h,013h,013h,003h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,04Ah,014h,014h,014h
        defb    013h,013h,004h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,000h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,001h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,002h,04Ah,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,013h,013h,003h,004h
        defb    000h,001h,002h,003h,004h,000h,001h,002h
        defb    003h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,000h,001h,002h
        defb    003h,004h,000h,001h,002h,003h,004h,000h
        defb    013h,013h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,010h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0AAh,013h,0A5h,0A5h,0A5h,011h
        defb    000h,002h,00Ch,0A5h,0A5h,0A5h,0A5h,0AAh
        defb    013h,0A5h,0A5h,0A5h,013h,002h,001h,00Eh
        defb    0A5h,0A5h,0A5h,0A5h,0AAh,013h,018h,0A5h
        defb    0A5h,013h,003h,00Dh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0AAh,013h,018h,018h,0A5h,013h,00Bh
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    076h,018h,018h,013h,028h,026h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,018h,018h,0A5h
        defb    013h,029h,027h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,018h,0A5h,0A5h,012h,014h,014h
        defb    00Fh,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    075h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,070h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,018h
        defb    018h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,018h,018h,018h,018h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    018h,075h,018h,018h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,018h,018h,018h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,018h,018h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,014h,014h,014h,014h,014h
        defb    014h,00Fh,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    014h,014h,014h,014h,014h,014h,010h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,000h,001h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,001h,000h,013h,03Ch,03Ah,03Ah
        defb    0A5h,03Ah,03Ah,03Ah,03Bh,013h,013h,002h
        defb    004h,013h,0A5h,0A5h,03Dh,0A5h,0A5h,041h
        defb    0A5h,0A5h,013h,013h,003h,003h,013h,03Ch
        defb    03Ah,03Ah,03Ah,0A5h,03Ah,03Ah,03Bh,013h
        defb    013h,004h,002h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0AAh,013h,000h,001h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0AAh,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,010h,0A8h,0A8h,0A8h
        defb    012h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    011h,014h,014h,014h,014h,014h,014h,013h
        defb    013h,0A5h,0A5h,0A5h,046h,013h,075h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,012h,014h,014h,014h,018h,018h
        defb    014h,013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    028h,026h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,029h,027h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,014h,014h,014h,014h,014h,014h
        defb    014h,00Fh,0A5h,0A5h,0A5h,013h,013h,001h
        defb    000h,004h,003h,002h,001h,000h,013h,045h
        defb    0A5h,0A5h,013h,013h,014h,014h,014h,014h
        defb    014h,014h,014h,010h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A6h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,010h,0A8h
        defb    0A8h,012h,014h,00Fh,013h,045h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,03Ch,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Ah,03Ah,03Ah,03Bh,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,03Dh,0A5h,0A5h,041h
        defb    0A5h,0A5h,013h,013h,03Ch,03Ah,03Ah,03Ah
        defb    03Ah,03Ah,0A5h,03Ah,03Ah,03Ah,03Bh,013h
        defb    013h,0A5h,0A5h,03Dh,0A5h,0A5h,041h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,03Ch,03Ah
        defb    03Ah,0A5h,03Ah,03Ah,03Ah,03Ah,03Ah,03Ah
        defb    03Bh,013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    018h,018h,018h,018h,00Fh,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h
        defb    0A5h,013h,0A5h,014h,014h,00Fh,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,013h,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,013h,013h,070h
        defb    0A5h,0A5h,0A5h,013h,045h,0A5h,0A5h,013h
        defb    01Fh,01Ch,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    013h,0A5h,0A5h,046h,013h,01Fh,01Ch,013h
        defb    013h,073h,0A5h,0A5h,0A5h,013h,0A5h,0A5h
        defb    0A5h,013h,01Fh,01Ch,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,013h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,010h,0A8h,0A8h,0A8h,012h
        defb    014h,014h,014h,00Fh,013h,000h,00Bh,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,034h,000h
        defb    013h,013h,004h,00Dh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,033h,004h,013h,013h,003h
        defb    00Eh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,031h
        defb    02Fh,003h,013h,013h,002h,00Ch,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,032h,030h,002h,013h
        defb    013h,001h,00Ch,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,034h,001h,013h,013h,000h,00Eh
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,033h
        defb    000h,013h,013h,004h,00Dh,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,035h,004h,013h,013h
        defb    003h,000h,071h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,036h,003h,013h,013h,002h,000h,000h
        defb    072h,0A5h,0A5h,0A5h,0A5h,0A5h,036h,002h
        defb    013h,013h,001h,000h,001h,002h,074h,0A5h
        defb    0A5h,0A5h,0A5h,034h,001h,013h,013h,000h
        defb    000h,001h,002h,003h,00Dh,0A5h,0A5h,0A5h
        defb    035h,000h,013h,013h,000h,001h,002h,003h
        defb    004h,000h,00Fh,0A5h,0A5h,011h,014h,013h
        defb    013h,000h,001h,001h,000h,004h,001h,013h
        defb    0A5h,0A5h,013h,0A5h,013h,013h,000h,004h
        defb    003h,002h,003h,002h,013h,0A5h,0A5h,013h
        defb    0A7h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,0A8h,0A8h,0A8h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    013h,0A5h,0A5h,0A5h,013h,000h,001h,002h
        defb    013h,013h,014h,014h,014h,013h,0A5h,0A5h
        defb    0A5h,013h,002h,000h,003h,013h,013h,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,013h,001h
        defb    000h,004h,013h,013h,014h,014h,014h,013h
        defb    0A5h,0A5h,0A5h,012h,014h,014h,014h,013h
        defb    013h,0A5h,0A5h,0A5h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,014h,014h
        defb    014h,013h,0A5h,0A5h,096h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,0A5h,0A5h,0A5h,013h,091h
        defb    090h,097h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    014h,014h,014h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,014h,014h,014h,013h,0A5h,0A5h
        defb    0A5h,011h,014h,014h,014h,013h,013h,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,013h,000h
        defb    002h,003h,013h,013h,014h,014h,014h,013h
        defb    0A5h,0A5h,0A5h,013h,001h,001h,004h,013h
        defb    013h,0A5h,0A5h,0A5h,013h,0A5h,0A5h,0A5h
        defb    013h,002h,000h,000h,013h,013h,0A5h,0A5h
        defb    0A5h,013h,0A5h,0A5h,0A5h,013h,003h,004h
        defb    001h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,000h,001h,002h
        defb    003h,004h,001h,002h,00Bh,0A5h,0A5h,0A5h
        defb    013h,013h,001h,000h,003h,002h,000h,000h
        defb    00Bh,0A5h,0A5h,0A5h,0A5h,012h,013h,002h
        defb    003h,004h,001h,001h,00Dh,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0AAh,013h,003h,003h,000h,000h
        defb    00Eh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0AAh
        defb    013h,004h,002h,001h,00Dh,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0AAh,013h,000h,001h
        defb    00Bh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,011h,013h,001h,000h,00Dh,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    002h,045h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,003h,00Bh,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,004h,045h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,014h
        defb    014h,014h,00Fh,0A5h,0A5h,0A5h,011h,014h
        defb    014h,014h,013h,013h,004h,003h,002h,013h
        defb    0A5h,0A5h,0A5h,013h,002h,001h,000h,013h
        defb    013h,000h,002h,001h,013h,0A5h,0A5h,0A5h
        defb    013h,003h,004h,000h,013h,013h,000h,001h
        defb    000h,013h,0A5h,0A5h,0A5h,013h,002h,001h
        defb    000h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,000h,004h,003h
        defb    002h,001h,000h,013h,070h,013h,0A5h,0A5h
        defb    013h,013h,014h,014h,014h,014h,014h,014h
        defb    010h,0A5h,013h,08Bh,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,0A5h,046h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,0A5h,0A5h,013h,013h,014h,014h
        defb    014h,014h,0A5h,014h,014h,014h,010h,0A5h
        defb    0A5h,013h,013h,045h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    03Ch,03Ah,03Ah,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Ah,03Bh,013h,013h,013h,0A5h,0A5h
        defb    03Dh,0A5h,0A5h,041h,0A5h,0A5h,0A5h,013h
        defb    013h,013h,03Ch,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Ah,03Ah,03Ah,03Bh,013h,013h,013h
        defb    0A5h,0A5h,0A5h,0A5h,03Dh,0A5h,0A5h,041h
        defb    0A5h,013h,013h,013h,03Ch,03Ah,03Ah,03Ah
        defb    03Ah,03Ah,03Ah,0A5h,03Ah,03Ah,03Bh,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,00Fh,0A9h
        defb    0A9h,0A9h,011h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,01Fh,0A5h,0A5h
        defb    013h,0A5h,0A5h,0A5h,013h,0A5h,0A5h,01Ch
        defb    013h,013h,01Fh,0A5h,0A5h,013h,0A5h,018h
        defb    0A5h,013h,0A5h,0A5h,01Ch,013h,013h,01Fh
        defb    0A5h,0A5h,012h,018h,018h,018h,010h,0A5h
        defb    0A5h,01Ch,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,018h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,071h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,014h,014h
        defb    014h,014h,047h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,001h,002h,001h,002h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,046h,013h,013h
        defb    000h,003h,000h,003h,013h,045h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,001h,004h,000h
        defb    004h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,046h
        defb    013h,04Ah,014h,014h,014h,014h,048h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,051h,013h,0ABh,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,052h,013h,0ABh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    0ABh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,047h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,04Ah,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,000h,003h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,001h,002h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,049h,014h,047h,0A5h,013h
        defb    002h,001h,013h,013h,045h,0A5h,0A5h,0A5h
        defb    013h,003h,013h,0A5h,013h,003h,000h,013h
        defb    013h,071h,0A5h,0A5h,0A5h,013h,002h,013h
        defb    0A5h,013h,004h,004h,013h,013h,0A5h,0A5h
        defb    0A5h,046h,013h,001h,013h,0A5h,013h,000h
        defb    003h,013h,013h,073h,0A5h,0A5h,0A5h,013h
        defb    000h,013h,0A5h,013h,001h,002h,013h,013h
        defb    045h,0A5h,0A5h,0A5h,013h,001h,013h,0A5h
        defb    013h,002h,001h,013h,013h,072h,0A5h,0A5h
        defb    0A5h,013h,000h,013h,0A5h,013h,003h,000h
        defb    013h,013h,0A5h,0A5h,0A5h,046h,013h,004h
        defb    013h,0A5h,012h,014h,014h,013h,013h,074h
        defb    0A5h,0A5h,0A5h,013h,003h,013h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,045h,0A5h,0A5h,0A5h
        defb    013h,002h,013h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,013h,001h,013h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,013h,000h,013h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,00Fh,0A9h,0A9h,0A9h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A6h,0A5h,0A5h
        defb    0A5h,013h,002h,001h,000h,004h,003h,002h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,013h,003h
        defb    000h,001h,002h,003h,001h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,013h,004h,000h,001h,000h
        defb    004h,000h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    012h,014h,014h,014h,014h,014h,014h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,03Ch,03Ah
        defb    03Ah,03Ah,0A5h,03Ah,03Ah,03Ah,03Ah,03Ah
        defb    03Bh,013h,013h,077h,0A5h,0A5h,0A5h,03Dh
        defb    0A5h,0A5h,041h,0A5h,0A5h,0A5h,013h,013h
        defb    03Ch,03Ah,03Ah,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Ah,03Bh,013h,013h,077h,0A5h,0A5h
        defb    0A5h,03Dh,0A5h,0A5h,041h,0A5h,0A5h,0A5h
        defb    013h,013h,03Ch,03Ah,03Ah,03Ah,03Ah,0A5h
        defb    03Ah,03Ah,03Ah,03Ah,03Bh,013h,013h,077h
        defb    0A5h,0A5h,0A5h,03Dh,0A5h,0A5h,041h,0A5h
        defb    0A5h,0A5h,013h,013h,03Ch,03Ah,03Ah,03Ah
        defb    03Ah,03Ah,03Ah,03Ah,0A5h,03Ah,03Bh,013h
        defb    013h,045h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,045h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,00Fh,0A9h,0A9h,0A9h
        defb    011h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,000h,013h,0A5h
        defb    0A5h,0A5h,013h,075h,0A5h,018h,0A5h,0A5h
        defb    013h,013h,014h,010h,0A5h,0A5h,0A5h,013h
        defb    0A5h,0A5h,018h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,0A5h,0A5h,018h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,076h,0A5h,018h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,011h,014h,014h,010h,0A5h
        defb    0A5h,018h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    013h,0A7h,0A5h,0A5h,0A5h,0A5h,013h,0A5h
        defb    0A5h,013h,013h,0A5h,0A5h,013h,075h,0A5h
        defb    0A5h,0A5h,0A5h,013h,0A5h,0A5h,013h,013h
        defb    0A5h,0A5h,012h,014h,014h,014h,014h,014h
        defb    010h,0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,014h,014h,014h,00Fh,0A5h,0A5h
        defb    0A5h,011h,014h,014h,014h,013h,013h,000h
        defb    002h,003h,013h,0A5h,0A5h,0A5h,013h,003h
        defb    004h,000h,013h,013h,001h,001h,004h,013h
        defb    0A5h,0A5h,0A5h,013h,002h,001h,001h,013h
        defb    013h,002h,000h,000h,013h,0A5h,0A5h,0A5h
        defb    013h,001h,000h,002h,013h,013h,003h,004h
        defb    001h,013h,0A5h,0A5h,0A5h,013h,000h,004h
        defb    003h,013h,012h,014h,014h,014h,014h,0A9h
        defb    0A9h,0A9h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,001h,002h,000h
        defb    013h,0A5h,0A5h,0A5h,013h,002h,001h,000h
        defb    013h,013h,000h,004h,004h,013h,0A5h,0A5h
        defb    0A5h,013h,000h,001h,002h,013h,013h,014h
        defb    014h,014h,010h,0A5h,0A5h,0A5h,012h,014h
        defb    014h,014h,013h,013h,045h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,046h,013h
        defb    013h,03Ch,03Ah,03Ah,03Ah,03Ah,03Ah,03Ah
        defb    03Ah,0A5h,03Ah,03Bh,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,03Dh,0A5h,0A5h,041h
        defb    0A5h,013h,013h,03Ch,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Ah,03Ah,03Ah,03Ah,03Bh,013h,013h
        defb    0A5h,03Dh,0A5h,0A5h,041h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,03Ch,03Ah,03Ah
        defb    03Ah,03Ah,03Ah,03Ah,0A5h,03Ah,03Ah,03Bh
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,03Dh
        defb    0A5h,0A5h,041h,0A5h,0A5h,013h,013h,03Ch
        defb    03Ah,03Ah,03Ah,03Ah,0A5h,03Ah,03Ah,03Ah
        defb    03Ah,03Bh,013h,013h,0A5h,0A5h,0A5h,03Dh
        defb    0A5h,0A5h,041h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,03Ch,03Ah,03Ah,0A5h,03Ah,03Ah,03Ah
        defb    03Ah,03Ah,03Ah,03Bh,013h,013h,045h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    046h,013h,012h,014h,014h,014h,014h,00Fh
        defb    0A9h,0A9h,0A9h,011h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,00Ch,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,00Bh,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,00Ch
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,00Bh,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,00Ch,0A5h,002h,003h,002h,001h,000h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,00Ch,0A5h
        defb    000h,00Bh,0A5h,034h,004h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,00Bh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    00Dh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,00Bh,0A5h,0A5h
        defb    0A5h,000h,001h,002h,003h,00Bh,0A5h,0A5h
        defb    013h,013h,000h,001h,002h,003h,004h,002h
        defb    045h,0A5h,0A5h,0A5h,0A5h,013h,013h,003h
        defb    002h,001h,000h,004h,003h,045h,0A5h,0A5h
        defb    0A5h,0A5h,013h,0ABh,0A5h,0A5h,0A5h,0A5h
        defb    004h,003h,002h,001h,00Eh,0A5h,0A5h,013h
        defb    0ABh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,0ABh,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,0A8h,0A8h,0A8h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,045h,0A5h,0A5h
        defb    0A5h,0A5h,033h,000h,000h,001h,003h,004h
        defb    013h,013h,045h,0A5h,0A5h,0A5h,0A5h,000h
        defb    002h,004h,002h,002h,004h,013h,013h,045h
        defb    0A5h,0A5h,0A5h,0A5h,036h,001h,003h,003h
        defb    001h,001h,013h,013h,000h,00Eh,0A5h,0A5h
        defb    0A5h,0A5h,033h,003h,004h,000h,002h,013h
        defb    013h,001h,00Bh,0A5h,0A5h,0A5h,034h,002h
        defb    002h,000h,004h,003h,013h,013h,003h,002h
        defb    00Dh,0A5h,0A5h,036h,001h,001h,001h,003h
        defb    004h,013h,013h,002h,004h,003h,00Eh,0A5h
        defb    035h,000h,000h,002h,002h,000h,013h,013h
        defb    001h,000h,004h,00Dh,0A5h,0A5h,033h,004h
        defb    003h,001h,001h,013h,013h,000h,001h,004h
        defb    000h,00Ch,0A5h,0A5h,035h,003h,000h,002h
        defb    013h,013h,004h,002h,003h,000h,001h,00Eh
        defb    0A5h,036h,002h,004h,003h,013h,013h,003h
        defb    003h,002h,001h,002h,00Dh,0A5h,0A5h,033h
        defb    000h,001h,013h,013h,002h,004h,001h,002h
        defb    000h,003h,00Eh,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,001h,000h,000h,003h,004h,004h,00Dh
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,000h,004h
        defb    003h,002h,001h,000h,000h,00Dh,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,010h,0A8h,0A8h,0A8h
        defb    012h,014h,014h,00Fh,013h,01Fh,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,045h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,01Fh
        defb    0A5h,0A5h,0A5h,0A5h,018h,018h,018h,0A5h
        defb    0A5h,051h,013h,013h,045h,0A5h,0A5h,0A5h
        defb    0A5h,018h,08Bh,018h,0A5h,0A5h,052h,013h
        defb    013h,01Fh,0A5h,0A5h,0A5h,0A5h,018h,018h
        defb    018h,0A5h,0A5h,0A5h,013h,013h,045h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,011h,014h,013h,013h
        defb    075h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,003h,013h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,011h,014h,002h,004h
        defb    013h,013h,014h,00Fh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,002h,001h,000h,013h,013h,000h
        defb    013h,0A5h,0A5h,0A5h,011h,014h,001h,003h
        defb    000h,001h,013h,013h,001h,013h,0A5h,0A5h
        defb    0A5h,013h,002h,003h,004h,004h,002h,013h
        defb    013h,002h,013h,0A5h,0A5h,0A5h,013h,001h
        defb    004h,000h,003h,003h,013h,013h,003h,013h
        defb    0A5h,0A5h,0A5h,013h,000h,000h,001h,002h
        defb    004h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,010h,0A8h
        defb    0A8h,0A8h,012h,00Fh,013h,018h,018h,018h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,018h,070h,018h,018h,018h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,018h
        defb    018h,018h,018h,018h,018h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,018h,08Bh,0A5h,0A5h
        defb    018h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,018h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,011h,014h,013h,013h,0A5h,018h
        defb    018h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    0A5h,013h,013h,0A5h,018h,0A5h,0A5h,0A5h
        defb    011h,014h,014h,014h,010h,0A5h,013h,013h
        defb    0A5h,018h,0A5h,0A5h,0A5h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,0B7h,018h,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A7h,018h,0A5h,0A5h,012h
        defb    014h,014h,00Fh,0A5h,0A5h,013h,013h,0A5h
        defb    0A7h,018h,018h,0A5h,0A5h,0A5h,0A5h,013h
        defb    0A5h,0A5h,013h,013h,014h,014h,014h,014h
        defb    00Fh,0A5h,0A5h,0A5h,013h,0A5h,0A5h,013h
        defb    013h,000h,003h,004h,002h,013h,0A5h,0A5h
        defb    0A5h,013h,0A5h,0A5h,013h,013h,001h,002h
        defb    000h,001h,013h,0A5h,0A5h,0A5h,013h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,010h,0A8h,0A8h,0A8h
        defb    012h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,046h
        defb    013h,013h,045h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,03Ch
        defb    03Ah,03Ah,0A5h,03Ah,03Ah,03Ah,03Ah,03Ah
        defb    03Ah,03Bh,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,03Dh,0A5h,0A5h,041h,0A5h,0A5h,013h
        defb    013h,03Ch,03Ah,03Ah,03Ah,03Ah,03Ah,0A5h
        defb    03Ah,03Ah,03Ah,03Bh,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,03Dh,0A5h,0A5h,041h,0A5h,0A5h
        defb    0A5h,013h,013h,03Ch,03Ah,03Ah,03Ah,03Ah
        defb    03Ah,03Ah,03Ah,0A5h,03Ah,03Bh,013h,013h
        defb    045h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,014h,00Fh,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,000h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,001h
        defb    003h,014h,014h,014h,014h,00Fh,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,002h,000h,004h,004h
        defb    000h,000h,013h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,003h,001h,000h,003h,001h,004h,013h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,004h,000h
        defb    001h,002h,002h,003h,013h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,048h,0A8h,0A8h,0A8h,04Ah
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,0A7h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,0A7h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,049h,014h,014h,013h,013h,0A7h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    002h,000h,013h,013h,014h,014h,014h,014h
        defb    047h,0A5h,0A5h,0A5h,013h,001h,001h,013h
        defb    013h,000h,003h,004h,002h,013h,0A5h,0A5h
        defb    0A5h,013h,000h,002h,013h,013h,001h,002h
        defb    000h,001h,013h,0A6h,0A5h,0A5h,013h,004h
        defb    003h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,048h,0A8h,0A8h,0A8h,04Ah
        defb    014h,014h,014h,00Fh,013h,00Ch,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,00Dh,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,00Ch
        defb    0A5h,0A5h,0A5h,049h,014h,014h,047h,0A5h
        defb    0A5h,0A5h,013h,013h,00Bh,0A5h,0A5h,0A5h
        defb    013h,0A5h,0A5h,013h,0A5h,0A5h,0A5h,013h
        defb    013h,00Eh,0A5h,0A5h,0A5h,013h,075h,0A5h
        defb    013h,0A5h,0A5h,0A5h,013h,013h,00Dh,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,013h,0A5h,0A5h
        defb    0A5h,013h,013h,00Ch,0A5h,0A5h,0A5h,013h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,013h,013h
        defb    00Bh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    0A5h,0A5h,0A5h,013h,013h,028h,026h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,0A5h,0A5h,0A5h
        defb    013h,013h,029h,027h,0A5h,049h,014h,014h
        defb    014h,048h,0A5h,0A5h,0A5h,013h,013h,00Bh
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,00Ch,0A5h,0A5h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,00Ch,0A5h,0A5h,013h,0A5h,0A5h,0A5h
        defb    049h,014h,014h,014h,013h,013h,075h,0A5h
        defb    0A5h,013h,0A5h,0A5h,0A5h,013h,002h,001h
        defb    000h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,048h,0A8h,0A8h
        defb    0A8h,04Ah,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,075h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,03Ch
        defb    03Ah,03Ah,03Ah,03Ah,03Ah,0A5h,03Ah,03Ah
        defb    03Ah,03Bh,013h,013h,0A5h,0A5h,03Dh,0A5h
        defb    0A5h,041h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,03Ch,03Ah,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Ah,03Ah,03Bh,013h,013h,0A5h,0A5h
        defb    03Dh,0A5h,0A5h,041h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,03Ch,03Ah,0A5h,03Ah,03Ah
        defb    03Ah,03Ah,03Ah,03Ah,03Ah,03Bh,013h,013h
        defb    0A5h,0A5h,03Dh,0A5h,0A5h,041h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,03Ch,0A5h,03Ah
        defb    03Ah,03Ah,03Ah,03Ah,03Ah,0A5h,03Ah,03Bh
        defb    013h,013h,0A5h,0A5h,03Dh,0A5h,0A5h,041h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,03Ch
        defb    03Ah,03Ah,03Ah,0A5h,03Ah,03Ah,03Ah,03Ah
        defb    03Ah,03Bh,013h,013h,075h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,014h,014h,014h,047h,0A5h,0A5h,0A5h
        defb    049h,014h,014h,014h,013h,013h,000h,001h
        defb    002h,013h,0A5h,0A5h,0A5h,013h,002h,001h
        defb    000h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,048h,0A8h,0A8h,0A8h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,071h,0A5h,0A5h,0A5h
        defb    013h,013h,045h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,070h,0A5h,0A5h,0A5h,013h,013h,01Fh
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,04Ah,014h,014h
        defb    018h,018h,013h,013h,045h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,01Fh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,045h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    051h,013h,013h,01Fh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,052h,013h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,018h,018h,018h,049h,014h,047h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A7h
        defb    0A5h,0A7h,013h,003h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,013h
        defb    002h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,075h,0A5h,0A5h,013h,001h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,013h,000h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,0A8h,0A8h,0A8h,04Ah,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,018h,018h,018h,018h,018h,018h,018h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,018h,0A7h
        defb    0A5h,018h,0A7h,0A5h,018h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,018h,070h,0A5h,018h,075h
        defb    0A5h,018h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    018h,018h,018h,018h,018h,018h,018h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,018h
        defb    0A7h,0A5h,0A5h,018h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,018h,076h,0A5h,0A5h
        defb    018h,013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,018h,018h,018h,018h,018h,013h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,018h,018h
        defb    018h,018h,018h,013h,013h,014h,014h,047h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,000h,001h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,002h
        defb    002h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,003h,004h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,004h,000h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,000h,003h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,048h,0A8h,0A8h,0A8h,04Ah
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,051h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,052h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,049h,014h,014h,013h,013h
        defb    03Ch,03Ah,0A5h,03Ah,03Ah,03Ah,03Ah,03Bh
        defb    013h,000h,000h,013h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,004h,004h
        defb    013h,013h,03Ch,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Bh,013h,003h,002h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    002h,003h,013h,013h,073h,0A5h,0A5h,0A5h
        defb    049h,014h,014h,014h,000h,004h,001h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,013h,004h,002h
        defb    002h,002h,001h,004h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,013h,000h,001h,004h,002h,003h
        defb    000h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,048h,0A8h,0A8h,0A8h,04Ah
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,018h,018h,018h,018h,018h,018h
        defb    018h,018h,018h,018h,018h,013h,013h,01Fh
        defb    0A5h,018h,0A5h,0A5h,018h,0A5h,0A5h,018h
        defb    0A5h,01Ch,013h,013h,018h,018h,018h,018h
        defb    018h,018h,018h,018h,018h,018h,018h,013h
        defb    013h,01Fh,0A5h,018h,0A5h,0A5h,018h,0A5h
        defb    0A5h,018h,0A5h,01Ch,013h,013h,018h,018h
        defb    018h,018h,018h,018h,018h,018h,018h,018h
        defb    018h,013h,013h,01Fh,0A5h,018h,0A5h,0A5h
        defb    018h,0A5h,0A5h,018h,0A5h,01Ch,013h,013h
        defb    018h,018h,018h,018h,018h,018h,018h,018h
        defb    018h,018h,018h,013h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,014h
        defb    014h,014h,047h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,000h,000h,002h,002h
        defb    0A5h,0A5h,0A5h,008h,0A5h,000h,0E0h,000h
        defb    013h,000h,001h,001h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,002h,004h
        defb    004h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,000h,003h,000h,001h,002h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    004h,001h,004h,000h,003h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,051h,013h,003h,002h,002h
        defb    004h,004h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    052h,013h,002h,000h,001h,003h,000h,013h
        defb    048h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,000h
        defb    004h,003h,002h,001h,013h,0ABh,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,003h,001h,000h,001h
        defb    002h,013h,0ABh,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    04Ah,014h,014h,014h,014h,014h,013h,0ABh
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,047h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,014h,014h,014h,047h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,000h,002h,001h,013h,070h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,004h,003h
        defb    003h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,0A8h,0A8h,0A8h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,000h,002h,003h,001h,003h
        defb    013h,013h,01Fh,0A5h,0A5h,0A5h,0A5h,013h
        defb    002h,004h,001h,002h,004h,013h,013h,0A5h
        defb    0A5h,0A5h,0A5h,01Ch,013h,004h,000h,000h
        defb    004h,000h,013h,013h,01Fh,0A5h,0A5h,0A5h
        defb    0A5h,013h,001h,003h,004h,000h,002h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,04Ah,014h
        defb    014h,014h,014h,014h,013h,013h,01Fh,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,018h,0A5h
        defb    0A5h,013h,013h,018h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,018h,0A5h,0A6h,013h,013h
        defb    0A5h,018h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    018h,0A5h,0A5h,013h,013h,045h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,018h,0A5h,0A5h
        defb    013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,018h
        defb    018h,018h,018h,018h,018h,013h,013h,00Ch
        defb    0A5h,0A5h,0A5h,0A5h,018h,018h,018h,018h
        defb    018h,018h,013h,013h,028h,026h,0A5h,0A5h
        defb    0A5h,018h,018h,075h,0A5h,0A5h,0A5h,013h
        defb    013h,029h,027h,0A5h,0A5h,0A5h,018h,018h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,00Eh,0A5h
        defb    0A5h,0A5h,0A5h,018h,018h,070h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,048h,0A8h,0A8h,0A8h
        defb    04Ah,014h,014h,00Fh,013h,045h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,046h
        defb    013h,013h,03Ch,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Ah,03Ah,03Ah,03Bh,013h,013h,0A5h
        defb    0A5h,0A5h,03Dh,0A5h,0A5h,041h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,03Ch,03Ah,03Ah,03Ah
        defb    03Ah,03Ah,03Ah,0A5h,03Ah,03Ah,03Bh,013h
        defb    013h,045h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,046h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,049h,014h,014h,018h,018h,014h
        defb    014h,013h,013h,0A5h,0A5h,0A5h,0A5h,013h
        defb    070h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h
        defb    075h,0A5h,0A5h,0A5h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,013h,018h,018h,018h
        defb    018h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,018h,0A5h,0A5h,018h,013h,071h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h
        defb    018h,018h,0A5h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,013h,074h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,000h,000h,004h,003h
        defb    013h,013h,08Bh,0A5h,0A5h,0A5h,0A5h,051h
        defb    013h,004h,002h,000h,002h,013h,048h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,052h,013h,003h,003h
        defb    001h,001h,013h,0ABh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,002h,000h,002h,004h,013h
        defb    0ABh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    001h,004h,003h,000h,013h,0ABh,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,04Ah,014h,014h,014h
        defb    014h,013h,047h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,046h,013h,013h
        defb    01Fh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,01Ch,013h,013h,01Fh,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,01Ch
        defb    013h,013h,01Fh,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,01Ch,013h,013h,014h
        defb    014h,014h,014h,047h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,003h,001h,004h,000h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,002h,000h,002h,001h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,000h,004h
        defb    003h,004h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,018h,0A5h,018h
        defb    018h,0A5h,018h,0A5h,018h,0A5h,018h,0A5h
        defb    013h,013h,0A5h,018h,0A5h,018h,0A5h,018h
        defb    0A5h,018h,0A5h,018h,0A5h,013h,013h,018h
        defb    049h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,013h,013h,0A5h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,078h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,014h,048h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,049h,014h,014h,014h,013h,013h
        defb    03Ch,03Ah,0A5h,03Ah,03Ah,03Ah,03Bh,013h
        defb    0A5h,018h,0A5h,013h,013h,0A5h,03Dh,0A5h
        defb    0A5h,041h,0A5h,0A5h,013h,018h,018h,018h
        defb    013h,013h,03Ch,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Bh,013h,0A5h,018h,0A5h,013h,013h,0A5h
        defb    03Dh,0A5h,0A5h,041h,0A5h,0A5h,013h,018h
        defb    018h,018h,013h,013h,03Ch,0A5h,03Ah,03Ah
        defb    03Ah,03Ah,03Bh,013h,0A5h,018h,0A5h,013h
        defb    013h,045h,0A5h,0A5h,0A5h,0A5h,0A5h,046h
        defb    013h,018h,018h,018h,013h,013h,045h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,046h,013h,0A5h,018h
        defb    0A5h,013h,012h,014h,047h,0A9h,0A9h,0A9h
        defb    049h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,000h,013h,0A5h
        defb    0A5h,0A5h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,004h,013h,0A5h,0A5h,0A5h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,003h
        defb    013h,0A5h,0A5h,0A5h,013h,0A7h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,002h,013h,005h,0A5h
        defb    0A5h,04Ah,014h,014h,014h,047h,0A5h,013h
        defb    013h,001h,013h,006h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,0A5h,013h,013h,000h,013h
        defb    007h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    0A5h,013h,013h,004h,013h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,0A5h,013h,013h
        defb    003h,013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,04Ah,014h,013h,013h,002h,013h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,033h
        defb    013h,013h,001h,013h,0A5h,0A5h,0A5h,018h
        defb    018h,0A5h,0A5h,0A5h,034h,013h,013h,000h
        defb    013h,0A5h,0A5h,018h,0A5h,0A5h,018h,0A5h
        defb    031h,02Fh,013h,013h,014h,048h,018h,018h
        defb    018h,018h,018h,018h,0A5h,032h,030h,013h
        defb    013h,0A5h,0A5h,0A5h,0A5h,018h,0A5h,0A5h
        defb    018h,0A5h,0A5h,036h,013h,013h,070h,0A5h
        defb    0A5h,0A5h,0A5h,018h,018h,0A5h,0A5h,0A5h
        defb    035h,013h,012h,014h,014h,014h,047h,0A9h
        defb    0A9h,0A9h,049h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,0A5h,0A5h,0A5h
        defb    013h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,048h,0A5h,0A5h,0A5h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,0ABh,0A5h
        defb    0A5h,0A5h,013h,01Fh,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,01Ch,013h,0ABh,0A5h,0A5h,0A5h,013h
        defb    01Fh,0A5h,0A5h,0A5h,0A5h,0A5h,01Ch,013h
        defb    0ABh,0A5h,0A5h,0A5h,04Ah,014h,014h,014h
        defb    047h,0A5h,0A5h,0A5h,013h,013h,075h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,0A5h,0A5h
        defb    046h,013h,013h,03Ch,03Ah,0A5h,03Ah,03Ah
        defb    03Ah,03Ah,03Ah,0A5h,03Ah,03Bh,013h,013h
        defb    0A5h,0A5h,0A5h,017h,0A5h,03Dh,0A5h,0A5h
        defb    041h,0A5h,0A5h,013h,013h,03Ch,0A5h,03Ah
        defb    03Ah,03Ah,03Ah,0A5h,03Ah,03Ah,03Ah,03Bh
        defb    013h,013h,0A5h,0A5h,0A5h,017h,0A5h,03Dh
        defb    0A5h,0A5h,041h,0A5h,0A5h,013h,013h,03Ch
        defb    03Ah,0A5h,03Ah,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Bh,013h,013h,0A5h,0A5h,0A5h,017h
        defb    0A5h,03Dh,0A5h,0A5h,041h,0A5h,0A5h,013h
        defb    013h,03Ch,0A5h,03Ah,03Ah,03Ah,0A5h,03Ah
        defb    03Ah,03Ah,03Ah,03Bh,013h,013h,045h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    046h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,015h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,01Ah,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,01Ah
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,01Ah,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,013h
        defb    013h,01Ah,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,013h,013h,01Ah,0A5h
        defb    0A5h,049h,014h,014h,014h,014h,014h,014h
        defb    014h,013h,013h,01Ah,0A5h,0A5h,013h,0A7h
        defb    013h,0A5h,0A5h,0A5h,0A5h,051h,013h,013h
        defb    01Ah,0A5h,0A5h,04Ah,014h,048h,0A5h,0A5h
        defb    0A5h,0A5h,052h,013h,013h,01Ah,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,046h
        defb    013h,013h,01Ah,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,01Ch,013h,013h,01Ah
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,046h,013h,013h,01Ah,014h,014h,014h
        defb    014h,047h,0A5h,0A5h,0A5h,0A5h,046h,013h
        defb    013h,01Ah,0A5h,0A5h,0A5h,0A5h,013h,0A5h
        defb    0A5h,0A5h,0A5h,01Ch,013h,013h,016h,0A5h
        defb    0A5h,0A5h,0A5h,013h,0A5h,0A5h,0A5h,0A5h
        defb    046h,013h,012h,014h,014h,014h,014h,014h
        defb    048h,0A9h,0A9h,0A9h,049h,014h,010h,011h
        defb    014h,014h,014h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,00Fh,013h,075h,0A5h,0A5h
        defb    0A5h,051h,013h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,013h,070h,0A5h,0A5h,0A5h,052h,013h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,013h,075h
        defb    0A5h,0A5h,0A5h,0A5h,013h,01Fh,0A5h,0A5h
        defb    0A5h,01Ch,013h,013h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,013h,01Fh,0A5h,0A5h,0A5h,01Ch,013h
        defb    013h,08Ah,08Bh,0A5h,0A5h,0A5h,013h,01Fh
        defb    0A5h,0A5h,0A5h,01Ch,013h,013h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,01Fh,0A5h,0A5h,0A5h
        defb    01Ch,013h,048h,018h,018h,018h,014h,014h
        defb    048h,0A5h,0A5h,0A5h,0A5h,0A5h,013h,0ABh
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,013h,0ABh,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    013h,0ABh,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,047h,018h
        defb    018h,018h,018h,018h,018h,018h,018h,0A5h
        defb    0A5h,0A5h,013h,013h,0A5h,018h,08Bh,018h
        defb    08Bh,018h,0A5h,018h,0A5h,0A5h,0A5h,013h
        defb    013h,0A7h,0A5h,018h,018h,018h,0A5h,0A5h
        defb    018h,0A5h,0A5h,0A5h,013h,013h,018h,0A5h
        defb    0A5h,018h,0A7h,0A5h,018h,018h,0A5h,0A5h
        defb    0A5h,013h,012h,014h,014h,014h,014h,014h
        defb    014h,014h,014h,014h,014h,014h,010h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h
label_phantom_7800:
        defb    0E5h,060h,069h,029h,04Dh,044h,011h,005h
        defb    000h,07Ah,02Fh,057h,07Bh,02Fh,05Fh,013h
        defb    021h,000h,000h,03Eh,011h
lbl_7815:
        defb    0E5h,019h,0D2h,01Bh,078h,0E3h
lbl_781b:
        defb    0E1h,0F5h,079h,017h,04Fh,078h,017h,047h
        defb    07Dh,017h,06Fh,07Ch,017h,067h,0F1h,03Dh
        defb    0C2h,015h,078h,0B7h,07Ch,01Fh,047h,07Dh
        defb    01Fh,05Fh,021h,004h,000h,009h,044h,04Dh
        defb    0E1h,0C9h
label_phantom_783d:
        defb    0F3h,0C5h,0E5h
label_7840:
        defb    0CDh,074h,078h,026h,002h,006h,004h,03Eh
        defb    080h,0D3h,01Bh
lbl_784b:
        defb    0DBh,01Bh,00Fh,0D2h,04Bh,078h
lbl_7851:
        defb    0DBh,01Bh,0A4h,0CAh,051h,078h,0DBh,018h
        defb    012h,01Ch,0C2h,051h,078h,014h,005h,0C2h
        defb    051h,078h
lbl_7863:
        defb    0DBh,01Bh,00Fh,0DAh,063h,078h,0DBh,01Bh
        defb    0E6h,0DDh,0C2h,020h,07Ah,0E1h,0C1h,000h
        defb    0C9h
label_phantom_7874:
        defb    03Eh,030h,032h,0A2h,078h,026h,004h,03Ah
        defb    01Eh,079h,0E6h,001h,0CAh,085h,078h,026h
        defb    000h
lbl_7885:
        defb    03Ah,0A2h,078h,0B4h,032h,0A2h,078h
lbl_788c:
        defb    03Ah,0A2h,078h,0D3h,01Ch,0DBh,01Bh,007h
        defb    0DAh,08Ch,078h,03Eh,0D0h,0D3h,01Bh
label_phantom_789b:
        defb    03Eh,080h
lbl_789d:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    03Dh,0C2h,09Dh,078h,0C9h
gap_78A2:
        defb    000h
label_phantom_78a3:
        defb    0F3h,0C5h,0E5h,0D5h,021h,01Fh,079h,07Eh
        defb    0B7h,01Fh,057h,0D3h,01Ah,03Ah,01Eh,079h
        defb    077h,0B7h,01Fh,05Fh,0D3h,018h,0BAh,0CAh
        defb    0EBh,078h,03Eh,059h,0D2h,0C4h,078h,03Eh
        defb    079h
lbl_78c4:
        defb    0CDh,0D3h,078h
label_78C7:
        defb    0DBh,01Ah,0BBh,0CAh,0EBh,078h,0CDh,0E6h
        defb    078h,0C3h,0C7h,078h
label_phantom_78d3:
        defb    0D3h,01Bh,0CDh,09Bh,078h
lbl_78d8:
        defb    03Ah,0A2h,078h,0D3h,01Ch,0DBh,01Bh,00Fh
        defb    0DAh,0D8h,078h,0C3h,09Bh,078h
label_phantom_78e6:
        defb    03Eh,038h,0C3h,0D3h,078h
lbl_78eb:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    03Eh,01Ch,0CDh,0D3h,078h,0DBh,01Bh,0E6h
        defb    018h,0CAh,010h,079h,0CDh,09Bh,078h,03Eh
        defb    003h,0CDh,0D3h,078h,0CDh,09Bh,078h,036h
        defb    000h,0D1h,0D5h,0CDh,03Dh,078h,0D1h,0E1h
        defb    0C1h,0C3h,0A3h,078h
gap_790F:
        defb    0C9h
lbl_7910:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    03Ah,01Dh,079h,03Ch,0D3h,019h,0D1h,0CDh
        defb    03Dh,078h,0E1h,0C1h,0C9h
gap_791D:
        defb    000h,000h,000h
label_phantom_7920:
        defb    0AFh,032h,011h,07Ah,0AFh,032h,01Dh,079h
        defb    03Eh,004h,032h,01Eh,079h
lbl_792d:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    021h,080h,077h,011h,000h,0EBh,0CDh,0A3h
        defb    078h,0CDh,04Ah,079h,0E5h,021h,01Dh,079h
        defb    034h,07Eh,0E1h,0FEh,004h,0C2h,02Dh,079h
        defb    0C9h
gap_7946:
        defb    0A0h,079h,000h,0EAh
label_phantom_794a:
        defb    0E5h,00Eh,020h,011h,000h,0EBh
lbl_7950:
        defb    01Ah,0FEh,0E5h,0CAh,08Bh,079h,0E5h,0D5h
        defb    006h,00Bh
lbl_795a:
        defb    01Ah,0E6h,07Fh,0BEh,0C2h,09Bh,079h,013h
        defb    023h,005h,0C2h,05Ah,079h,0D1h,0E1h,0D5h
        defb    0C5h,0E5h,062h,06Bh,0E5h,021h,011h,07Ah
        defb    034h,02Ah,048h,079h,0EBh,0E1h,006h,020h
lbl_797a:
        defb    07Eh,012h,013h,023h,005h,0C2h,07Ah,079h
        defb    0E5h,0EBh,022h,048h,079h,0E1h,0E1h,0C1h
        defb    0D1h
lbl_798b:
        defb    0C5h,0E5h,0EBh,001h,020h,000h,009h,0EBh
        defb    0E1h,0C1h,00Dh,0C2h,050h,079h,0E1h,0C9h
lbl_799b:
        defb    0D1h,0E1h,0C3h,08Bh,079h
label_79A0:
        defb    0F3h,021h,010h,0EAh
label_79A4:
        defb    0E5h,0CDh,0B8h,079h,0E1h,03Ah,011h,07Ah
        defb    03Dh,0C8h,032h,011h,07Ah,001h,020h,000h
        defb    009h,0C3h,0A4h,079h
label_phantom_79b8:
        defb    03Eh,008h,032h,010h,07Ah
label_79BD:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    04Eh,023h,046h,023h,078h,0B1h,0C8h,03Ah
        defb    010h,07Ah,0B7h,0C8h,03Dh,032h,010h,07Ah
        defb    0CDh,000h,078h,079h,032h,01Eh,079h,07Bh
        defb    032h,01Dh,079h,0C5h,0D5h,0E5h,02Ah,007h
        defb    07Ah,0EBh,0CDh,0A3h,078h,03Ah,01Dh,079h
        defb    0FEh,004h,0CCh,009h,07Ah,03Ch,032h,01Dh
        defb    079h,0CDh,0A3h,078h,03Ah,01Dh,079h,0FEh
        defb    004h,0CCh,009h,07Ah,03Ch,032h,01Dh,079h
        defb    0EBh,022h,007h,07Ah,0E1h,0D1h,0C1h,0C3h
        defb    0BDh,079h
gap_7A07:
        defb    000h,080h
label_7A09:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    021h,01Eh,079h,034h,0AFh,03Dh,0C9h
gap_7A10:
        defb    000h,000h,0D5h,0C3h,05Ch,018h,078h,0FEh
        defb    0FFh,0C2h,020h,018h,0AFh,0C3h,060h,018h
lbl_7a20:
; Uncovered ROM bytes — neither code nor an RDB object
        defb    07Ah,0D6h,004h,057h,0C3h,040h,078h
gap_7A27:
; --- Symbols at addresses owned by another unit ---
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,005h,003h,001h,028h,086h,000h
        defb    007h,004h,001h,022h,088h,000h,00Ah,002h
        defb    000h,020h,088h,000h,009h,001h,001h,01Fh
        defb    088h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,0A5h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,013h,0A5h,0A5h
        defb    013h,013h,014h,014h,014h,014h,0A5h,014h
        defb    014h,014h,010h,0A5h,0A5h,013h,013h,045h
        defb    0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h,0A5h
        defb    0A5h,0A5h,013h,013h,03Ch,03Ah,03Ah,03Ah
        defb    03Ah,03Ah,0A5h,0AFh,0D3h,010h,03Ah,005h
        defb    000h,0B7h,0CAh,012h,001h,011h,01Eh,001h
        defb    00Eh,009h,0CDh,005h,000h,0F3h,0C3h,088h
        defb    001h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,00Ch,01Bh,05Ch,057h,045h,04Ch,043h
        defb    04Fh,04Dh,045h,020h,054h,04Fh,020h,047h
        defb    041h,04Dh,045h,00Ah,06Bh,06Fh,06Dh,070h
        defb    072h,065h,073h,073h,06Fh,072h,020h,056h
        defb    031h,02Eh,030h,00Ah,062h,065h,06Ch,061h
        defb    072h,075h,073h,078h,020h,031h,039h,039h
        defb    032h,00Ah,032h,032h,032h,031h,032h,06Fh
        defb    020h,067h,02Eh,062h,06Fh,072h,069h,073h
        defb    06Fh,077h,00Ah,070h,061h,077h,06Ch,06Fh
        defb    077h,061h,020h,031h,037h,00Ah,06Bh,075h
        defb    07Eh,069h,06Eh,073h,06Bh,06Fh,06Dh,075h
        defb    020h,061h,06Eh,064h,072h,065h,060h,020h
        defb    069h,077h,061h,06Eh,06Fh,077h,069h,07Eh
        defb    075h,00Ah,024h,021h,000h,002h,011h,000h
        defb    080h,07Eh,012h,013h,023h,07Ah,0FEh,0FEh
        defb    0C2h,08Eh,001h,011h,0D8h,001h,021h,000h
        defb    0FFh,00Eh,026h,01Ah,077h,013h,023h,00Dh
        defb    0C2h,0A0h,001h,031h,0FFh,000h,0C3h,000h
        defb    0FFh,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,021h,000h,080h,011h,000h
        defb    001h,07Eh,0FEh,0CAh,0CAh,0CAh,0CAh,0CAh
        defb    0CAh,0CAh,0CAh,0CAh,0CAh,0CAh,0CAh,0CAh
        defb    0CAh,0CAh,0CAh,0CAh,0CAh,0CAh,0CAh,0CAh
        defb    0CAh,0CAh,0CAh,0FFh,012h,013h,023h,07Ch
        defb    0FEh,0FFh,0C2h,006h,0FFh,0C3h,000h,001h
        defb    023h,07Eh,023h,046h,012h,013h,005h,0C2h
        defb    01Ch,0FFh,0C3h,00Eh,0FFh,000h,000h,000h
        defb    000h,000h,007h,0FFh,0C0h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,006h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,007h,0FDh,0FFh,0E0h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,0FFh,080h
        defb    000h,027h,080h,000h,000h,000h,000h,000h
        defb    000h,00Fh,0FFh,0F8h,01Fh,0E3h,0FFh,0FFh
        defb    0F0h,0FFh,0FEh,01Fh,0FFh,0FEh,03Fh,0FFh
        defb    0FCh,07Fh,0FFh,0F8h,0FFh,01Ch,0FEh,007h
        defb    000h,02Ah,0A0h,000h,000h,000h,000h,000h
        defb    000h,000h,00Ch,000h,003h,0EFh,01Eh,000h
        defb    01Eh,00Fh,01Fh,083h,0E6h,03Ch,0C3h,0C0h
        defb    00Fh,081h,0E0h,01Fh,003h,0C0h,078h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,00Fh,0DFh,0EFh,0F0h,0FFh
        defb    0FFh,0FFh,0E0h,003h,0FFh,0C3h,0FCh,003h
        defb    0FFh,0F8h,0FFh,01Fh,0FFh,0FFh,0FEh,000h
        defb    000h,0AAh,0A0h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,00Fh,0E0h,063h,0F7h
        defb    0E0h,07Eh,0DBh,03Fh,018h,0DBh,0B6h,003h
        defb    05Bh,0F6h,00Fh,0EDh,0BBh,0F0h,000h,000h
        defb    000h,08Ah,0A0h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,00Ah,0A0h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,034h,064h,008h,0AAh,07Eh,02Ah
        defb    0A9h,0FEh,0C0h,000h,000h,000h,000h,000h
        defb    00Ah,0ABh,0E8h,000h,000h,000h,008h,000h
        defb    000h,000h,003h,0FFh,080h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,009h,080h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,003h,0FFh,0FFh,0C0h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,0FFh,000h
        defb    000h,010h,050h,000h,000h,000h,000h,000h
        defb    000h,007h,0F8h,000h,01Fh,0E7h,0F8h,01Fh
        defb    0E1h,0FEh,000h,03Fh,081h,0FCh,07Fh,087h
        defb    0F8h,0FFh,00Fh,0F1h,0FEh,03Eh,0FEh,006h
        defb    080h,015h,050h,000h,000h,000h,000h,000h
        defb    000h,000h,007h,0F8h,01Fh,0EFh,0FFh,0E1h
        defb    0FFh,0FEh,03Fh,0FFh,000h,07Fh,087h,0F8h
        defb    0FFh,00Fh,0F1h,0FEh,03Fh,0C1h,0FEh,007h
        defb    000h,0E7h,000h,030h,000h,060h,000h,000h
        defb    000h,000h,000h,007h,0DFh,0EFh,0E1h,0FFh
        defb    0FFh,0FFh,0C0h,001h,0FFh,087h,0F8h,001h
        defb    0FFh,0F1h,0FEh,03Fh,0FFh,0FFh,0FEh,000h
        defb    000h,055h,050h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,007h,0E0h,063h,036h
        defb    000h,060h,0D9h,0B3h,018h,0D9h,0B3h,003h
        defb    01Bh,0F6h,00Ch,06Dh,09Bh,000h,000h,000h
        defb    000h,055h,050h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,04Ch,084h,0C4h,054h,003h
        defb    0E0h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,051h,050h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,010h,09Bh,061h,055h,07Fh,0C5h
        defb    054h,0FEh,0E0h,000h,000h,000h,000h,000h
        defb    015h,053h,0A8h,000h,000h,000h,022h,000h
        defb    000h,000h,001h,0FFh,000h,07Fh,0FFh,080h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,00Bh,080h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,001h,0FFh,0FFh,080h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,0FEh,000h
        defb    000h,02Ah,0A0h,000h,000h,000h,000h,040h
        defb    000h,003h,0FCh,000h,01Fh,0EFh,0F0h,03Fh
        defb    0C3h,0FCh,000h,07Fh,003h,0F8h,0FFh,00Fh
        defb    0F1h,0FEh,01Fh,0E3h,0FCh,07Fh,0FEh,007h
        defb    034h,02Ah,0A0h,000h,000h,000h,000h,000h
        defb    000h,000h,003h,0FCh,01Fh,0E0h,03Fh,0C3h
        defb    0FCh,000h,07Fh,0FFh,080h,0FFh,00Fh,0F1h
        defb    0FEh,01Fh,0E3h,0FCh,07Fh,080h,0FEh,006h
        defb    081h,08Ch,000h,030h,000h,0D0h,000h,000h
        defb    000h,000h,000h,003h,0DFh,0EFh,0C3h,0FFh
        defb    0FFh,0FFh,080h,000h,0FFh,007h,0F0h,000h
        defb    0FFh,0E3h,0FCh,07Fh,0FFh,0FFh,0FEh,000h
        defb    000h,08Ah,0A0h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,003h,0E0h,063h,037h
        defb    0E0h,060h,0DFh,0B3h,018h,0D9h,0BFh,003h
        defb    01Bh,037h,0ECh,06Dh,09Bh,0DAh,001h,02Ch
        defb    001h,08Ah,0A0h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,090h,01Bh,02Ah,0AAh,08Fh
        defb    0F8h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,0AAh,0A0h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,041h,064h,002h,0AAh,07Fh,0F8h
        defb    0AAh,07Ch,0F0h,000h,000h,000h,000h,000h
        defb    00Ah,0AAh,0A8h,000h,000h,000h,008h,000h
        defb    000h,000h,000h,0FFh,080h,03Fh,0FFh,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,00Fh,000h,000h,000h,000h,000h,000h
        defb    001h,0FFh,0FFh,0FEh,0FFh,0FFh,01Fh,0FFh
        defb    000h,006h,000h,0F0h,0FFh,0E0h,001h,0FFh
        defb    0C0h,003h,0FFh,080h,07Fh,0F8h,0FEh,000h
        defb    000h,015h,050h,000h,000h,000h,000h,0A0h
        defb    000h,001h,0FEh,000h,01Fh,0EFh,0E0h,07Fh
        defb    087h,0F8h,000h,0FEh,007h,0F1h,0FEh,01Fh
        defb    0E3h,0FCh,03Fh,0C7h,0F8h,0FFh,0FEh,006h
        defb    0B4h,015h,050h,000h,000h,000h,000h,000h
        defb    000h,000h,001h,0FFh,0DFh,0E0h,07Fh,087h
        defb    0F8h,000h,0FFh,07Fh,0C1h,0FEh,01Fh,0E3h
        defb    0FCh,03Fh,0C7h,0F8h,0FFh,000h,0FEh,007h
        defb    01Dh,0CEh,073h,031h,080h,0C3h,01Ch,0E6h
        defb    000h,000h,000h,000h,01Fh,0E0h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,000h,000h,000h,000h
        defb    000h,055h,050h,000h,000h,000h,000h,000h
        defb    000h,000h,000h,000h,001h,0E0h,063h,037h
        defb    0E0h,060h,0DFh,0B3h,018h,0D9h,0BFh,003h
        defb    01Bh,037h,0ECh,06Dh,09Bh,0F0h,000h,000h
        defb    000h