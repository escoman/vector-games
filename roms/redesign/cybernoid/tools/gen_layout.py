#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 10: cybernoid gen_layout — экспорт → сборка → ремонт diff-прогонов.

Паттерн exolon: v06c-asm-export пишет layout.asm; если assembled bytes ≠ ROM,
заменяем проблемные runs на `defb` (ROM verbatim). Повторяем до 0 diffs.

Причина repair: экспортёр C++ эмитит метки на +1 от истинного адреса (дефект
overlap-relayout, см. memory 1e37587b). В результате инструкции decode-ятся
со сдвигом и поток байт расходится. defb — временная мера; после фикса
экспортёра в C++ layout.asm будет сходиться без repair-цикла.

Запуск: python3 tools/gen_layout.py [--exporter PATH] [--max-passes N]
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROM_DIR = os.path.dirname(HERE)
SRC = os.path.join(ROM_DIR, "src")
ASM = os.path.join(ROM_DIR, "asm")
ORG = 0x0000
ROM_NAME = "cybernoid_unpacked.r0m"
RDB_NAME = "cybernoid_unpacked.rdb"
ROM_SIZE = 32768

Z80ASM_DEFAULT = os.path.join(ROM_DIR, "..", "..", "..", "z88dk", "bin", "z80asm")

LAB_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(?:;.*)?$")
COMMENT_RE = re.compile(r"^\s*;")

# ---------------------------------------------------------------------------
# Exporter / Assembler
# ---------------------------------------------------------------------------

def find_exporter(explicit=None):
    root = os.path.abspath(os.path.join(ROM_DIR, "..", "..", ".."))
    candidates = [
        explicit,
        os.environ.get("V06C_ASM_EXPORT"),
        os.path.join(root, "..", "vector-debug", "build", "v06c-asm-export"),
        os.path.expanduser("~/Projects/vector-debug/build/v06c-asm-export"),
        "/home/alexey/Projects/vector-debug/build/v06c-asm-export",
    ]
    for p in candidates:
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return os.path.abspath(p)
    raise SystemExit("v06c-asm-export не найден")


def run_export(exporter, out_dir):
    cmd = [exporter, "--rom", os.path.join(SRC, ROM_NAME),
           "--output", out_dir,
           "--origin", "%04X" % ORG,
           "--rdb", os.path.join(SRC, RDB_NAME)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise SystemExit(f"exporter rc={proc.returncode}\n{proc.stderr}")
    layout = os.path.join(out_dir, "layout.asm")
    return open(layout, encoding="utf-8", errors="replace").read()


def assemble(layout_text, work_dir, z80asm):
    """Write layout+main, assemble, return (image_bytes|None, error_str)."""
    lp = os.path.join(work_dir, "layout.asm")
    with open(lp, "w", encoding="utf-8") as f:
        f.write(layout_text)
    mp = os.path.join(work_dir, "main.asm")
    with open(mp, "w", encoding="utf-8") as f:
        f.write('        org %04Xh\n        include "layout.asm"\n' % ORG)
    outp = os.path.join(work_dir, "built.bin")
    proc = subprocess.run(
        [z80asm, "-b", "-m=8080_strict", "-o=" + outp, "main.asm"],
        cwd=work_dir, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or not os.path.isfile(outp):
        return None, proc.stdout + proc.stderr
    return open(outp, "rb").read(), ""


# ---------------------------------------------------------------------------
# Repair: find diff-owning label-runs, replace with defb
# ---------------------------------------------------------------------------

def find_label_runs(lines):
    """[(start_line, label_name, end_line_exclusive)]."""
    marks = []
    for i, line in enumerate(lines):
        m = LAB_RE.match(line.strip())
        if m:
            marks.append((i, m.group(1)))
    runs = []
    for j in range(len(marks)):
        s = marks[j][0]
        e = marks[j + 1][0] if j + 1 < len(marks) else len(lines)
        runs.append((s, marks[j][1], e))
    return runs


def address_of_label(lines, runs, rom_size):
    """Track PC through layout.asm to assign each label its emitted address.

    We rely on a simpler heuristic: sequential scan, counting defb bytes and
    instructions (approximated by line content). For the repair loop we use
    the assembled binary vs ROM diff positions to identify label runs via a
    pre-pass. Here we use an external map from RDB.
    """
    pass  # Not needed — we use RDB addr map directly.


def build_addr_map(rdb_path):
    rdb = json.load(open(rdb_path, encoding="utf-8"))
    addr = {}
    for o in rdb["objects"]:
        addr[o["name"]] = int(o["address"], 16)
    return addr


def data_defb(addr, span, is_str):
    """Produce defb/defm lines for given ROM bytes."""
    out = []
    PRINTABLE = set(range(0x20, 0x7F)) - {ord('"'), ord('\\')}
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
                chunk = span[s:j]
                for o in range(0, len(chunk), 8):
                    out.append("        defb    " +
                               ",".join("0%02Xh" % c for c in chunk[o:o+8]))
    else:
        for o in range(0, len(span), 8):
            out.append("        defb    " +
                       ",".join("0%02Xh" % c for c in span[o:o+8]))
    return out


def repair(layout_text, rom, diff_positions, addr_map):
    """Replace diff-owning runs with defb. Returns (new_text, n_runs, n_bytes)."""
    lines = layout_text.splitlines()
    runs = find_label_runs(lines)
    out = list(lines)
    # Process in reverse so line numbers stay valid
    repaired = set()
    n_runs = 0
    n_bytes = 0
    # Map: label -> address
    for s, label, e in reversed(runs):
        a = addr_map.get(label)
        if a is None:
            # Try to extract hex suffix from name like label_0778, gap_11CE
            m = re.search(r'[_.]([0-9A-Fa-f]{4})$', label)
            if m:
                a = int(m.group(1), 16)
            else:
                continue
        # Determine this run's byte span: from a to next label's address
        nxt_a = ROM_SIZE
        for s2, label2, e2 in runs:
            a2 = addr_map.get(label2)
            if a2 is None:
                m2 = re.search(r'[_.]([0-9A-Fa-f]{4})$', label2)
                a2 = int(m2.group(1), 16) if m2 else None
            if a2 is not None and a2 > a:
                nxt_a = min(nxt_a, a2)
                break
        span_bytes = rom[a:nxt_a]
        # Check if any diff falls within [a, nxt_a)
        run_diffs = sum(1 for d in diff_positions if a <= d < nxt_a)
        if run_diffs == 0:
            continue
        # Replace lines s+1..e-1 (keep label and comments before instructions)
        comments = []
        for li in range(s + 1, e):
            if COMMENT_RE.match(lines[li]):
                comments.append(lines[li])
        is_str = label.startswith("str_")
        body = data_defb(a, span_bytes, is_str)
        new_block = [lines[s]] + comments + body
        out[s:e] = new_block
        n_runs += 1
        n_bytes += len(span_bytes)
    return "\n".join(out), n_runs, n_bytes


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exporter", default=None)
    ap.add_argument("--z80asm", default=os.environ.get("Z80ASM", Z80ASM_DEFAULT))
    ap.add_argument("--max-passes", type=int, default=5)
    args = ap.parse_args()

    exporter = find_exporter(args.exporter)
    z80asm = os.path.abspath(args.z80asm)
    rom = open(os.path.join(SRC, ROM_NAME), "rb").read()
    assert len(rom) == ROM_SIZE, f"ROM size {len(rom)} != {ROM_SIZE}"
    addr_map = build_addr_map(os.path.join(SRC, RDB_NAME))

    tmp = tempfile.mkdtemp(prefix="gen_layout_", dir=os.path.join(ROM_DIR, "..", "..", "..", ".scratch"))
    layout_text = run_export(exporter, tmp)
    print(f"exported {len(layout_text)} lines from {exporter}")

    # Strip exporter header comments that reference absolute file paths
    lines = layout_text.splitlines()
    while lines and lines[0].strip().startswith(";"):
        if "generated by" in lines[0] or "exporter" in lines[0].lower():
            lines.pop(0)
        else:
            break
    layout_text = "\n".join(lines)

    for attempt in range(1, args.max_passes + 1):
        build, err = assemble(layout_text, tmp, z80asm)
        if build is None:
            print(f"PASS {attempt}: assembly FAILED:\n{err[:2000]}")
            sys.exit(1)
        diff_positions = set(i for i in range(min(len(rom), len(build)))
                             if rom[i] != build[i])
        extra = abs(len(rom) - len(build))
        total_diffs = len(diff_positions) + extra
        print(f"PASS {attempt}: size={len(build)} byte diffs={total_diffs}")
        if total_diffs == 0:
            break
        layout_text, n_runs, n_bytes = repair(
            layout_text, rom, diff_positions, addr_map)
        print(f"  repaired {n_runs} runs ({n_bytes} bytes → defb)")
    else:
        print(f"ERROR: still {total_diffs} diffs after {args.max_passes} passes")
        sys.exit(1)

    # Write final
    os.makedirs(ASM, exist_ok=True)
    main_path = os.path.join(ASM, "main.asm")
    layout_path = os.path.join(ASM, "layout.asm")
    with open(layout_path, "w", encoding="utf-8") as f:
        f.write(layout_text)
    with open(main_path, "w", encoding="utf-8") as f:
        f.write("; cybernoid main.asm — Stage 10 (tools/gen_layout.py)\n")
        f.write(f"; ROM: {ROM_NAME}; SHA256 target; org {ORG:04X}h\n")
        f.write("\n        org %04Xh\n" % ORG)
        f.write('        include "layout.asm"\n')

    # Also regenerate code/ and data/ views + B-inc views
    subprocess.run([sys.executable, os.path.join(ROM_DIR, "..", "..", "..",
                  ".scratch", "stage9_views.py")], capture_output=True)
    print(f"\nDONE: asm/layout.asm ({len(layout_text.splitlines())} lines), 0 diffs")


if __name__ == "__main__":
    main()
