#!/usr/bin/env python3
"""beam_timing.py — машинная проверка гонки за лучом в fire3.asm.

Собирает ISR ассемблером v06_emu, исполняет _beam_isr по одной инструкции,
начисляя video-такты (v_cycles) по таблице, извлечённой из ядра vector-psp
(utils/analyze/extract_vcycles.py), и печатает:
  * номер строки развёртки, на который попадает каждый OUT (0Ch);
  * длительность каждого витка тела строки (должна быть ровно LINE_VC=768);
  * сколько строк прогнано и куда лёг первый OUT (для калибровки COARSE).

REPT/ENDR в fire3.asm разворачиваются на лету (v06_emu их не знает).

Запуск:  python3 beam_timing.py [COARSE]
COARSE переопределяет грубую задержку (LXI B в прологе), чтобы подобрать
строку, на которую ложится первый OUT (цель — строка 0 картинки, см. README).
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EMU = os.path.join(ROOT, "utils", "emulator")
EXTRACT = os.path.join(ROOT, "utils", "analyze", "extract_vcycles.py")
CORE = "/home/alexey/Projects/vector-psp/src/i8080.cpp"

sys.path.insert(0, EMU)
import v06_emu  # noqa: E402


def load_vcycles():
    if os.path.exists(CORE):
        out = subprocess.run([sys.executable, EXTRACT], capture_output=True, text=True)
        table = {int(k, 16): v for k, v in json.loads(out.stdout).items()}
    else:
        # запасная таблица, если ядро не под рукой
        table = {0x00: 4, 0x01: 12, 0x0b: 8, 0x0c: 8, 0x21: 12, 0x23: 8, 0x32: 16,
                 0x3a: 16, 0x3e: 8, 0x7e: 8, 0xb1: 4, 0xc1: 12, 0xc2: 12, 0xc3: 12,
                 0xc5: 16, 0xd1: 12, 0xd3: 12, 0xd5: 16, 0xe1: 12, 0xe5: 16, 0xf1: 12,
                 0xf2: 12, 0xf5: 16, 0xfb: 4, 0x0f: 4, 0x37: 4, 0x3f: 4, 0x2f: 4,
                 0xf3: 4, 0xaf: 4}
    return table


def preprocess(path, coarse=None):
    """Read fire3.asm, expand REPT/ENDR, optionally override COARSE_DEF."""
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()

    equs = {}
    for ln in lines:
        m = re.match(r"^\s*([A-Za-z_.$?]\w*)\s+EQU\s+(.+?)\s*(?:;.*)?$", ln)
        if m:
            equs[m.group(1).upper()] = m.group(2).strip()

    def ev(expr):
        e = expr.strip()
        e = re.sub(r"0[xX]([0-9A-Fa-f]+)", r"\1", e)
        def sub(mo):
            k = mo.group(1).upper()
            if k in equs:
                return str(int(ev(equs[k])))
            return mo.group(0)
        e = re.sub(r"[A-Za-z_.$?][\w.$?]*", lambda mo: str(int(ev(mo.group(0)))) if mo.group(0).upper() in equs else mo.group(0), e)
        return int(eval(e)) if re.fullmatch(r"[\d+\-*/() ]+", e) else (int(e, 16) if re.fullmatch(r"[0-9A-Fa-f]+H?", e, re.I) else int(e))

    if coarse is not None:
        equs["COARSE_DEF"] = str(int(coarse))

    # EXTERN-символы (например _frame_count) для харнесса размещаем в
    #дали от кода/стека: они только читаются/пишутся, важны для тайминга,
    # а не для значений.
    externs = []
    for ln in lines:
        m = re.match(r"^\s*EXTERN\s+(\w+)", ln, re.I)
        if m:
            externs.append(m.group(1))
    seed = []
    addr = 0x4000
    for name in externs:
        seed.append(f"{name} EQU {addr:#06x}")
        addr += 4

    out = []
    i = 0
    rept_depth = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^\s*REPT\s+(.+?)\s*(?:;.*)?$", ln, re.I)
        if m:
            cnt = equs.get(m.group(1).strip().upper())
            cnt = int(cnt) if cnt is not None and str(cnt).isdigit() else _safe_eval(m.group(1), equs)
            block = []
            i += 1
            while i < len(lines) and not re.match(r"^\s*ENDR\s*(?:;.*)?$", lines[i], re.I):
                block.append(lines[i]); i += 1
            out.extend(block * cnt)
            i += 1
            continue
        # подменить immediate грубой задержки
        if coarse is not None and re.match(r"^\s*lxi\s+b\s*,\s*COARSE_DEF", ln, re.I):
            ln = re.sub(r"COARSE_DEF", str(int(coarse)), ln)
        # v06_emu понимает out/in без скобок порта: out (0Ch) -> out 0Ch
        ln = re.sub(r"\b(out|in)\s*\(\s*([0-9A-Fa-f]+[Hh]?)\s*\)", r"\1 \2", ln, flags=re.I)
        out.append(ln)
        i += 1
    return "\n".join(seed + out) + "\n"


def _safe_eval(expr, equs):
    e = expr.strip()
    for k, v in equs.items():
        e = re.sub(r"\b%s\b" % re.escape(k), str(v), e)
    e = re.sub(r"0[xX]", "0x", e)
    return int(eval(e))


def _patch_asm(v06_emu):
    """Добавить INX/DCX (пары) в ограниченный ассемблер v06_emu."""
    orig = v06_emu.assemble_instruction
    RPS = v06_emu.RPS
    def new(line, symbols, unresolved_zero=False):
        toks = line.strip().split(None, 1)
        m = toks[0].lower() if toks else ""
        if m in ("inx", "dcx") and len(toks) > 1:
            rp = RPS[toks[1].strip().lower()]
            base = 0x03 if m == "inx" else 0x0B
            return [base | (rp << 4)]
        b = orig(line, symbols, unresolved_zero)
        if b:
            b = [x & 0xFF for x in b]   # как z80asm: mvi c,256 -> 0
        return b
    v06_emu.assemble_instruction = new


def main():
    _patch_asm(v06_emu)
    coarse = sys.argv[1] if len(sys.argv) > 1 else None
    asm_path = os.path.join(HERE, "fire3.asm")
    text = preprocess(asm_path, coarse)

    asm = v06_emu.Assembler8080()
    asm.symbols = {}
    assembled = asm.assemble_text(text.splitlines())
    labels = asm.symbols
    data = assembled.data

    VC = load_vcycles()
    LINE_VC = 768
    IRQ_VC = 174       # RST7 берётся на v_cycle 174 строки 0
    PIC_TOP = 40       # первая строка картинки (abs строка) = индекс строки 0 в таблице

    cpu = v06_emu.CPU8080()
    # отобразить образ по адресам ассемблера (data проиндексирован от 0)
    for a in range(len(data)):
        if data[a]:
            cpu.wb(a, data[a])

    entry = labels["_beam_isr"]
    ret_sentinel = 0x0000  # сюда «вернёмся» по RET; поставим JP-ловушку
    # стек: растёт вниз от 0x0100, под адрес возврата
    cpu.set_hl(0)
    sp = 0x00F0
    cpu.sp = sp
    cpu.wb((sp - 1) & 0xFFFF, (ret_sentinel >> 8) & 0xFF)
    cpu.wb((sp - 2) & 0xFFFF, ret_sentinel & 0xFF)
    cpu.sp = sp - 2
    cpu.pc = entry

    total = 0
    body_pc = labels.get("_beam_body")
    body_starts = []      # абсолютные v_cycle начала каждой итерации тела
    first_out_abs = None
    out_count = 0
    max_iter = 2_000_000

    for _ in range(max_iter):
        if cpu.pc == ret_sentinel:
            break
        opc = cpu.rb(cpu.pc)
        cost = VC.get(opc)
        if cost is None:
            raise SystemExit(f"нет v_cycles для опкода {opc:#04x} at PC={cpu.pc:#06x}")
        if opc == 0xD3 and cpu.rb((cpu.pc + 1) & 0xFFFF) == 0x0C:
            out_count += 1
            if first_out_abs is None:
                first_out_abs = total
            absline = (IRQ_VC + total) // LINE_VC
            pic_index = absline - PIC_TOP
            body_starts.append((out_count, pic_index, (IRQ_VC + total) % LINE_VC))
        cpu.step()
        total += cost

    print(f"собрано инструкций тела (REPT развёрнут): файл OK")
    print(f"всего v_cycles за гонку: {total}   (= {total/LINE_VC:.3f} строк)")
    print(f"OUT(0Ch) всего: {out_count}")
    if first_out_abs is not None:
        first_line = (IRQ_VC + first_out_abs) // LINE_VC - PIC_TOP
        print(f"первый OUT: v_cycle {first_out_abs}, индекс строки картинки = {first_line}")

    # дельты между последовательными OUT (должны быть ровно LINE_VC=768)
    if out_count >= 2:
        # восстановим абсолютные v_cycle начал: проще — разность по записи не годится,
        # пересчитаем дельты по сохранённым pic_index/offset
        deltas = []
        prev = None
        for _, pic, off in body_starts:
            cur = pic * LINE_VC + off
            if prev is not None:
                deltas.append(cur - prev)
            prev = cur
        uniq = sorted(set(deltas))
        print(f"дельта между строками (v_cycles): уникальные = {uniq}")
        bad = [d for d in deltas if d != LINE_VC]
        if bad:
            print(f"!! {len(bad)} дельт != {LINE_VC}: первые = {bad[:8]}")
        else:
            print(f"OK: все {len(deltas)} дельт = {LINE_VC}")

    # строки, по которым разложены OUT (первые/последние несколько)
    picseq = [pic for _, pic, _ in body_starts]
    print(f"строки картинки по OUT: head={picseq[:5]} tail={picseq[-5:]}")
    exp = list(range(0, min(out_count, 256)))
    ok = all(i == p for i, (_, p, _) in enumerate(body_starts))
    print(f"последовательность строк 0..255 непрерывна: {'ДА' if ok else 'НЕТ'}")


if __name__ == "__main__":
    main()
