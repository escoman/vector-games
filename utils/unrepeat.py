#!/usr/bin/env python3
"""unrepeat.py — разворачивает [ ... ]n обратно в плоские токены.

Использование:
    python3 utils/unrepeat.py path/to/track_rep.mus

Результат: track_back.mus рядом с исходником.

Противоположность find_repeats.py: каждый `[ pattern ]n` заменяется
на n копий pattern. Состояние O/L восстанавливается автоматически,
т.к. токены внутри скобок уже содержат все модификаторы.
"""

import sys
import os
import re


def parse_mus(text):
    """Разобрать .mus → (header_lines, [(name, tokens), ...])."""
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
            cur_name = m.group(1).replace(' ', '')
            cur_toks = []
            continue
        if cur_name is not None:
            cur_toks.extend(s.split())

    if cur_name is not None:
        sections.append((cur_name, cur_toks))

    return header, sections


def unrepeat(tokens):
    """Разворачивает все [ ... ]n в плоский список токенов."""
    result = []
    i = 0
    while i < len(tokens):
        if tokens[i] == '[':
            # Ищем парную ]n
            depth = 1
            j = i + 1
            while j < len(tokens) and depth > 0:
                if tokens[j] == '[':
                    depth += 1
                elif tokens[j].startswith(']') and tokens[j][1:].isdigit():
                    depth -= 1
                j += 1
            # tokens[i] = '[', tokens[j-1] = ']n'
            close_idx = j - 1
            n = int(tokens[close_idx][1:])  # число после ']'
            pattern = tokens[i + 1:close_idx]
            # Разворачиваем n раз
            result.extend(pattern * n)
            i = j
        else:
            result.append(tokens[i])
            i += 1
    return result


def format_tokens(tokens, width=76):
    """Расставить переводы строк, чтобы уложиться в ~width символов."""
    if not tokens:
        return ''
    lines = []
    cur = []
    cur_len = 0
    for tok in tokens:
        tlen = len(tok)
        add = tlen + (1 if cur else 0)
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


def main():
    if len(sys.argv) < 2:
        print('Использование: unrepeat.py <файл_rep.mus>')
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding='utf-8') as f:
        text = f.read()

    header, sections = parse_mus(text)

    # Имя результата: track_1_rep.mus → track_1_back.mus
    base, ext = os.path.splitext(path)
    # track_1_rep → track_1_back
    if base.endswith('_rep'):
        out_path = base[:-4] + '_back' + ext
    else:
        out_path = base + '_back' + ext

    total_before = 0
    total_after = 0

    out_lines = list(header)

    for name, tokens in sections:
        n_before = len(tokens)
        new_tokens = unrepeat(tokens)
        n_after = len(new_tokens)
        total_before += n_before
        total_after += n_after

        if name.startswith('score'):
            out_lines.append(f'score {name[5]}:')
        else:
            out_lines.append(f'{name}:')
        out_lines.append(format_tokens(new_tokens))

        expanded = n_after - n_before
        if expanded:
            print(f'  {name}: {n_before} → {n_after} токенов'
                  f' (+{expanded})')
        else:
            print(f'  {name}: {n_before} токенов (без повторов)')

    out_text = '\n'.join(out_lines) + '\n'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(out_text)

    print(f'\n→ {out_path}')
    print(f'  Всего: {total_before} → {total_after} токенов'
          f' (+{total_after - total_before})')


if __name__ == '__main__':
    main()
