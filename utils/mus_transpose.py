#!/usr/bin/env python3
#
# mus_transpose.py — транспонирование партитур Вектора-06Ц по октавам.
#
# Меняет только команды октавы `O<n>` в указанных партитурах файла .mus;
# ноты, длительности, повторы, темп и комментарии остаются нетронутыми.
# Октава в .mus — состояние компилятора (см. mus2inc.py), поэтому сдвиг
# на октаву = сдвиг `O` на 1: абсолютный номер ноты меняется на 12 полутонов.
#
# Назначение: ручная замена коротких токенов вроде O5->O4 в плотном тексте
# партитуры ненадёжна (правки применяются частично), а скрипт делает это
# детерминированно и заодно показывает, что именно и где изменилось.
#
# Примеры:
#   python3 utils/mus_transpose.py title.mus -n -1            # все голоса на октаву ниже
#   python3 utils/mus_transpose.py title.mus -n -1 --score 1  # только второй голос
#   python3 utils/mus_transpose.py title.mus -n 1 --score 0,2 --dry-run
#   python3 utils/mus_transpose.py --self-test
#
# Октавы ограничены диапазоном 0..7: при выходе за границу значение
# прижимается к границе и печатается предупреждение (ноты ниже абсолютного
# номера 12 mus2inc.py и так превращает в паузы — это не ошибка, а тишина).

import argparse
import re
import sys

OCT_RE = re.compile(r'O([0-7])')
SCORE_RE = re.compile(r'^\s*score\s+(\d+)\s*:', re.I)


def shift_line(line, n):
    """Сдвинуть все O<n> в строке на n октав.

    Возвращает (новая_строка, число_изменённых_токенов, число_прижатых_к_границе).
    Часть строки после ';' (комментарий) не трогается."""
    body, sep, tail = line.partition(';')
    changed = [0]
    clamped = [0]

    def sub(m):
        old = int(m.group(1))
        new = min(7, max(0, old + n))
        if new != old:
            changed[0] += 1
        if new != old + n:
            clamped[0] += 1
        return 'O%d' % new

    # комментарий (';' и всё после него) остаётся как был
    return OCT_RE.sub(sub, body) + sep + tail, changed[0], clamped[0]


def histogram(lines):
    """Счётчики октав по партиям: {имя: {'O5': 3, ...}}."""
    cur, acc = None, {}
    for line in lines:
        m = SCORE_RE.match(line)
        if m:
            cur = 'score %s' % m.group(1)
            acc.setdefault(cur, [])
            continue
        if re.match(r'^\s*drums\s*:', line, re.I):
            cur = 'drums'
            acc.setdefault(cur, [])
            continue
        if cur is not None and line.strip():
            acc[cur] += OCT_RE.findall(line)
    return {k: {'O%s' % d: v.count(d) for d in sorted(set(v))}
            for k, v in acc.items()}


def transpose(text, n, scores=None):
    """Транспонировать текст .mus. scores — {'0','1','2'} или None (все).

    Возвращает (новый_текст, изменено_токенов, прижато_к_границе)."""
    lines = text.split('\n')
    cur, total, clamped = None, 0, 0
    for i, line in enumerate(lines):
        m = SCORE_RE.match(line)
        if m:
            cur = m.group(1)
            continue
        if re.match(r'^\s*drums\s*:', line, re.I):
            cur = 'D'
            continue
        if cur is None or not line.strip():
            continue
        if scores is not None and cur not in scores:
            continue
        new_line, changed, was_clamped = shift_line(line, n)
        lines[i] = new_line
        total += changed
        clamped += was_clamped
    return '\n'.join(lines), total, clamped


def run_self_test():
    src = 'Tempo: T120\nscore 0:\nO5 C L4 D O6 E\nscore 1:\nO5 C P O7 D\n'
    out, n, _ = transpose(src, -1, {'0'})
    assert 'O4 C L4 D O5 E' in out, out
    assert 'O5 C P O7 D' in out, 'чужая партия не тронута'
    assert n == 2, n
    out6, total6, clamped = transpose(src, -6, None)
    assert clamped == 2, clamped        # O5+(-6)<0 — прижаты; O6->O0 и O7->O1 целы
    assert total6 == 4, total6          # изменены все четыре O-команды
    assert 'O0 C L4 D O0 E' in out6, out6
    assert 'O0 C P O1 D' in out6, out6
    out, _, _ = transpose('score 0:\nO7 C ; O7 в комментарии\n', -1, None)
    assert out.splitlines()[1] == 'O6 C ; O7 в комментарии', repr(out)
    print('self-test OK')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Транспонирование .mus по октавам (только команды O<n>).')
    ap.add_argument('mus', nargs='?', help='файл партитуры .mus')
    ap.add_argument('-n', '--octaves', type=int, default=None,
                    help='сдвиг в октавах (можно отрицательный)')
    ap.add_argument('--score', default=None,
                    help='партии через запятую (0,1,2,D); по умолчанию все')
    ap.add_argument('-o', '--out', help='куда писать (по умолчанию — поверх)')
    ap.add_argument('--dry-run', action='store_true',
                    help='ничего не писать, только отчёт')
    ap.add_argument('--self-test', action='store_true',
                    help='проверка логики сдвига и выход')
    if argv is None:
        argv = sys.argv[1:]
    a = ap.parse_args(argv)

    if a.self_test:
        return run_self_test()
    if not a.mus or a.octaves is None:
        ap.error('нужны mus и -n/--octaves (или --self-test)')

    scores = None
    if a.score is not None:
        scores = set(x.strip().upper() for x in a.score.split(',') if x.strip())

    with open(a.mus, encoding='utf-8') as f:
        src = f.read()

    before = histogram(src.split('\n'))
    dst, changed, clamped = transpose(src, a.octaves, scores)
    after = histogram(dst.split('\n'))

    scope = ','.join(sorted(scores)) if scores else 'все партии'
    print('mus_transpose: %s: %+d октав(a), %s' % (a.mus, a.octaves, scope))
    print('  изменено O-команд: %d%s' % (
        changed, ', прижато к границе 0..7: %d' % clamped if clamped else ''))
    for name in sorted(set(before) | set(after)):
        print('  %-8s было %-34s стало %s' % (
            name,
            ' '.join('%s x%d' % kv for kv in sorted(before.get(name, {}).items())) or '—',
            ' '.join('%s x%d' % kv for kv in sorted(after.get(name, {}).items())) or '—'))
    if clamped:
        print('  ВНИМАНИЕ: часть нот прижата к краю диапазона октав 0..7 —'
              ' слишком низкие ноты mus2inc.py сделает паузами.')

    if a.dry_run:
        print('  --dry-run: файл не изменён')
        return 0
    out = a.out or a.mus
    with open(out, 'w', encoding='utf-8') as f:
        f.write(dst)
    print('  -> %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
