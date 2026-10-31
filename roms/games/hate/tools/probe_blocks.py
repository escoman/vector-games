"""Быстрый зонд: блоки уровней из таблицы $CF04 и таблица частей $C8EA."""
import sys

sys.path.insert(0, '/home/alexey/Projects/zx-disasm/skoolkit')
from skoolkit.snapshot import get_snapshot  # noqa: E402

SNAP = '/home/alexey/Projects/zx-disasm/games/hate/tmp/run10_56000.z80'
mem = bytes(get_snapshot(SNAP))
b = mem.__getitem__


def w(a):
    return b(a) | (b(a + 1) << 8)


print('=== таблица $CF04 (слова до $FFFF) ===')
words = []
a = 0xCF04
while w(a) != 0xFFFF:
    words.append(w(a))
    a += 2
print('  %d слов: %s' % (len(words), ' '.join('$%04X' % x for x in words)))

print('\n=== блоки: список кодов частей (до $FF) ===')
for i, p in enumerate(words):
    codes = []
    q = p
    while b(q) != 0xFF and len(codes) < 300:
        codes.append(b(q))
        q += 1
    print('  блок %2d $%04X: %3d кодов, длина %d байт, коды %s'
          % (i + 1, p, len(codes), q + 1 - p,
             ' '.join('%d' % c for c in codes[:24])))

print('\n=== таблица частей $C8EA: код -> число столбцов ===')
cnt = []
for code in range(64):
    a = 0xC8EA + 2 * code
    n = 0
    while b(a + 1) != 0 and n < 40:
        n += 1
        a += 2
    cnt.append(n)
print('  ', ' '.join('%d' % c for c in cnt))
print('   всего записей-указателей: %d пар' % sum(cnt))

print('\n=== где лежат записи столбцов ===')
lo = hi = None
for code in range(64):
    a = 0xC8EA + 2 * code
    while b(a + 1) != 0:
        p = b(a) | (b(a + 1) << 8)
        lo = p if lo is None or p < lo else lo
        hi = p if hi is None or p > hi else hi
        a += 2
print('   диапазон указателей: $%04X..$%04X' % (lo, hi))
print('   шаг между соседними записями (пример):',
      ['%04X' % (w(0xC8EA + 2 * c)) for c in range(4, 12)])
