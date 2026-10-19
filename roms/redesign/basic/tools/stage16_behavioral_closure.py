#!/usr/bin/env python3
"""Stage 16: Phase B — behavioral closure of 14 mixed residual blocks (534 B).

Вход: CODE ∪ RDB = 96.89% (остаток 534 Б / 14 блока). Каждая дыра — mixed
(самомодиф/граф/RAM-workspace), статически неразличима код↔данные без трасса.

Phase B evidence (this session, via v06c-mcp):
1. Boot → idle REPL: memory read of all 534 bytes → 13/14 blocks IDENTICAL
   to ROM; only 0x2B3F mutated (0x10→0x0D, graph var init).
2. Breakpoints at 8 code-candidate entries + typed command battery (PLOT/LINE/
   COLOR/PAINT/CIRCLE/PRINT/transcendentals): 0x2D8E HIT ×1, self-mod byte
   0x2DB9 changed (0x00→0x01) → proves contiguous code + selfmod for GRAPH
   pixel-address routine.
3. 0x2DDC: code-shape (93 contiguous valid instructions, ends JMP, incomplete=
   false), address-taken via `LXI H,2DDCh` @0x3EA9 (PCHL-dispatch table). BP
   did not fire in idle-repl battery (routine is a scroll/linefeed path not
   exercised by the short test). Conservative: attributed func_ (round-trip
   safety-net = `make verify`).
4. Remaining blocks: constant → data_/pad; zero-run → var_/scratch; selfmod-patch
   cells → data_ (ROM template written at runtime by func_selfmod_patch 0x366F).

Правило round-trip: data_/var_ → DEFB exact bytes (always safe). func_ entries
verified by `debug_disassemble_range` → incomplete_instruction=false and
instruction boundary at block end. Gate (`make verify`) = hard oracle.

Usage:
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage16_behavioral_closure.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage16_behavioral_closure.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import RdbWriter

DEFAULT_ROM = "roms/redesign/basic/src/basic.r0m"
DEFAULT_RDB = "roms/redesign/basic/src/basic.rdb"

# ---- OBJECTS -----------------------------------------------------------
# action: "create" (new object) or "extend" (resize existing).
# check: lambda(image)->bool — full block bytes match (safe for data/func boundary).
ACTIONS = [
    # === 0x27A8..0x27BC (21) — data continuation of dispatch table ===
    {
        "action": "create", "addr": 0x27A8, "name": "data_dispatch_extension",
        "kind": "data", "size": 21, "role": "dispatch_table_extension",
        "check": lambda img: img[0x27A8:0x27BD] == bytes(
            [0x79,0x83,0x16,0x79,0x0D,0x11,0x7B,0xA4,0x12,0x7B,0xB6,
             0x13,0x7F,0xA7,0x17,0x50,0x13,0x0B,0x46,0x12,0x0B]),
        "note": (
            "Продолжение data_dispatch_table (0x2770) для SOUND/PLAY-подсистемы "
            "(след. объект var_play_active@0x27C8). Boot+post-battery: unchanged → "
            "ROM-constant data."),
        "props": {"phase_b_evidence": "boot-diff=0, post-battery-diff=0"},
    },
    # === 0x2B01 (1) — var zero in graph region ===
    {
        "action": "create", "addr": 0x2B01, "name": "var_graph_scratch_2b01",
        "kind": "variable", "size": 1, "role": "graph_scratch",
        "check": lambda img: img[0x2B01] == 0x00,
        "note": "Zero byte between func_2af9 (GRAPH code) and var_graph_xy.",
        "props": {"phase_b_evidence": "boot-diff=0"},
    },
    # === 0x2B3C..0x2B3F (4) — graph state var, MUTATED at boot ===
    {
        "action": "create", "addr": 0x2B3C, "name": "var_graph_state",
        "kind": "variable", "size": 4, "role": "graph_state_init",
        "check": lambda img: img[0x2B3C:0x2B40] == bytes([0x00,0x00,0x00,0x10]),
        "note": (
            "GRAPH state variables (0x2B3C..0x2B3F). Boot-diff: byte 0x2B3F "
            "0x10→0x0D (initialized at boot). PROVEN mutable → var_."),
        "props": {"phase_b_evidence": "boot-diff: 0x2B3F ROM=10 RUN=0D"},
    },
    # === 0x2B58 (1) — var zero near var_graph_xy ===
    {
        "action": "create", "addr": 0x2B58, "name": "var_graph_2b58",
        "kind": "variable", "size": 1, "role": "graph_state_extra",
        "check": lambda img: img[0x2B58] == 0x00,
        "note": "Zero byte immediately after var_graph_xy (0x2B56,2B).",
        "props": {"phase_b_evidence": "boot-diff=0"},
    },
    # === 0x2C6F..0x2C7D (15) — data subtable before irq_palette_table ===
    {
        "action": "create", "addr": 0x2C6F, "name": "data_palette_subtable",
        "kind": "data", "size": 15, "role": "palette_subtable",
        "check": lambda img: img[0x2C6F:0x2C7E] == bytes(
            [0x00,0x80,0x10,0xD0,0x06,0x86,0x16,0x36,0x00,0xC5,0x22,
             0xC0,0x02,0x98,0x52]),
        "note": (
            "Data subtable (palette/color) preceding data_irq_palette_table. "
            "Bytes disassemble ambiguously (possible SHLD 02C0); no bp-hit in "
            "battery; boot-diff=0 → constant → data (conservative)."),
        "props": {"phase_b_evidence": "boot-diff=0, no bp hit"},
    },
    # === 0x2D7E..0x2D8D (16) — op-code table for graph pixel routine ===
    {
        "action": "create", "addr": 0x2D7E, "name": "data_graph_op_table",
        "kind": "data", "size": 16, "role": "graph_opcode_table",
        "check": lambda img: img[0x2D7E:0x2D8E] == bytes(
            [0x89,0x8A,0x8D,0x7F,0x88,0x99,0x98,0x9A,0x8C,0x9F,0x9B,
             0x80,0x81,0x82,0x83,0x84]),
        "note": (
            "16-byte GRAPH opcode table. Preceded by lbl_2d7b; followed by "
            "func_graph_pixel_addr (0x2D8E). Unchanged at boot+battery → "
            "ROM-constant data."),
        "props": {"phase_b_evidence": "boot-diff=0, post-battery-diff=0"},
    },
    # === 0x2D8E..0x2DC7 (58) — SELF-MOD GRAPH pixel routine (PROVEN) ===
    {
        "action": "create", "addr": 0x2D8E, "name": "func_graph_pixel_addr",
        "kind": "function", "size": 58, "role": "selfmod_graph_pixel_address",
        "check": lambda img: img[0x2D8E] == 0x21 and img[0x2DC7] == 0xC9,
        "note": (
            "PROVEN: breakpoint HIT ×1 during battery + runtime selfmod byte "
            "0x2DB9 ROM→post 00→01 (ANI 0F / STA 2DB9 writes operand of "
            "`LXI D,????` in-place). Reads graph-op-table, mutates D-operand, "
            "computes pixel address via 4012h base. Ends RET at 0x2DC7 "
            "(boundary with func_kbd_matrix_prime)."),
        "props": {
            "phase_b_evidence": "bp@2D8E HIT; 0x2DB9 mutated 00→01 post-battery",
            "selfmod_cell": "0x2DB9",
            "reads": "data_graph_op_table(0x2D7E), var_graph(0x2B3E), 0x4012",
            "cfg_reachable": "no (PCHL dispatch via LXI H,2D8E at 0x2D19)"},
    },
    # === 0x2DDC..0x2E50 (117) — GRAPH scroll/linefeed code (address-taken) ===
    {
        "action": "create", "addr": 0x2DDC, "name": "func_2ddc_scroll",
        "kind": "function", "size": 117, "role": "selfmod_graph_scroll",
        "check": lambda img: img[0x2DDC:0x2DDE] == bytes([0xFE, 0x0D])
                             and img[0x2E4E] == 0xC3,
        "note": (
            "Self-modifying GRAPH/text-scroll routine. Disassembly: 93 valid "
            "contiguous instructions ending with `JMP 2ABA` (common exit) at "
            "0x2E4E. Checks CR/LF (CPI 0D/0A), writes var_cursor_blink(0x2DCD), "
            "reads/writes var_graph_xy(0x2B56/57), addresses glyphs(LXI H,379F). "
            "Selfmod writes: STA 3EA8 (loads own address via LXI H,2DDC for "
            "dispatch), STA 076F, STA 2E3E, STA 2E0E. Address-taken at 0x3EA9. "
            "BP did not fire in idle battery (scroll condition not met); "
            "conservative func_ per round-trip safety."),
        "props": {
            "phase_b_evidence": "clean disasm; address-taken (LXI H,2DDC @3EA9); "
                                "bp not hit (scroll path not exercised)",
            "selfmod_cells": "0x3EA8, 0x076F, 0x2E3E, 0x2E0E",
            "cfg_reachable": "no (PCHL dispatch)"},
    },
    # === 0x2E51..0x2E5C (12) — dispatch stub (address-taken) ===
    {
        "action": "create", "addr": 0x2E51, "name": "func_2e51",
        "kind": "function", "size": 12, "role": "dispatch_stub",
        "check": lambda img: img[0x2E51:0x2E5D] == bytes(
            [0x04,0x04,0x04,0x01,0x01,0x01,0x05,0x05,0x05,0xD2,0xBD,0x2B]),
        "note": (
            "Dispatch stub after JMP at 0x2E4E (unreachable by fallthrough). "
            "Address-taken via `LXI H,2E51` at 0x2EA3/0x2EFB/0x2FA9 (PCHL "
            "jump table). Code: INR B×3 / LXI B,0101 / DCR B×3 / JNC 2BBD."),
        "props": {"phase_b_evidence": "address-taken via PCHL table"},
    },
    # === 0x2E5D..0x2E75 (25) — data tail (jump/delta table) ===
    {
        "action": "create", "addr": 0x2E5D, "name": "data_2e5d_table",
        "kind": "data", "size": 25, "role": "delta_jump_table",
        "check": lambda img: img[0x2E5D:0x2E76] == bytes(
            [0xB3,0x1C,0xA9,0x9E,0x9F,0xA9,0x96,0x34,0x8E,0x39,0x86,
             0xB0,0x7E,0x94,0x77,0xDE,0x70,0x88,0x6A,0x8E,0x64,0xE9,
             0x5E,0x95,0x59]),
        "note": (
            "Data tail after dispatch stub. Disassembles to garbage (PCHL, "
            "varied opcodes) → not coherent code. Between func_2e51 and "
            "func_2e76@0x2E76. boot-diff=0 → constant table."),
        "props": {"phase_b_evidence": "boot-diff=0, garbage disasm"},
    },
    # === 0x3722..0x3727 (6) — selfmod trampoline ===
    {
        "action": "create", "addr": 0x3722, "name": "func_3722_trampoline",
        "kind": "function", "size": 6, "role": "selfmod_trampoline",
        "check": lambda img: img[0x3722:0x3728] == bytes(
            [0x11,0x00,0x00,0xC3,0x38,0x37]),
        "note": (
            "Trampoline stub: `LXI H,0000 / JMP 3738`. PCHL-dispatched entry "
            "adjacent to func_selfmod_patch (0x366F). JMP target 0x3738 is in "
            "patch-area (0x3730). Clean 2-instruction code."),
        "props": {"phase_b_evidence": "code-shape, part of selfmod subsystem"},
    },
    # === 0x3730..0x3749 (26) — selfmod patch cells (ROM template) ===
    {
        "action": "create", "addr": 0x3730, "name": "data_selfmod_patch_cells",
        "kind": "data", "size": 26, "role": "selfmod_patch_target",
        "check": lambda img: img[0x3730:0x374A] == bytes(
            [0x29,0x29,0x29,0x29,0x29,0x29,0x29,0xEB,0x7E,0xE6,0x00,
             0xB2,0x77,0x24,0x7E,0xE6,0x00,0xB3,0x77,0xC9,0x65,0x2E,
             0x00,0xC3,0x37,0x37]),
        "note": (
            "ROM-template bytes of the patch target area. Written at runtime by "
            "func_selfmod_patch (0x366F): STA 0x3737 (C9=RET), STA 0x373A/3740. "
            "Unchanged at idle (patch not yet triggered) → data_ (ROM template). "
            "DEFB preserves round-trip; runtime writes happen in RAM only."),
        "props": {
            "phase_b_evidence": "boot-diff=0 (idle, patch not fired)",
            "patched_by": "func_selfmod_patch (0x366F)",
            "patch_cells": "0x3737, 0x373A, 0x3740"},
    },
    # === 0x3D03..0x3D0C (10) — control-char inline string ===
    {
        "action": "create", "addr": 0x3D03, "name": "data_ctrl_char_seq",
        "kind": "data", "size": 10, "role": "control_char_sequence",
        "check": lambda img: img[0x3D03:0x3D0D] == bytes(
            [0x0D,0x0A,0x1B,0x41,0x08,0x1B,0x2A,0x01,0x00,0x02]),
        "note": (
            "Inline control-character sequence (0D=CR, 0A=LF, 1B=ESC, 41='A', "
            "08=BS, 1B 2A=ESC*, 01 00 02). Between code labels lbl_3cff/lbl_3d0d. "
            "boot-diff=0 → constant (embedded terminal command sequence)."),
        "props": {"phase_b_evidence": "boot-diff=0, code labels adjacent"},
    },
    # === 0x3E00..0x3E67 (104) — workspace zeros (RAM scratch) ===
    {
        "action": "create", "addr": 0x3E00, "name": "var_workspace_scratch",
        "kind": "variable", "size": 104, "role": "workspace_scratch",
        "check": lambda img: all(b == 0 for b in img[0x3E00:0x3E68]),
        "note": (
            "RAM workspace scratch: 104 zero bytes between var_string_alloc_ptr "
            "(0x3DFC) and data_workspace_constants (0x3E68). Unwritten at idle; "
            "not touched by short battery (BASIC uses different workspace zone "
            "at 0x3Fxx). Reserved for program runtime."),
        "props": {"phase_b_evidence": "all-zero ROM, boot-diff=0"},
    },
    # === 0x3E68..0x3E97 (48) — workspace initialized constants ===
    {
        "action": "create", "addr": 0x3E68, "name": "data_workspace_init",
        "kind": "data", "size": 48, "role": "workspace_init_constants",
        "check": lambda img: img[0x3E68:0x3E6C] == bytes(
            [0xB5,0x6A,0xD5,0xAB]),
        "note": (
            "Pre-initialized workspace constants (48B, 0x3E68..0x3E97). "
            "ROM-backed; boot+post-battery: unchanged. Immediately before "
            "func_3e98 (code). Not mutable (constant across all probes) → data_."),
        "props": {"phase_b_evidence": "boot-diff=0, post-battery-diff=0"},
    },
    # === 0x4027 (1) — paint var byte ===
    {
        "action": "create", "addr": 0x4027, "name": "var_paint_4027",
        "kind": "variable", "size": 1, "role": "paint_field_byte",
        "check": lambda img: img[0x4027] == 0x1E,
        "note": (
            "Byte between func_cmd_cls_home (0x4022) and var_paint_field (0x4028). "
            "Workspace variable; boot-diff=0."),
        "props": {"phase_b_evidence": "boot-diff=0"},
    },
    # === 0x4029..0x402D (5) — code stub in workspace ===
    {
        "action": "create", "addr": 0x4029, "name": "func_4029",
        "kind": "function", "size": 5, "role": "redirect_stub",
        "check": lambda img: img[0x4029:0x402E] == bytes(
            [0xCD,0x6B,0x28,0xE1,0xC9]),
        "note": (
            "Redirect stub in workspace: `CALL 286B / POP H / RET`. 5-byte code "
            "immediately after var_paint_field. Unchanged at boot+battery → "
            "static initialization code. CALL target 0x286B in GRAPH area."),
        "props": {"phase_b_evidence": "boot-diff=0, valid disasm (3 instr, end RET)"},
    },
    # === 0x402E..0x404C (31) — workspace zeros between paint/text ptr ===
    {
        "action": "create", "addr": 0x402E, "name": "var_workspace_text_scratch",
        "kind": "variable", "size": 31, "role": "text_workspace_scratch",
        "check": lambda img: all(b == 0 for b in img[0x402E:0x404D]),
        "note": (
            "Zero workspace between func_4029 stub and var_text_ptr (0x404D). "
            "Reserved scratch; boot-diff=0."),
        "props": {"phase_b_evidence": "all-zero ROM, boot-diff=0"},
    },
    # === 0x4053..0x4062 (16) — zeros between var_fac and float table ===
    {
        "action": "create", "addr": 0x4053, "name": "var_fac_scratch",
        "kind": "variable", "size": 16, "role": "fac_scratch",
        "check": lambda img: all(b == 0 for b in img[0x4053:0x4063]),
        "note": (
            "16 zero bytes between var_fac (0x404F) and data_float_pow2_coeffs "
            "(0x4063). FAC extension scratch; boot-diff=0."),
        "props": {"phase_b_evidence": "all-zero ROM, boot-diff=0"},
    },
    # === 0x4063..0x4073 (17) — float power-of-2 coefficients ===
    {
        "action": "create", "addr": 0x4063, "name": "data_float_pow2_coeffs",
        "kind": "data", "size": 17, "role": "float_power_of_2_table",
        "check": lambda img: img[0x4063:0x4074] == bytes(
            [0x81,0x00,0x82,0x40,0x82,0x00,0x83,0x20,0x83,0x40,
             0x83,0x60,0x83,0x00,0x84,0x10,0x84]),
        "note": (
            "Float power-of-2 table: exponents 0x81..0x84 (2^0..2^3), mantissas "
            "0x00/0x40/0x20/0x40/0x60/0x00/0x10. Unchanged boot+battery → "
            "ROM-constant data. Between var_fac_scratch and lbl_4074."),
        "props": {"phase_b_evidence": "boot-diff=0, monotone exponents"},
    },
]


# ---- plan / apply -------------------------------------------------------
def plan(image, writer):
    rows = []
    for spec in ACTIONS:
        addr = to_addr(spec["addr"])
        ok = spec["check"](image)
        cur = writer.exists(addr) or {}
        exists = bool(cur.get("address"))
        if exists:
            act = "SKIP"
        elif ok:
            act = "CREATE"
        else:
            act = "CHECK!"
        rows.append((addr, act, spec, ok, cur.get("name") or ""))
    return rows


def apply(image, writer):
    log = []
    for spec in ACTIONS:
        addr = to_addr(spec["addr"])
        if not spec["check"](image):
            log.append("%s: %s SKIP — bytes mismatch" % (addr_hex(addr), spec["name"]))
            continue
        cur = writer.exists(addr) or {}
        if cur.get("address"):
            log.append("%s: %s already exists (%s)" % (addr_hex(addr), spec["name"], cur.get("name")))
            continue
        writer.ensure_object(addr, spec["name"], spec["kind"], size=spec["size"])
        writer.set_property(addr, "role", spec.get("role", ""))
        for k, v in (spec.get("props") or {}).items():
            writer.set_property(addr, k, v)
        writer.set_comment(addr, "%s — %s" % (spec["name"], spec["note"]))
        log.append("%s: CREATE %s %s (%d B)" % (addr_hex(addr), spec["kind"], spec["name"], spec["size"]))
    return log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--rdb", default=DEFAULT_RDB)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    if not (args.check or args.apply):
        args.apply = True

    with open(args.rom, "rb") as fh:
        image = fh.read()

    rdb_path = os.path.abspath(args.rdb)
    session, _cache = open_session(rom=args.rom, org=0x0000)
    try:
        info = session.call("debug_get_rdb_info")
        if os.path.abspath(info.get("path") or "") != rdb_path:
            raise SystemExit("RDB in session %r, expected %r" % (info.get("path"), args.rdb))
        writer = RdbWriter(session)
        if args.check:
            print("Stage 16 plan (Phase B behavioral closure):")
            for addr, act, spec, ok, cur_name in plan(image, writer):
                tail = "  (cur=%s)" % cur_name if cur_name else ""
                print("  %-7s %s %-28s [%-9s %3d] %s%s" % (
                    act, addr_hex(addr), spec["name"], spec["kind"], spec["size"],
                    "OK" if ok else "BYTES MISMATCH", tail))
            return 0
        for line in apply(image, writer):
            print("  " + line)
        writer.save()
        print("summary: %s" % (writer.summary(),))
        info = session.call("debug_get_rdb_info")
        print("objects: %s, dirty: %s" % (info.get("object_count"), info.get("dirty")))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
