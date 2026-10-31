#!/usr/bin/env python3
"""
gen_push.py — генератор spr_push.asm: спрайт как функция, вывод в VRAM через PUSH.

Идея (максимально «хардкорный» вариант SPR_FORMAT):
  * каждый спрайт — самостоятельная функция, данные лежат ПРЯМО В ЕЁ КОДЕ:
    пара строк столбца — это `lxi b, imm16` (байты внутри кода), а не блок
    данных по указателю;
  * на время вывода SP уводится в видеопамять (sphl), и строки выплёвываются
    через `push b`: 8080 кладёт пару по убывающим адресам, а внутри столбца
    экрана адрес убывает вниз по экрану — то есть один PUSH пишет ДВЕ
    соседние строки, старший байт (B) — верхняя, младший (C) — нижняя;
  * весь вывод идёт под `di`: SP в VRAM, кадровое прерывание не должно
    толкать туда стек. SP сохраняется в pu_sp (DAD SP / SHLD — 8080 не умеет
    `ld (nn),sp`) и восстанавливается перед `ei`/`ret`.

Цена записи: lxi b (10 тактов) + push b (11) = 21 такт на 2 байта, то есть
10.5 такта на байт против 24 у «лесенки» SMC (ldax d / mov m,a / inx d / dcx h).

Запись ПЛОТНАЯ: все 32 строки столбца, включая прозрачные нули, поэтому
отдельный erase_sprite_box под спрайтом не нужен — нули затирают фон сами.

Вход: mario_old.inc (tile-prefab, источник истины) — колонки и плоскости
берутся тем же разбором, что и в convert_spr.py, чтобы байт-в-байт совпадать
с draw_sprite_new / draw_sprite_smc / draw_sprite_stub.
Выход: spr_push.asm (руками не править).
"""

import re
from pathlib import Path

from convert_spr import parse_old_format, build_columns

HERE = Path(__file__).resolve().parent
OLD_INC = HERE / 'mario_old.inc'
OUT_ASM = HERE / 'spr_push.asm'

# Смещение плоскости от базы П3 (0x8000) в единицах старшего байта адреса:
# П3 = 0x8000, П2 = 0xA000, П1 = 0xC000, П0 = 0xE000 — шаг 0x2000 = 0x20.
PLANE_OFF = {3: 0x00, 2: 0x20, 1: 0x40, 0: 0x60}
PLANE_NAME = {3: 'П3', 2: 'П2', 1: 'П1', 0: 'П0'}

# Соответствие «имя массива в mario_old.inc» -> «имя функции в spr_push.asm»
SPRITES = [('mario1_l', 'mario1', 'фаза 0 (ноги вместе)'),
           ('mario2_l', 'mario2', 'фаза 1 (шаг вперёд)'),
           ('mario3_l', 'mario3', 'фаза 2 (широкий шаг)')]

COL_COMMENT = 32                # комментарии — с этой колонки, как в spr_smc.asm


def hx8(v):
    """Литерал байта для z80asm: в строгом 8080 нужен суффикс h и первая
    цифра 0..9 (0C0h, 0E1h, 0FFh)."""
    s = f'{v & 0xFF:02X}'
    return ('0' + s if s[0] in 'ABCDEF' else s) + 'h'


def hx16(v):
    s = f'{v & 0xFFFF:04X}'
    return ('0' + s if s[0] in 'ABCDEF' else s) + 'h'


def ins(code, comment=None):
    """Строка инструкции с выравниванием комментария по COL_COMMENT."""
    line = f'        {code}'
    if comment is None:
        return line
    pad = ' ' * max(1, COL_COMMENT - len(line))
    return f'{line}{pad}; {comment}'


def read_old_arrays():
    """Разбор mario_old.inc: имя массива -> список байт."""
    text = OLD_INC.read_text()
    arrays = {}
    for m in re.finditer(r'static const unsigned char (\w+)\[\] = \{([^}]+)\}', text):
        arrays[m.group(1)] = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', m.group(2))]
    return arrays


def column_words(rows):
    """Строки столбца сверху вниз -> слова для `lxi b`:
    (строка 0) << 8 | (строка 1). Первый PUSH пишет старший байт в строку 0,
    младший — в строку 1."""
    rows = list(rows)
    if len(rows) % 2:
        rows.append(0)
    return [(rows[i] << 8) | rows[i + 1] for i in range(0, len(rows), 2)]


def emit_function(name, comment, planes, cols, rows_total):
    """Одна функция-спрайт: пролог, прогоны PUSH по плоскостям, эпилог.
    planes: {номер плоскости: [[байты столбца], ...]}"""
    out = []
    w = out.append

    w('; ---------------------------------------------------------------')
    w(f'; {comment}')
    w(f'; {cols} столбца x {rows_total} строк, плоскости '
      + ' + '.join(PLANE_NAME[p] for p in planes))
    w('; ---------------------------------------------------------------')
    w(f'_spr_push_{name}:')

    # Пролог: снять аргументы (__z88dk_callee, стек: ret, y, x), вернуть ret.
    w(ins('pop     d', 'ret'))
    w(ins('pop     h'))
    w(ins('mov     a, l'))
    w(ins('sta     pu_y', 'y — верх спрайта'))
    w(ins('pop     h'))
    w(ins('mov     a, l'))
    w(ins('sta     pu_x', 'x — левый край (кратен 8)'))
    w(ins('push    d', 'ret обратно на стек: дальше SP уедет в VRAM'))
    w('')
    w(ins('di', 'SP в VRAM — кадровое прерывание трогать стек не должно'))
    w(ins('lxi     h, 0'))
    w(ins('dad     sp', '8080 не умеет ld (nn),sp'))
    w(ins('shld    pu_sp', 'SP на входе в функцию'))
    w('')
    w(ins('; HL = 0x8000 + (x/8)*256 + (255-y) — верх левого столбца П3'))
    w(ins('lda     pu_x'))
    w(ins('ora     a', 'CY=0, иначе rar вставит бит переноса в H'))
    w(ins('rar'))
    w(ins('rar'))
    w(ins('rar'))
    w(ins('mov     h, a'))
    w(ins('mvi     l, 0'))
    w(ins('mov     a, h'))
    w(ins('adi     80h'))
    w(ins('mov     h, a'))
    w(ins('lda     pu_y'))
    w(ins('cma'))
    w(ins('mov     l, a', 'L = 255-y — строка 0 столбца'))

    prev_off = None
    plane_keys = list(planes)
    for p in plane_keys:
        off = PLANE_OFF[p]
        w('')
        w(ins(f'; --- {PLANE_NAME[p]} ({0x8000 + off * 0x100:04X}h) ---'))
        # ИНВАРИАНТ: HL = верх текущего столбца + 1 (ровно то, что нужно в SP).
        # Первая плоскость: HL = верх левого столбца П3 — +1 делается ниже,
        # в «inx h» первого столбца. Следующие: прогон PUSH оставил HL = верх
        # ПОСЛЕДНЕГО столбца предыдущей плоскости + 1 — его и переводим на
        # базу новой плоскости.
        if prev_off is None:
            delta = off
            note = 'база плоскости (HL = верх П3)'
        else:
            delta = off - prev_off - (cols - 1)
            note = 'база плоскости минус уже пройденные столбцы'
        w(ins('mov     a, h'))
        w(ins(f'adi     {hx8(delta)}', note))
        w(ins('mov     h, a'))

        for c in range(cols):
            words = column_words(planes[p][c])
            w('')
            w(ins(f'; ------- {PLANE_NAME[p]}, столбец {c} -------'))
            # SP = верх столбца + 1: первый PUSH пишет строки 0 и 1.
            if c > 0:
                w(ins('inr     h', '+0x100 — следующий столбец'))
            elif prev_off is not None:
                w(ins('; HL уже = верх столбца + 1 (осталось от прошлой плоскости)'))
            else:
                w(ins('inx     h', 'SP = верх столбца + 1'))
            w(ins('sphl'))
            for i, word in enumerate(words):
                note_w = f'строки {2 * i}-{2 * i + 1}' if i % 4 == 0 else None
                w(ins(f'lxi     b, {hx16(word)}', note_w))
                w(ins('push    b'))
        prev_off = off

    w('')
    w(ins('lhld    pu_sp', 'SP ровно как был на входе'))
    w(ins('sphl'))
    w(ins('ei'))
    w(ins('ret'))
    w('')
    return out


HEADER = f'''\
; spr_push.asm — «хардкорное» ядро вывода спрайтов: PUSH прямо в видеопамять.
;
; СГЕНЕРИРОВАН gen_push.py из mario_old.inc — руками не править: правки
; вносить в генератор и пересобирать (файл уже в SRCS Makefile).
;
; Каждый спрайт — самостоятельная функция:
;   * данные спрайта лежат ПРЯМО В ЕЁ КОДЕ: пара строк столбца — это
;     `lxi b, imm16`, отдельного блока данных и указателя нет вообще;
;   * на время вывода SP уводится в видеопамять (sphl), строки выплёвываются
;     через `push b`: 8080 кладёт пару по убывающим адресам, а внутри
;     столбца экрана адрес убывает вниз — один PUSH пишет ДВЕ соседние
;     строки, B (старший) — верхняя, C — нижняя;
;   * поэтому SP ставится в «верх столбца + 1», а прогон из 16 PUSH пишет
;     ровно 32 строки столбца; следующий столбец = HL += 0x100 и sphl.
;
; Цена: lxi b (10 тактов) + push b (11) = 21 такт на 2 байта (10.5 на байт)
; против 24 тактов на байт у «лесенки» SMC. Обратная сторона — `di` на весь
; вывод: SP стоит в VRAM, а кадровое прерывание (isr_frame в
; lib/sys/startup.asm) толкает в стек af/bc/de/hl. SP сохраняется через
; DAD SP / SHLD и восстанавливается до EI, так что стык с ISR честный.
;
; Запись ПЛОТНАЯ — весь прямоугольник 8*COLS x 32, включая прозрачные нули,
; поэтому erase_sprite_box под спрайтом не нужен: нули затирают фон сами.
;
; Раскладка адресов: П3 = 8000h, П2 = A000h, П1 = C000h, П0 = E000h;
; строка r столбца c = база + 256*c + (255-y-r), то есть вниз по экрану
; адрес УБЫВАЕТ.
;
; Внешний вид (как у прочих движков): void spr_push_marioN(unsigned char x,
; unsigned int y) __z88dk_callee — x кратен 8, y — верх спрайта.
'''


def main():
    arrays = read_old_arrays()
    bodies = []
    publics = []

    for old_name, new_name, comment in SPRITES:
        if old_name not in arrays:
            raise SystemExit(f'{OLD_INC}: нет массива {old_name}')
        wcells, hcells, _hpix, tiles = parse_old_format(arrays[old_name])
        columns = build_columns(wcells, hcells, tiles)
        planes = {p: [columns[c][p] for c in range(wcells)]
                  for p in (3, 2, 1, 0)
                  if any(any(columns[c][p]) for c in range(wcells))}
        publics.append(f'        PUBLIC  _spr_push_{new_name}')
        bodies.extend(emit_function(new_name, comment, planes, wcells, hcells * 8))

    out = [HEADER, '', '        SECTION code_clib', '']
    out.extend(publics)
    out.append('')
    out.extend(bodies)
    out.append('        SECTION bss_compiler')
    out.append('pu_x:     defb    0               ; x — пиксельная координата (кратна 8)')
    out.append('pu_y:     defb    0               ; y — верх спрайта')
    out.append('pu_sp:    defw    0               ; SP функции на входе (DAD SP / SHLD)')
    out.append('')

    OUT_ASM.write_text('\n'.join(out))
    print(f'Создан {OUT_ASM}')


if __name__ == '__main__':
    main()
