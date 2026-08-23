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
[ ... ]n.

Существующие BEGIN/END и уже расставленные скобки сохраняются
(поиск только на глубине 0).

Оптимизации скорости:
  * префиксные полиномиальные хеши — сравнение подстрок за O(1)
    вместо O(length), суммарно O(n²) на проход;
  * токены кодируются плотными id (int), без повторного сравнения
    строк при проверке копий;
  * за один проход собираются ВСЕ валидные кандидаты, затем жадно
    применяются непересекающиеся замены с максимальной экономией.
    Это даёт обычно 2–5 проходов вместо сотен (когда на каждый
    повтор делался полный пересчёт → фактически O(n³)).
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
            # «score 0» → «score0»
            cur_name = m.group(1).replace(' ', '')
            cur_toks = []
            continue
        if cur_name is not None:
            cur_toks.extend(s.split())

    if cur_name is not None:
        sections.append((cur_name, cur_toks))

    return header, sections


# ── Поиск повторов ─────────────────────────────────────────────────

def _is_mod_token(t):
    """True, если токен — модификатор O* или L*."""
    return (t[0] in 'OoLl') and t[1:].isdigit() if t else False


def find_repeats(tokens):
    """Поиск повторов на уровне токенов с автосбросом состояния O/L.

    Алгоритм за каждый проход:
      1. Строит префиксные хеши и таблицы depth / oct_at / len_at / is_mod.
      2. Перебирает все (длина, позиция), находит consecutive-run'ы
         одинаковых блоков длины ≥ 2.
      3. Для каждого кандидата считает savings =
           (count-1)*length - 2 - len(resets) и список сбросов O/L.
      4. Жадно применяет непересекающиеся кандидаты (по убыванию
         savings, затем более длинные, затем более ранние).

    Граничные ограничения:
      • Паттерн НЕ начинается с ноты/P, если перед ней стоит L/O
        (модификатор остался бы снаружи, оторванный от ноты).
      • Паттерн НЕ заканчивается токеном L/O
        (модификатор оказался бы перед следующей нотой снаружи).
      • Поиск только на глубине 0 (не внутри уже существующих [ ]n).

    Сбросы L/O (если нужны) кладутся *внутрь* [ ... ]n в начало секции,
    чтобы выполняться на каждой итерации цикла.  Сброс L нужен только
    когда в паттерне нет ведущего L* (до первой ноты) и l_end ≠ l_enter;
    аналогично для O.  Если ведущий модификатор уже есть — он сам
    выставит состояние на каждой итерации, сброс не требуется.

    Оптимизация strip: если сбросов нет и паттерн начинается с O/L,
    совпадающего с enter *и* end, ведущий модификатор можно убрать
    из тела [ ] — снаружи он уже действует.

    Цикл проходов ограничен 32 итерациями; на практике сходится
    за 2–5 из‑за multi-apply.
    """
    tokens = list(tokens)
    re_o = re.compile(r'^[Oo](\d+)$')
    re_l = re.compile(r'^[Ll](\d+)$')
    re_bracket_end = re.compile(r'^\]\d+$')
    MAX_REPEAT = 255

    for _pass in range(32):
        n = len(tokens)
        if n < 4:
            break

        # --- плотные id + префиксные хеши (сравнение подстрок O(1)) ---
        id_map = {}
        ids = [0] * n
        for i, t in enumerate(tokens):
            k = id_map.get(t)
            if k is None:
                k = len(id_map) + 1
                id_map[t] = k
            ids[i] = k

        MOD = (1 << 61) - 1          # 2^61 - 1
        BASE = 257
        H = [0] * (n + 1)
        Pw = [1] * (n + 1)
        for i in range(n):
            H[i + 1] = (H[i] * BASE + ids[i]) % MOD
            Pw[i + 1] = (Pw[i] * BASE) % MOD

        def subh(i, length):
            """Хеш tokens[i : i+length]."""
            return (H[i + length] - H[i] * Pw[length]) % MOD

        def equal_ids(a, b, length):
            """Точное сравнение по id (защита от коллизий хеша)."""
            return ids[a:a + length] == ids[b:b + length]

        # --- глубина скобок, is_mod, состояние O/L перед каждым токеном ---
        depth = [0] * (n + 1)
        is_mod = [False] * n
        oct_at = [4] * (n + 1)       # default O4
        len_at = [4] * (n + 1)       # default L4
        for i, t in enumerate(tokens):
            depth[i + 1] = depth[i]
            oct_at[i + 1] = oct_at[i]
            len_at[i + 1] = len_at[i]
            if t == '[':
                depth[i + 1] += 1
            elif re_bracket_end.match(t):
                depth[i + 1] -= 1
            else:
                mo = re_o.match(t)
                if mo:
                    oct_at[i + 1] = int(mo.group(1))
                    is_mod[i] = True
                    continue
                ml = re_l.match(t)
                if ml:
                    len_at[i + 1] = int(ml.group(1))
                    is_mod[i] = True

        # --- сбор кандидатов: (savings, length, pos, count, resets) ---
        # Для каждой длины идём слева направо; после run'а перескакиваем
        # на его конец — не плодим пересекающиеся кандидаты одной длины.
        cands = []
        max_len = n // 2
        for length in range(2, max_len + 1):
            i = 0
            limit = n - 2 * length
            while i <= limit:
                if depth[i] != 0:
                    i += 1
                    continue
                # Границы: не разрывать L/O с нотой
                if i > 0 and is_mod[i - 1] and not is_mod[i]:
                    i += 1
                    continue
                if is_mod[i + length - 1]:
                    i += 1
                    continue

                h0 = subh(i, length)
                if h0 != subh(i + length, length):
                    i += 1
                    continue
                if not equal_ids(i, i + length, length):
                    i += 1
                    continue

                # Считаем число подряд идущих копий
                count = 2
                end_limit = n - length
                while i + count * length <= end_limit:
                    j = i + count * length
                    if depth[j] != 0:
                        break
                    if h0 != subh(j, length) or not equal_ids(i, j, length):
                        break
                    count += 1

                # Ведущие модификаторы в паттерне (до первой ноты / P / …)
                has_L = has_O = False
                for k in range(i, i + length):
                    t = tokens[k]
                    if is_mod[k]:
                        if t[0] in 'Ll':
                            has_L = True
                            continue
                        if t[0] in 'Oo':
                            has_O = True
                            continue
                    break

                # Сбросы внутрь [ ] — только если end ≠ enter и нет
                # ведущего модификатора, который сам выставит состояние
                resets = []
                if not has_L and len_at[i + length] != len_at[i]:
                    resets.append(f'L{len_at[i]}')
                if not has_O and oct_at[i + length] != oct_at[i]:
                    resets.append(f'O{oct_at[i]}')

                savings = (count - 1) * length - 2 - len(resets)
                if savings > 0:
                    cands.append((savings, length, i, count, resets))

                # Непересекающиеся run'ы одной длины
                i += count * length

        if not cands:
            break

        # --- жадно применить непересекающиеся (max savings first) ---
        cands.sort(key=lambda c: (-c[0], -c[1], c[2]))
        occupied = bytearray(n)
        planned = []  # (pos, end, new_toks)

        for savings, length, pos, count, resets in cands:
            end = pos + count * length
            if occupied[pos:end].find(1) != -1:
                continue
            occupied[pos:end] = b'\x01' * (end - pos)

            section = tokens[pos:pos + length]
            # Strip ведущего O/L, если он совпадает с enter и end
            if not resets and length > 2:
                t0 = tokens[pos]
                mo = re_o.match(t0)
                if (mo and int(mo.group(1)) == oct_at[pos]
                        and oct_at[pos + length] == oct_at[pos]):
                    section = tokens[pos + 1:pos + length]
                else:
                    ml = re_l.match(t0)
                    if (ml and int(ml.group(1)) == len_at[pos]
                            and len_at[pos + length] == len_at[pos]):
                        section = tokens[pos + 1:pos + length]

            nrep = count if count <= MAX_REPEAT else MAX_REPEAT
            planned.append(
                (pos, end, ['['] + resets + section + [f']{nrep}'])
            )

        if not planned:
            break

        # Сборка результата слева направо
        planned.sort(key=lambda p: p[0])
        out = []
        cursor = 0
        for pos, end, new_toks in planned:
            out.extend(tokens[cursor:pos])
            out.extend(new_toks)
            cursor = end
        out.extend(tokens[cursor:])
        tokens = out

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
