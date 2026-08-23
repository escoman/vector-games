#!/usr/bin/env python3
"""find_repeats.py — поиск повторов в .mus-файле и замена на [ ... ]n.

Использование:
    python3 utils/find_repeats.py path/to/track.mus

Результат: track_rep.mus рядом с исходником.

Алгоритм: для каждой секции (score0/score1/score2/drums) токены
склеиваются (переводы строк — только визуал). Поиск повторов идёт
на уровне токенов с защитой границ: модификатор L*/O* никогда не
отрывается от следующей ноты (паттерн не начинается сразу после
«чужого» L/O и не заканчивается голым L/O).

Если для корректного зацикливания нужно восстановить O/L (состояние
на выходе паттерна ≠ входу и паттерн сам не выставляет его ведущим
модификатором), сбросы добавляются *внутрь* [ ... ]n — они
выполняются на каждой итерации. Найденный повтор оборачивается в
[ ... ]n. Процесс повторяется, пока находятся новые повторы.

Существующие BEGIN/END и уже расставленные скобки сохраняются
(поиск только на глубине 0).
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

def _is_mod(t):
    """True, если токен — модификатор O* или L*."""
    return bool(re.match(r'^[OoLl]\d+$', t))


def find_repeats(tokens):
    """Поиск повторов на уровне токенов с автосбросом состояния O/L.

    Алгоритм перебирает ВСЕ (позиция, длина) и выбирает паттерн с
    максимальной экономией: savings = (count-1)*length - 2 - len(resets).

    Граничные ограничения:
      • Паттерн НЕ начинается с ноты/P, если перед ней стоит L/O
        (модификатор остался бы снаружи, оторванный от ноты).
      • Паттерн НЕ заканчивается токеном L/O
        (модификатор оказался бы перед следующей нотой снаружи).

    Сбросы L/O (если нужны) кладутся *внутрь* [ ... ]n в начало секции,
    чтобы выполняться на каждой итерации цикла.  Сброс L нужен только
    когда в паттерне нет ведущего L* (до первой ноты) и l_end ≠ l_enter;
    аналогично для O.  Если ведущий модификатор уже есть — он сам
    выставит состояние на каждой итерации, сброс не требуется.

    Без вложенности: только глубина 0.
    """
    MAX_REPEAT = 255

    changed = True
    while changed:
        changed = False
        best = None          # (savings, length, position, count, resets)

        # Глубина скобок (для запрета вложенности)
        depth = [0] * (len(tokens) + 1)
        for idx, t in enumerate(tokens):
            depth[idx + 1] = depth[idx]
            if t == '[':
                depth[idx + 1] += 1
            elif t.startswith(']') and t[1:].isdigit():
                depth[idx + 1] -= 1

        # Состояние O/L в каждой позиции (для определения сбросов)
        # oct_at[i] / len_at[i] — состояние *перед* токеном tokens[i]
        oct_at = [4] * (len(tokens) + 1)
        len_at = [4] * (len(tokens) + 1)      # L4 = старт по умолчанию
        for idx, t in enumerate(tokens):
            oct_at[idx + 1] = oct_at[idx]
            len_at[idx + 1] = len_at[idx]
            m = re.match(r'[Oo](\d+)$', t)
            if m:
                oct_at[idx + 1] = int(m.group(1))
                continue
            m = re.match(r'[Ll](\d+)$', t)
            if m:
                len_at[idx + 1] = int(m.group(1))

        # Перебор всех (длина, позиция)
        max_len = len(tokens) // 2
        for length in range(2, max_len + 1):
            for i in range(len(tokens) - 2 * length + 1):
                if depth[i] != 0:
                    continue
                # Границы: паттерн не должен разрывать L/O с нотой
                if i > 0 and _is_mod(tokens[i - 1]) and not _is_mod(tokens[i]):
                    continue                # перед паттерном L/O — оторвётся
                if _is_mod(tokens[i + length - 1]):
                    continue                # паттерн кончается L/O
                # Быстрая проверка: первая копия == вторая?
                if tokens[i:i + length] != tokens[i + length:i + 2 * length]:
                    continue
                # Считаем кол-во копий
                count = 2
                while (i + (count + 1) * length <= len(tokens) and
                       tokens[i + count * length:
                              i + (count + 1) * length] ==
                       tokens[i:i + length]):
                    count += 1

                # Есть ли ведущие модификаторы в паттерне (до первой ноты)?
                has_leading_L = False
                has_leading_O = False
                for t in tokens[i:i + length]:
                    if re.match(r'[Ll]\d+$', t):
                        has_leading_L = True
                        continue
                    if re.match(r'[Oo]\d+$', t):
                        has_leading_O = True
                        continue
                    break   # дошли до ноты / P / цифры / скобки

                enter_o = oct_at[i]
                enter_l = len_at[i]
                o_end = oct_at[i + length]
                l_end = len_at[i + length]

                # Сброс нужен только если модификатор НЕ выставляется
                # внутри паттерна в начале и состояние на выходе другое.
                # Сбросы пойдут *внутрь* [ ], поэтому сработают на каждой
                # итерации.
                resets = []
                if not has_leading_L and l_end != enter_l:
                    resets.append(f'L{enter_l}')
                if not has_leading_O and o_end != enter_o:
                    resets.append(f'O{enter_o}')

                savings = ((count - 1) * length - 2 - len(resets))
                if best is None or savings > best[0]:
                    best = (savings, length, i, count, resets)

        if best:
            savings, length, pos, count, resets = best
            n = min(count, MAX_REPEAT)
            section = tokens[pos:pos + length]

            # Оптимизация: если сбросов нет и паттерн начинается с
            # модификатора, совпадающего с состоянием перед паттерном,
            # *и* состояние этого параметра на выходе паттерна тоже
            # равно enter (иначе после первой итерации «вынесенный»
            # модификатор уже не действует, а end ≠ enter), то можно
            # убрать ведущий модификатор из секции.  Заменяем всегда
            # полный исходный диапазон n * orig_length.
            orig_pos = pos
            orig_length = length
            if not resets and length > 2:
                t0 = tokens[pos]
                m = re.match(r'[Oo](\d+)$', t0)
                if (m and int(m.group(1)) == oct_at[pos]
                        and oct_at[pos + length] == oct_at[pos]):
                    section = tokens[pos + 1:pos + length]
                else:
                    m = re.match(r'[Ll](\d+)$', t0)
                    if (m and int(m.group(1)) == len_at[pos]
                            and len_at[pos + length] == len_at[pos]):
                        section = tokens[pos + 1:pos + length]

            new_toks = ['['] + resets + section + [f']{n}']
            # Всегда заменяем исходный полный span копий
            tokens[orig_pos:orig_pos + n * orig_length] = new_toks
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
