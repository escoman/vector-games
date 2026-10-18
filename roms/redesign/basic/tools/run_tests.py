#!/usr/bin/env python3
"""Stage 10.2: поведенческая батарея BASIC — собран образ против эталона через MCP.

Идея Tier 2 (TZ §10 п.3): прогнать каждый эталонный `.bas` на ОРИГИНАЛЕ
(`src/bas2997.rom`, грузится на `0x0100`, самораспаковывается на boot) и на
РЕКОНСТРУКЦИИ (`src/basic_new.r0m`, RAM-образ на `0x0000`), и сверить поведение.
Критерий — совпадение картинки экрана (VRAM), а не байтов прошивки.

Старт — только `debug_load_rom` + `debug_run` (без `debug_reset`: reset затирает
page-zero встроенным мониторным ROM эмулятора — см. отчёт Stage10).

Съём «поведения» — дамп VRAM `0x8000..0xFFFF` (четыре битовые плоскости). Чтобы
мигающий курсор не давал ложных расхождений, каждый ROM снимается дважды с
паузой; позиции, отличающиеся между двумя кадрами одного и того же ROM,
считаются «мигающими» и исключаются из сравнения.

    PYTHONPATH=utils python3 roms/redesign/basic/tools/run_tests.py
    PYTHONPATH=utils python3 roms/redesign/basic/tools/run_tests.py --only 01,07
    PYTHONPATH=utils python3 roms/redesign/basic/tools/run_tests.py --skip-ref   # только сборка (калибровка раскладки)
"""
from __future__ import annotations

import argparse
import base64
import glob
import hashlib
import os
import sys
import time

from analyze.mcp_session import bytes_of, open_session

HERE = os.path.dirname(os.path.abspath(__file__))
BASIC = os.path.dirname(HERE)                 # roms/redesign/basic
TESTS_DIR = os.path.join(BASIC, "tests")
DEFAULT_REF = os.path.join(BASIC, "src", "bas2997.rom")
DEFAULT_NEW = os.path.join(BASIC, "src", "basic_new.r0m")
DEFAULT_OUT = os.path.join(BASIC, "reports", "Stage10_tests.md")
DEFAULT_SHOTS = os.path.join(BASIC, "reports", "tests")

VRAM_LO, VRAM_LEN = 0x8000, 0x8000            # 0x8000..0xFFFF = 32768 байт

# --- Раскладка: символ -> последовательность действий над клавишами MCP. -----
# Калибровка по БАЙТАМ буфера ввода 0x3F77 (точнее OCR-скриншотов): для каждого
# ключа читаем код в слоях нетто/SS/US. Итог (латиница):
#   нетто:  1..0 MINUS'-' COMMA',' SEMICOLON';' PERIOD'.' SLASH'/' APOSTROPHE':'
#   SS:     1! 2" 3# 4$ 5% 6& 7' 8( 9) 0' '  MINUS'=' COMMA'<' PERIOD'>'
#           SLASH'?' SEMICOLON'+' APOSTROPHE'*'  LBRACKET'{' RBRACKET'}' GRAVE'~'
# ВАЖНО: '+' = SS+SEMICOLON, '*' = SS+APOSTROPHE, '=' = SS+MINUS (НЕ EQUALS —
# EQUALS и MINUS одна клетка матрицы, дают '-').
DIRECT = {
    " ": "SPACE", "-": "MINUS", ",": "COMMA", ";": "SEMICOLON",
    ".": "PERIOD", "/": "SLASH", ":": "APOSTROPHE",
}
SHIFTED = {
    "!": "1", '"': "2", "#": "3", "$": "4", "%": "5", "&": "6",
    "'": "7", "(": "8", ")": "9", "=": "MINUS", "<": "COMMA",
    ">": "PERIOD", "?": "SLASH", "+": "SEMICOLON", "*": "APOSTROPHE",
    "{": "LBRACKET", "}": "RBRACKET", "~": "GRAVE",
}


def char_actions(ch):
    """Символ -> список действий [(kind, key)]; kind ∈ press/release/tap."""
    up = ch.upper()
    if up == "\n":
        return [("tap", "ENTER")]
    if ("A" <= up <= "Z"):
        return [("tap", up)]
    if ("0" <= ch <= "9"):
        return [("tap", ch)]
    if ch in DIRECT:
        return [("tap", DIRECT[ch])]
    if ch in SHIFTED:
        return [("press", "SS"), ("tap", SHIFTED[ch]), ("release", "SS")]
    return []          # неподдерживаемый символ — пропускаем (не роняем прогон)


TAP_TOOL = {"press": "debug_press_key", "release": "debug_release_key",
            "tap": "debug_type_key"}


def type_line(session, text, gap=0.14):
    """Набрать строку посимвольно (печатающие клавиши) + ENTER в конце.

    `gap` — пауза после каждого нажатия: ROM опрашивает матрицу на VBlank
    (~20 мс), поэтому между тапами нужно выдержать видимое отпускание,
    иначе клавиши сливаются и теряются (проверено: 0.02 мс -> «PRIT»)."""
    for ch in text:
        for kind, key in char_actions(ch):
            session.call(TAP_TOOL[kind], {"key": key})
            time.sleep(gap)
    session.call("debug_type_key", {"key": "ENTER"})
    time.sleep(gap)


def vram_read(session):
    """Дамп VRAM 0x8000..0xFFFF одним вызовом debug_get_vram_bytes."""
    payload = session.call("debug_get_vram_bytes",
                           {"address": VRAM_LO, "length": VRAM_LEN})
    return bytes_of(payload)


def capture(session, blink_gap=0.35):
    """Два кадра VRAM -> (первый кадр, множество «мигающих» байтов)."""
    v1 = vram_read(session)
    time.sleep(blink_gap)
    v2 = vram_read(session)
    blink = {i for i in range(min(len(v1), len(v2))) if v1[i] != v2[i]}
    return v1, blink


def boot(session, rom, org, settle=3.0):
    """Чистая загрузка ROM и выход на READY (load -> run, без reset)."""
    session.load_rom(rom, org=org)
    session.call("debug_run")
    time.sleep(settle)


def save_shot(session, path):
    """Снимок ТВ-кадра (PNG) для человека; не критично, если не выйдет."""
    try:
        res = session._request("tools/call",
                               {"name": "debug_get_screen_snapshot", "arguments": {}})
        for item in (res.get("content") or []):
            if item.get("type") == "image" and item.get("data"):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as fh:
                    fh.write(base64.b64decode(item["data"]))
                return True
    except Exception as exc:                          # noqa: BLE001
        print("  (скриншот не сохранён: %s)" % exc, file=sys.stderr)
    return False


def fp(data):
    return hashlib.sha256(data).hexdigest()[:16]


def diff_positions(a, b, mask):
    """Позиции, где a!=b, кроме замаскированных (мигающих)."""
    n = min(len(a), len(b))
    return [i for i in range(n) if a[i] != b[i] and i not in mask]


def load_cases(tests_dir, only):
    cases = []
    for path in sorted(glob.glob(os.path.join(tests_dir, "*.bas"))):
        name = os.path.basename(path)[:-4]
        if only and not any(name.startswith(pref) for pref in only):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
        cases.append((name, path, lines))
    return cases


def main(argv=None):
    ap = argparse.ArgumentParser(prog="run_tests")
    ap.add_argument("--tests-dir", default=TESTS_DIR)
    ap.add_argument("--ref", default=DEFAULT_REF)
    ap.add_argument("--new", default=DEFAULT_NEW)
    ap.add_argument("--org-ref", type=lambda s: int(s, 0), default=0x0100)
    ap.add_argument("--org-new", type=lambda s: int(s, 0), default=0x0000)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--shots", default=DEFAULT_SHOTS)
    ap.add_argument("--only", default="", help="префиксы имён через запятую")
    ap.add_argument("--skip-ref", action="store_true",
                    help="прогнать только сборку (для калибровки раскладки)")
    ap.add_argument("--no-shots", action="store_true")
    args = ap.parse_args(argv)

    only = [x for x in args.only.split(",") if x.strip()]
    cases = load_cases(args.tests_dir, only)
    if not cases:
        print("нет тестов в %s" % args.tests_dir, file=sys.stderr)
        return 2

    session, _ = open_session(rom=args.new, org=args.org_new, cache=False)
    rows = []
    try:
        for name, path, lines in cases:
            print("=== %s ===" % name)
            for ln in lines:
                print("    | " + ln)

            row = {"name": name, "lines": len(lines)}

            if not args.skip_ref:
                boot(session, args.ref, args.org_ref)
                for ln in lines:
                    type_line(session, ln)
                time.sleep(1.2)
                rv, rb = capture(session)
                row["ref_fp"] = fp(rv)
                row["_ref"] = (rv, rb)

            boot(session, args.new, args.org_new)
            for ln in lines:
                type_line(session, ln)
            time.sleep(1.2)
            nv, nb = capture(session)
            row["new_fp"] = fp(nv)
            row["_new"] = (nv, nb)

            if not args.skip_ref:
                rv, rb = row["_ref"]
                mask = rb | nb
                dpos = diff_positions(rv, nv, mask)
                row["match"] = (len(dpos) == 0)
                row["diff"] = len(dpos)
                print("    ref=%s new=%s  diff=%d  -> %s"
                      % (row["ref_fp"], row["new_fp"], row["diff"],
                         "MATCH" if row["match"] else "MISMATCH"))
            else:
                row["match"] = None
                row["diff"] = None

            if not args.no_shots:
                shot = os.path.join(args.shots, "%s__new.png" % name)
                save_shot(session, shot)

            rows.append(row)
    finally:
        session.close()

    write_report(args, rows)
    total = len(rows)
    if args.skip_ref:
        print("\nпрогнано %d кейсов (только сборка; сверка пропущена)" % total)
        return 0
    ok = sum(1 for r in rows if r["match"])
    print("\nИТОГ: %d/%d кейсов совпали с эталоном (VRAM, мигающий курсор исключён)"
          % (ok, total))
    return 0 if ok == total else 1


def write_report(args, rows):
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    mode = "только сборка (калибровка)" if args.skip_ref else "эталон ↔ сборка"
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("# Stage 10.2 — поведенческая батарея BASIC (Tier 2)\n\n")
        fh.write("Сверка: `%s` (VRAM `0x8000..0xFFFF`, мигающие байты исключены).\n" % mode)
        fh.write("Эталон — `bas2997.rom` (org `0x0100`, самораспаковка на boot); "
                 "сборка — `basic_new.r0m` (org `0x0000`).\n\n")
        fh.write("| тест | строк | отпечаток эталон | отпечаток сборка | расхожд. | вердикт |\n")
        fh.write("|---|---:|---|---|---:|---|\n")
        for r in rows:
            if args.skip_ref:
                fh.write("| %s | %d | — | `%s` | — | — |\n"
                         % (r["name"], r["lines"], r["new_fp"]))
            else:
                verdict = "✅ MATCH" if r["match"] else "❌ MISMATCH"
                fh.write("| %s | %d | `%s` | `%s` | %d | %s |\n"
                         % (r["name"], r["lines"], r["ref_fp"], r["new_fp"],
                            r["diff"], verdict))
        fh.write("\nСкриншоты кадров — `reports/tests/*__new.png`.\n")
    print("отчёт: %s" % args.out)


if __name__ == "__main__":
    sys.exit(main())
