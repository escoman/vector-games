#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 8/10: консольдированный экспорт ASM — ОДИН монолит `asm/code.asm`.

Почему монолит, а не «по файлу на объект»: `z80asm -b -m=8080_strict` не
переносит второй `ORG` («ORG redefined») и не заполняет гэпы, а код и данные в
ROM перемешаны (25 стыков). Значит побайтово-идентичная пересборка обязана
идти строго адресным потоком. Поэтому весь код — один файл `code.asm`
(мнемоники из disassembly), а данные/строки/шрифты/спрайты/гэпы живут в нём же
помеченными секциями (`defb`/`defm` с именами-метками RDB).

Алгоритм:
  1. Запустить v06c-asm-export (ROM+RDB) → адресно-упорядоченный `layout.asm`
     (мнемоники кода + `defb` размеченных данных + `defb` гэпов). ASM пишет
     экспортёр, не Python (правило пакета).
  2. Починить синтаксис, который z80asm отвергает: `rst <символ>` → `rst <addr>`
     (операнд RST обязан быть константой 00h..38h).
  3. Собрать и побайтово сверить с ROM. Найденные расхождения — это куски
     ДАННЫХ, которые disassemblerdecodeировал как код (мнемоника не
     рекодируется байт-в-байт). Для каждого такого label-прогона заменить
     тело на `defb` (для строк — `defm`) фактических байтов ROM. Метки внутри
     прогона сохраняются (прогон = соседние метки).
  4. Записать `asm/code.asm` и мастер `asm/exolon_new.asm` (org + include).
  5. Собрать `src/EXOLON_NEW.ROM` и утвердить 0 расхождений.

Запуск: python3 tools/gen_layout.py
"""
from __future__ import annotations
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROM_DIR = os.path.dirname(HERE)
SRC = os.path.join(ROM_DIR, "src")
ASM = os.path.join(ROM_DIR, "asm")
ORG = 0x0100
END = 0x8000
ROM_SIZE = END - ORG
ROM_NAME = "exolon.rom"
RDB_NAME = "exolon.rdb"
Z80ASM = os.environ.get(
    "Z80ASM", os.path.join(ROM_DIR, "..", "..", "..", "z88dk", "bin", "z80asm"))

LAB_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(?:;.*)?$")
HEX_SUFFIX_RE = re.compile(r"([0-9A-Fa-f]{4})$")
RST_SYMB_RE = re.compile(r"^(\s*)rst(\s+)([A-Za-z_][A-Za-z0-9_]*)\s*(?:;.*)?$",
                         re.IGNORECASE)

# Печатные ASCII для DEFM; кавычка и обратный слэш не помещаются в строку.
PRINTABLE = set(range(0x20, 0x7F)) - {ord('"'), ord("\\")}


def load():
    rom = open(os.path.join(SRC, ROM_NAME), "rb").read()
    rdb = json.load(open(os.path.join(SRC, RDB_NAME), encoding="utf-8"))
    addr_of = {}
    for o in rdb["objects"]:
        addr_of[o["name"]] = int(o["address"], 16)
    return rom, addr_of


def run_exporter(layout_dir):
    """Вызвать v06c-asm-export, вернуть текст layout.asm."""
    sys.path.insert(0, os.path.join(ROM_DIR, "..", "..", "..", "utils"))
    try:
        from analyze import export_asm
    except Exception as exc:  # noqa: BLE001
        raise SystemExit("не импортирован пакет analyze (%s)" % exc)
    exporter = export_asm.find_exporter()
    if not exporter:
        raise SystemExit("v06c-asm-export не найден (--exporter / $V06C_ASM_EXPORT)")
    export_asm.run_export(
        os.path.join(SRC, ROM_NAME), layout_dir, exporter=exporter,
        rdb=os.path.join(SRC, RDB_NAME), origin=ORG)
    path = os.path.join(layout_dir, "layout.asm")
    return open(path, encoding="utf-8", errors="replace").read()


def fix_rst(text, addr_of):
    """`rst <символ>` → `rst <NN>h`; символ — валидный RST-вектор 00h..38h."""
    out = []
    for line in text.splitlines():
        m = RST_SYMB_RE.match(line)
        if m:
            name = m.group(3)
            a = addr_of.get(name)
            if a is None:
                hs = HEX_SUFFIX_RE.search(name)
                a = int(hs.group(1), 16) if hs else None
            if a is not None and 0 <= a <= 0x38 and a % 8 == 0:
                line = "%srst%s%02Xh" % (m.group(1), m.group(2), a)
        out.append(line)
    return out


def assemble(lines, main_dir):
    """Собрать code-подобный файл; вернуть bytes образа (или None при ошибке)."""
    codep = os.path.join(main_dir, "code.asm")
    with open(codep, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    master = os.path.join(main_dir, "master.asm")
    with open(master, "w", encoding="utf-8") as f:
        f.write("        org %04Xh\n        include \"code.asm\"\n" % ORG)
    outp = os.path.join(main_dir, "built.bin")
    proc = subprocess.run([Z80ASM, "-b", "-m=8080_strict", "-o=" + outp, "master.asm"],
                          cwd=main_dir, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.isfile(outp):
        return None, (proc.stdout + proc.stderr)
    return open(outp, "rb").read(), ""


def label_index(lines, addr_of):
    """[(line_idx, name, addr|None)] по всем меткам файла."""
    idx = []
    for i, t in enumerate(lines):
        m = LAB_RE.match(t.strip())
        if not m:
            continue
        name = m.group(1)
        a = addr_of.get(name)
        if a is None:
            hs = HEX_SUFFIX_RE.search(name)
            if hs:
                a = int(hs.group(1), 16)
        idx.append((i, name, a))
    return idx


def data_directives(addr, span, is_str):
    """Строки листинга defb/defm, побайтово дающие `span`."""
    out = []

    def defb(chunk):
        for o in range(0, len(chunk), 8):
            out.append("        defb    " +
                       ",".join("0%02Xh" % c for c in chunk[o:o + 8]))

    if is_str and span:
        j = 0
        while j < len(span):
            if span[j] in PRINTABLE:
                s = j
                while j < len(span) and span[j] in PRINTABLE:
                    j += 1
                out.append('        defm "' +
                           "".join(chr(c) for c in span[s:j]) + '"')
            else:
                s = j
                while j < len(span) and span[j] not in PRINTABLE:
                    j += 1
                defb(span[s:j])
    else:
        defb(span)
    return out


def repair(lines, rom, diff, addr_of):
    """Заменить mis-decoded data-прогоны на defb/defm. Вернуть (новые, n_runs, n_bytes)."""
    idx = label_index(lines, addr_of)
    n = len(lines)
    out = list(lines[:idx[0][0]]) if idx and idx[0][0] > 0 else []
    runs = 0
    rbytes = 0
    for k, (ln, name, a) in enumerate(idx):
        nxt_ln = idx[k + 1][0] if k + 1 < len(idx) else n
        nxt_a = idx[k + 1][2] if k + 1 < len(idx) else END
        out.append(lines[ln])  # метку всегда сохраняем
        body = lines[ln + 1:nxt_ln]
        if a is None or nxt_a is None or nxt_a <= a:
            out.extend(body)
            continue
        if not any(a <= x < nxt_a for x in diff):
            out.extend(body)  # код round-trip'ится — не трогаем
            continue
        runs += 1
        span = rom[a - ORG:nxt_a - ORG]  # rom — образ: адрес = смещение + ORG
        rbytes += len(span)
        for cl in body:  # сохранить описательные комментарии объекта
            if cl.strip().startswith(";"):
                out.append(cl)
        out.extend(data_directives(a, span, name.startswith("str_")))
    return out, runs, rbytes


def main():
    rom, addr_of = load()
    assert len(rom) == ROM_SIZE, "размер ROM %d != %d" % (len(rom), ROM_SIZE)
    tmp = tempfile.mkdtemp(prefix="gen_layout_", dir=os.path.join(ROM_DIR, "..", "..", "..", ".scratch"))
    base = fix_rst(run_exporter(tmp), addr_of)
    build, err = assemble(base, tmp)
    if build is None:
        raise SystemExit("базовая сборка не удалась:\n" + err)
    diff = {ORG + i for i in range(ROM_SIZE) if build[i] != rom[i]}
    print("базовая сборка: расхождений %d → чиним data-прогоны" % len(diff))
    repaired, runs, rbytes = repair(base, rom, diff, addr_of)
    final, err = assemble(repaired, tmp)
    if final is None:
        raise SystemExit("финальная сборка не удалась:\n" + err)
    fdiff = {ORG + i for i in range(ROM_SIZE) if final[i] != rom[i]}
    if fdiff:
        raise SystemExit("после починки остались расхождения: %d (см. tmp)" % len(fdiff))

    os.makedirs(ASM, exist_ok=True)
    with open(os.path.join(ASM, "code.asm"), "w", encoding="utf-8") as f:
        f.write("\n".join(repaired) + "\n")
    with open(os.path.join(ASM, "exolon_new.asm"), "w", encoding="utf-8") as f:
        f.write(
            "; exolon_new.asm — мастер компоновки (Stage 10, tools/gen_layout.py)\n"
            "; Побайтовая копия exolon.rom из ОДНОГО монолита asm/code.asm.\n"
            "; Сборка: z80asm -b -m=8080_strict -o=src/EXOLON_NEW.ROM exolon_new.asm\n"
            "\n"
            "        org %04Xh\n"
            "        include \"code.asm\"\n" % ORG)
    print("repaired runs: %d (%d байт данных → defb/defm)" % (runs, rbytes))
    print("code.asm: %d строк; round-trip: 0 расхождений" % len(repaired))
    print("выпущено: %s, %s" % (os.path.join(ASM, "code.asm"),
                                os.path.join(ASM, "exolon_new.asm")))


if __name__ == "__main__":
    main()
