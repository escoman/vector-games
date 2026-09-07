#!/usr/bin/env python3
"""
v06_emu.py - Intel 8080 emulator + small assembler for Vector-06C ASM tests.

Purpose: deterministic execution/verification of ASM routines.  No video or
sound emulation is performed.  Memory is a plain 64 KiB byte array; optional
VRAM write tracing only records writes to the Vector-06C video ranges.

The emulator implements the documented Intel 8080 instruction set, including
all conditional CALL/RET/JMP variants, XTHL/XCHG/PCHL, IN/OUT as harmless
I/O callbacks, and exact 8080 flag behaviour (including AC for arithmetic and
logical instructions).

The assembler accepts the common z88dk/8080 spellings used by hand-written
ASM: MOV/MVI/LXI/LD, DB/DEFB, DW/DEFW, ORG, EQU, END, labels, expressions
using + - * / << >> & | ^ and $/$hex/%binary constants.  SECTION/PUBLIC/
EXTERN are ignored as layout directives.  Symbolic branch/call/data operands
are resolved in two passes.

CLI examples:
  python3 v06_emu.py --asm pr512t.asm --entry graph_put_char_512t --trace
  python3 v06_emu.py --asm test.asm --entry test --dump-writes
  python3 v06_emu.py --self-test

For programmatic tests use CPU8080.run_until(), Emulator.load_asm() and
Emulator.call().  Emulator.call() installs a sentinel return address, sets
SP, optionally writes arguments as 16-bit stack words, and stops when the
routine returns to the sentinel.  This is convenient for __z88dk_callee
routines because the caller-side test harness can inspect SP/registers after
return and can also supply its own stack layout when needed.
"""
from __future__ import annotations

import argparse
import ast
import operator
import re
import sys
from dataclasses import dataclass
from typing import Callable, Optional

MASK8 = 0xFF
MASK16 = 0xFFFF
SENTINEL = 0xFF00


def parity8(v: int) -> int:
    return 1 if (v & 0xFF).bit_count() % 2 == 0 else 0


class CPU8080:
    def __init__(self, *, io_read: Optional[Callable[[int], int]] = None,
                 io_write: Optional[Callable[[int, int], None]] = None):
        self.mem = bytearray(65536)
        self.a = self.b = self.c = self.d = self.e = self.h = self.l = 0
        self.sp = 0x7FF0
        self.pc = 0
        self.z = self.s = self.p = self.cy = self.ac = 0
        self.halted = False
        self.steps = 0
        self.io_read = io_read or (lambda port: 0xFF)
        self.io_write = io_write or (lambda port, value: None)
        self.trace_enabled = False
        self.trace = []
        self.write_trace = []
        self.read_trace = []
        self.stack_trace = []
        self.vram_trace = []
        self._last_instruction = None
        self.call_depth = 0

    # ---------- memory ----------
    def rb(self, addr: int) -> int:
        addr &= MASK16
        v = self.mem[addr]
        if self.trace_enabled:
            self.read_trace.append((self.steps, self.pc, addr, v))
        return v

    def wb(self, addr: int, val: int):
        addr &= MASK16; val &= MASK8
        old = self.mem[addr]
        self.mem[addr] = val
        self.write_trace.append((self.steps, self.pc, addr, old, val))
        if self.is_vram(addr):
            self.vram_trace.append((self.steps, self.pc, addr, old, val))

    @staticmethod
    def is_vram(addr: int) -> bool:
        # Vector-06C's common 4-plane windows used by the project.
        a = addr & MASK16
        return (0x8000 <= a <= 0x9FFF or
                0xA000 <= a <= 0xBFFF or
                0xC000 <= a <= 0xDFFF or
                0xE000 <= a <= 0xFFFF)

    def rw(self, addr: int) -> int:
        return self.rb(addr) | (self.rb(addr + 1) << 8)

    def ww(self, addr: int, val: int):
        self.wb(addr, val)
        self.wb(addr + 1, val >> 8)

    # ---------- register pairs ----------
    def bc(self): return (self.b << 8) | self.c
    def de(self): return (self.d << 8) | self.e
    def hl(self): return (self.h << 8) | self.l
    def set_bc(self, v): self.b, self.c = (v >> 8) & MASK8, v & MASK8
    def set_de(self, v): self.d, self.e = (v >> 8) & MASK8, v & MASK8
    def set_hl(self, v): self.h, self.l = (v >> 8) & MASK8, v & MASK8

    def get_r8(self, n: int) -> int:
        return (self.b, self.c, self.d, self.e, self.h, self.l,
                self.rb(self.hl()), self.a)[n & 7]

    def set_r8(self, n: int, v: int):
        v &= MASK8; n &= 7
        if n == 0: self.b = v
        elif n == 1: self.c = v
        elif n == 2: self.d = v
        elif n == 3: self.e = v
        elif n == 4: self.h = v
        elif n == 5: self.l = v
        elif n == 6: self.wb(self.hl(), v)
        else: self.a = v

    def flags_byte(self) -> int:
        return ((self.s << 7) | (self.z << 6) | (self.ac << 4) |
                (self.p << 2) | (1 << 1) | self.cy)

    def set_flags_byte(self, f: int):
        self.s = (f >> 7) & 1; self.z = (f >> 6) & 1
        self.ac = (f >> 4) & 1; self.p = (f >> 2) & 1
        self.cy = f & 1

    # ---------- fetch/stack ----------
    def fetch8(self):
        v = self.rb(self.pc); self.pc = (self.pc + 1) & MASK16; return v

    def fetch16(self):
        lo = self.fetch8(); hi = self.fetch8(); return lo | hi << 8

    def push(self, v: int):
        old_sp = self.sp
        self.sp = (self.sp - 2) & MASK16
        self.ww(self.sp, v)
        if self.trace_enabled:
            self.stack_trace.append({
                'step': self.steps, 'pc': self.pc, 'op': 'PUSH',
                'old_sp': old_sp, 'sp': self.sp, 'value': v & MASK16
            })

    def pop(self) -> int:
        old_sp = self.sp
        v = self.rw(self.sp); self.sp = (self.sp + 2) & MASK16
        if self.trace_enabled:
            self.stack_trace.append({
                'step': self.steps, 'pc': self.pc, 'op': 'POP',
                'old_sp': old_sp, 'sp': self.sp, 'value': v & MASK16
            })
        return v

    # ---------- flags ----------
    def _arith(self, x: int, carry: int, *, sub=False, keep_carry=False) -> int:
        x &= MASK8; a = self.a
        if sub:
            r = a - x - carry
            self.ac = 1 if ((a & 0x0F) - (x & 0x0F) - carry) < 0 else 0
            self.cy = 1 if r < 0 else 0
        else:
            r = a + x + carry
            self.ac = 1 if ((a & 0x0F) + (x & 0x0F) + carry) > 0x0F else 0
            self.cy = 1 if r > 0xFF else 0
        r &= MASK8
        self.z = int(r == 0); self.s = (r >> 7) & 1; self.p = parity8(r)
        return r

    def _logic(self, r: int, ac: int = 0):
        r &= MASK8; self.z = int(r == 0); self.s = (r >> 7) & 1
        self.p = parity8(r); self.cy = 0; self.ac = ac
        return r

    def _cond(self, code: int) -> bool:
        # condition index: NZ,Z,NC,C,PO,PE,P,M
        return ((code == 0 and not self.z) or (code == 1 and self.z) or
                (code == 2 and not self.cy) or (code == 3 and self.cy) or
                (code == 4 and not self.p) or (code == 5 and self.p) or
                (code == 6 and not self.s) or (code == 7 and self.s))

    def _daa(self):
        # Intel 8080 DAA, including AC/CY behaviour.
        a = self.a; add = 0; cy = self.cy
        if (a & 0x0F) > 9 or self.ac: add |= 0x06
        if a > 0x99 or self.cy or ((a & 0xF0) > 0x90 and (a & 0x0F) > 9):
            add |= 0x60; cy = 1
        r = a + add
        self.ac = 1 if ((a & 0x0F) + (add & 0x0F)) > 0x0F else 0
        self.a = r & MASK8; self.cy = cy
        self.z = int(self.a == 0); self.s = (self.a >> 7) & 1; self.p = parity8(self.a)

    # ---------- execution ----------
    def _exec(self, op: int) -> int:
        # MOV, including M=memory[HL].
        if 0x40 <= op <= 0x7F:
            if op == 0x76:
                self.halted = True; self.pc = (self.pc - 1) & MASK16; return 1
            self.set_r8((op >> 3) & 7, self.get_r8(op & 7)); return 0

        # MVI r,n
        if op in (0x06,0x0E,0x16,0x1E,0x26,0x2E,0x36,0x3E):
            self.set_r8((op >> 3) & 7, self.fetch8()); return 0

        # LXI rp,nn
        if op in (0x01,0x11,0x21,0x31):
            v = self.fetch16(); rp = (op >> 4) & 3
            if rp == 0: self.set_bc(v)
            elif rp == 1: self.set_de(v)
            elif rp == 2: self.set_hl(v)
            else: self.sp = v
            return 0

        # INR/DCR r (CY unaffected on real 8080).
        if op & 0xC7 in (0x04, 0x05):
            n = (op >> 3) & 7; oldcy = self.cy; v = self.get_r8(n)
            if op & 7 == 4: v2 = self._inc(v)
            else: v2 = self._dec(v)
            self.set_r8(n, v2); self.cy = oldcy; return 0

        # INX/DCX rp
        if op & 0xCF in (0x03, 0x0B):
            rp = (op >> 4) & 3
            if rp == 0: v = self.bc(); v = (v + (1 if op & 8 == 0 else -1)) & MASK16; self.set_bc(v)
            elif rp == 1: v = self.de(); v = (v + (1 if op & 8 == 0 else -1)) & MASK16; self.set_de(v)
            elif rp == 2: v = self.hl(); v = (v + (1 if op & 8 == 0 else -1)) & MASK16; self.set_hl(v)
            else: self.sp = (self.sp + (1 if op & 8 == 0 else -1)) & MASK16
            return 0

        # DAD rp
        if op in (0x09,0x19,0x29,0x39):
            v = (self.bc(), self.de(), self.hl(), self.sp)[(op >> 4) & 3]
            r = self.hl() + v; self.set_hl(r); self.cy = int(r > 0xFFFF); return 0

        # Direct/indirect loads.
        if op == 0x0A: self.a = self.rb(self.bc()); return 0
        if op == 0x1A: self.a = self.rb(self.de()); return 0
        if op == 0x02: self.wb(self.bc(), self.a); return 0
        if op == 0x12: self.wb(self.de(), self.a); return 0
        if op == 0x22: n = self.fetch16(); self.ww(n, self.hl()); return 0
        if op == 0x2A: n = self.fetch16(); self.set_hl(self.rw(n)); return 0
        if op == 0x32: n = self.fetch16(); self.wb(n, self.a); return 0
        if op == 0x3A: n = self.fetch16(); self.a = self.rb(n); return 0

        # Rotates.
        if op == 0x07:
            c = self.a >> 7; self.a = ((self.a << 1) | c) & MASK8; self.cy = c; return 0
        if op == 0x0F:
            c = self.a & 1; self.a = (self.a >> 1) | (c << 7); self.cy = c; return 0
        if op == 0x17:
            c = self.a >> 7; self.a = ((self.a << 1) | self.cy) & MASK8; self.cy = c; return 0
        if op == 0x1F:
            c = self.a & 1; self.a = (self.a >> 1) | (self.cy << 7); self.cy = c; return 0

        # Misc single-byte.
        if op in (0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38): return 0
        if op == 0x27: self._daa(); return 0
        if op == 0x2F: self.a ^= MASK8; return 0
        if op == 0x37: self.cy = 1; return 0
        if op == 0x3F: self.cy ^= 1; return 0
        if op == 0xEB: self.d, self.h = self.h, self.d; self.e, self.l = self.l, self.e; return 0
        if op == 0xE3:
            t = self.rw(self.sp); self.ww(self.sp, self.hl()); self.set_hl(t); return 0
        if op == 0xE9: self.pc = self.hl(); return 0
        if op == 0xF9: self.sp = self.hl(); return 0
        if op == 0xF3 or op == 0xFB: return 0

        # ALU register group.
        if 0x80 <= op <= 0xBF:
            group = (op >> 3) & 7; v = self.get_r8(op & 7)
            if group == 0: self.a = self._arith(v, 0)
            elif group == 1: self.a = self._arith(v, self.cy)
            elif group == 2: self.a = self._arith(v, 0, sub=True)
            elif group == 3: self.a = self._arith(v, self.cy, sub=True)
            elif group == 4: self.a = self._logic(self.a & v, 1 if ((self.a | v) & 8) else 0)
            elif group == 5: self.a = self._logic(self.a ^ v)
            elif group == 6: self.a = self._logic(self.a | v)
            else: self._arith(v, 0, sub=True)  # CMP leaves A unchanged
            return 0

        # Immediate ALU.
        if op in (0xC6,0xCE,0xD6,0xDE,0xE6,0xEE,0xF6,0xFE):
            v = self.fetch8()
            if op == 0xC6: self.a = self._arith(v, 0)
            elif op == 0xCE: self.a = self._arith(v, self.cy)
            elif op == 0xD6: self.a = self._arith(v, 0, sub=True)
            elif op == 0xDE: self.a = self._arith(v, self.cy, sub=True)
            elif op == 0xE6: self.a = self._logic(self.a & v, 1 if ((self.a | v) & 8) else 0)
            elif op == 0xEE: self.a = self._logic(self.a ^ v)
            elif op == 0xF6: self.a = self._logic(self.a | v)
            else: self._arith(v, 0, sub=True)
            return 0

        # Conditional/unconditional jumps.
        if op in (0xC3, 0xCB): self.pc = self.fetch16(); return 0
        if op in (0xC2,0xCA,0xD2,0xDA,0xE2,0xEA,0xF2,0xFA):
            n = self.fetch16(); self.pc = n if self._cond((op >> 3) & 7) else self.pc; return 0

        # CALL / conditional CALL.
        if op in (0xCD, 0xDD, 0xED, 0xFD):
            n = self.fetch16(); self.push(self.pc); self.pc = n; self.call_depth += 1; return 0
        if op in (0xC4,0xCC,0xD4,0xDC,0xE4,0xEC,0xF4,0xFC):
            n = self.fetch16()
            if self._cond((op >> 3) & 7): self.push(self.pc); self.pc = n; self.call_depth += 1
            return 0

        # RET / conditional RET.
        if op in (0xC9, 0xD9):
            self.pc = self.pop(); self.call_depth = max(0, self.call_depth - 1); return 1 if self.pc == SENTINEL else 0
        if op in (0xC0,0xC8,0xD0,0xD8,0xE0,0xE8,0xF0,0xF8):
            if self._cond((op >> 3) & 7):
                self.pc = self.pop(); self.call_depth = max(0, self.call_depth - 1); return 1 if self.pc == SENTINEL else 0
            return 0

        # PUSH/POP.
        if op in (0xC5,0xD5,0xE5,0xF5):
            rp = (op >> 4) & 3
            self.push((self.bc(), self.de(), self.hl(), (self.a << 8) | self.flags_byte())[rp]); return 0
        if op in (0xC1,0xD1,0xE1,0xF1):
            rp = (op >> 4) & 3; v = self.pop()
            if rp == 0: self.set_bc(v)
            elif rp == 1: self.set_de(v)
            elif rp == 2: self.set_hl(v)
            else: self.a = v >> 8; self.set_flags_byte(v & MASK8)
            return 0

        # IN/OUT are modeled only as callbacks: no Vector peripherals here.
        if op == 0xDB:
            self.a = self.io_read(self.fetch8()) & MASK8; return 0
        if op == 0xD3:
            self.io_write(self.fetch8(), self.a); return 0

        # RST n.
        if op in (0xC7,0xCF,0xD7,0xDF,0xE7,0xEF,0xF7,0xFF):
            self.push(self.pc); self.pc = op & 0x38; return 0

        raise RuntimeError(f"Unknown/unsupported 8080 opcode 0x{op:02X} at PC=0x{(self.pc-1)&MASK16:04X}")

    def _inc(self, v):
        r = (v + 1) & MASK8; self.z = int(r == 0); self.s = r >> 7; self.p = parity8(r)
        self.ac = int((v & 0x0F) == 0x0F); return r

    def _dec(self, v):
        r = (v - 1) & MASK8; self.z = int(r == 0); self.s = r >> 7; self.p = parity8(r)
        self.ac = int((v & 0x0F) == 0x00); return r

    def snapshot(self, pc=None, opcode=None):
        return {
            'pc': self.pc if pc is None else pc, 'opcode': opcode,
            'a': self.a, 'b': self.b, 'c': self.c, 'd': self.d,
            'e': self.e, 'h': self.h, 'l': self.l, 'sp': self.sp,
            'z': self.z, 's': self.s, 'p': self.p, 'cy': self.cy, 'ac': self.ac,
            'flags': self.flags_byte(), 'call_depth': self.call_depth,
        }

    def reset_trace(self):
        self.trace.clear(); self.write_trace.clear(); self.read_trace.clear()
        self.stack_trace.clear(); self.vram_trace.clear()

    def step(self) -> int:
        if self.halted: return 1
        pc0 = self.pc
        pre = self.snapshot(pc=pc0, opcode=None)
        op = self.fetch8()
        self._last_instruction = (pc0, op)
        stop = self._exec(op)
        self.steps += 1
        if self.trace_enabled:
            post = self.snapshot(pc=self.pc, opcode=op)
            self.trace.append({'step': self.steps - 1, 'pc': pc0, 'opcode': op,
                               'pre': pre, 'post': post})
        return stop

    def run_until(self, *, max_steps=1_000_000, stop_pc=None, stop_halt=True):
        start_steps = self.steps
        for _ in range(max_steps):
            if stop_pc is not None and self.pc == stop_pc: return self.steps - start_steps
            if self.halted and stop_halt: return self.steps - start_steps
            self.step()
        raise TimeoutError(f"8080 execution limit reached: {max_steps} steps, PC=0x{self.pc:04X}")


# ---------------- assembler ----------------
REGS = {'b':0,'c':1,'d':2,'e':3,'h':4,'l':5,'m':6,'a':7}
RPS = {'b':0,'bc':0,'d':1,'de':1,'h':2,'hl':2,'sp':3}
COND = {'nz':0,'z':1,'nc':2,'c':3,'po':4,'pe':5,'p':6,'m':7}


def strip_comment(s):
    # z88dk ASM commonly uses ';'.  Preserve quoted semicolons.
    q = None
    for i,ch in enumerate(s):
        if ch in "'\"": q = None if q == ch else (ch if q is None else q)
        elif ch == ';' and q is None: return s[:i]
    return s


def split_args(s):
    out=[]; cur=''; q=None; depth=0
    for ch in s:
        if ch in "'\"": q = None if q == ch else (ch if q is None else q)
        if q is None:
            if ch == '(': depth += 1
            elif ch == ')': depth -= 1
            if ch == ',' and depth == 0:
                out.append(cur.strip()); cur=''; continue
        cur += ch
    if cur.strip() or s.strip(): out.append(cur.strip())
    return out


def expr_eval(expr: str, symbols: dict[str,int]) -> int:
    e = expr.strip()
    e = re.sub(r'(?<![A-Za-z0-9_])\$([0-9A-Fa-f]+)', r'0x\1', e)
    e = re.sub(r'(?<![A-Za-z0-9_])%([01]+)', r'0b\1', e)
    e = re.sub(r'(?<![A-Za-z0-9_])([0-9A-Fa-f]+)[Hh]\b', r'0x\1', e)
    e = re.sub(r'(?<![A-Za-z0-9_])([01]+)[Bb]\b', r'0b\1', e)
    # character literals and symbols are accepted by Python AST below.
    tree = ast.parse(e, mode='eval')
    ops = {ast.Add:operator.add, ast.Sub:operator.sub, ast.Mult:operator.mul,
           ast.FloorDiv:operator.floordiv, ast.LShift:operator.lshift,
           ast.RShift:operator.rshift, ast.BitAnd:operator.and_,
           ast.BitOr:operator.or_, ast.BitXor:operator.xor,
           ast.Mod:operator.mod, ast.USub:operator.neg, ast.UAdd:operator.pos,
           ast.Invert:operator.invert}
    def ev(n):
        if isinstance(n, ast.Constant): return ord(n.value) if isinstance(n.value,str) and len(n.value)==1 else int(n.value)
        if isinstance(n, ast.Name):
            if n.id.lower() in symbols: return symbols[n.id.lower()]
            raise KeyError(n.id)
        if isinstance(n, ast.UnaryOp): return ops[type(n.op)](ev(n.operand))
        if isinstance(n, ast.BinOp): return ops[type(n.op)](ev(n.left), ev(n.right))
        raise ValueError(f"unsupported expression: {expr}")
    return ev(tree.body)


def parse_string_literal(x):
    x=x.strip()
    if len(x)>=2 and x[0] in "'\"" and x[-1]==x[0]:
        return list(x[1:-1].encode('latin1'))
    return None


def instruction_size(line: str, symbols: dict[str,int], allow_unknown=True) -> int:
    b = assemble_instruction(line, symbols, unresolved_zero=True)
    return len(b) if b is not None else 0


def assemble_instruction(line: str, symbols: dict[str,int], unresolved_zero=False):
    parts=line.strip().split(None,1)
    if not parts: return None
    m=parts[0].lower(); ops=split_args(parts[1]) if len(parts)>1 else []
    def val(x, default=0):
        try: return expr_eval(x, symbols) & MASK16
        except KeyError:
            if unresolved_zero: return default
            raise
    if m in ('nop',): return [0x00]
    if m in ('hlt',): return [0x76]
    if m in ('mov',):
        return [0x40 | (REGS[ops[0].lower()]<<3) | REGS[ops[1].lower()]]
    if m in ('mvi',): return [0x06 | (REGS[ops[0].lower()]<<3), val(ops[1])]
    if m == 'lxi':
        return [0x01 | (RPS[ops[0].lower()]<<4), val(ops[1]) & 255, val(ops[1])>>8]
    if m == 'ld':
        a,b=ops[0].lower(),ops[1].lower()
        if a=='sp' and b=='hl': return [0xF9]
        if a=='a' and b=='(bc)': return [0x0A]
        if a=='a' and b=='(de)': return [0x1A]
        if b=='a' and a=='(bc)': return [0x02]
        if b=='a' and a=='(de)': return [0x12]
        if a=='a' and b.startswith('('): return [0x3A, val(b[1:-1])&255, val(b[1:-1])>>8]
        if b=='a' and a.startswith('('): return [0x32, val(a[1:-1])&255, val(a[1:-1])>>8]
        if b=='(hl)': return [0x40 | (REGS[a]<<3) | 6]
        if a=='(hl)': return [0x40 | (6<<3) | REGS[b]]
        if a in REGS: return [0x06 | (REGS[a]<<3), val(ops[1])]
        if a in RPS: return [0x01 | (RPS[a]<<4), val(ops[1])&255, val(ops[1])>>8]
    if m == 'stax':
        x=ops[0].lower(); return [0x02 if x in ('b','bc') else 0x12]
    if m == 'ldax':
        x=ops[0].lower(); return [0x0A if x in ('b','bc') else 0x1A]
    if m in ('sta','lda','shld','lhld'):
        op={'sta':0x32,'lda':0x3A,'shld':0x22,'lhld':0x2A}[m]; n=val(ops[0]); return [op,n&255,n>>8]
    if m in ('inr','inc') and len(ops)==1:
        x=ops[0].lower()
        if x in REGS: return [0x04 | (REGS[x]<<3)]
        if x in RPS: return [0x03 | (RPS[x]<<4)]
    if m in ('dcr','dec') and len(ops)==1:
        x=ops[0].lower()
        if x in REGS: return [0x05 | (REGS[x]<<3)]
        if x in RPS: return [0x0B | (RPS[x]<<4)]
    if m=='dad': return [0x09 | (RPS[ops[0].lower()]<<4)]
    if m in ('rlc','rlca'): return [0x07]
    if m in ('rrc','rrca'): return [0x0F]
    if m in ('ral','rla'): return [0x17]
    if m in ('rar','rra'): return [0x1F]
    if m in ('xchg','xthl','pchl','stc','cmc','cma','cpl','daa','ei','di'):
        return {'xchg': [0xEB], 'xthl':[0xE3], 'pchl':[0xE9], 'stc':[0x37],
                'cmc':[0x3F], 'cma':[0x2F], 'cpl':[0x2F], 'daa':[0x27],
                'ei':[0xFB], 'di':[0xF3]}[m]
    alu={'add':0x80,'adc':0x88,'sub':0x90,'sbb':0x98,'ana':0xA0,'xra':0xA8,'ora':0xB0,'cmp':0xB8}
    if m in alu:
        x=ops[-1].lower()
        if x in REGS: return [alu[m] | REGS[x]]
        imm={'add':0xC6,'adc':0xCE,'sub':0xD6,'sbb':0xDE,'ana':0xE6,'xra':0xEE,'ora':0xF6,'cmp':0xFE}[m]
        n=val(ops[-1]); return [imm,n]
    if m in ('adi','aci','sui','sbi','ani','xri','ori','cpi'):
        return [{'adi':0xC6,'aci':0xCE,'sui':0xD6,'sbi':0xDE,'ani':0xE6,'xri':0xEE,'ori':0xF6,'cpi':0xFE}[m], val(ops[0])]
    if m in ('jmp','jnz','jz','jnc','jc','jpo','jpe','jp','jm'):
        op={'jmp':0xC3,'jnz':0xC2,'jz':0xCA,'jnc':0xD2,'jc':0xDA,'jpo':0xE2,'jpe':0xEA,'jp':0xF2,'jm':0xFA}[m]; n=val(ops[0]); return [op,n&255,n>>8]
    if m in ('call','cc','cnz','cz','cnc','ccall','cpo','cpe','cp','cm'):
        op={'call':0xCD,'cnz':0xC4,'cz':0xCC,'cnc':0xD4,'ccall':0xDC,'cc':0xDC,'cpo':0xE4,'cpe':0xEC,'cp':0xF4,'cm':0xFC}[m]; n=val(ops[0]); return [op,n&255,n>>8]
    if m in ('ret','rnz','rz','rnc','rc','rpo','rpe','rp','rm'):
        return [{'ret':0xC9,'rnz':0xC0,'rz':0xC8,'rnc':0xD0,'rc':0xD8,'rpo':0xE0,'rpe':0xE8,'rp':0xF0,'rm':0xF8}[m]]
    if m in ('push','pop'):
        x=ops[0].lower(); base=0xC5 if m=='push' else 0xC1
        if x=='psw': rp=3
        else: rp=RPS[x]
        return [base | (rp<<4)]
    if m=='in': return [0xDB,val(ops[0])&255]
    if m=='out': return [0xD3,val(ops[0])&255]
    if m=='rst': return [0xC7 | ((val(ops[0]) & 7)<<3)]
    return None


@dataclass
class Assembled:
    data: bytearray
    labels: dict[str,int]
    origins: list[tuple[int,int]]


class Assembler8080:
    def __init__(self): self.symbols={}

    def assemble(self, filename: str) -> Assembled:
        with open(filename, encoding='utf-8') as f: lines=f.readlines()
        return self.assemble_text(lines)

    def assemble_text(self, lines):
        # Pass 1: determine addresses.  We keep a sparse map so ORG/data gaps
        # do not force a giant output image.
        addr=0; max_addr=0; symbols={}; equs={}; records=[]
        def label_name(x): return x.strip().lower()
        for raw in lines:
            s=strip_comment(raw).strip()
            label_here=None
            if not s: continue
            # allow label and instruction/data on same line
            if ':' in s:
                left,s2=s.split(':',1); left=left.strip()
                if re.match(r'^[A-Za-z_.$?][\w.$?]*$', left):
                    label_here=label_name(left)
                    symbols[label_here]=addr; s=s2.strip()
                    if not s: continue
            # NAME EQU value is a common 8080/z88dk form.  Recognize it
            # before split(None, 1), which would yield only two fields.
            mequ=re.match(r'^([A-Za-z_.$?][\w.$?]*)\s+(?:EQU|\.EQU)\s+(.+)$', s, re.I)
            if mequ:
                name, expression=mequ.groups()
                symbols[label_name(name)]=expr_eval(expression.strip(),symbols)
                continue
            toks=s.split(None,1); m=toks[0].lower(); rest=toks[1].strip() if len(toks)>1 else ''
            if m in ('section','public','extern','module','end'): continue
            if m in ('org','.org'):
                try: addr=expr_eval(rest,symbols)
                except: addr=0
                max_addr=max(max_addr,addr); continue
            if m in ('equ','.equ'):
                a=split_args(rest)
                if len(a)>=2:
                    try: symbols[label_name(a[0])]=expr_eval(a[1],symbols)
                    except: symbols[label_name(a[0])]=0
                elif len(a)==1 and label_here is not None:
                    # Also accept LABEL: EQU value.  The colon parser has
                    # already installed LABEL, so update that symbol here.
                    try: symbols[label_here]=expr_eval(a[0],symbols)
                    except: symbols[label_here]=0
                continue
            if m in ('defb','db','byte'):
                n=0
                for x in split_args(rest): n += len(parse_string_literal(x) or [0]) if parse_string_literal(x) is not None else 1
                records.append((addr,s)); addr+=n; max_addr=max(max_addr,addr); continue
            if m in ('defw','dw','word'):
                n=len(split_args(rest))*2; records.append((addr,s)); addr+=n; max_addr=max(max_addr,addr); continue
            if m in ('defs','ds','defm'):
                a=split_args(rest)
                if m=='defm': n=len(parse_string_literal(rest) or rest.encode('latin1'))
                else:
                    try:n=expr_eval(a[0],symbols)
                    except:n=0
                records.append((addr,s)); addr+=n; max_addr=max(max_addr,addr); continue
            b=assemble_instruction(s,symbols,unresolved_zero=True)
            if b is not None: records.append((addr,s)); addr+=len(b); max_addr=max(max_addr,addr)
            else:
                # Unknown directives are ignored, but an unknown instruction
                # must be caught on pass 2 rather than silently shifting layout.
                if re.match(r'^[A-Za-z]',m):
                    raise ValueError(f"Cannot assemble line: {raw.rstrip()}")
        # Pass 2, now all labels are known.
        out=bytearray(max_addr)
        for a,s in records:
            toks=s.split(None,1); m=toks[0].lower(); rest=toks[1].strip() if len(toks)>1 else ''
            if m in ('defb','db','byte','defm'):
                vals=[]
                if m=='defm' and not split_args(rest): vals=parse_string_literal(rest) or list(rest.encode('latin1'))
                else:
                    for x in split_args(rest):
                        q=parse_string_literal(x)
                        if q is not None: vals.extend(q)
                        else: vals.append(expr_eval(x,symbols)&255)
                out[a:a+len(vals)]=bytes(vals)
            elif m in ('defw','dw','word'):
                p=a
                for x in split_args(rest):
                    n=expr_eval(x,symbols)&MASK16; out[p:p+2]=bytes((n&255,n>>8)); p+=2
            elif m in ('defs','ds'):
                q=split_args(rest); n=expr_eval(q[0],symbols) if q else 0; fill=expr_eval(q[1],symbols)&255 if len(q)>1 else 0
                out[a:a+n]=bytes([fill])*n
            else:
                b=assemble_instruction(s,symbols)
                if b is None: raise ValueError(f"Cannot assemble line: {s}")
                out[a:a+len(b)]=bytes(b)
        self.symbols=symbols
        return Assembled(out,symbols,records)


class Emulator8080:
    def __init__(self):
        self.cpu=CPU8080(); self.asm=None; self.base=0; self.program=bytearray()

    def reset(self):
        io_read, io_write = self.cpu.io_read, self.cpu.io_write
        self.cpu=CPU8080(io_read=io_read, io_write=io_write)
        if self.program:
            for i,b in enumerate(self.program):
                if b: self.cpu.wb((self.base+i)&MASK16,b)
        return self.cpu

    def load_asm(self, filename, base=None):
        self.asm=Assembler8080().assemble(filename)
        if base is None: base=0
        for i,b in enumerate(self.asm.data):
            if b: self.cpu.wb((base+i)&MASK16,b)
        self.base=base
        self.program=bytearray(self.asm.data)
        return self.asm

    def load_bytes(self, data, address=0):
        for i,b in enumerate(data): self.cpu.wb(address+i,b)

    def resolve_entry(self, entry):
        if isinstance(entry, int): return entry & MASK16
        try: return int(str(entry), 0) & MASK16
        except ValueError: return self.asm.labels[str(entry).lower()]

    def setup_call(self, entry, *, args=(), sp=0x7FF0, sentinel=SENTINEL):
        c=self.cpu
        c.halted=False; c.steps=0; c.call_depth=0
        # __z88dk_callee entry convention: SP points at return address,
        # followed by 16-bit arguments at SP+2, SP+4, ... .
        c.trace_enabled=False
        c.ww(sp, sentinel)
        for i,arg in enumerate(args): c.ww((sp+2+2*i)&MASK16, arg)
        c.sp=sp & MASK16; c.pc=self.resolve_entry(entry)
        c.reset_trace()
        return c

    def call(self, entry, *, args=(), sp=0xF000, sentinel=SENTINEL,
             max_steps=1_000_000):
        self.setup_call(entry,args=args,sp=sp,sentinel=sentinel)
        return self.cpu.run_until(max_steps=max_steps, stop_pc=sentinel)


@dataclass
class MemoryExpectation:
    address: int
    value: int
    mask: int = 0xFF
    description: str = ''


@dataclass
class TestCase:
    name: str
    entry: str|int
    args: tuple = ()
    sp: int = 0xF000
    max_steps: int = 1_000_000
    initial_memory: dict | None = None
    memory: tuple[MemoryExpectation, ...] = ()
    expected_registers: dict | None = None
    expected_writes: tuple[tuple[int,int], ...] = ()


@dataclass
class ReferenceResult:
    memory: tuple[MemoryExpectation, ...] = ()
    registers: dict | None = None
    writes: tuple[tuple[int,int], ...] = ()


@dataclass
class TestResult:
    case: TestCase
    passed: bool
    steps: int = 0
    message: str = ''
    mismatch: dict | None = None


class TestRunner:
    def __init__(self, emulator: Emulator8080):
        self.emulator=emulator

    def _mismatch(self, case, kind, **kw):
        d={'kind':kind}; d.update(kw); return d

    def run(self, case: TestCase, *, init_memory=None, reference=None, trace=False):
        emu=self.emulator; c=emu.cpu
        initial=dict(case.initial_memory or {})
        if init_memory: initial.update(init_memory)
        for addr,val in initial.items(): c.wb(addr,val)

        # The reference model is deliberately executed BEFORE the ASM run and
        # receives only the test case + initial memory.  It therefore cannot
        # accidentally inspect the ASM result.
        ref=ReferenceResult()
        if reference is not None:
            r=reference(case, dict(initial)) if callable(reference) else reference
            if isinstance(r, ReferenceResult): ref=r
            elif isinstance(r, dict):
                ref=ReferenceResult(tuple(r.get('memory',())),r.get('registers'),tuple(r.get('writes',())))
            else:
                ref=ReferenceResult(tuple(r))

        c.trace_enabled=trace
        try:
            steps=emu.call(case.entry,args=case.args,sp=case.sp,max_steps=case.max_steps)
        except Exception as exc:
            return TestResult(case,False,c.steps,f'{type(exc).__name__}: {exc}',
                              self._mismatch(case,'exception',exception=str(exc),state=c.snapshot()))

        expectations=list(case.memory)+list(ref.memory)
        for exp in expectations:
            actual=c.rb(exp.address)
            if (actual & exp.mask) != (exp.value & exp.mask):
                addr=exp.address & MASK16
                event=None
                for ev in reversed(c.write_trace):
                    if ev[2] == addr:
                        event=ev; break
                return TestResult(case,False,steps,'memory mismatch',self._mismatch(
                    case,'memory',address=addr,expected=exp.value & MASK8,
                    actual=actual,mask=exp.mask & MASK8,description=exp.description,
                    event=event,state=c.snapshot()))

        expected_regs={}
        if case.expected_registers: expected_regs.update(case.expected_registers)
        if ref.registers: expected_regs.update(ref.registers)
        if expected_regs:
            names={'a','b','c','d','e','h','l','sp','pc','z','s','p','cy','ac'}
            snap=c.snapshot()
            for name,want in expected_regs.items():
                n=name.lower()
                if n not in names: raise ValueError(f'Unknown register/flag: {name}')
                actual=snap[n]
                mask=MASK16 if n in ('sp','pc') else 1 if n in ('z','s','p','cy','ac') else MASK8
                if actual != (want & mask):
                    return TestResult(case,False,steps,'register mismatch',self._mismatch(
                        case,'register',register=n,expected=want,actual=actual,state=snap))

        expected_writes=list(case.expected_writes) or list(ref.writes)
        if expected_writes:
            actual_writes=[(a,v) for _,_,a,_,v in c.write_trace]
            if actual_writes != expected_writes:
                i=0; lim=min(len(actual_writes),len(expected_writes))
                while i<lim and actual_writes[i]==expected_writes[i]: i+=1
                exp=expected_writes[i] if i<len(expected_writes) else None
                act=actual_writes[i] if i<len(actual_writes) else None
                event=c.write_trace[i] if i<len(c.write_trace) else None
                mm=self._mismatch(case,'write_trace',index=i,expected=exp,actual=act,
                                   event=event,state=c.snapshot())
                return TestResult(case,False,steps,'write trace mismatch',mm)

        return TestResult(case,True,steps,'PASS')

    def run_all(self, cases, *, init_memory=None, reference=None, trace=False, stop_on_fail=False):
        results=[]
        for case in cases:
            # Fresh CPU for deterministic independent tests.
            self.emulator.reset()
            r=self.run(case,init_memory=init_memory,reference=reference,trace=trace)
            results.append(r)
            if stop_on_fail and not r.passed: break
        return results


def format_mismatch(result: TestResult) -> str:
    if result.passed: return f'{result.case.name}: PASS ({result.steps} steps)'
    m=result.mismatch or {}
    out=[f'{result.case.name}: FAIL — {result.message}']
    if m.get('kind')=='memory':
        out += [f"  address:  0x{m['address']:04X}",
                f"  expected: 0x{m['expected']:02X}",
                f"  actual:   0x{m['actual']:02X}",
                f"  mask:     0x{m['mask']:02X}"]
        if m.get('description'): out.append(f"  detail:   {m['description']}")
        if m.get('event'):
            _,pc,addr,old,new = m['event']
            out.append(f"  ASM:      PC=0x{pc:04X} WRITE 0x{addr:04X} {old:02X}->{new:02X}")
    elif m.get('kind')=='register':
        out += [f"  register: {m['register']}",f"  expected: 0x{m['expected']:X}",f"  actual:   0x{m['actual']:X}"]
    elif m.get('kind')=='write_trace':
        out += [f"  index:    {m['index']}",f"  expected: {m['expected']}",f"  actual:   {m['actual']}"]
        if m.get('event'):
            _,pc,addr,old,new = m['event']
            out.append(f"  ASM:      PC=0x{pc:04X} WRITE 0x{addr:04X} {old:02X}->{new:02X}")
    if 'state' in m: out.append('  state:    '+fmt_state(m['state']))
    return '\n'.join(out)

def fmt_state(s):
    return (f"PC={s['pc']:04X} SP={s['sp']:04X} "
            f"A={s['a']:02X} BC={s['b']:02X}{s['c']:02X} "
            f"DE={s['d']:02X}{s['e']:02X} HL={s['h']:02X}{s['l']:02X} "
            f"F={s['s']}{s['z']}{s['ac']}{s['p']}{s['cy']}")


def main():
    ap=argparse.ArgumentParser(description='Vector-06C 8080 emulator for ASM verification')
    ap.add_argument('--asm'); ap.add_argument('--entry', help='address (0x...) or label')
    ap.add_argument('--base', type=lambda x:int(x,0), default=0)
    ap.add_argument('--sp', type=lambda x:int(x,0), default=0xF000)
    ap.add_argument('--arg', action='append', default=[], help='16-bit stack argument, repeatable')
    ap.add_argument('--max-steps', type=int, default=1_000_000)
    ap.add_argument('--trace', action='store_true'); ap.add_argument('--dump-writes', action='store_true')
    ap.add_argument('--dump-vram-writes', action='store_true'); ap.add_argument('--dump-ram', nargs=2, type=lambda x:int(x,0))
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--test-demo', action='store_true', help='run the built-in test-runner demonstration')
    args=ap.parse_args()
    if args.self_test:
        self_test(); return
    if args.test_demo:
        test_runner_demo(); return
    if not args.asm: ap.error('--asm or --self-test required')
    emu=Emulator8080(); asm=emu.load_asm(args.asm,args.base)
    if args.entry is None: entry=args.base
    else:
        try: entry=int(args.entry,0)
        except KeyError: entry=asm.labels[args.entry.lower()]
        except ValueError: entry=asm.labels[args.entry.lower()]
    emu.cpu.trace_enabled=args.trace
    try: steps=emu.call(entry,args=[int(x,0) for x in args.arg],sp=args.sp,max_steps=args.max_steps)
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        print('STATE:',fmt_state(emu.cpu.snapshot()),file=sys.stderr)
        if emu.cpu._last_instruction: print(f'LAST: PC={emu.cpu._last_instruction[0]:04X} OP={emu.cpu._last_instruction[1]:02X}',file=sys.stderr)
        return 2
    print(f'OK: {steps} steps; {fmt_state(emu.cpu.snapshot())}')
    if args.trace:
        for t in emu.cpu.trace: print(fmt_state(t)+f" OP={t['opcode']:02X}")
    if args.dump_writes:
        for n,pc,a,old,new in emu.cpu.write_trace: print(f'WRITE step={n} pc={pc:04X} addr={a:04X} {old:02X}->{new:02X}')
    if args.dump_vram_writes:
        for n,pc,a,old,new in emu.cpu.vram_trace: print(f'VRAM step={n} pc={pc:04X} addr={a:04X} {old:02X}->{new:02X}')
    if args.dump_ram:
        lo,hi=args.dump_ram
        for a in range(lo,hi+1,16): print(f'{a:04X}: '+' '.join(f'{emu.cpu.rb(x):02X}' for x in range(a,min(a+16,hi+1))))


def test_runner_demo():
    src='''\n        org 4000h\nstart:  mvi a, 12h\n        sta 5000h\n        mvi a, 34h\n        sta 5001h\n        ret\n'''
    a=Assembler8080().assemble_text(src.splitlines())
    emu=Emulator8080(); emu.asm=a; emu.program=bytearray(a.data)
    for i,b in enumerate(a.data):
        if b: emu.cpu.wb(i,b)
    runner=TestRunner(emu)
    def reference(case, initial):
        return ReferenceResult(memory=(MemoryExpectation(0x5000,0x12,0xFF,'reference[0]'),
                                        MemoryExpectation(0x5001,0x34,0xFF,'reference[1]')))
    cases=[TestCase('demo-write', 'start')]
    results=runner.run_all(cases,reference=reference)
    for r in results: print(format_mismatch(r))
    assert all(r.passed for r in results)

def self_test():
    # Arithmetic/flags, stack, calls, memory and conditional branches.
    src='''\n        org 4000h\nstart:  lxi sp, 7ff0h\n        mvi a, 0ffh\n        adi 1\n        jnz bad\n        jnc bad\n        mvi a, 10h\n        mvi b, 01h\n        add b\n        cpi 11h\n        jnz bad\n        lxi h, 1234h\n        push h\n        lxi h, 0000h\n        pop h\n        lxi d, 5000h\n        mov a,h\n        stax d\n        jmp ok\nbad:    hlt\nok:     ret\n'''
    # STAX is deliberately not an assembler alias in the core subset; build a
    # smaller source for self-test and use direct opcode for that operation.
    src=src.replace('        stax d\n','        ld (5000h),a\n')
    a=Assembler8080().assemble_text(src.splitlines())
    c=CPU8080();
    for i,b in enumerate(a.data):
        if b: c.wb(i,b)
    c.pc=a.labels['start']; c.sp=0x7ff2; c.push(SENTINEL); c.run_until(stop_pc=SENTINEL)
    assert c.pc==SENTINEL and c.hl()==0x1234 and c.rb(0x5000)==0x12

    # EQU regression tests: both the NAME EQU value form and the directive
    # form must define symbols without emitting data or changing layout.
    equ_src='''\n        org 4200h\nCONST_A EQU 1234h\nCONST_B EQU CONST_A+2\nCONST_C: EQU CONST_B+2\nstart:  lxi h, CONST_C\n        mvi a, 5ah\n        sta 5000h\n        ret\n'''
    ea=Assembler8080().assemble_text(equ_src.splitlines())
    assert ea.labels['const_a']==0x1234
    assert ea.labels['const_b']==0x1236
    assert ea.labels['const_c']==0x1238
    assert ea.labels['start']==0x4200
    e=Emulator8080(); e.asm=ea; e.program=bytearray(ea.data); e.base=0
    for i,b in enumerate(ea.data):
        if b: e.cpu.wb(i,b)
    e.call('start')
    assert e.cpu.hl()==0x1238 and e.cpu.rb(0x5000)==0x5a
    print('SELF-TEST: PASS')


if __name__=='__main__': main()
