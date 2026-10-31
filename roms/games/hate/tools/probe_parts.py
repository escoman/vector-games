"""Полный разбор «частей» уровня: таблица $C8EA до очереди $CA43 + скрипты уровней.

Снимок: zx-disasm/games/hate/tmp/run10_56000.z80.
"""
import sys
from collections import Counter

sys.path.insert(0, '/home/alexey/Projects/zx-disasm/skoolkit')
from skoolkit.snapshot import get_snapshot  # noqa: E402

SNAP = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/alexey/Projects/zx-disasm/games/hate/tmp/run10_56000.z80'
mem = bytes(get_snapshot(SNAP))
b = mem.__getitem__


def w(a):
    return b(a) | (b(a + 1) << 8)


print('=== таблица частей $C8EA (все коды, пока high != 0) ===')
counts = []
for code in range(180):
    a = 0xC8EA + 2 * code
    if a + 1 >= 0xCA43:
        print('  уперлись в очередь $CA43 на коде %d' % code)
        break
    ptrs = []
    while b(a + 1) != 0 and len(ptrs) < 60:
        ptrs.append(w(a))
        a += 2
    counts.append(len(ptrs))
    print('  код %3d -> $%04X: %2d столбцов  %s'
          % (code, 0xC8EA + 2 * code, len(ptrs),
             ' '.join('$%04X' % p for p in ptrs[:8])))
print('  кодов с ненулевой записью: %d, максимум кода: %s'
      % (sum(1 for c in counts if c), max((i for i, c in enumerate(counts) if c), default=None)))
print('  всего записей-пар: %d' % sum(counts))

print('\n=== скрипты уровней ($CF04, слова 0,4,8,...) ===')
levels = []
a = 0xCF04
i = 0
while w(a) != 0xFFFF:
    script, other = w(a), w(a + 2)
    codes = []
    q = script + 1
    while b(q) != 0xFF and len(codes) < 2000:
        codes.append(b(q))
        q += 1
    cols = sum(counts[c] for c in codes if c < len(counts))
    levels.append((script, other, codes))
    print('  ур %2d: скрипт $%04X (кодов %d, байт %d, до $%04X) пар $%04X -> столбцов %d'
          % (i + 1, script, len(codes), q - script, q, other, cols))
    print('        коды: %s' % ' '.join('%d' % c for c in codes))
    i += 1
    a += 4

print('\n=== записи столбцов: диапазон и шаг ===')
seen = []
for code in range(len(counts)):
    a = 0xC8EA + 2 * code
    while b(a + 1) != 0:
        seen.append(w(a))
        a += 2
print('  записей %d, диапазон $%04X..$%04X' % (len(seen), min(seen), max(seen)))
d = sorted(set(seen))
steps = [d[i + 1] - d[i] for i in range(len(d) - 1)]
print('  шаги между разными записями:', Counter(steps).most_common(8))
print('  пример записи $%04X: %s' % (d[0], ' '.join('%02X' % b(d[0] + j) for j in range(18))))
print('  пример записи $%04X: %s' % (d[1], ' '.join('%02X' % b(d[1] + j) for j in range(18))))
