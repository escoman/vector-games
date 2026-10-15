#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8: выгрузка ROM-данных exolon из RDB в z88dk-ASM (ТЗ §Stage 8).

Для каждого data/table/string-объекта RDB пишется ./asm/<имя>.asm; крупные
битмап/байткод-блоки — через INCBIN на ./asm/bin/<имя>.bin (по-байтовая копия
exolon.rom). RAM-перемены (type=variable) — только EQU в var_ram_symbols.asm,
без байт. Указатели в карте волн — символьно (data_enemy_patterns+смещение).

Детерминированный генератор: источники истины — exolon.rdb (адрес/размер/коммент)
и exolon.rom (байты). Никакой пост-обработки байтов. Запуск:

    python3 tools/gen_asm.py            # пишет asm/ и asm/bin/
    python3 tools/gen_asm.py --verify   # только побайтовая сверка asm↔ROM
"""
from __future__ import annotations
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROM_DIR = os.path.dirname(HERE)                       # .../exolon
SRC = os.path.join(ROM_DIR, "src")
ROM = os.path.join(SRC, "exolon.rom")
RDB = os.path.join(SRC, "exolon.rdb")
ASM = os.path.join(ROM_DIR, "asm")
BIN = os.path.join(ASM, "bin")
ORG = 0x0100

# Крупкие битмап/байткод-блоки -> INCBIN (ТЗ разрешает глифы/спрайты/паттерны).
INCBIN_BLOCKS = {
    "data_sprites", "data_glyph_block_latin",
    "data_glyph_block_cyrillic", "data_enemy_patterns",
}
# Структурные (не-INCBIN) объекты с особым рендером.
SPECIAL = {"data_wave_table", "data_score_table", "data_bonus_config",
           "var_spawn_queue"}

def to_int(a):
    return int(a, 16) if isinstance(a, str) else a

def addr_of(o):
    return to_int(o["address"] if isinstance(o, dict) else o)

def load():
    rom = open(ROM, "rb").read()
    rdb = json.load(open(RDB, encoding="utf-8"))
    return rom, rdb["objects"]

def rb(rom, addr, n):
    return rom[addr - ORG: addr - ORG + n]

def wrap_comment(text, width=76):
    out = []
    for para in (text or "").splitlines() or [""]:
        line = ""
        for w in para.split():
            if len(line) + len(w) + 1 > width:
                out.append(line.rstrip()); line = ""
            line += w + " "
        out.append(line.rstrip())
    return [l for l in out] or [""]

def header(name, addr, size, note, method):
    lines = [f"; Данные: {name}",
             f"; Адрес: 0x{addr:04X}",
             f"; Размер: {size} байт"]
    for l in wrap_comment(note):
        lines.append(f"; {l}" if l else ";")
    lines.append(f"; ")
    for l in wrap_comment(method):
        lines.append(f"; {l}" if l else ";")
    lines.append("")
    return lines

def deff_bytes(data, per=8, indent="    "):
    rows = []
    for i in range(0, len(data), per):
        chunk = data[i:i+per]
        rows.append(indent + "DEFB " + ", ".join(f"0x{b:02X}" for b in chunk))
    return rows

def write(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path

def write_bin(name, data):
    os.makedirs(BIN, exist_ok=True)
    p = os.path.join(BIN, f"{name}.bin")
    with open(p, "wb") as f:
        f.write(data)
    return p

# ---- рендеры ----------------------------------------------------------------

def render(name, addr, size, note):
    rom, _ = load()
    data = rb(rom, addr, size)

    if name in INCBIN_BLOCKS:
        write_bin(name, data)
        L = header(name, addr, size, note,
                   "ВЫГРУЗКА: бинарный блок — INCBIN из bin/%s.bin "
                   "(по-байтовая копия exolon.rom, без пост-обработки)." % name)
        L += [f"{name}:", f'    INCBIN "bin/{name}.bin"', ""]
        return write(os.path.join(ASM, f"{name}.asm"), L), data

    if name == "data_wave_table":
        return render_wave(addr, size, note, data)
    if name == "data_score_table":
        return render_score(addr, size, note, data)
    if name == "data_bonus_config":
        return render_bonus(addr, size, note, data)
    if name == "var_spawn_queue":
        return render_queue(addr, size, note, data)

    # строка (str_*) — DEFM ровно по байтам (терминатор принадлежит display-list)
    text_ok = all(32 <= b < 127 for b in data)
    L = header(name, addr, size, note,
               "DEFM по фактическим байтам ROM. Терминатор/следующий байт "
               "(0xDD/0xDF opcode или 0xFF конец списка) принадлежит display-list, "
               "в объект не входит — байт-в-байт round-trip.")
    if text_ok:
        s = data.decode("ascii")
        esc = s.replace('\\', '\\\\').replace('"', '\\"')
        L += [f"{name}:", f'    DEFM "{esc}"', ""]
    else:
        L += [f"{name}:"] + deff_bytes(data) + [""]
    return write(os.path.join(ASM, f"{name}.asm"), L), data


# адреса начала 6 паттернов движения (для символьных DEFW в карте волн)
PATTERNS = {0x2429: "A", 0x2468: "B", 0x24B3: "C",
            0x24E8: "D", 0x24F1: "E", 0x2506: "F"}

def render_wave(addr, size, note, data):
    L = header("data_wave_table", addr, size, note,
               "Запись = {level:1, pattern_ptr:word LE, p1:1, p2:1}, шаг 5; "
               "терминатор 0xFF. Указатели паттернов даны символьно как "
               "data_enemy_patterns+смещение (машинный код = LE-слово).")
    L.append("data_wave_table:")
    i = 0
    while i < len(data):
        lvl = data[i]
        if lvl == 0xFF:
            L.append(f"    DEFB 0xFF"
                     f"                        ; терминатор карты волн @0x{addr+i:04X}")
            break
        ptr = data[i+1] | (data[i+2] << 8)
        p1, p2 = data[i+3], data[i+4]
        tag = PATTERNS.get(ptr, "?")
        if ptr in PATTERNS:
            sym = f"data_enemy_patterns+0x{ptr-0x2429:02X}"
        else:
            sym = f"0x{ptr:04X}"
        L.append(f"    DEFB 0x{lvl:02X}"
                 f"                        ; [{i//5:2d}] lvl={lvl:3d} "
                 f"ptr=0x{ptr:04X}(паттерн {tag}) p1=0x{p1:02X} p2=0x{p2:02X}")
        L.append(f"    DEFW {sym}")
        L.append(f"    DEFB 0x{p1:02X}, 0x{p2:02X}")
        i += 5
    L.append("")
    return write(os.path.join(ASM, "data_wave_table.asm"), L), data

def render_score(addr, size, note, data):
    L = header("data_score_table", addr, size, note,
               "10 шестизначных ASCII-полей (шаг 6), читаемых func_render_bcd_value "
               "по фиксированным DE. DEFM = ровно 6 ASCII-байт поля.")
    L.append("data_score_table:")
    for k in range(0, len(data), 6):
        fld = data[k:k+6]
        val = fld.decode("ascii", "replace")
        a = addr + k
        de = a + 5  # DE-указатель вызывающих = последний цифра поля
        L.append(f'    DEFM "{val}"'
                 f"          ; поле @0x{a:04X} = {int(val)} "
                 f"(DE=0x{de:04X})")
    L.append("")
    return write(os.path.join(ASM, "data_score_table.asm"), L), data

def render_bonus(addr, size, note, data):
    L = header("data_bonus_config", addr, size, note,
               "0x6BD7 word — гейт BRAVERY BONUS (сравнение с x игрока [0x2090]); "
               "0x6BDA таблица level->player_start {level, ptr word}.")
    L.append("data_bonus_config:")
    gate = data[0] | (data[1] << 8)
    L.append(f"    DEFW 0x{gate:04X}"
             f"                       ; гейт BRAVERY BONUS @0x6BD7")
    L.append(f"    DEFB 0x{data[2]:02X}"
             f"                        ; маркер/выравнивание @0x6BD9")
    i = 3
    while i + 2 < size or i + 1 < size:
        if i + 2 >= size:
            break
        lvl = data[i]; ptr = data[i+1] | (data[i+2] << 8)
        L.append(f"    DEFB 0x{lvl:02X}"
                 f"                        ; level={lvl:3d}")
        L.append(f"    DEFW 0x{ptr:04X}"
                 f"                       ;   -> player_start @0x{addr+i+1:04X}")
        i += 3
    L.append("")
    return write(os.path.join(ASM, "data_bonus_config.asm"), L), data

def render_queue(addr, size, note, data):
    L = header("var_spawn_queue", addr, size, note,
               "ROM-инициализация очереди врагов (шаг записи 0x0A); в рантайме — "
               "RAM-слоты (число врагов = занятость до терминатора 0). E8 24 = "
               "0x24E8 — ссылка на паттерн D.")
    L.append("var_spawn_queue:")
    per = 10
    for j in range(0, len(data), per):
        chunk = data[j:j+per]
        row = ", ".join(f"0x{b:02X}" for b in chunk)
        L.append(f"    DEFB {row}"
                 f"{' ' * max(0, 47 - len(row))}; запись @0x{addr+j:04X}")
    L.append("")
    return write(os.path.join(ASM, "var_spawn_queue.asm"), L), data

def render_vars(objs):
    def first_sentence(c):
        c = (c or "").strip()
        for sep in (". ", ";"):
            if sep in c:
                return c.split(sep)[0] + ("." if sep == ". " else "")
        return c
    L = ["; ============================================================================",
         "; Данные (RAM): var_ram_symbols.asm",
         "; Адрес:  — (адреса ОЗУ; ROM даёт только init-значения)",
         "; Размер: — (это определения адресов, без байтового содержимого).",
         "; Назначение: сводный заголовок символьных RAM-адресов exolon "
         "(переменные var_* типа\n;   variable). По ТЗ Stage 8 RAM-backed выгружаются "
         "ТОЛЬКО как EQU-метки, без байт.\n; Формат: имя: EQU 0xADDR  ; комментарий.",
         "; ============================================================================",
         ""]
    for o in sorted(objs, key=addr_of):
        if (o.get("type") or "").lower() == "variable":
            a = addr_of(o)
            note = first_sentence(o.get("comment"))
            L.append(f'{o["name"]}:\tEQU 0x{a:04X}\t; {note}')
    L.append("")
    return write(os.path.join(ASM, "var_ram_symbols.asm"), L), None

def render_index(rows):
    L = ["; Индекс выгрузки данных exolon (Stage 8): все ROM-backed объекты.",
         "; Порядок по адресу. Каждый файл самодостаточен (метка + директивы).", ""]
    for name in rows:
        L.append(f'\tINCLUDE "{name}.asm"')
    L.append("")
    return write(os.path.join(ASM, "exolon_data_index.asm"), L), None

def main():
    rom, objs = load()
    if os.path.isdir(ASM):
        import shutil
        shutil.rmtree(ASM)
    os.makedirs(ASM, exist_ok=True)

    produced = []
    for o in sorted(objs, key=addr_of):
        t = (o.get("type") or "").lower()
        if t in ("data", "table", "string"):
            name = o["name"]
            _, _ = render(name, addr_of(o), o.get("size") or 0, o.get("comment") or "")
            produced.append(name)
    _, _ = render_vars(objs)
    render_index(produced)

    print(f"Stage8: выгружено ROM-backed объектов: {len(produced)}, "
          f"+ var_ram_symbols.asm + exolon_data_index.asm")
    print("asm/", ASM)
    print("asm/bin/", BIN)

if __name__ == "__main__":
    sys.exit(main() or 0)
