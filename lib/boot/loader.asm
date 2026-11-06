;
; loader.asm — вызов второго загрузчика (stage-2) из ROM заставки.
; ТЗ: docs/LOADER_TZ.MD, сам blob: boot/loader_stage2.asm.
;
;   void loader_boot(void);
;   void loader_boot_cfg(const struct loader_cfg *cfg);
;
; НЕ возвращается: копия stage-2 в 0xE000h стирает машину вместе с кодом
; заставки, поэтому возврат сюда физически невозможен.
;
; loader_boot — дефолт: цвета как на эталоне (голубой фон, жёлтые линии),
; панелей нет. loader_boot_cfg — то же плюс настройка из struct loader_cfg:
; два цвета и до двух картинок в углы экрана (docs/LOADER_TZ.MD §5.2, §7).
; Стаб тащит в high RAM всё, что загрузчику понадобится ПОСЛЕ стирания
; 0000h..DFFFh: сам blob, 14 байт конфига и данные панелей. Указатели в
; struct — это адреса внутри этой ROM, после стирания они будут мусор.
;
; Blob лежит в коде этой ROM (INCLUDE сгенерированного .inc — тот же
; порядок, что у шрифтов в gfx/pr.asm) и копируется побайтово БЕЗ релопации:
; loader_stage2.asm собирается отдельным прогоном z80asm с ORG 0E000h,
; поэтому все его метки уже разрешены в абсолютные адреса там, где он будет
; исполняться (`make loader2` в корне).
;
; DI здесь, а не в stage-2: пока идёт копир и запуск, кадровой прерывающей
; может сработать обработчик заставки (он пишет порт 01h — мотор ленты, и
; скролл в 03h). С этого момента прерываний на машине больше нет вообще, см.
; docs/LOADER_TZ.MD §2.
;
; Команды — только КР580ВМ80А (в z80-синтаксисе, как во всём lib/: каждый
; операнд имеет 8080-эквивалент, недаром здесь нет ни LDIR, ни индексирующих
; пар, ни JR).
;

        SECTION code_clib
        PUBLIC  loader_boot
        PUBLIC  _loader_boot
        PUBLIC  loader_boot_cfg
        PUBLIC  _loader_boot_cfg

        INCLUDE "loader_stage2.inc"

LOADER_STAGE2_ADR equ 0e000h        ; адрес, под который собран blob
LOADER_CFG_ADR    equ 0e840h        ; конфиг stage-2 (ТЗ §4.2, §5.2)
LOADER_CFG_SIZE   equ 14            ; bg, line, 2x(x,y,wb,h), 2x указатель
LOADER_P1_ADR     equ 0e860h        ; слот данных панели 1, 2 КБ
LOADER_P2_ADR     equ 0f060h        ; слот данных панели 2, 2 КБ

loader_boot:
_loader_boot:
        di                          ; F3h — он же в i8080, прерывания гасим сразу
        lxi h, cfg_default          ; фон/линии эталона, панелей нет
        jmp loader_go

loader_boot_cfg:
_loader_boot_cfg:
        di
        pop de                      ; адрес возврата: из stage-2 не возвращаются
        pop hl                      ; HL = struct loader_cfg * — первый аргумент
                                    ; z88dk лежит глубже всех, то есть сразу за
                                    ; возвратом (ср. gfx_put_char в gfx/pr.asm)
loader_go:
        ; --- 1) blob под 0E000h ---
        push hl                     ; конфиг доживёт до своего копира
        lxi de, loader_stage2       ; DE = источник, HL = назначение — как в
        lxi hl, LOADER_STAGE2_ADR   ; исходном копире этого файла. Обратный
        lxi bc, LOADER_STAGE2_SIZE  ; порядок тоже легален (LD (DE),A = STAX D,
        call cpbl                   ; 12h), но плодит ещё одну пару инкрементов
        pop hl

        ; --- 2) конфиг: 14 байт struct как есть в 0E840h ---
        ; (первые 10 — цвета и дескрипторы, их читает stage-2; два указателя
        ; на данные панелей — +10/+12, их читает только копир ниже)
        ld e, l                     ; MOV E,L / MOV D,H: struct становится
        ld d, h                     ;   источником пары DE
        lxi hl, LOADER_CFG_ADR
        lxi bc, LOADER_CFG_SIZE
        call cpbl

        ; --- 3) данные панелей в слоты; wb = 0 значит «панели нет» ---
        ; панель 1: wb/h в 0E844h/0E845h, указатель данных в 0E84Ah.., слот 0E860h
        ld a, (LOADER_CFG_ADR + 5)  ; h — счётчик сложений
        ld b, a
        ld a, (LOADER_CFG_ADR + 11) ; старший байт указателя данных
        ld d, a
        ld a, (LOADER_CFG_ADR + 10)
        ld e, a                     ; DE = источник (ROM заставки)
        lxi hl, LOADER_P1_ADR       ; HL = слот назначения
        ld a, (LOADER_CFG_ADR + 4)  ; wb — последним: pncpy ждёт его в A
        call pncpy

        ; панель 2: wb/h в 0E848h/0E849h, указатель в 0E84Ch.., слот 0F060h
        ld a, (LOADER_CFG_ADR + 9)
        ld b, a
        ld a, (LOADER_CFG_ADR + 13)
        ld d, a
        ld a, (LOADER_CFG_ADR + 12)
        ld e, a
        lxi hl, LOADER_P2_ADR
        ld a, (LOADER_CFG_ADR + 8)
        call pncpy

        jp LOADER_STAGE2_ADR        ; управление уходит stage-2 навсегда

; ---------------------------------------------------------------
; pncpy: данные панели в слот high RAM. Вход: A = wb, B = h,
; DE = источник (указатель из struct), HL = слот назначения.
; Длина = wb*h считается сложением: таблицы и самомодификации тут дороже,
; а 16-битного умножения в 8080 нет.
; ---------------------------------------------------------------
pncpy:  ld c, a                   ; MOV C,A — wb переживёт проверку в A
        or a
        ret z                     ; wb = 0: панели нет (дефолтный конфиг)
        ld a, b
        or a
        ret z                     ; h = 0: на BC = 0 копир вылил бы 64 КБ
        push de                   ; источник
        push hl                   ; слот назначения
        ld a, c
        ld d, 0
        ld e, a                   ; DE = wb (множимое)
        ld h, d
        ld l, d                   ; HL = 0 (сумма)
pn1:    add hl, de                ; DAD D — 8080; флаги, кроме C, не трогает
        dec b                     ; DCR B
        jp nz, pn1
        ld b, h                   ; MOV B,H
        ld c, l                   ; MOV C,L — BC = wb*h
        pop hl                    ; слот назначения
        pop de                    ; источник
        jp cpbl                   ; хвостовой вызов: ret из cpbl вернёт сюда

; ---------------------------------------------------------------
; cpbl: побайтовый копир. Вход: DE = источник, HL = назначение,
; BC = длина. Все четыре пересылки — штатные 8080: LD A,(DE) = LDAX D
; (1Ah), LD (HL),A = MOV M,A (77h), INX D, INX H, DCX B.
; ---------------------------------------------------------------
cpbl:   ld a, (de)                  ; LDAX D — легальный 8080-опкод
        ld (hl), a                  ; MOV M,A
        inc de                      ; INX D
        inc hl                      ; INX H
        dec bc                      ; DCX B — уменьшаем ПАРУ: вариант
        ld a, b                     ;   «dec c / or b» сюда не годится
        or c                        ;   при length > 0FFh
        jp nz, cpbl                 ; (jp nz, — с запятой: иначе это JMP)
        ret

cfg_default:
        db      080h                ; фон: голубой, как на эталоне
        db      02dh                ; линии: жёлтый
        db      0, 0, 0, 0          ; панель 1: x, y, wb = 0 (нет)
        db      0, 0, 0, 0          ; панель 2: то же
        db      0, 0                ; указатель данных 1
        db      0, 0                ; указатель данных 2

