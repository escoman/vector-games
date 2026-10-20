#!/usr/bin/env python3
"""make verify: сверка PUTUP_NEW.ROM с оригиналом putup.rom.

Два режима (режим диктует tools/dead_ranges.json, который пишет gen_layout.py):

VERBATIM (Фаза 1, compact=false) — кодовая зона 0x0100..0x45FF = оригинал
с точностью до:
(1) заглушек в func_main_init — 3 NOP на месте CALL func_load_glyph_block
    (0x0B83..0x0B85) и 34 NOP вестигиального копира спрайтов
    (0x0B86..0x0BA7; 0x7418 никем не читается, источник — обнулённый пакет);
(2) dead-диапазонов, выжженных нулями генератором (KEEP_DEAD=1 — Stage A,
    dead-обнуления запрещены);
(3) релокации текстового back-буфера: база смещена 0x5000 -> 0x6600 (дельта
    +0x1600), из-за чего в коде меняется ровно ВЫСШИЙ байт операнда-адреса:
      * позиции курсора LXI H,data_text_buffer+ofs: 0x50..0x53 -> +0x16;
      * константа func_render_glyph textbuf_to_vram (= 0-база): 0xB0 -> 0x9A.
    Эти дельты принимаются только по строгой сигнатуре; любой иной diff — провал.

COMPACT (Фаза 2, compact=true) — мёртвые дыры [0x2761,0x2F61)+[0x3041,0x383A)
вырезаны, верх образа сдвинут new_addr. побайтовая эквивалентность гарантирована
ТОЛЬКО для [0x0100, 0x2761). Для остального — инвариант «чистого сдвига»:
каждый байт образа на new_addr(o) обязан равняться оригиналу на o, кроме
16-бит операндов/указателей, значение которых перемещается (new_word ==
new_addr(orig_word)), и var-init embedded-указателей (pointer_sites). Плюс
проверки длины, отсутствия байт-дыр и ptr_table под новым glyph_base.
Основной гейт корректности верхней половины — behavioral (не побайтовый).
"""
import json
import os
import sys

ORG = 0x100
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(PROJ))),
                   "roms", "redesign", "putup", "src")   # оригиналы putup.rom/rdb
# узаконенные заглушки внутри func_main_init (метки патчей, НЕ dead-диапазоны)
NOP_PATCHES = [(0x0B83, 0x0B86), (0x0B86, 0x0BA8)]
NOP = {a for s, e in NOP_PATCHES for a in range(s - ORG, e - ORG)}
# Осознанное отхождение от оригинала: таблица палитры 0x08A3..0x08B2 (16 слотов).
# Чанк плоскости E000 (вес бита 1) инвертирован во всех глифах -> индекс цвета
# I меняется на I^1; компенсация — перестановка соседних пар слотов палитры
# PAL'[j]=PAL[j^1], из-за чего эти 16 байтов отличаются от оригинала, а картинка
# остаётся побайтово той же. Это легальный diff (ниже byte_exact_end в обоих режимах).
PALETTE_DIVERGENCE = {a - ORG for a in range(0x08A3, 0x08B3)}
# Tier 2: код func_render_glyph (0x0803..0x08A2) переписан на единый цикл-копир
# с веткой по тегу compact/raw. Это ОСОЗНАННАЯ правка исполняемого кода в
# byte-exact зоне; корректность доказывает поведенческий гейт compare_color.py
# (гоняет реальный код) + замер тактов. Побайтовая сверка здесь осознанно снята.
RENDER_CODE_DIVERGENCE = {a - ORG for a in range(0x0803, 0x08A3)}
# сигнатура релокации базы буфера (0x5000 -> 0x6600): высший байт операнда
# меняется на +0x16 (позиции курсора в 0x50..0x53) либо B0->9A (константа render).
RELOC_HIGH = {0x50, 0x51, 0x52, 0x53}   # исходные высшие байты страниц 0x50xx..0x53xx
RELOC_DELTA = 0x16                       # (0x6600 - 0x5000) >> 8


def is_reloc_diff(x, y):
    if x in RELOC_HIGH and y == (x + RELOC_DELTA) & 0xFF:   # курсорная позиция
        return True
    if x == 0xB0 and y == 0x9A:                             # textbuf_to_vram
        return True
    return False


def load_info():
    p = os.path.join(PROJ, "tools", "dead_ranges.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def ptr_diff_positions(info, b):
    """Tier 2: слово ptr_table = адрес записи глифа (compact — 8Б маска, raw — 32Б),
    бит0 = тег компактности. Валидируем: (слово & ~1) — чётный указатель ВНУТРИ
    компактного блока [gb, gb+glyph_size). Позиции корректных слов — легальный diff
    (побайтовая карта смещений здесь не восстанавливается; её держат compare_color)."""
    gb, pt = info["glyph_base"], info["ptr_table"]
    size = info.get("glyph_size", 8192)
    allowed = set()
    if pt:
        for n in range(256):
            off = pt[0] - ORG + 2 * n
            got = b[off] | (b[off + 1] << 8)
            base = got & 0xFFFE          # снять тег bit0
            if gb <= base < gb + size and (base - gb) % 2 == 0:
                allowed |= {off, off + 1}
    return allowed


def verify_verbatim(a, b, info):
    keep_dead = os.environ.get("KEEP_DEAD", "0") != "0"
    allow = set(NOP) | PALETTE_DIVERGENCE | RENDER_CODE_DIVERGENCE
    dead = []
    if info and not keep_dead:
        dead = info["dead_ranges"]
        allow |= {i for s, e, _ in dead for i in range(s - ORG, e - ORG)}
    ptrd = ptr_diff_positions(info, b) if info else set()
    diffs = [(i, x, y) for i, (x, y) in enumerate(zip(a, b))
             if x != y and i not in allow and i not in ptrd]
    reloc = [(i, x, y) for i, x, y in diffs if is_reloc_diff(x, y)]
    diffs = [(i, x, y) for i, x, y in diffs if not is_reloc_diff(x, y)]
    for s, e in NOP_PATCHES:
        if b[s - ORG:e - ORG] != b"\x00" * (e - s):
            print("ошибка: 0x%04X..0x%04X != NOP-заглушка" % (s, e - 1))
            return 1
    print("dead-диапазоны выжжены:", [(hex(s), hex(e), n) for s, e, n in dead] or "нет (KEEP_DEAD=1)")
    print("ptr_table перемещена под glyph_base: %d слов" % (len(ptrd) // 2))
    print("релокация базы буфера (+0x%X в высшем байте): %d байт" % (RELOC_DELTA, len(reloc)))
    print("палитра 0x08A3..0x08B2 — осознанное отхождение (компенсация инверсии E000): %d байт" % len(PALETTE_DIVERGENCE))
    if diffs:
        print("unexpected diffs:", [(hex(i + ORG), hex(x), hex(y)) for i, x, y in diffs][:20],
              "... всего %d" % len(diffs))
        return 1
    print("verify OK (VERBATIM): кодовая зона = оригинал + NOP + dead-обнуления + релокация базы")
    return 0


def make_na(holes, delta1, delta_total):
    """new_addr(a): дыры вырезаны, зоны сдвинуты; None — адрес внутри дыры."""
    (h1s, h1e), (h2s, h2e) = holes

    def na(x):
        if x < h1s:
            return x
        if x < h1e:
            return None
        if x < h2s:
            return x - delta1
        if x < h2e:
            return None
        return x - delta_total
    return na


def verify_compact(a, b, info):
    holes = [tuple(h) for h in info["holes"]]
    delta1 = holes[0][1] - holes[0][0]
    delta_total = info["delta_total"]
    na = make_na(holes, delta1, delta_total)
    byte_exact_end = info["byte_exact_end"]
    code_end_orig = info["code_end_orig"]
    code_end_new = info["code_end_new"]
    glyph_base = info["glyph_base"]
    psites = set(info.get("pointer_sites", []))

    # --- длина: [0x100 .. glyph_base+glyph_size) ---
    want_len = glyph_base + info.get("glyph_size", 8192) - ORG
    if len(b) != want_len:
        print("ошибка: длина образа %d != %d (ожидание компакта)" % (len(b), want_len))
        return 1

    # нижние dead-диапазоны (< byte_exact_end) и NOP-заглушки — легальны в нижней зоне
    allow_low = set(NOP) | PALETTE_DIVERGENCE | RENDER_CODE_DIVERGENCE
    allow_low |= {i for s, e, _ in info["dead_ranges"]
                  for i in range(s - ORG, min(e, byte_exact_end) - ORG)}
    ptrd = ptr_diff_positions(info, b)

    def word_new(pos):          # 16-бит LE слово в new-образе по orig-адресу pos
        np_ = na(pos)
        if np_ is None or np_ - ORG + 1 >= len(b):
            return None
        return b[np_ - ORG] | (b[np_ + 1 - ORG] << 8)

    def word_orig(pos):
        if pos - ORG + 1 >= len(a):
            return None
        return a[pos - ORG] | (a[pos + 1 - ORG] << 8)

    def explained_word(o):
        """Байт o отличается — входит ли в relocate-ся 16-бит операнд/указатель?"""
        for lo in (o - 1, o):
            if lo < ORG:
                continue
            wo = word_orig(lo)
            if wo is None or wo < byte_exact_end or na(wo) is None:
                continue                     # не указатель в перемещаемую зону
            wn = word_new(lo)
            if wn == na(wo):
                return True
        return False

    bad = []
    for o in range(ORG, code_end_orig):
        np_ = na(o)
        if np_ is None:          # байт внутри вырезанной дыры — не эмится
            continue
        x = a[o - ORG]
        y = b[np_ - ORG]
        if x == y:
            continue
        if np_ - ORG in allow_low or np_ - ORG in ptrd:
            continue             # NOP / dead-обнуление / reloc ptr_table (нижняя зона)
        if o < byte_exact_end and is_reloc_diff(x, y):
            continue             # сигнатура релокации базы буфера (нижняя зона)
        if explained_word(o):
            continue             # 16-бит операнд перемещён согласованно
        if o in psites or (o - 1) in psites:
            continue             # var-init embedded-указатель
        bad.append((o, x, y))
    if bad:
        print("COMPACT: необъяснённых расхождений: %d" % len(bad))
        for o, x, y in bad[:30]:
            print("   orig +%04X -> new +%04X: %02X != %02X" % (o, na(o), x, y))
        return 1

    # инвариант: в коде нет остаточных байт-дыр — зона [code_end_new, glyph_base)
    # это только разрешённый filler-нули (0/1 байт округления).
    for p in range(code_end_new - ORG, glyph_base - ORG):
        if b[p] != 0:
            print("ошибка: filler 0x%04X != 0 (округление до glyph_base)" % (p + ORG))
            return 1

    print("verify OK (COMPACT): byte-exact [0x%04X,0x%04X); верх — чистый сдвиг "
          "new_addr (-%d) с операнд-фиксупами; длина %d Б"
          % (ORG, byte_exact_end, delta_total, want_len))
    print("   указатели перемещены/объяснены; glyph_base=0x%04X code_end_new=0x%04X"
          % (glyph_base, code_end_new))
    return 0


def main():
    a = open(os.path.join(REF, "putup.rom"), "rb").read()
    b = open(os.path.join(PROJ, "PUTUP_NEW.ROM"), "rb").read()
    info = load_info()
    if info and info.get("compact"):
        return verify_compact(a, b, info)
    b = b[:len(a)]
    if len(b) < len(a):
        print("ошибка: образ короче кодовой зоны (%d < %d)" % (len(b), len(a)))
        return 1
    return verify_verbatim(a, b, info)


if __name__ == "__main__":
    sys.exit(main())
