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
; 0000h..DFFFh: сам blob, 14 байт конфига и РАЗУПАКОВАННЫЕ панели (в ROM они
; лежат сжатыми ZX0, стаб вызывает zx0_decompress). Указатели в struct —
; адреса сжатых потоков внутри этой ROM; после стирания они были бы мусор,
; поэтому распаковка делается здесь, до прыжка в stage-2.
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
LOADER_CFG_ADR    equ 0fb10h        ; конфиг stage-2 (ТЗ §4.2, §5.2)
LOADER_CFG_SIZE   equ 14            ; bg, line, 2x(x,y,wb,h), 2x указатель
; Слоты данных панелей — ФОРМУЛА base + номер·stride (ТЗ §2.1): рост одной
; панели в пределах stride не сдвигает соседнюю и не требует правки адресов
; ни здесь, ни в v06.h. Панели в ROM лежат сжатыми ZX0 — распаковывает
; zx0_decompress (lib/unpack/zx0.asm), отсюда EXTERN.
LOADER_PANEL_BASE   equ 0e300h      ; слот панели 0 — сразу за кодом blob
LOADER_PANEL_STRIDE equ 0c00h       ; 3 КБ на панель (= бюджет png2panel --slot)
LOADER_P1_ADR       equ LOADER_PANEL_BASE                        ; панель 1: +0
LOADER_P2_ADR       equ LOADER_PANEL_BASE + LOADER_PANEL_STRIDE  ; панель 2: +1
        extern  _zx0_decompress     ; void zx0_decompress(const uchar*, uchar*)

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

        ; --- 2) конфиг: 14 байт struct как есть в 0FB10h ---
        ; (первые 10 — цвета и дескрипторы, их читает stage-2; два указателя
        ; на данные панелей — +10/+12, их читает только копир ниже)
        ld e, l                     ; MOV E,L / MOV D,H: struct становится
        ld d, h                     ;   источником пары DE
        lxi hl, LOADER_CFG_ADR
        lxi bc, LOADER_CFG_SIZE
        call cpbl

        ; --- 3) панели: распаковать ZX0-поток из ROM в слот; wb = 0 — нет ---
        ; src — указатель на сжатый поток в struct (+10 / +12), dst — слот.
        ; zx0_decompress читает аргументы со стека (1-й src глубже, 2-й dst
        ; ближе) и не знает длины: поток кончается EOF-маркером Elias(256).
        ld a, (LOADER_CFG_ADR + 4)  ; wb панели 1
        or a
        jp z, unp2                  ; wb = 0: панели нет
        ld a, (LOADER_CFG_ADR + 11) ; старший байт указателя src
        ld d, a
        ld a, (LOADER_CFG_ADR + 10)
        ld e, a                     ; DE = src (сжатый поток в ROM)
        lxi h, LOADER_P1_ADR        ; HL = dst (слот панели 1)
        call zx_unpack

        ; панель 2: wb в 0FB18h, указатель src в 0FB1Ch.., слот 0EF00h
unp2:   ld a, (LOADER_CFG_ADR + 8)  ; wb панели 2
        or a
        jp z, unp_go                ; панели нет
        ld a, (LOADER_CFG_ADR + 13)
        ld d, a
        ld a, (LOADER_CFG_ADR + 12)
        ld e, a
        lxi h, LOADER_P2_ADR
        call zx_unpack

unp_go: jp LOADER_STAGE2_ADR        ; управление уходит stage-2 навсегда

; ---------------------------------------------------------------
; zx_unpack: распаковать ZX0-поток панели в слот. Вход: DE = src (сжатый
; поток в ROM), HL = dst (слот high RAM). Обёртка под соглашение вызова
; z88dk classic C-функции zx0_decompress(src, dst): первый аргумент лежит
; глубже всех, поэтому src пушим ПЕРВЫМ; стек чистит вызывающий.
; ---------------------------------------------------------------
zx_unpack:
        push de                     ; src  — первый аргумент (глубже)
        push hl                     ; dst  — второй (ближе к SP, sp+2)
        call _zx0_decompress
        pop de                      ; caller cleans: снять оба аргумента
        pop de
        ret

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

