#!/usr/bin/env python3
"""find_repeats.py — поиск повторов в .mus-файле и замена на [ ... ]n.

Использование:
    python3 utils/find_repeats.py path/to/track.mus

Результат: track_rep.mus рядом с исходником.

Алгоритм: для каждой секции (score0/score1/score2/drums) токены
склеиваются (переводы строк — только визуал), затем жадно ищутся
самые длинные соседние повторы (подряд идущие идентичные подпоследо-
вательности). Найденный повтор оборачивается в [ ... ]n. Процесс
повторяется, пока повторы находятся.

Существующие BEGIN/END сохраняются как есть (они не влияют на поиск).
"""

import sys
import os
import re


# ── Парсинг ────────────────────────────────────────────────────────

def parse_mus(text):
    """Разобрать .mus → (header_lines, [(name, tokens), ...]).

    header_lines — строки до первой секции (комментарии, Tempo).
    tokens — плоский список токенов секции (без переводов строк).
    """
    lines = text.split('\n')
    header = []
    sections = []
    cur_name = None
    cur_toks = []

    for line in lines:
        s = line.strip()
        if not s or s.startswith(';'):
            if cur_name is None:
                header.append(line)
            continue
        if s.startswith('Tempo'):
            if cur_name is None:
                header.append(line)
            continue
        m = re.match(r'^(score\s*\d+|drums)\s*:', s)
        if m:
            if cur_name is not None:
                sections.append((cur_name, cur_toks))
            cur_name = m.group(1).replace(' ', '')   # «score 0» → «score0»
            cur_toks = []
            continue
        if cur_name is not None:
            cur_toks.extend(s.split())

    if cur_name is not None:
        sections.append((cur_name, cur_toks))

    return header, sections


# ── Поиск повторов ─────────────────────────────────────────────────

def _is_flat(tokens):
    """True, если в токенах нет скобок [ / ]N."""
    return not any(t == '[' or (t.startswith(']') and t[1:].isdigit())
                   for t in tokens)


def find_repeats(tokens):
    """Жадная замена соседних повторов: [ A B C ]n и т. п.

    На каждом шаге ищется паттерн, дающий максимальную экономию токенов:
    savings = (count - 1) * length - 2 (скобки). Если несколько
    паттернов дают одинаковую экономию — берётся более ранний.
    Процесс повторяется, пока повторы находятся.

    Без вложенности: повтор wrapping только на глубине 0 (не внутри
    уже существующих скобок). Повтор может содержать только «плоские»
    токены (без скобок).
    """
    MAX_REPEAT = 255

    changed = True
    while changed:
        changed = False
        best = None                       # (savings, длина, позиция, кол-во)

        # Глубина скобок в каждой позиции (0 = вне любых скобок)
        depth = [0] * (len(tokens) + 1)
        for idx, t in enumerate(tokens):
            depth[idx + 1] = depth[idx]
            if t == '[':
                depth[idx + 1] += 1
            elif t.startswith(']') and t[1:].isdigit():
                depth[idx + 1] -= 1

        # Ищем паттерн с максимальной экономией
        max_len = len(tokens) // 2
        for length in range(2, max_len + 1):
            for i in range(len(tokens) - 2 * length + 1):
                # Только на глубине 0 — без вложенности
                if depth[i] != 0:
                    continue
                if tokens[i:i + length] == tokens[i + length:i + 2 * length]:
                    # пропускаем, если внутри есть скобки
                    if not _is_flat(tokens[i:i + length]):
                        continue
                    # Считаем сколько всего копий подряд
                    count = 2
                    while (i + (count + 1) * length <= len(tokens) and
                           tokens[i + count * length:
                                  i + (count + 1) * length] ==
                           tokens[i:i + length]):
                        count += 1
                    # Экономика: (count-1)*length токенов заменяем на 2 (скобки)
                    savings = (count - 1) * length - 2
                    if best is None or savings > best[0]:
                        best = (savings, length, i, count)

        if best:
            savings, length, pos, count = best
            section = tokens[pos:pos + length]
            n = min(count, MAX_REPEAT)
            # Заменяем n копий на [ section ]n
            tokens[pos:pos + n * length] = (
                ['['] + section + [f']{n}']
            )
            changed = True

    return tokens


# ── Форматирование ──────────────────────────────────────────────────

def format_tokens(tokens, width=76):
    """Расставить переводы строк, чтобы уложиться в ~width символов."""
    if not tokens:
        return ''
    lines = []
    cur = []
    cur_len = 0
    for tok in tokens:
        tlen = len(tok)
        add = tlen + (1 if cur else 0)    # пробел-разделитель
        if cur_len + add > width and cur:
            lines.append(' '.join(cur))
            cur = [tok]
            cur_len = tlen
        else:
            cur.append(tok)
            cur_len += add
    if cur:
        lines.append(' '.join(cur))
    return '\n'.join(lines)


# ── Главная ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print('Использование: find_repeats.py <файл.mus>')
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding='utf-8') as f:
        text = f.read()

    header, sections = parse_mus(text)

    # Имя результата: track_1.mus → track_1_rep.mus
    base, ext = os.path.splitext(path)
    out_path = f'{base}_rep{ext}'

    total_before = 0
    total_after = 0

    out_lines = list(header)                  # копируем заголовок

    for name, tokens in sections:
        n_before = len(tokens)
        new_tokens = find_repeats(tokens)
        n_after = len(new_tokens)
        saved = n_before - n_after
        total_before += n_before
        total_after += n_after

        # mus2inc.py требует «score 0:», а не «score0:»
        if name.startswith('score'):
            out_lines.append(f'score {name[5]}:')
        else:
            out_lines.append(f'{name}:')
        out_lines.append(format_tokens(new_tokens))

        if saved:
            print(f'  {name}: {n_before} → {n_after} токенов'
                  f' (−{saved})')
        else:
            print(f'  {name}: {n_before} токенов (без изменений)')

    out_text = '\n'.join(out_lines) + '\n'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(out_text)

    print(f'\n→ {out_path}')
    print(f'  Всего: {total_before} → {total_after} токенов'
          f' (−{total_before - total_after})')


if __name__ == '__main__':
    main()
