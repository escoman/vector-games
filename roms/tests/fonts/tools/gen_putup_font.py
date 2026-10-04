#!/usr/bin/env python3
"""Генератор putup_font.asm — шрифт PUTUP как подключаемый шрифт lib/gfx.

Вход:  tools/glyph_block.bin (256 глифов x 32 байта = 4 плоскости x 8 строк),
       снятый с RUNTIME RAM запущенного putup.rom — см. dump_glyph_block.py.

Отбор глифов. В блоке «правильный» глиф шрифта удовлетворяет двум условиям:
plane1 == plane0 и plane3 == ~plane0 (так утверждает разбор PUTUP, и это
видно по кодам 0x20..0x5F и 0xE1..0xFF). Строчных букв в шрифте PUTUP нет:
коды 0x61..0x7A занимают другие данные, условию они не следуют — берём
только верхний регистр. Запрошенные коды, не прошедшие проверку,
отбрасываются (из верхнего регистра это 'Ч': его плоскости в блоке мусорные).

Формат выхода — контракт lib/gfx/pr.asm:
  * таблица имён (0 = конец), индекс глифа = позиция символа;
  * глифы 8 байт, строка 0 = ВЕРХНЯЯ (в блоке PUTUP строки идут снизу вверх,
    поэтому разворачиваем);
  * дескриптор _putup_font (4 слова: chars, glyphs, first_code, last_code),
    метка с подчёркиванием — так его видит C (sccz80 добавляет _ к имени).

Второй дескриптор, _putup_digits, — те же 10 цифр в режиме прямого индекса
(chars = 0, границы 0x30..0x39) — без таблицы имён вовсе.

Запуск:  python3 tools/gen_putup_font.py
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BLOCK = HERE / 'glyph_block.bin'
OUT = HERE.parent / 'putup_font.asm'
ROWS, STRIDE = 8, 32

raw = BLOCK.read_bytes()
assert len(raw) == 256 * STRIDE, len(raw)


def planes(code):
    base = code * STRIDE
    return [raw[base + p * ROWS: base + (p + 1) * ROWS] for p in range(4)]


def is_font_glyph(code):
    """Есть ли в коде настоящий глиф шрифта (а не мусор чужих плоскостей)."""
    p0, p1, _, p3 = planes(code)
    if not any(p0):
        return False
    return p1 == p0 and p3 == bytes(b ^ 0xFF for b in p0)


def koi(ch):
    return ch.encode('koi8-r')[0]


# Верхний регистр: ASCII 0x20..0x5F + кириллица KOI8-R 0xE1..0xFF.
ASCII = [c for c in range(0x20, 0x60)]
CYR_UPPER = 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'

codes, skipped = [], []
for code in ASCII + [koi(ch) for ch in CYR_UPPER]:
    # Пробел пустой по определению, но он обязан быть глифом 0.
    (codes if code == 0x20 or is_font_glyph(code) else skipped).append(code)


def label(code):
    """Человеческое имя кода для комментариев."""
    if 0x20 <= code <= 0x7E:
        return chr(code)
    return bytes([code]).decode('koi8-r')


skipped_desc = ', '.join(f'{c:#04x} ({label(c)})' for c in skipped)

# Пробел обязан быть первым: он же глиф 0 = «неизвестный символ».
assert codes[0] == 0x20, f'первый код не пробел: {codes[0]:#04x}'


lines = []
lines.append(';')
lines.append('; putup_font.asm — шрифт игры PUTUP ("Ну, погоди!") как подключаемый')
lines.append('; шрифт для lib/gfx/pr.asm. Тест roms/tests/fonts печатает им текст')
lines.append('; рядом со шрифтом по умолчанию, меняя текущий шрифт gfx_select_font().')
lines.append(';')
lines.append('; Источник: RUNTIME-блок глифов putup.rom @0x6000 (256 глифов x 32 байта,')
lines.append('; 4 плоскости x 8 строк), плоскость 0 — сам битмап. Строки в блоке лежат')
lines.append('; снизу вверх (байт 0 = нижняя строка), в формате pr.asm байт 0 = верхняя,')
lines.append('; поэтому строки развёрнуты. Кодировка источника — KOI8-R, в PUTUP индекс')
lines.append('; глифа равен коду символа; здесь код переведён в таблицу имён (pr.asm')
lines.append('; ищет символ в таблице и рисует глиф с его позицией), поэтому глифы')
lines.append('; идут в порядке таблицы ниже.')
lines.append(';')
lines.append('; Строчных букв в шрифте PUTUP нет: коды 0x61..0x7A в блоке занимают')
lines.append('; другие данные (условие plane1==plane0, plane3==~plane0 для них не')
lines.append('; выполняется). Из запрошенных кодов проверку не прошли: ' + skipped_desc)
lines.append(';')
lines.append('; Глифов: ' + str(len(codes)) + ' (данные — ' + str(len(codes) * ROWS) + ' байт),')
lines.append('; плюс дескриптор прямого индекса для цифр (10 глифов, 80 байт).')
lines.append('; Сгенерировано tools/gen_putup_font.py, руками не править.')
lines.append(';')
lines.append('        SECTION code_clib')
lines.append('        PUBLIC  _putup_font')
lines.append('        PUBLIC  _putup_digits')
lines.append('')
lines.append('; ---------------------------------------------------------------')
lines.append('; Таблица имён: символы в том же порядке, что глифы ниже.')
lines.append('; ---------------------------------------------------------------')
lines.append('')
lines.append('putup_chars:')

# defm для печатаемых подряд, defb для остальных — как в default_8x8.inc.
# Кавычку и обратный слэш в defm не берём: экранирование в z80asm двусмысленно.
run = []
for code in codes:
    printable = 0x20 <= code <= 0x7E and code not in (ord('"'), ord('\\'))
    if not printable and run:
        lines.append(f'        defm    "{"".join(chr(c) for c in run)}"')
        run = []
    if not printable:
        lines.append(f"        defb    0x{code:02X}            ; '{label(code)}'")
        continue
    run.append(code)
if run:
    lines.append(f'        defm    "{"".join(chr(c) for c in run)}"')
lines.append('        defb    0')
lines.append('')
lines.append('; ---------------------------------------------------------------')
lines.append('; Глифы 8x8: строка 0 — верхняя, бит 7 — левый пиксель.')
lines.append('; ---------------------------------------------------------------')
lines.append('')
lines.append('putup_glyphs:')
for code in codes:
    rows = planes(code)[0][::-1]
    body = ', '.join(f'0x{b:02X}' for b in rows)
    name = label(code)
    comment = name if 0x20 <= code <= 0x7E else f'{name} (KOI8-R)'
    lines.append(f'        defb    {body} ; \'{comment}\'')
lines.append('')
lines.append('; ---------------------------------------------------------------')
lines.append('; Дескриптор (gfx_font_t в v06.h): таблица имён, данные глифов,')
lines.append('; first_code/last_code (в режиме таблицы имён не используются).')
lines.append('; ---------------------------------------------------------------')
lines.append('')
lines.append('_putup_font:')
lines.append('        defw    putup_chars')
lines.append('        defw    putup_glyphs')
lines.append('        defw    0')
lines.append('        defw    0')
lines.append('')

# --- то же десятью цифрами, но прямым индексом -------------------------
DIGITS = list(range(0x30, 0x3A))
assert all(is_font_glyph(c) for c in DIGITS)

lines.append('; ---------------------------------------------------------------')
lines.append('; Те же цифры 0x30..0x39, но в режиме прямого индекса: chars = 0,')
lines.append('; поэтому таблицы имён нет, а глиф берётся как')
lines.append('; putup_digits_glyphs + (код - 0x30) * 8. Поиск — два сравнения')
lines.append('; вместо обхода ' + str(len(codes)) + ' записей, индекс — 0 байт вместо')
lines.append('; ' + str(len(codes)) + '. Коды вне диапазона pr.asm пропускает: клетка')
lines.append('; остаётся нетронутой (см. roms/tests/fonts/main.c, строка "123 ABC 456").')
lines.append('; ---------------------------------------------------------------')
lines.append('')
lines.append('putup_digits_glyphs:')
for code in DIGITS:
    rows = planes(code)[0][::-1]
    body = ', '.join(f'0x{b:02X}' for b in rows)
    lines.append(f"        defb    {body} ; '{chr(code)}'")
lines.append('')
lines.append('_putup_digits:')
lines.append('        defw    0                       ; chars = 0: прямой индекс')
lines.append('        defw    putup_digits_glyphs')
lines.append('        defw    0x30                    ; first_code')
lines.append('        defw    0x39                    ; last_code')
lines.append('')

OUT.write_text('\n'.join(lines), encoding='utf-8')
print(f'{OUT}: {len(codes)} глифов, {len(codes) * ROWS} байт данных, '
      f'{len(lines)} строк')
print('пропущено кодов:', skipped_desc)

# --- подсказка для main.c: строки KOI8-R как восьмеричные экранизации ---
print('\n--- фразы для main.c (KOI8-R) ---')
for phrase in ('НУ, ПОГОДИ!', 'ВЕКТОР 06Ц', 'ШРИФТ ПУТАП'):
    esc = ''.join(f'\\{c:03o}' for c in phrase.encode('koi8-r'))
    print(f'{phrase!r:24} -> "{esc}"')
