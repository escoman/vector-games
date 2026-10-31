"""Разобрать из снапшота H.A.T.E. байт-код карт уровней.

Снимок: zx-disasm/games/hate/tmp/run10_56000.z80 (mid-mission).

Что проверяем (модель из ENGINE.MD §3.3, §5):
  $CF04  — таблица 10 уровней: пара слов (указатель скрипта, ???), конец $FFFF;
  скрипт уровня — байты-коды «частей», $FF = конец;
  $C8EA  — таблица частей: по коду A идёт пара (low,high) указателей на записи
           столбцов, high=0 конец части;
  запись столбца — 15 байт кодов клеток банка $C400 (64 клетки × 8 байт);
  $CA43  — очередь, $C3F8 — указатель чтения.
"""
import os
import sys

SKOOLKIT = '/home/alexey/Projects/zx-disasm/skoolkit'
sys.path.insert(0, SKOOLKIT)
from skoolkit.snapshot import get_snapshot  # noqa: E402

SNAP = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/alexey/Projects/zx-disasm/games/hate/tmp/run10_56000.z80'
mem = bytes(get_snapshot(SNAP))
print('снапшот:', SNAP)


def b(a):
    return mem[a]


def w(a):
    return b(a) | (b(a + 1) << 8)


# --- таблица уровней ---
print('\n=== $CF04: таблица уровней ===')
i = 0
a = 0xCF04
while True:
    p, q = w(a), w(a + 2)
    if p == 0xFFFF:
        print('  терминатор $FFFF at $%04X' % a)
        break
    print('  уровень %2d: скрипт $%04X   второе $%04X' % (i + 1, p, q))
    i += 1
    a += 4
print('  текущий ($CF2E) = $%04X, ($CF30) = $%04X' % (w(0xCF2E), w(0xCF30)))
print('  страница ($C32E) = $%02X, половина ($C32F) = $%02X' % (b(0xC32E), b(0xC32F)))

# --- банк шаблонов ---
print('\n=== банк клеток $C400 (64 × 8) ===')
for c in range(64):
    row = [b(0xC400 + 8 * c + j) for j in range(8)]
    print('  %02X: %s' % (c, ' '.join('%02X' % v for v in row)))

# --- таблица частей ---
print('\n=== $C8EA: таблица частей (первые 40 кодов) ===')
for code in range(40):
    a = 0xC8EA + 2 * code
    ptrs = []
    while True:
        lo, hi = b(a), b(a + 1)
        if hi == 0:
            break
        ptrs.append(lo | (hi << 8))
        a += 2
        if len(ptrs) > 40:
            break
    print('  код %2d -> $%04X: %d столбцов [%s]'
          % (code, 0xC8EA + 2 * code, len(ptrs),
             ' '.join('$%04X' % p for p in ptrs[:6])))

# --- скрипт текущего уровня ---
print('\n=== скрипт текущего уровня ($CF2E) ===')
p = w(0xCF2E)
codes = []
while b(p) != 0xFF and len(codes) < 400:
    codes.append(b(p))
    p += 1
print('  %d байт: %s' % (len(codes), ' '.join('%02X' % c for c in codes)))
print('  за терминатором: %s' % ' '.join('%02X' % b(p + 1 + k) for k in range(16)))

# --- записи столбцов ---
print('\n=== примеры записей столбцов (15 кодов) ===')
for code in range(0, 8):
    a = 0xC8EA + 2 * code
    lo, hi = b(a), b(a + 1)
    if hi == 0:
        continue
    col = lo | (hi << 8)
    rec = [b(col + j) for j in range(15)]
    print('  часть %2d, 1-й столбец $%04X: %s' % (code, col, ' '.join('%02X' % v for v in rec)))

# --- трасса $6000 ---
print('\n=== $6000..$62FF (трасса, 24×32) первые 3 строки ===')
for r in range(3):
    print('  ', ' '.join('%02X' % b(0x6000 + r * 32 + c) for c in range(32)))
