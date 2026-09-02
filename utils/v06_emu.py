#!/usr/bin/env python3
"""
v06_emu.py — Minimal Intel 8080 emulator for Vector-06C 512x256 VRAM verification.

Usage:
    python3 v06_emu.py [--asm FILE] [--entry ADDR] [--dump-vram] [--dump-ram START END]

Features:
    - 8080 CPU core (no CB/DD/ED/FD prefixes — matches pr512t.asm constraints)
    - 64K memory with VRAM plane tracking
    - Mini-assembler for pr512t.asm-style code
    - VRAM text dump (shows rendered pixels)
"""

import sys
import re
import argparse

# ─────────────────────────────────────────────────────────
#  8080 CPU
# ─────────────────────────────────────────────────────────
class CPU8080:
    def __init__(self):
        self.mem = bytearray(65536)
        self.a = self.b = self.c = self.d = self.e = self.h = self.l = 0
        self.sp = 0xFFF0
        self.pc = 0
        self.z = self.s = self.p = self.cy = self.ac = 0  # flags

    # --- memory ---
    def rb(self, addr):
        return self.mem[addr & 0xFFFF]

    def wb(self, addr, val):
        self.mem[addr & 0xFFFF] = val & 0xFF

    def rw(self, addr):
        return self.rb(addr) | (self.rb(addr + 1) << 8)

    def ww(self, addr, val):
        self.wb(addr, val & 0xFF)
        self.wb(addr + 1, (val >> 8) & 0xFF)

    # --- register pairs ---
    def get_rp(self, r1, r2):
        return (r1 << 8) | r2

    def set_rp(self, r1, r2, val):
        return (val >> 8) & 0xFF, val & 0xFF

    def get_hl(self): return self.get_rp(self.h, self.l)
    def get_bc(self): return self.get_rp(self.b, self.c)
    def get_de(self): return self.get_rp(self.d, self.e)
    def get_sp(self): return self.get_rp(self.a, self.a)  # not used directly
    def set_hl(self, v): self.h, self.l = self.set_rp(self.h, self.l, v)
    def set_bc(self, v): self.b, self.c = self.set_rp(self.b, self.c, v)
    def set_de(self, v): self.d, self.e = self.set_rp(self.d, self.e, v)

    def get_reg(self, r):
        return {'a': self.a, 'b': self.b, 'c': self.c, 'd': self.d,
                'e': self.e, 'h': self.h, 'l': self.l, 'm': self.rb(self.get_hl())}[r]

    def set_reg(self, r, v):
        v &= 0xFF
        if r == 'a': self.a = v
        elif r == 'b': self.b = v
        elif r == 'c': self.c = v
        elif r == 'd': self.d = v
        elif r == 'e': self.e = v
        elif r == 'h': self.h = v
        elif r == 'l': self.l = v
        elif r == 'm': self.wb(self.get_hl(), v)

    # --- flags ---
    def update_flags(self, result, carry=0):
        result &= 0xFF
        self.z = 1 if result == 0 else 0
        self.s = 1 if result & 0x80 else 0
        self.p = 1 if bin(result).count('1') % 2 == 0 else 0
        self.cy = carry & 1
        return result

    def update_logic_flags(self, result):
        return self.update_flags(result, 0)

    # --- stack ---
    def push_word(self, val):
        self.sp = (self.sp - 2) & 0xFFFF
        self.ww(self.sp, val)

    def pop_word(self):
        val = self.rw(self.sp)
        self.sp = (self.sp + 2) & 0xFFFF
        return val

    # --- fetch ---
    def fetch_byte(self):
        b = self.rb(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return b

    def fetch_word(self):
        lo = self.fetch_byte()
        hi = self.fetch_byte()
        return lo | (hi << 8)

    # --- execute one instruction ---
    def step(self):
        op = self.fetch_byte()
        return self._exec(op)

    def _exec(self, op):
        """Execute opcode. Returns 0=continue, 1=halt/ret-to-caller."""
        # NOP
        if op == 0x00: return 0
        # HLT
        if op == 0x76: return 1

        # --- LD r,r' (MOV) ---
        if 0x40 <= op <= 0x7F and op != 0x76:
            dst_idx = (op >> 3) & 7
            src_idx = op & 7
            regs = ['b','c','d','e','h','l','m','a']
            val = self.get_reg(regs[src_idx])
            self.set_reg(regs[dst_idx], val)
            return 0

        # --- MVI r,n ---
        if op in (0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E):
            regs = {0x06:'b', 0x0E:'c', 0x16:'d', 0x1E:'e',
                    0x26:'h', 0x2E:'l', 0x36:'m', 0x3E:'a'}
            n = self.fetch_byte()
            self.set_reg(regs[op], n)
            return 0

        # --- LXI rp,nn ---
        if op in (0x01, 0x11, 0x21, 0x31):
            nn = self.fetch_word()
            if op == 0x01: self.set_bc(nn)
            elif op == 0x11: self.set_de(nn)
            elif op == 0x21: self.set_hl(nn)
            elif op == 0x31: self.sp = nn
            return 0

        # --- LD A,(rr) / LD (rr),A ---
        if op == 0x0A:  # LD A,(BC)
            self.a = self.rb(self.get_bc()); return 0
        if op == 0x1A:  # LD A,(DE)
            self.a = self.rb(self.get_de()); return 0
        if op == 0x02:  # LD (BC),A
            self.wb(self.get_bc(), self.a); return 0
        if op == 0x12:  # LD (DE),A
            self.wb(self.get_de(), self.a); return 0
        if op == 0x32:  # LD (nn),A
            nn = self.fetch_word(); self.wb(nn, self.a); return 0
        if op == 0x3A:  # LD A,(nn)
            nn = self.fetch_word(); self.a = self.rb(nn); return 0

        # --- LD SP,HL ---
        if op == 0xF9:
            self.sp = self.get_hl(); return 0

        # --- ALU on A ---
        def alu_op(func, use_carry=False):
            src_idx = op & 7
            regs = ['b','c','d','e','h','l','m','a']
            val = self.get_reg(regs[src_idx])
            return func(val, use_carry)

        # ADD
        if 0x80 <= op <= 0x87:
            def do_add(val, _):
                r = self.a + val
                c = 1 if r > 0xFF else 0
                self.a = self.update_flags(r, c)
            return alu_op(do_add) or 0
        # ADC
        if 0x88 <= op <= 0x8F:
            def do_adc(val, _):
                r = self.a + val + self.cy
                c = 1 if r > 0xFF else 0
                self.a = self.update_flags(r, c)
            return alu_op(do_adc) or 0
        # SUB
        if 0x90 <= op <= 0x97:
            def do_sub(val, _):
                r = self.a - val
                c = 1 if r < 0 else 0
                self.a = self.update_flags(r & 0xFF, c)
            return alu_op(do_sub) or 0
        # SBB
        if 0x98 <= op <= 0x9F:
            def do_sbb(val, _):
                r = self.a - val - self.cy
                c = 1 if r < 0 else 0
                self.a = self.update_flags(r & 0xFF, c)
            return alu_op(do_sbb) or 0
        # ANA (AND)
        if 0xA0 <= op <= 0xA7:
            def do_and(val, _):
                c = 0  # AND clears carry
                # auxiliary carry: logical AND of bit 3
                ac = 1 if ((self.a | val) & 0x08) else 0
                self.a = self.update_logic_flags(self.a & val)
                self.cy = 0
                self.ac = ac
            return alu_op(do_and) or 0
        # XRA (XOR)
        if 0xA8 <= op <= 0xAF:
            def do_xor(val, _):
                self.a = self.update_logic_flags(self.a ^ val)
                self.cy = 0; self.ac = 0
            return alu_op(do_xor) or 0
        # ORA
        if 0xB0 <= op <= 0xB7:
            def do_or(val, _):
                self.a = self.update_logic_flags(self.a | val)
                self.cy = 0; self.ac = 0
            return alu_op(do_or) or 0
        # CMP
        if 0xB8 <= op <= 0xBF:
            def do_cmp(val, _):
                r = self.a - val
                c = 1 if r < 0 else 0
                self.update_flags(r & 0xFF, c)
            return alu_op(do_cmp) or 0

        # --- ALU immediate ---
        if op == 0xC6:  # ADI A,n
            n = self.fetch_byte(); r = self.a + n
            self.a = self.update_flags(r, 1 if r > 0xFF else 0); return 0
        if op == 0xD6:  # SUI A,n
            n = self.fetch_byte(); r = self.a - n
            self.a = self.update_flags(r & 0xFF, 1 if r < 0 else 0); return 0
        if op == 0xE6:  # ANI A,n
            n = self.fetch_byte()
            self.a = self.update_logic_flags(self.a & n)
            self.cy = 0; return 0
        if op == 0xF6:  # ORI A,n
            n = self.fetch_byte()
            self.a = self.update_logic_flags(self.a | n)
            self.cy = 0; return 0
        if op == 0xEE:  # XRI A,n
            n = self.fetch_byte()
            self.a = self.update_logic_flags(self.a ^ n)
            self.cy = 0; return 0
        if op == 0xFE:  # CPI A,n
            n = self.fetch_byte(); r = self.a - n
            self.update_flags(r & 0xFF, 1 if r < 0 else 0); return 0

        # --- INC/DEC register ---
        if op in (0x04,0x0C,0x14,0x1C,0x24,0x2C,0x3C):  # INR
            regs = {0x04:'b',0x0C:'c',0x14:'d',0x1C:'e',0x24:'h',0x2C:'l',0x3C:'a'}
            r = self.get_reg(regs[op])
            self.set_reg(regs[op], self.update_flags(r + 1, self.cy))
            return 0
        if op in (0x05,0x0D,0x15,0x1D,0x25,0x2D,0x3D):  # DCR
            regs = {0x05:'b',0x0D:'c',0x15:'d',0x1D:'e',0x25:'h',0x2D:'l',0x3D:'a'}
            r = self.get_reg(regs[op])
            self.set_reg(regs[op], self.update_flags(r - 1, self.cy))
            return 0

        # --- INC/DEC 16-bit ---
        if op in (0x03,0x13,0x23,0x33):  # INX
            if op==0x03: self.set_bc((self.get_bc()+1)&0xFFFF)
            elif op==0x13: self.set_de((self.get_de()+1)&0xFFFF)
            elif op==0x23: self.set_hl((self.get_hl()+1)&0xFFFF)
            elif op==0x33: self.sp = (self.sp+1)&0xFFFF
            return 0
        if op in (0x0B,0x1B,0x2B,0x3B):  # DCX
            if op==0x0B: self.set_bc((self.get_bc()-1)&0xFFFF)
            elif op==0x1B: self.set_de((self.get_de()-1)&0xFFFF)
            elif op==0x2B: self.set_hl((self.get_hl()-1)&0xFFFF)
            elif op==0x3B: self.sp = (self.sp-1)&0xFFFF
            return 0

        # --- DAD rp ---
        if op in (0x09,0x19,0x29,0x39):
            if op==0x09: v = self.get_bc()
            elif op==0x19: v = self.get_de()
            elif op==0x29: v = self.get_hl()
            elif op==0x39: v = self.sp
            r = self.get_hl() + v
            self.set_hl(r & 0xFFFF)
            self.cy = 1 if r > 0xFFFF else 0
            return 0

        # --- Rotates ---
        if op == 0x07:  # RLC
            c = (self.a >> 7) & 1
            self.a = ((self.a << 1) | c) & 0xFF
            self.cy = c; return 0
        if op == 0x0F:  # RRC
            c = self.a & 1
            self.a = ((self.a >> 1) | (c << 7)) & 0xFF
            self.cy = c; return 0
        if op == 0x17:  # RAL
            c = (self.a >> 7) & 1
            self.a = ((self.a << 1) | self.cy) & 0xFF
            self.cy = c; return 0
        if op == 0x1F:  # RAR
            c = self.a & 1
            self.a = ((self.a >> 1) | (self.cy << 7)) & 0xFF
            self.cy = c; return 0

        # --- Jumps ---
        if op == 0xC3:  # JMP nn
            nn = self.fetch_word(); self.pc = nn; return 0
        if op == 0xC2:  # JNZ
            nn = self.fetch_word();
            if not self.z: self.pc = nn
            return 0
        if op == 0xCA:  # JZ
            nn = self.fetch_word()
            if self.z: self.pc = nn
            return 0
        if op == 0xD2:  # JNC
            nn = self.fetch_word()
            if not self.cy: self.pc = nn
            return 0
        if op == 0xDA:  # JC
            nn = self.fetch_word()
            if self.cy: self.pc = nn
            return 0
        if op == 0xE2:  # JPO
            nn = self.fetch_word()
            if not self.p: self.pc = nn
            return 0
        if op == 0xEA:  # JPE
            nn = self.fetch_word()
            if self.p: self.pc = nn
            return 0
        if op == 0xF2:  # JP
            nn = self.fetch_word()
            if not self.s: self.pc = nn
            return 0
        if op == 0xFA:  # JM
            nn = self.fetch_word()
            if self.s: self.pc = nn
            return 0
        if op == 0xE9:  # PCHL
            self.pc = self.get_hl(); return 0

        # --- Calls ---
        if op == 0xCD:  # CALL nn
            nn = self.fetch_word()
            self.push_word(self.pc)
            self.pc = nn; return 0
        if op == 0xC4:  # CNZ
            nn = self.fetch_word()
            if not self.z:
                self.push_word(self.pc); self.pc = nn
            return 0
        if op == 0xCC:  # CZ
            nn = self.fetch_word()
            if self.z:
                self.push_word(self.pc); self.pc = nn
            return 0

        # --- Returns ---
        if op == 0xC9:  # RET
            self.pc = self.pop_word(); return 0
        if op == 0xC0:  # RNZ
            if not self.z: self.pc = self.pop_word()
            return 0
        if op == 0xC8:  # RZ
            if self.z: self.pc = self.pop_word()
            return 0

        # --- PUSH/POP ---
        if op in (0xC5,0xD5,0xE5,0xF5):  # PUSH
            if op==0xC5: v = self.get_bc()
            elif op==0xD5: v = self.get_de()
            elif op==0xE5: v = self.get_hl()
            elif op==0xF5: v = (self.a << 8) | self.a  # AF: push A then flags
            # Actually for PUSH PSW (F5): pushes A and flags (PSW)
            if op == 0xF5:
                flags = (self.s<<7)|(self.z<<6)|(self.ac<<4)|(self.p<<2)|(self.cy<<1)|1
                self.push_word((self.a << 8) | flags)
            else:
                self.push_word(v)
            return 0
        if op in (0xC1,0xD1,0xE1,0xF1):  # POP
            v = self.pop_word()
            if op==0xC1: self.set_bc(v)
            elif op==0xD1: self.set_de(v)
            elif op==0xE1: self.set_hl(v)
            elif op==0xF1:
                self.a = (v >> 8) & 0xFF
                flags = v & 0xFF
                self.s = (flags>>7)&1; self.z = (flags>>6)&1
                self.ac = (flags>>4)&1; self.p = (flags>>2)&1
                self.cy = (flags>>1)&1
            return 0

        # --- Special ---
        if op == 0xEB:  # XCHG
            self.d, self.h = self.h, self.d
            self.e, self.l = self.l, self.e
            return 0
        if op == 0xE3:  # XTHL
            v = self.rw(self.sp)
            self.ww(self.sp, self.get_hl())
            self.set_hl(v)
            return 0
        if op == 0xF3:  # DI — nop in emulator
            return 0
        if op == 0xFB:  # EI — nop in emulator
            return 0
        if op == 0x27:  # DAA — simplified
            # Not needed for pr512t.asm, just nop
            return 0
        if op == 0x3F:  # CMC
            self.cy ^= 1; return 0
        if op == 0x37:  # STC
            self.cy = 1; return 0
        if op == 0x2F:  # CPL
            self.a = (~self.a) & 0xFF; return 0

        # RST instructions
        if 0xC7 <= op <= 0xFF and (op & 0x07) == 0x07 and op != 0xC7:
            pass  # not used
        if op in (0xC7,0xCF,0xD7,0xDF,0xE7,0xEF,0xF7,0xFF):
            addr = op & 0x38
            self.push_word(self.pc)
            self.pc = addr
            return 0

        print(f"  !!! Unknown opcode 0x{op:02X} at PC=0x{self.pc-1:04X}")
        return 1

    # --- run with cycle limit ---
    def run(self, max_steps=100000):
        for i in range(max_steps):
            r = self.step()
            if r:
                return i
        print(f"  !!! Cycle limit reached ({max_steps})")
        return max_steps


# ─────────────────────────────────────────────────────────
#  Mini-assembler for pr512t.asm instruction subset
# ─────────────────────────────────────────────────────────
REG8_MAP = {'b':0,'c':1,'d':2,'e':3,'h':4,'l':5,'m':6,'a':7}
RP16_MAP = {'b':0,'d':1,'h':2,'sp':3}

def parse_num(s):
    """Parse a number: 0xFF, 0xE0, 255, etc."""
    s = s.strip()
    if s.startswith('0x') or s.startswith('0X'):
        return int(s, 16)
    if s.startswith('$'):
        return int(s[1:], 16)
    if s.startswith('%'):
        return int(s[1:], 2)
    return int(s)

def assemble_line(line):
    """Assemble one line. Returns list of bytes or None."""
    # Strip comments
    if ';' in line:
        line = line[:line.index(';')]
    line = line.strip()
    if not line:
        return None
    # Skip labels, directives
    if line.startswith('defb') or line.startswith('defm') or line.startswith('defw'):
        return None
    if line.startswith('SECTION') or line.startswith('PUBLIC') or line.startswith('EXTERN'):
        return None
    if line.endswith(':'):
        return None
    if line.startswith('PUSH') or line.startswith('pop') or line.startswith('PUSH'):
        pass  # handle below

    parts = line.split(None, 1)
    if len(parts) == 0:
        return None
    mnem = parts[0].lower()
    operands = parts[1].strip().lower() if len(parts) > 1 else ''

    # Parse operands
    ops = [o.strip() for o in operands.split(',')] if operands else []

    # --- NOP ---
    if mnem == 'nop': return [0x00]
    if mnem == 'hlt': return [0x76]

    # --- MOV r,r' ---
    if mnem == 'mov' and len(ops) == 2:
        d = REG8_MAP.get(ops[0])
        s = REG8_MAP.get(ops[1])
        if d is not None and s is not None:
            return [0x40 | (d << 3) | s]

    # --- MVI r,n ---
    if mnem == 'mvi' and len(ops) == 2:
        d = REG8_MAP.get(ops[0])
        if d is not None:
            n = parse_num(ops[1])
            return [0x06 | (d << 3), n]

    # --- LXI rp,nn ---
    if mnem == 'lxi' and len(ops) == 2:
        rp = RP16_MAP.get(ops[0])
        if rp is not None:
            nn = parse_num(ops[1])
            return [0x01 | (rp << 4), nn & 0xFF, (nn >> 8) & 0xFF]

    # --- LD variants ---
    if mnem == 'ld':
        # LD A,(BC) / LD A,(DE) / LD A,(nn)
        if ops[0] == 'a':
            src = ops[1]
            if src == '(bc)': return [0x0A]
            if src == '(de)': return [0x1A]
            if src.startswith('(') and src.endswith(')'):
                addr = parse_num(src[1:-1])
                return [0x3A, addr & 0xFF, (addr >> 8) & 0xFF]
        # LD (BC),A / LD (DE),A / LD (nn),A
        if ops[1] == 'a':
            dst = ops[0]
            if dst == '(bc)': return [0x02]
            if dst == '(de)': return [0x12]
            if dst.startswith('(') and dst.endswith(')'):
                addr = parse_num(dst[1:-1])
                return [0x32, addr & 0xFF, (addr >> 8) & 0xFF]
        # LD SP,HL
        if ops[0] == 'sp' and ops[1] == 'hl':
            return [0xF9]
        # LD r,(HL) — same as MOV r,M
        if ops[1] == '(hl)':
            d = REG8_MAP.get(ops[0])
            if d is not None: return [0x40 | (d << 3) | 6]
        # LD (HL),r — same as MOV M,r
        if ops[0] == '(hl)':
            s = REG8_MAP.get(ops[1])
            if s is not None: return [0x40 | (6 << 3) | s]
        # LD r,n — same as MVI
        if len(ops) == 2:
            d = REG8_MAP.get(ops[0])
            if d is not None:
                try:
                    n = parse_num(ops[1])
                    return [0x06 | (d << 3), n]
                except:
                    pass
        # LD rp,nn — same as LXI
        rp = RP16_MAP.get(ops[0])
        if rp is not None:
            try:
                nn = parse_num(ops[1])
                return [0x01 | (rp << 4), nn & 0xFF, (nn >> 8) & 0xFF]
            except:
                pass

    # --- ALU r ---
    alu_ops = {'add':0x80,'adc':0x88,'sub':0x90,'sbb':0x98,
               'ana':0xA0,'xra':0xA8,'ora':0xB0,'cmp':0xB8}
    if mnem in alu_ops and len(ops) >= 1:
        base = alu_ops[mnem]
        # Could be "add a,r" or "add r" (8080 style) or "ana 0xF0" (immediate)
        src = ops[-1]  # last operand
        s = REG8_MAP.get(src)
        if s is not None:
            return [base | s]
        # Immediate
        try:
            n = parse_num(src)
            imm_map = {'add':0xC6,'adc':0xCE,'sub':0xD6,'sbb':0xDE,
                       'ana':0xE6,'xra':0xEE,'ora':0xF6,'cmp':0xFE}
            return [imm_map[mnem], n]
        except:
            pass

    # --- OR (HL) / AND (HL) etc ---
    if mnem in alu_ops and '(hl)' in operands:
        base = alu_ops[mnem]
        return [base | 6]

    # --- INC/DEC r ---
    if mnem == 'inc' and len(ops) == 1:
        r = REG8_MAP.get(ops[0])
        if r is not None: return [0x04 | (r << 3)]
        rp = RP16_MAP.get(ops[0])
        if rp is not None: return [0x03 | (rp << 4)]
    if mnem == 'dec' and len(ops) == 1:
        r = REG8_MAP.get(ops[0])
        if r is not None: return [0x05 | (r << 3)]
        rp = RP16_MAP.get(ops[0])
        if rp is not None: return [0x0B | (rp << 4)]

    # --- Rotates ---
    if mnem == 'rlc': return [0x07]
    if mnem == 'rrc': return [0x0F]
    if mnem == 'ral': return [0x17]
    if mnem == 'rar': return [0x1F]
    if mnem == 'rrca': return [0x0F]  # rrca = rrc on 8080
    if mnem == 'rlca': return [0x07]  # rlca = rlc on 8080

    # --- Jumps ---
    jmp_map = {'jmp':0xC3,'jnz':0xC2,'jz':0xCA,'jnc':0xD2,'jc':0xDA,
               'jpo':0xE2,'jpe':0xEA,'jp':0xF2,'jm':0xFA}
    if mnem in jmp_map:
        nn = parse_num(ops[0])
        return [jmp_map[mnem], nn & 0xFF, (nn >> 8) & 0xFF]

    # --- CALL ---
    if mnem == 'call':
        nn = parse_num(ops[0])
        return [0xCD, nn & 0xFF, (nn >> 8) & 0xFF]

    # --- RET ---
    if mnem == 'ret': return [0xC9]

    # --- PUSH/POP ---
    push_map = {'b':0xC5,'d':0xD5,'h':0xE5,'psw':0xF5}
    pop_map = {'b':0xC1,'d':0xD1,'h':0xE1,'psw':0xF1}
    if mnem == 'push' and len(ops) == 1:
        return [push_map.get(ops[0])]
    if mnem == 'pop' and len(ops) == 1:
        return [pop_map.get(ops[0])]

    # --- Special ---
    if mnem == 'xchg': return [0xEB]
    if mnem == 'xthl': return [0xE3]
    if mnem == 'di': return [0xF3]
    if mnem == 'ei': return [0xFB]
    if mnem == 'stc': return [0x37]
    if mnem == 'cmc': return [0x3F]
    if mnem == 'cma': return [0x2F]
    if mnem == 'daa': return [0x27]
    if mnem == 'pchl': return [0xE9]

    # --- DAD ---
    if mnem == 'dad':
        rp = RP16_MAP.get(ops[0])
        if rp is not None: return [0x09 | (rp << 4)]

    # --- SHLD / LHLD ---
    if mnem == 'shld':
        nn = parse_num(ops[0])
        return [0x22, nn & 0xFF, (nn >> 8) & 0xFF]
    if mnem == 'lhld':
        nn = parse_num(ops[0])
        return [0x2A, nn & 0xFF, (nn >> 8) & 0xFF]

    # --- STA / LDA ---
    if mnem == 'sta':
        nn = parse_num(ops[0])
        return [0x32, nn & 0xFF, (nn >> 8) & 0xFF]
    if mnem == 'lda':
        nn = parse_num(ops[0])
        return [0x3A, nn & 0xFF, (nn >> 8) & 0xFF]

    # --- CPI ---
    if mnem == 'cpi':
        n = parse_num(ops[0])
        return [0xFE, n]

    # --- OR A (zero operand) ---
    if mnem == 'or' and operands in ('', 'a'):
        return [0xB7]
    if mnem == 'and' and operands in ('', 'a'):
        return [0xA7]

    return None


def assemble_file(filename):
    """Assemble a .asm file into bytes. Returns (code_bytes, labels_dict)."""
    labels = {}
    lines = []
    with open(filename) as f:
        for line in f:
            lines.append(line.rstrip())

    # First pass: collect labels and compute addresses
    addr = 0
    code_lines = []
    for line in lines:
        stripped = line.strip()
        # Check for label
        if ':' in stripped and not stripped.startswith(';'):
            lbl = stripped.split(':')[0].strip()
            if lbl and not lbl.startswith('defb') and not lbl.startswith('defm'):
                labels[lbl] = addr
        # Try to assemble
        bytes_out = assemble_line(stripped)
        if bytes_out is not None:
            code_lines.append((addr, bytes_out, stripped))
            addr += len(bytes_out)
        elif stripped.startswith('defb'):
            # Parse defb values
            vals_str = stripped[4:].strip()
            for v in vals_str.split(','):
                v = v.strip()
                if v:
                    try:
                        labels[f'__data_{addr}'] = parse_num(v)
                        addr += 1
                    except:
                        pass
        elif stripped.startswith('defw'):
            vals_str = stripped[4:].strip()
            for v in vals_str.split(','):
                v = v.strip()
                if v:
                    try:
                        addr += 2
                    except:
                        pass

    # Second pass: resolve label references in code
    result = bytearray()
    for (a, bts, orig) in code_lines:
        # Replace label names in operands with addresses
        resolved = bytes(bts)
        result.extend(resolved)

    return bytes(result), labels


# ─────────────────────────────────────────────────────────
#  VRAM Visualization
# ─────────────────────────────────────────────────────────
def dump_vram_plane(cpu, base_addr, plane_name, width=32):
    """Dump a VRAM plane as text. Each byte → 8 pixels."""
    print(f"\n  {plane_name} (base 0x{base_addr:04X}):")
    print(f"  {'':4} " + "".join(f"{i:2d}" for i in range(8)))
    for row in range(16):  # Show 16 rows
        y = 255 - row  # Top rows first (y decreases downward in VRAM)
        line = f"  {y:3d}: "
        for col in range(width):
            addr = (base_addr + col * 0x100 + (255 - y)) & 0xFFFF
            byte_val = cpu.rb(addr)
            for bit in range(7, -1, -1):
                line += '#' if (byte_val >> bit) & 1 else '.'
        print(line)


def dump_thin_render(cpu, font_base, tmp_vars_base, x, y, char_idx):
    """
    Simulate graph_put_char_512t by directly setting up state and running.
    Returns the VRAM state after rendering.
    """
    pass  # We'll use the CPU to run the actual code


def dump_vram_512(cpu, x_start=0, y_start=255, w_bytes=8, h_rows=16):
    """
    Dump 512x256 VRAM as a pixel map.
    Combines all 4 planes into a 2-bit-per-pixel display.
    """
    print(f"\n  VRAM dump (x={x_start}..{x_start+w_bytes*16-1}, y={y_start}..{y_start-h_rows+1}):")
    print(f"  Legend: .=00, :=01, +=10, #=11")

    for row_idx in range(h_rows):
        y = y_start - row_idx
        line = f"  y={y:3d}: "
        for byte_col in range(w_bytes):
            x_base = (x_start // 16) + byte_col
            # Even plane (E000)
            e_addr = 0xE000 + x_base * 0x100 + (255 - y)
            e_val = cpu.rb(e_addr & 0xFFFF)
            # Odd plane (A000)
            o_addr = 0xA000 + x_base * 0x100 + (255 - y)
            o_val = cpu.rb(o_addr & 0xFFFF)

            for bit in range(7, -1, -1):
                e_pix = (e_val >> bit) & 1
                o_pix = (o_val >> bit) & 1
                color = (e_pix << 1) | o_pix
                # For display, just show plane 0 (even) and plane 1 (odd) separately
                if e_pix and o_pix:
                    line += '#'
                elif e_pix:
                    line += '+'
                elif o_pix:
                    line += ':'
                else:
                    line += '.'
        print(line)


# ─────────────────────────────────────────────────────────
#  Main: load and run pr512t.asm draw routine
# ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Vector-06C 8080 emulator for VRAM verification')
    parser.add_argument('--asm', default=None, help='ASM file to load')
    parser.add_argument('--entry', type=lambda x: int(x, 0), default=None, help='Entry point address')
    parser.add_argument('--dump-vram', action='store_true', help='Dump VRAM after execution')
    parser.add_argument('--test-font', action='store_true', help='Run built-in font render test')
    args = parser.parse_args()

    cpu = CPU8080()

    if args.test_font:
        run_font_test(cpu)
        return

    if args.asm:
        code, labels = assemble_file(args.asm)
        load_addr = args.entry or 0x4000
        for i, b in enumerate(code):
            cpu.wb(load_addr + i, b)
        print(f"Loaded {len(code)} bytes at 0x{load_addr:04X}")
        print(f"Labels: {len(labels)}")
        for name, addr in sorted(labels.items(), key=lambda x: x[1]):
            print(f"  {name}: 0x{addr:04X}")

        if args.dump_vram:
            cpu.pc = args.entry or load_addr
            cpu.run()
            dump_vram_512(cpu)


def run_font_test(cpu):
    """
    Built-in test: encode draw_char_512t and font data, run it, dump VRAM.
    """
    print("=== Vector-06C Thin Font VRAM Test ===\n")

    # Font data from font_thin in pr512t.asm
    # combined = (even_nibble << 4) | odd_nibble
    # Each nibble uses all 4 bits → 4 sub-columns per character.
    # Even nibble → even-plane bits 7-4 (descending bit mapping)
    # Odd nibble → odd-plane bits 7-4 (after shift) or bits 3-0
    font_a = [0x44, 0x6C, 0xAA, 0xAA, 0xEE, 0xAA, 0xAA, 0x00]
    font_b = [0xEE, 0x5A, 0x5A, 0x6E, 0x5A, 0x5A, 0xEE, 0x00]

    print("Font format: combined byte = (even_nibble << 4) | odd_nibble")
    print("  High nibble (bits 7-4): even-plane pixels (4 sub-cols, descending bits)")
    print("  Low nibble  (bits 3-0): odd-plane pixels  (4 sub-cols, descending bits)")
    print()

    # Run the emulator with the draw routines
    run_emu_test(cpu, font_a, font_b)


def run_emu_test(cpu, font_a, font_b):
    """Run the actual draw routines in the emulator.

    Tests all 4 draw routines:
      - draw_even_plane:       AND 0xF0, write        (even-x, even-plane)
      - draw_odd_plane_low:    rlc×4, AND 0xF0, OR    (even-x, odd-plane)
      - draw_even_plane_high:  rrca×4, AND 0x0F, write (odd-x, even-plane)
      - draw_odd_plane_direct: AND 0x0F, write        (odd-x, odd-plane)
    """

    CODE_BASE = 0x4000
    FONT_BASE = 0x4200
    HALT_ADDR = 0x3FFE

    # --- Encode 4 draw routines ---
    draw_bytes = bytearray()

    # draw_even_plane: push bc, push hl, mvi b,8,
    #   loop: ld a,(de), ani 0xF0, mov c,a, ld a,(hl), ani 0x0F, ora c, mov (hl),a,
    #         dcx hl, inx de, dcr b, mov a,b, ora a, jnz loop,
    #   pop hl, pop bc, ret
    dep = len(draw_bytes)
    draw_bytes += bytes([
        0xC5, 0xE5, 0x06, 0x08,             # push bc / push hl / mvi b,8
        0x1A, 0xE6, 0xF0, 0x4F,             # ld a,(de) / ani 0xF0 / mov c,a
        0x7E, 0xE6, 0x0F, 0xB1, 0x77,       # ld a,(hl) / ani 0x0F / ora c / mov (hl),a
        0x2B, 0x13, 0x05,                   # dcx hl / inx de / dcr b
        0x78, 0xB7,                         # mov a,b / ora a
        0xC2, 0x00, 0x00,                   # jnz loop
        0xE1, 0xC1, 0xC9,                   # pop hl / pop bc / ret
    ])
    draw_bytes[dep + 19] = (CODE_BASE + dep + 5) & 0xFF
    draw_bytes[dep + 20] = ((CODE_BASE + dep + 5) >> 8) & 0xFF

    # draw_odd_plane_low: push bc, push hl, mvi b,8,
    #   loop: ld a,(de), rlc×4, ani 0xF0, ora (hl), mov (hl),a,
    #         dcx hl, inx de, dcr b, mov a,b, ora a, jnz loop,
    #   pop hl, pop bc, ret
    dopl = len(draw_bytes)
    draw_bytes += bytes([
        0xC5, 0xE5, 0x06, 0x08,             # push bc / push hl / mvi b,8
        0x1A, 0x07, 0x07, 0x07, 0x07,       # ld a,(de) / rlc×4
        0xE6, 0xF0, 0xB6, 0x77,             # ani 0xF0 / ora (hl) / mov (hl),a
        0x2B, 0x13, 0x05,                   # dcx hl / inx de / dcr b
        0x78, 0xB7,                         # mov a,b / ora a
        0xC2, 0x00, 0x00,                   # jnz loop
        0xE1, 0xC1, 0xC9,                   # pop hl / pop bc / ret
    ])
    draw_bytes[dopl + 20] = (CODE_BASE + dopl + 5) & 0xFF
    draw_bytes[dopl + 21] = ((CODE_BASE + dopl + 5) >> 8) & 0xFF

    # draw_even_plane_high: push bc, push hl, mvi b,8,
    #   loop: ld a,(de), rrc×4, ani 0x0F, mov c,a, ld a,(hl), ani 0xF0, ora c, mov (hl),a,
    #         dcx hl, inx de, dcr b, mov a,b, ora a, jnz loop,
    #   pop hl, pop bc, ret
    deph = len(draw_bytes)
    draw_bytes += bytes([
        0xC5, 0xE5, 0x06, 0x08,             # push bc / push hl / mvi b,8
        0x1A, 0x0F, 0x0F, 0x0F, 0x0F,       # ld a,(de) / rrc×4
        0xE6, 0x0F, 0x4F,                   # ani 0x0F / mov c,a
        0x7E, 0xE6, 0xF0, 0xB1, 0x77,       # ld a,(hl) / ani 0xF0 / ora c / mov (hl),a
        0x2B, 0x13, 0x05,                   # dcx hl / inx de / dcr b
        0x78, 0xB7,                         # mov a,b / ora a
        0xC2, 0x00, 0x00,                   # jnz loop
        0xE1, 0xC1, 0xC9,                   # pop hl / pop bc / ret
    ])
    draw_bytes[deph + 23] = (CODE_BASE + deph + 5) & 0xFF
    draw_bytes[deph + 24] = ((CODE_BASE + deph + 5) >> 8) & 0xFF

    # draw_odd_plane_direct: push bc, push hl, mvi b,8,
    #   loop: ld a,(de), ani 0x0F, mov c,a, ld a,(hl), ani 0xF0, ora c, mov (hl),a,
    #         dcx hl, inx de, dcr b, mov a,b, ora a, jnz loop,
    #   pop hl, pop bc, ret
    dopd = len(draw_bytes)
    draw_bytes += bytes([
        0xC5, 0xE5, 0x06, 0x08,             # push bc / push hl / mvi b,8
        0x1A, 0xE6, 0x0F, 0x4F,             # ld a,(de) / ani 0x0F / mov c,a
        0x7E, 0xE6, 0xF0, 0xB1, 0x77,       # ld a,(hl) / ani 0xF0 / ora c / mov (hl),a
        0x2B, 0x13, 0x05,                   # dcx hl / inx de / dcr b
        0x78, 0xB7,                         # mov a,b / ora a
        0xC2, 0x00, 0x00,                   # jnz loop
        0xE1, 0xC1, 0xC9,                   # pop hl / pop bc / ret
    ])
    draw_bytes[dopd + 19] = (CODE_BASE + dopd + 5) & 0xFF
    draw_bytes[dopd + 20] = ((CODE_BASE + dopd + 5) >> 8) & 0xFF

    # --- Encode test functions ---
    # Each test: set DE=font_ptr, HL=VRAM_addr, call even_routine, switch H-=0x40, call odd_routine, ret
    test_code = bytearray()
    abs_base = CODE_BASE

    def make_test(font_offset, even_routine_off, odd_routine_off):
        """Build a 20-byte test function."""
        nonlocal test_code
        off = len(test_code)
        font_addr = FONT_BASE + font_offset
        test_code += bytes([
            0x11, font_addr & 0xFF, (font_addr >> 8) & 0xFF,  # lxi d, font_addr
            0x21, 0xF8, 0xE0,          # lxi h, 0xE0F8
            0xCD, 0x00, 0x00,          # call even_routine (patched)
            0x11, font_addr & 0xFF, (font_addr >> 8) & 0xFF,  # lxi d, font_addr (RELOAD)
            0x7C, 0xD6, 0x40, 0x67,    # mov a,h / sui 0x40 / mov h,a
            0xCD, 0x00, 0x00,          # call odd_routine (patched)
            0xC9,                       # ret
        ])
        test_code[off + 7] = (abs_base + even_routine_off) & 0xFF
        test_code[off + 8] = ((abs_base + even_routine_off) >> 8) & 0xFF
        test_code[off + 16] = (abs_base + odd_routine_off) & 0xFF
        test_code[off + 17] = ((abs_base + odd_routine_off) >> 8) & 0xFF
        return off

    t1 = make_test(0, dep, dopl)      # 'A' even-x: draw_even_plane + draw_odd_plane_low
    t2 = make_test(0, deph, dopd)      # 'A' odd-x:  draw_even_plane_high + draw_odd_plane_direct
    t3 = make_test(8, deph, dopd)      # 'B' odd-x:  draw_even_plane_high + draw_odd_plane_direct
    t4 = make_test(8, dep, dopl)       # 'B' even-x: draw_even_plane + draw_odd_plane_low

    # Test 5: 'B' at odd-x, byte-column 1 (HL=0xE1F8 instead of 0xE0F8)
    t5 = len(test_code)
    font_addr_b = FONT_BASE + 8
    test_code += bytes([
        0x11, font_addr_b & 0xFF, (font_addr_b >> 8) & 0xFF,  # lxi d, font_b
        0x21, 0xF8, 0xE1,          # lxi h, 0xE1F8 (byte-column 1)
        0xCD, 0x00, 0x00,          # call draw_even_plane_high (patched)
        0x11, font_addr_b & 0xFF, (font_addr_b >> 8) & 0xFF,  # lxi d, font_b (RELOAD)
        0x7C, 0xD6, 0x40, 0x67,    # mov a,h / sui 0x40 / mov h,a  → H=0xA1
        0xCD, 0x00, 0x00,          # call draw_odd_plane_direct (patched)
        0xC9,                       # ret
    ])
    test_code[t5 + 7] = (abs_base + deph) & 0xFF
    test_code[t5 + 8] = ((abs_base + deph) >> 8) & 0xFF
    test_code[t5 + 16] = (abs_base + dopd) & 0xFF
    test_code[t5 + 17] = ((abs_base + dopd) >> 8) & 0xFF

    cpu.wb(HALT_ADDR, 0x76)  # HLT at return address

    print(f"\nDraw routines: {len(draw_bytes)} bytes at 0x{CODE_BASE:04X}")
    print(f"  draw_even_plane:       +0x{dep:02X} (24 bytes)")
    print(f"  draw_odd_plane_low:    +0x{dopl:02X} (24 bytes)")
    print(f"  draw_even_plane_high:  +0x{deph:02X} (28 bytes)")
    print(f"  draw_odd_plane_direct: +0x{dopd:02X} (24 bytes)")

    VRAM_EVEN_BASE = 0xE0F8  # even-plane writes: 0xE0F8..0xE0F1
    VRAM_ODD_BASE = 0xA0F8   # odd-plane writes:  0xA0F8..0xA0F1

    def dump_test(cpu_t, font_data, test_label):
        print(f"\n  {test_label}:")
        print(f"  {'Row':>4} {'Comb':>5}  {'EvenVRAM':>8} {'OddVRAM':>8}  Pixels (16 cols: even|odd)")
        for row in range(8):
            combined = font_data[row]
            e_val = cpu_t.rb(VRAM_EVEN_BASE - row)
            o_val = cpu_t.rb(VRAM_ODD_BASE - row)

            # Build pixel row: 16 columns (8 even + 8 odd interleaved)
            pixels = ['.' for _ in range(16)]
            for bit in range(7, -1, -1):
                col = 2 * (7 - bit)      # even pixel column
                if (e_val >> bit) & 1:
                    pixels[col] = '#'
            for bit in range(7, -1, -1):
                col = 2 * (7 - bit) + 1  # odd pixel column
                if (o_val >> bit) & 1:
                    pixels[col] = '#'

            vis = ''.join(pixels)
            print(f"  {row:4d} 0x{combined:02X}  0x{e_val:02X}({e_val:08b}) 0x{o_val:02X}({o_val:08b})  {vis}")

    # Run each test with a fresh CPU
    for test_name, test_off, font_data in [
        ("'A' at x=0 (even-x)", t1, font_a),
        ("'A' at x=1 (odd-x)", t2, font_a),
        ("'B' at x=1 (odd-x)", t3, font_b),
        ("'B' at x=0 (even-x)", t4, font_b),
    ]:
        cpu_t = CPU8080()
        # Load font data
        for i, b in enumerate(font_a):
            cpu_t.wb(FONT_BASE + i, b)
        for i, b in enumerate(font_b):
            cpu_t.wb(FONT_BASE + 8 + i, b)
        # Load code
        for i, b in enumerate(draw_bytes):
            cpu_t.wb(CODE_BASE + i, b)
        for i, b in enumerate(test_code):
            cpu_t.wb(CODE_BASE + len(draw_bytes) + i, b)
        cpu_t.wb(HALT_ADDR, 0x76)
        cpu_t.pc = CODE_BASE + len(draw_bytes) + test_off
        cpu_t.sp = 0xFFF0
        cpu_t.push_word(HALT_ADDR)
        steps = cpu_t.run(max_steps=10000)
        status = f"{steps} steps" if steps < 10000 else "TIMEOUT!"
        print(f"\n  [{status}]")
        dump_test(cpu_t, font_data, test_name)

    # --- Summary: render 'AB' side by side ---
    # 'A' at even-x=0 (byte-col 0), 'B' at odd-x=1 (byte-col 1)
    print("\n=== Side-by-side 'AB' rendering ===")
    print("  'A' at x=0 (even, byte-col 0) + 'B' at x=1 (odd, byte-col 1)")
    cpu_ab = CPU8080()
    for i, b in enumerate(font_a):
        cpu_ab.wb(FONT_BASE + i, b)
    for i, b in enumerate(font_b):
        cpu_ab.wb(FONT_BASE + 8 + i, b)
    for i, b in enumerate(draw_bytes):
        cpu_ab.wb(CODE_BASE + i, b)
    for i, b in enumerate(test_code):
        cpu_ab.wb(CODE_BASE + len(draw_bytes) + i, b)
    cpu_ab.wb(HALT_ADDR, 0x76)
    # Run test 1: 'A' at even-x, byte-col 0
    cpu_ab.pc = CODE_BASE + len(draw_bytes) + t1
    cpu_ab.sp = 0xFFF0
    cpu_ab.push_word(HALT_ADDR)
    steps1 = cpu_ab.run(max_steps=10000)
    # Run test 5: 'B' at odd-x, byte-col 1
    cpu_ab.pc = CODE_BASE + len(draw_bytes) + t5
    cpu_ab.push_word(HALT_ADDR)
    steps2 = cpu_ab.run(max_steps=10000)

    # 'A' is at byte-col 0: even-plane 0xE0F8-row, odd-plane 0xA0F8-row
    # 'B' is at byte-col 1: even-plane 0xE1F8-row, odd-plane 0xA1F8-row
    print(f"  Steps: A={steps1}, B={steps2}")
    print(f"  {'Row':>4}  {'A even':>16}  {'A odd':>16}  {'B even':>16}  {'B odd':>16}  Pixels")
    for row in range(8):
        a_comb = font_a[row]
        b_comb = font_b[row]
        # 'A' byte-col 0
        ae = cpu_ab.rb(0xE0F8 - row)
        ao = cpu_ab.rb(0xA0F8 - row)
        # 'B' byte-col 1
        be = cpu_ab.rb(0xE1F8 - row)
        bo = cpu_ab.rb(0xA1F8 - row)

        # Build 32-pixel row: 16 from 'A' (byte-col 0) + 16 from 'B' (byte-col 1)
        pixels = ['.' for _ in range(32)]
        # 'A' pixels (byte-col 0)
        for bit in range(7, -1, -1):
            col = 2 * (7 - bit)
            if (ae >> bit) & 1:
                pixels[col] = '#'
        for bit in range(7, -1, -1):
            col = 2 * (7 - bit) + 1
            if (ao >> bit) & 1:
                pixels[col] = '#'
        # 'B' pixels (byte-col 1, offset by 16)
        for bit in range(7, -1, -1):
            col = 16 + 2 * (7 - bit)
            if (be >> bit) & 1:
                pixels[col] = '#'
        for bit in range(7, -1, -1):
            col = 16 + 2 * (7 - bit) + 1
            if (bo >> bit) & 1:
                pixels[col] = '#'

        vis = ''.join(pixels)
        print(f"  {row:4d}  0x{ae:02X}({ae:08b})  0x{ao:02X}({ao:08b})"
              f"  0x{be:02X}({be:08b})  0x{bo:02X}({bo:08b})  {vis}")


if __name__ == '__main__':
    main()
