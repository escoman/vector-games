# -*- coding: utf-8 -*-
"""
Извлечение мелодий (BGM) из jackal.nes по каналам.

Источник структуры: дизассемблер RayofJay (NES-Jackal_Disassembly_Fully_Commented),
файлы Bank0.ASM / Sound.ASM.

Модель данных в ROM (PRG Bank 0, CPU $8000-$BFFF, файловый оффсет = CPU - $8000 + $10):

  tblSound_MusicData — таблица SoundDefinition, по 3 байта на ID (начиная с ID 1):
      db  (ClipCount*64 + Channel*4)   ; заголовок
      dw  <адрес Definition-блока>     ; указатель на поток канала

  Для каждой мелодии 4 последовательных ID: Pulse1 (ch0), Pulse2 (ch1),
  Triangle (ch2), DMC (ch6).

  Definition-блок — сырой поток команд звукового движка (db ...).
  Некоторые треки (level1/2/3, boss, ending) состоят из вступления и
  зацикленной части: блок заканчивается на dw <адрес Repeat-блока>.
  В выходной файл канала вступление и Repeat-блок пишутся подряд.

Байты берутся ИЗ ROM; дизассемблер используется только для точных границ
блоков (по меткам) и для контроля совпадения.
"""

import os
import re
import sys

ROM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jackal.nes")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")

# Кэш-копия Bank0.ASM из репозитория RayofJay (получена через raw.githubusercontent.com)
ASM_PATH = r"C:\Users\escom\.qoder\cache\projects\jackal-2cee84ae\agent-tools\3912a6c4\2c9a7c2a.txt"

BANK0_CPU_BASE = 0x8000
CHANNEL_NAMES = ["pulse1", "pulse2", "triangle", "dmc"]

# ID первых каналов мелодий -> имя папки
SONGS = [
    (0x34, "01_intro"),
    (0x38, "02_level1"),
    (0x3C, "03_level2"),
    (0x40, "04_level3"),
    (0x44, "05_boss"),
    (0x48, "06_final_boss"),
    (0x4C, "07_stage_clear"),
    (0x50, "08_game_over"),
    (0x54, "09_ending"),
]


def strip_comment(line):
    """Убирает комментарий ; ... (в данных '$' всегда предваряет число)."""
    i = line.find(";")
    return line[:i] if i >= 0 else line


def parse_asm(path):
    """
    Возвращает {label: (bytes, dw_target_label_or_None)} для всех меток,
    у которых есть хотя бы один db. dw учитывается только как завершающий
    указатель сразу за db-строками блока (паттерн музыкальных потоков).
    """
    blocks = {}
    cur_label = None
    cur_bytes = bytearray()
    cur_dw = None

    label_re = re.compile(r"^([A-Za-z_]\w*):")
    db_byte_re = re.compile(r"\$([0-9A-Fa-f]{1,2})")

    def flush():
        nonlocal cur_label, cur_bytes, cur_dw
        if cur_label is not None and len(cur_bytes) > 0:
            blocks[cur_label] = (bytes(cur_bytes), cur_dw)
        cur_label, cur_bytes, cur_dw = None, bytearray(), None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = strip_comment(raw.rstrip("\n")).strip()
            if not line:
                continue
            m = label_re.match(line)
            if m:
                flush()
                cur_label = m.group(1)
                continue
            low = line.lower()
            if low.startswith("db ") or low.startswith("db\t"):
                for hexv in db_byte_re.findall(line):
                    cur_bytes.append(int(hexv, 16))
                continue
            if low.startswith("dw "):
                target = line[2:].strip()
                if re.match(r"^[A-Za-z_]\w*$", target) and len(cur_bytes) > 0:
                    cur_dw = target  # запоминаем только первый dw после db
                continue
            # прочее (defc/section/код) завершает блок данных
            flush()
    flush()
    return blocks


def find_label_at(blocks, rom_bank0, offset):
    """Ищет метку, чьи байты совпадают с ROM по адресу offset. Возвращает (label, bytes, dw)."""
    matches = []
    for label, (data, dw) in blocks.items():
        n = len(data)
        if rom_bank0[offset:offset + n] == data:
            matches.append((label, data, dw))
    return matches


def label_name_of(blocks, rom_bank0, offset):
    m = find_label_at(blocks, rom_bank0, offset)
    return m[0][0] if m else ""


def locate_table(bank0):
    """Ищет tblSound_MusicData по байтам записей ID 1 и ID 2 (из Sound.ASM)."""
    pat = bytes([0x50, 0xEE, 0x8A, 0x0C, 0x39, 0x8B])  # ID1 + ID2
    candidates = []
    start = 0
    while True:
        i = bank0.find(pat, start)
        if i < 0:
            break
        # проверка: ID3 тоже 3-байтовая запись с заголовком $0C
        if i + 8 <= len(bank0) and bank0[i + 6] == 0x0C:
            candidates.append(i)
        start = i + 1
    return candidates


def main():
    rom = open(ROM_PATH, "rb").read()
    if len(rom) != 131088:
        sys.exit(f"НЕ ОЖИДАЛОСЬ: размер ROM {len(rom)}, ждали 131088")
    bank0 = rom[0x10:0x10 + 0x4000]

    blocks = parse_asm(ASM_PATH)
    n_music_labels = sum(1 for l in blocks if "Definition" in l)
    print(f"Разобрано меток с данными в Bank0.ASM: {len(blocks)} (Definition: {n_music_labels})")

    cands = locate_table(bank0)
    if len(cands) != 1:
        sys.exit(f"tblSound_MusicData: найдено кандидатов {len(cands)}: {cands}")
    tbl = cands[0]
    tbl_cpu = BANK0_CPU_BASE + tbl
    print(f"tblSound_MusicData: CPU ${tbl_cpu:04X} (файловый оффсет ${tbl + 0x10:04X})")

    os.makedirs(OUT_DIR, exist_ok=True)
    report = []
    problems = []

    for base_id, folder in SONGS:
        song_dir = os.path.join(OUT_DIR, folder)
        os.makedirs(song_dir, exist_ok=True)
        for ch in range(4):
            sid = base_id + ch
            ent = tbl + (sid - 1) * 3
            header = bank0[ent]
            ptr = bank0[ent + 1] | (bank0[ent + 2] << 8)
            chname = CHANNEL_NAMES[ch]

            out_path = os.path.join(song_dir, chname + ".bin")
            if ptr == 0:
                open(out_path, "wb").write(b"\xFF")
                problems.append(f"{folder}/{chname}: канал отсутствует (ptr=0), записан $FF")
                continue

            off = ptr - BANK0_CPU_BASE
            if not (0 <= off < len(bank0)):
                problems.append(f"{folder}/{chname}: указатель ${ptr:04X} вне Bank0")
                open(out_path, "wb").write(b"\xFF")
                continue

            stream = bytearray()
            chain = []
            cur_off, cur_ptr = off, ptr
            stream_start = ptr
            loop_anchor = None
            base = re.sub(r"\d*Definition$", "", label_name_of(blocks, bank0, cur_off))
            while True:
                matches = find_label_at(blocks, bank0, cur_off)
                if not matches:
                    problems.append(
                        f"{folder}/{chname}: по адресу ${cur_ptr:04X} нет совпадения с метками Bank0.ASM")
                    break
                label, data, dw = matches[0]
                stream += bank0[cur_off:cur_off + len(data)]
                chain.append(f"{label} @ ${cur_ptr:04X} ({len(data)} байт)")
                if dw is not None:
                    # блок завершается dw-якорем цикла (иногда на самого себя)
                    w = cur_off + len(data)
                    if w + 2 <= len(bank0):
                        loop_anchor = bank0[w] | (bank0[w + 1] << 8)
                    break
                # продолжение: Repeat-блок того же трека, лежащий в ROM сразу за текущим
                cont = None
                for lbl2, (data2, _dw2) in blocks.items():
                    if not lbl2.startswith(base) or "Repeat" not in lbl2:
                        continue
                    c = cur_off + len(data)
                    if bank0[c:c + len(data2)] == data2:
                        cont = (lbl2, c)
                        break
                if cont is None:
                    break
                cur_off, cur_ptr = cont[1], BANK0_CPU_BASE + cont[1]

            open(out_path, "wb").write(bytes(stream))
            hdr_cpu = (header >> 2) & 0x0F
            anchor_note = ""
            if loop_anchor is not None:
                ok = stream_start <= loop_anchor < stream_start + len(stream)
                if not ok:
                    problems.append(
                        f"{folder}/{chname}: якорь цикла ${loop_anchor:04X} вне потока")
                anchor_note = f"; цикл -> ${loop_anchor:04X}"
            report.append(
                f"{folder}/{chname}.bin: ID ${sid:02X}, header ${header:02X} (chnl {hdr_cpu}), "
                f"{len(stream)} байт{anchor_note}; блоки: " + " -> ".join(chain))

    readme = (
        "Jackal NES — извлечённые мелодии по каналам\n"
        "Источник: PRG Bank 0\n"
        "Формат данных: сырой поток команд звукового движка Konami\n"
        "Каналы:\n"
        "  pulse1.bin  — Pulse 1\n"
        "  pulse2.bin  — Pulse 2\n"
        "  triangle.bin — Triangle\n"
        "  dmc.bin     — DMC (ударные/шум)\n"
        "\n"
        "Мелодии пронумерованы в порядке появления в игре.\n"
        "Данные предназначены для дальнейшего переноса на Vector-06C (ВИ53).\n"
    )
    with open(os.path.join(OUT_DIR, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme)

    print("\n".join(report))
    if problems:
        print("\n=== ПРОБЛЕМЫ ===")
        print("\n".join(problems))
    else:
        print("\nПроблем не обнаружено: все байты совпадают с метками Bank0.ASM.")


if __name__ == "__main__":
    main()
