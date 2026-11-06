#!/usr/bin/env python3
"""Дизассемблирование потока байтов как чистого i8080 (проверка ТЗ §9.4).

Контроль, что loader_stage2.bin декодируется валидными командами
КР580ВМ80А от первого до последнего байта: без DD/FD/ED/CB-префиксов
Z80 на позициях опкодов и без смещения потока (иначе код, собранный как
Z80, на 8080 исполнялся бы другими командами). Входит в `make loader2`
ступенькой после bin2inc: z80asm расширения не отвергает, поэтому
проверяется именно бинарь.

Использование:
    disasm8080.py FILE [--org 0xe000] [--text] [--no-interrupts]
                       [--refs ДИАПАЗОН[,ДИАПАЗОН]] [--ref-allow АДРЕС]
Код возврата 0 — поток декодируется целиком и префиксов нет;
--no-interrupts (его и ставит `make loader2`) дополнительно считает
запрещённые EI/HLT/RST — ТЗ §3.1: stage-2 живёт без прерываний.
--refs включает проверку ТЗ §9.3: все 16-битные адресные операнды (LDA/STA/
SHLD/LHLD — память, JMP/CALL/Jcc/Ccc — код) должны попадать в разрешённые
диапазоны вида `0e000-0e22f`; `--ref-allow` добавляет отдельные разрешённые
адресы (финальный `JP 0000h`). `LXI` сюда не входит сознательно: это
непосредственное значение в регистровой паре, а не обращение, и оно легально
указывает и в стираемую область (стек, цикл очистки, аккумулятор TSBIT).
"""
import sys

R8 = ['B', 'C', 'D', 'E', 'H', 'L', 'M', 'A']
RP = ['B', 'D', 'H', 'SP']
STK = ['B', 'D', 'H', 'PSW']            # коды регпар для PUSH/POP
ALU = ['ADD', 'ADC', 'SUB', 'SBB', 'ANA', 'XRA', 'ORA', 'CMP']
ALI = ['ADI', 'ACI', 'SUI', 'SBI', 'ANI', 'XRI', 'ORI', 'CPI']
COND = ['NZ', 'Z', 'NC', 'C', 'PO', 'PE', 'P', 'M']

FIXED = {
    0x00: (1, 'NOP'), 0x02: (1, 'STAX B'), 0x0A: (1, 'LDAX B'),
    0x12: (1, 'STAX D'), 0x1A: (1, 'LDAX D'),
    0x07: (1, 'RLC'), 0x0F: (1, 'RRC'), 0x17: (1, 'RAL'), 0x1F: (1, 'RAR'),
    0x27: (1, 'DAA'), 0x2F: (1, 'CMA'), 0x37: (1, 'STC'), 0x3F: (1, 'CMC'),
    0x22: (3, 'SHLD'), 0x2A: (3, 'LHLD'), 0x32: (3, 'STA'), 0x3A: (3, 'LDA'),
    0xC3: (3, 'JMP'), 0xCD: (3, 'CALL'), 0xC9: (1, 'RET'), 0xE9: (1, 'PCHL'),
    0xE3: (1, 'XTHL'), 0xEB: (1, 'XCHG'), 0xF9: (1, 'SPHL'),
    0xF3: (1, 'DI'), 0xFB: (1, 'EI'), 0x76: (1, 'HLT'),
    0xDB: (2, 'IN'), 0xD3: (2, 'OUT'),
}


def decode(data, pc):
    """-> (длина, текст) либо (None, причина)."""
    op = data[pc]
    if op in (0xDD, 0xFD, 0xED, 0xCB):
        return None, 'префикс Z80 (%02Xh)' % op
    if op in FIXED:
        size, name = FIXED[op]
        if pc + size > len(data):
            return None, 'усечённая команда %s' % name
        if size == 2:
            return size, '%s %02Xh' % (name, data[pc + 1])
        if size == 3:
            return size, '%s %04Xh' % (name, data[pc + 1] | (data[pc + 2] << 8))
        return size, name

    hi, lo, nib = op >> 4, op & 7, op & 0x0F
    # MOV r,r' (01 xx x yyy), HLT уже исключён
    if (op & 0xC0) == 0x80:                             # ALU op r / M
        return 1, '%s %s' % (ALU[(op >> 3) & 7], R8[op & 7])
    if (op & 0xC0) == 0x40:                             # MOV r,r' (HLT исключён)
        return 1, 'MOV %s,%s' % (R8[(op >> 3) & 7], R8[op & 7])
    if (op & 0xC0) == 0x00:
        if lo == 0:                                   # 00h/10h/20h/30h — NOP
            return 1, 'NOP'
        if nib == 1:
            if not ok(data, pc, 3):
                return None, 'усечено LXI'
            return 3, 'LXI %s,%04Xh' % (RP[(op >> 4) & 3], rd16(data, pc))
        if nib == 3:
            return 1, 'INX %s' % RP[(op >> 4) & 3]
        if nib == 9:
            return 1, 'DAD %s' % RP[(op >> 4) & 3]
        if nib == 0x0B:
            return 1, 'DCX %s' % RP[(op >> 4) & 3]
        if lo == 4:
            return 1, 'INR %s' % R8[(op >> 3) & 7]
        if lo == 5:
            return 1, 'DCR %s' % R8[(op >> 3) & 7]
        if lo == 6:
            return (2, 'MVI %s,%02Xh' % (R8[(op >> 3) & 7], data[pc + 1])
                    if ok(data, pc, 2) else (None, 'усечено MVI'))
        if lo == 8:
            return 1, 'NOP'                    # 08h/18h/28h/38h — NOP-варианты
        if lo == 7:
            return 1, ['RLC', 'RRC', 'RAL', 'RAR'][(op >> 4) & 3]
    # класс условных/стек (11 xx x yyy)
    if (op & 0xC0) == 0xC0:
        if lo == 0:
            return 1, 'RET ' + COND[(op >> 3) & 7]
        if nib == 1:
            return 1, 'POP %s' % STK[(op >> 4) & 3]
        if lo == 2:
            return (3, 'J%s %04Xh' % (COND[(op >> 3) & 7], rd16(data, pc))
                    if ok(data, pc, 3) else (None, 'усечено J'))
        if lo == 4:
            return (3, 'C%s %04Xh' % (COND[(op >> 3) & 7], rd16(data, pc))
                    if ok(data, pc, 3) else (None, 'усечено C'))
        if nib == 5:
            return 1, 'PUSH %s' % STK[(op >> 4) & 3]
        if lo == 6:
            return (2, '%s %02Xh' % (ALI[(op >> 3) & 7], data[pc + 1])
                    if ok(data, pc, 2) else (None, 'усечено immediate'))
        if lo == 7:
            return 1, 'RST %d' % (((op >> 3) & 7) * 8)
    return None, 'нелегальный опкод %02Xh' % op


def ok(data, pc, size):
    return pc + size <= len(data)


def parse_addr(s):
    """Адрес из командной строки: 0e000h / 0xE000 / 57344 — как удобно.
    Вид «0e000» (hex с ведущей цифрой, как в исходниках z80asm) тоже
    принимается: int(s, 0) на нём падает, тогда читаем как 16-ричное."""
    s = s.strip()
    if s.lower().endswith('h'):
        return int(s[:-1], 16)
    try:
        return int(s, 0)
    except ValueError:
        return int(s, 16)


def rd16(data, pc):
    return data[pc + 1] | (data[pc + 2] << 8)


REF16 = {0x22: 'SHLD', 0x2A: 'LHLD', 0x32: 'STA', 0x3A: 'LDA',
         0xC3: 'JMP', 0xCD: 'CALL'}


def is_ref(op):
    """Опкод с 16-битным адресным операндом (память или цель перехода)."""
    if op in REF16:
        return True
    return (op & 0xC0) == 0xC0 and (op & 7) in (2, 4)   # Jcc / Ccc


def ranges(spec):
    """'0e000-0e22f,0000' -> [(lo, hi), ...]"""
    out = []
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        lo, _, hi = part.partition('-')
        out.append((parse_addr(lo), parse_addr(hi or lo)))
    return out


def in_ranges(v, rs):
    return any(lo <= v <= hi for lo, hi in rs)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    org = parse_addr(sys.argv[sys.argv.index('--org') + 1]) \
        if '--org' in sys.argv else 0
    text = '--text' in sys.argv
    no_int = '--no-interrupts' in sys.argv
    rs = ranges(sys.argv[sys.argv.index('--refs') + 1]) if '--refs' in sys.argv \
        else []
    allowed = ranges(sys.argv[sys.argv.index('--ref-allow') + 1]) \
        if '--ref-allow' in sys.argv else []
    data = open(path, 'rb').read()

    bad, pc, maxpc = [], 0, len(data)
    opcodes = []                        # байты на позициях опкодов (обход)
    ints = []                           # EI / HLT / RST — их быть не должно
    refs = []                           # адресные операнды вне диапазона (§9.3)
    while pc < maxpc:
        size, res = decode(data, pc)
        if size is None:
            bad.append((pc, res))
            if data[pc] in (0xDD, 0xFD, 0xED, 0xCB):
                opcodes.append(pc)
            pc += 1
            continue
        if res.split()[0] in ('EI', 'HLT') or res.startswith('RST'):
            ints.append((pc, res))
        if rs and is_ref(data[pc]):
            target = rd16(data, pc)
            if not in_ranges(target, rs) and not in_ranges(target, allowed):
                refs.append((pc, res, target))
        if text:
            print('%04X: %-12s %s' % (org + pc,
                                      ' '.join('%02X' % b for b in
                                               data[pc:pc + size]), res))
        pc += size

    # Осмысленный критерий — префиксы на позициях опкодов (их отлавливает
    # сам обход: decode возвращает None). В сырых байтах DD/FD/ED/CB быть
    # МОЖЕТ — это значения immediate/адресов, они не команды.
    raw = sum(1 for b in data if b in (0xDD, 0xFD, 0xED, 0xCB))
    print('size=%d  illegal=%d  z80_prefix_at_opcode=%d  ei_hlt_rst=%d  '
          'refs_out_of_range=%d  (raw prefix bytes=%d)'
          % (maxpc, len(bad), len(opcodes), len(ints), len(refs), raw))
    for pc, why in bad[:20]:
        print('  %04X: %s' % (org + pc, why))
    for pc, what in ints[:20]:
        print('  %04X: %s — прерывания запрещены ТЗ §3.1' % (org + pc, what))
    for pc, what, target in refs[:20]:
        print('  %04X: %s -> %04Xh — вне разрешённых областей (ТЗ §9.3)'
              % (org + pc, what, target))
    return 1 if bad or (no_int and ints) or refs else 0


if __name__ == '__main__':
    sys.exit(main())
