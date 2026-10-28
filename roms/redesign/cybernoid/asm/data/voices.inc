; voices.inc — B-viewStage 9 (только чтение).
; Источник: data/data.asm (v06c-asm-export). Байты дословно из RDB-объектов,
; без переформатирования. В сборку НЕ включается: main.asm знает только
; layout.asm (Stage 6.23 §2.2). Список объектов и их комментарии — в RDB
; (cybernoid_unpacked.rdb); здесь — только human-readable срез по классу.
; Покрытые гэпы (gap_*) сюда не переносим — они живут только в мастере.


; str_voice: речевая фраза заставки (exec-буфер 0x0600, момент речи #1). Транслит (разделитель — пробел, НЕ '%'): «GRU DIL SOFT PREDLAGAET NOWEJSIE PROGRAMMY K WEKTOR NOL SEST… C PISITE NAM PO ADRESU» → «ГРУ Дил Софт предлагает новейшие программы к Вектор-06… пишите нам по адресу». В ROM-файле источник на 0x065A (блок speech −0x59 relocation → exec 0x0600). Произносится func_speak_engine (Stage 7).
str_voice_title:
	defb	00h

; Демо-фраза синтезатора речи (translit, 94B): 'GRU DIL SOFT PREDLAGAET NOWEJSIE PROGRAMMY K WEKTOR NOL SESTX C PISITE NAM PO ADRESU'; терминатор (00h) в 0x06B8 (после 'ADRESU' идут 10 09 04 00 = NOP/DAD B/INR B/NOP, затем DI-вход). Адреса 0x0660/0x0663/0x0669/0x06C3 внутри строки — НЕ код: ранние Stage-2 функции по этим адресам были фантомами (исправлено в этом проходе). Ветки речи (CALL 0x0669; цели 0x069B/0x0686/0x068C/0x0690/0x0697/0x06FD/0x06DC, JMP 0x066B) прилетают в область строки — аномалию разрешать трейсингом в Stage 7 (см. func_speak_walker).
str_speak_demo:
	defb	44h,52h,45h,53h,55h,00h

; Счётчикsoftware-delay PDM-бита (LDA 0733/DCR/JNZ в func_speak_phoneme). Задаёт каденс бита-бэнга (~40 T-c на OUT 00h → ~37 кГц при такте машины). Косвенно = частота дискретизации речи.
var_voice_period:
	defb	10h

; Курсор буфера сэмплов речи (LHLD 0734 в хвосте func_speak_phoneme, 0x071B). Указывает на текущую позицию в data_pdm_planes при побитовом выводе.
var_voice_bufptr:
	defb	00h,02h

; Таблица-индексатор символ→смещение (exec). Операнд base=0x06F7; реальные литеры A..Z лежат на 0x0738+ (низкие control-коды никогда не индексируются — обходчик divertит '.'/','/' ' на паузы). Значения = смещения в articulogram data_speak_codes. A=0,B=2,C=6,D=10,E=14,F=16,G=18,H=22,I=26,J=28,K=34,L=38,M=42,N=46,O=50,P=52,Q=56,R=66,S=72,T=74,U=78,V=80,W=80,X=86,Y=26,Z=92. Дубли V=W=80, Y=I=26 = слитые фонемы транслита. Индекс = raw ASCII charcode (живой stepping: 'D'=0x44 → 0x073B → 10 → table2 0x0776).
data_speak_char_index:
	defb	00h,02h,06h,0Ah,0Eh,10h,12h

; Последовательность артикулограмм-дескрипторов (exec base 0x076C). Индекс = смещение из data_speak_char_index. Единица читается func_speak_phoneme по 2 байта: byte0 — low-nibble=длительность (ANI 0F → C), bits4-6=номер бит-плоскости сэмпла (RLC×3/ANI 07), bit7=флаг; byte1 bit7=флаг продолжения пары. Чтение пар до терминатора (JZ 0x071B при plane#==0). Плоскость → длина из data_speak_plane_lengths, биты → data_pdm_planes. Пример 'D': offset 10 → 0x0776: 34 19 | 31 E0 | …
label_0778:
	defb	31h,0E0h,36h,84h,92h,0E3h,35h,19h
	defb	51h,9Ch,31h,31h,34h,96h,36h,87h
	defb	33h,3Ah,32h,3Dh,32h,0C0h,18h,19h
	defb	51h,9Ch,33h,22h,31h,0B1h,31h,31h
	defb	36h,0A5h,31h,31h,36h,0A8h,36h,8Ah
	defb	18h,19h,31h,0ABh,18h,19h,51h,1Ch
	defb	34h,31h,32h,34h,32h,0B7h,22h,10h
	defb	13h,19h,21h,0AEh,92h,0C3h,18h,19h
	defb	31h,0E0h,36h,8Dh,34h,31h,32h,34h
	defb	32h,0B7h,18h,19h,71h,1Ch,92h,0C3h
	defb	32h,31h,32h,43h,32h,44h,32h,0C5h
	defb	3Fh,81h,34h,19h,31h,2Bh,33h,3Ah
	defb	32h,3Dh,32h,0C0h,18h,19h,91h,0D3h
	defb	33h,19h,71h,6Dh,32h,93h,3Eh,84h
	defb	92h,63h,33h,3Ah,32h,3Dh,32h,0C0h
	defb	92h,0F3h,3Eh,87h,31h,31h,36h,25h
	defb	31h,31h,35h,25h,32h,93h,3Eh,8Ah
	defb	18h,19h,31h,2Bh,33h,3Ah,32h,3Dh
	defb	32h,0C0h,13h,19h,32h,60h,13h,19h
	defb	71h,0DDh,92h,0D3h,18h,19h,71h,6Dh
	defb	32h,93h,3Eh,8Dh,34h,31h,32h,34h
	defb	32h,37h,33h,3Ah,32h,3Dh,32h,0C0h
	defb	32h,53h,32h,54h,32h,0D5h

; data_pdm_planes — база бит-плоскостей PDM-сэмплов (EXEC 0x082E..0x0934, ~262B высокоэнтропийных данных). Индекс: LXI D,082E + смещение(RAL из дескриптора) → ANA M (маска MVI A,80) → OUT 00 значением 0x00/0x01. Каждый бит плоскости = один такт PDM-бит-бэнга; период задаёт var_voice_period@0x0733 (~40 T-с → ~37 кГц). Это носитель звучания (форм-фактор units) — декодер выбирает плоскость по номеру из data_speak_codes.
data_pdm_planes:
	defb	1Ah

; Заголовок бит-плоскостей (exec): длины/число итераций эмита на единицу. Байты 00 2E 5A 5E FE (plane0..4). Читается как LXI D,0935 + plane# → MOV B,M = счётчик внутреннего цикла эмита (0x06ED). plane#==0 → конец фонемы (JZ 0x071B). Плотная упаковка: сразу за заголовком (0x093A) стартуют строки-фразы (область 0x098D/0x09C3).
data_speak_plane_lengths:
	defb	00h,2Eh,5Ah,5Eh,0FEh

; str_voice: речевая фраза (транслит, space-разделитель): «JSEM HLAS VAS'EHO POC'I'TAC'E SPEKTRUM» → ≈ «Йэм глас Вашэго почтачье Спектрум» («Я слыхал голос Вашего почерка, Спектрум»). Хедер записи 2E 5A 5E FE перед текстом. Озвучка движком речи (Stage 7).
str_voice_098d:
	defb	41h,20h,53h,45h,4Dh,4Eh,41h,44h
	defb	43h,41h,54h,58h,20h,20h,50h,4Fh
	defb	44h,4Fh,56h,44h,49h,54h,45h,20h
	defb	4Dh,49h,4Eh,55h,54h,4Fh,48h,4Bh
	defb	55h,20h,20h,50h,4Fh,56h,41h,4Ch
	defb	55h,4Ah

; str_voice: речевая фраза (транслит): «ESTI DVA STO DVADCATX GOROD BORISOV PAVLOWA SEMNADCATX PODOVDITE MINUTOHKU POVALUJSTA» → «[в]от два сто двадцать, город Борисов Павлова семнадцать, подождите минутку, пожалуйста». str_voice_* — речь (Stage 7).
str_voice_09b8:
	defb	54h,41h,20h,20h,20h,20h,20h,20h
	defb	20h,20h,00h,4Fh,44h,49h,4Eh,00h
	defb	44h,57h,41h,00h,54h,52h,49h,00h
	defb	44h,49h,4Ch,20h,53h,4Fh,46h,54h
	defb	20h,50h,52h,45h,44h,4Ch,41h,47h
	defb	41h,45h,54h,20h,4Eh,4Fh,57h,59h
	defb	45h,20h,49h,47h,52h,59h,20h,4Bh
	defb	20h,57h,45h,4Bh,54h,4Fh,52h,20h
	defb	4Eh,4Fh,4Ch,20h,53h,45h,53h,54h
	defb	20h,43h,20h,20h,50h,49h,53h,49h
	defb	54h,45h,20h,50h,4Fh,20h,41h,44h
	defb	52h

; str_voice: речевая фраза (транслит): «DIL SOFT PREDLAGAET NOWYE IGRY K WEKTOR NOL SEST C PISITE PO ADRESU DWESTE DWADCAT NOL SEMDESUAT ODIN ABANEBENTNYJ IASIK SESDESUAT ODIN» → «Дил Софт предлагает новые игры к Вектор-06… пишите по адресу 220-01-71 абонентский ящик 71». str_voice_* — речь (Stage 7).
str_voice_0a23:
	defb	54h,20h,4Eh,4Fh,4Ch,20h,53h,45h
	defb	4Dh,44h,45h,53h,55h,41h,54h,20h
	defb	4Fh,44h,49h,4Eh,20h,41h,42h,41h
	defb	4Eh,45h,42h,45h,4Eh,54h,4Eh,59h
	defb	4Ah,20h,49h,41h,53h,49h,4Bh,20h
	defb	53h,45h,53h,44h,45h,53h,55h,41h
	defb	54h,20h,4Fh,44h,49h,4Eh,00h,00h
	defb	00h,00h,00h,00h,00h
