;
; loader.asm — вызов второго загрузчика (stage-2) из ROM заставки.
; ТЗ: docs/LOADER_TZ.MD, сам blob: boot/loader_stage2.asm.
;
;   void loader_boot(void);
;
; НЕ возвращается: копия stage-2 в 0xE000h стирает машину вместе с кодом
; заставки, поэтому возврат сюда физически невозможен.
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
; Команды — только КР580ВМ80А.
;

        SECTION code_clib
        PUBLIC  loader_boot
        PUBLIC  _loader_boot

        INCLUDE "loader_stage2.inc"

LOADER_STAGE2_ADR equ 0e000h        ; адрес, под который собран blob

loader_boot:
_loader_boot:
        di                        ; F3h — он же в i8080, прерывания гасим сразу
        ld      de, loader_stage2   ; источник: массив в коде ROM
        ld      hl, LOADER_STAGE2_ADR
        ld      bc, LOADER_STAGE2_SIZE
cp1:    ld      a, (de)             ; LDAX D — легальный 8080-опкод
        ld      (hl), a             ; MOV M,A
        inc     de                  ; INX D
        inc     hl                  ; INX H
        dec     bc                  ; DCX B (0Bh) — уменьшаем ПАРУ: вариант
        ld      a, b                ;   «dec c / or b» сюда не годится, B = 01h
        or      c                   ;   и он никогда не обнулился бы
        jp      nz, cp1             ; (jp nz, — с запятой: иначе это JMP)
        jp      LOADER_STAGE2_ADR   ; управление уходит stage-2 навсегда
