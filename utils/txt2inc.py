#!/usr/bin/env python3
"""txt2inc.py — полная цепочка: TXT -> .mus -> повторы -> .inc.

Объединяет три скрипта в один вызов:
    txt2mus.py  → find_repeats.py  → mus2inc.py
    .txt        → /tmp/*_temp.mus  → /tmp/*_rep_temp.mus → .inc

Промежуточные файлы создаются в /tmp и удаляются после завершения.

Использование (аналог mus2inc.py, плюс --tempo от txt2mus):
    python3 utils/txt2inc.py track_0.txt \
        -o rom_data/track_0_music.inc \
        --name track_0_music \
        --use-shared nes_drums \
        --allow-len-mismatch \
        [--tempo N]
"""

import argparse
import os
import sys
import tempfile

# Пути до скриптов-соседей
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, UTILS_DIR)

import txt2mus
import find_repeats
import mus2inc


def main():
    ap = argparse.ArgumentParser(
        description='Полная цепочка: TXT -> .mus (с повторами) -> .inc')
    ap.add_argument('txt', help='входной .txt (экспорт NSF)')
    ap.add_argument('-o', '--output', required=True,
                    help='выходной .inc')
    ap.add_argument('--name',
                    help='префикс символов C (по умолчанию — имя файла)')
    ap.add_argument('--tempo', type=int,
                    help='темп T (32..255); по умолчанию — из framerate')
    ap.add_argument('--allow-len-mismatch', action='store_true',
                    help='предупреждение вместо ошибки при разной длине'
                         ' партитур')
    ap.add_argument('--use-shared', metavar='NAME',
                    help='семплы из внешней библиотеки NAME')
    ap.add_argument('--shared-lib', action='store_true',
                    help='генерировать библиотеку: .h + .c')
    ap.add_argument('--verify', action='store_true',
                    help='сравнить .mus с исходным TXT')
    args = ap.parse_args()

    # ── 1. TXT → .mus (в памяти) ──────────────────────────────────
    try:
        with open(args.txt, encoding='utf-8') as f:
            text = f.read()
        txt = txt2mus.parse_txt(text, args.txt)
        tempo = txt2mus.choose_tempo(txt['framerate'], args.tempo)
        mus_text, drum_names = txt2mus.convert(
            txt, args.txt, tempo, label=args.output)
    except (txt2mus.ConvError, OSError) as e:
        print(f'txt2inc: txt2mus: {e}', file=sys.stderr)
        sys.exit(1)

    n_ev = {k: sum(1 for e in v if 'type' not in e)
            for k, v in txt['channels'].items()}
    print(f'  txt2mus: T{tempo}, события'
          f' s0={n_ev["score0"]} s1={n_ev["score1"]}'
          f' s2={n_ev["score2"]} drums={n_ev["drums"]}')

    # ── 2. .mus → повторы (find_repeats) ──────────────────────────
    header, sections = find_repeats.parse_mus(mus_text)

    total_before = 0
    total_after = 0
    out_lines = list(header)

    for name, tokens in sections:
        n_before = len(tokens)
        new_tokens = find_repeats.find_repeats(tokens)
        n_after = len(new_tokens)
        total_before += n_before
        total_after += n_after

        if name.startswith('score'):
            out_lines.append(f'score {name[5]}:')
        else:
            out_lines.append(f'{name}:')
        out_lines.append(find_repeats.format_tokens(new_tokens))

        saved = n_before - n_after
        if saved:
            print(f'  repeats: {name} {n_before} → {n_after}'
                  f' (−{saved})')

    rep_text = '\n'.join(out_lines) + '\n'
    print(f'  repeats: всего {total_before} → {total_after}'
          f' (−{total_before - total_after})')

    # ── 3. .mus (с повторами) → .inc (через временные файлы) ──────
    base = os.path.splitext(os.path.basename(args.txt))[0]
    tmp_mus = os.path.join(tempfile.gettempdir(), f'{base}_temp.mus')
    tmp_rep = os.path.join(tempfile.gettempdir(), f'{base}_rep_temp.mus')

    try:
        # Записываем промежуточные .mus (для отладки / просмотра)
        with open(tmp_mus, 'w', encoding='utf-8') as f:
            f.write(mus_text)
        with open(tmp_rep, 'w', encoding='utf-8') as f:
            f.write(rep_text)

        # Вызываем mus2inc
        mus2inc_args = ['mus2inc', tmp_rep, '-o', args.output]
        if args.name:
            mus2inc_args += ['--name', args.name]
        if args.use_shared:
            mus2inc_args += ['--use-shared', args.use_shared]
        if args.shared_lib:
            mus2inc_args += ['--shared-lib']
        if args.allow_len_mismatch:
            mus2inc_args += ['--allow-len-mismatch']

        # Парсим аргументы mus2inc напрямую
        mus2inc_ap = argparse.ArgumentParser()
        mus2inc_ap.add_argument('mus', nargs='?')
        mus2inc_ap.add_argument('-o', '--output')
        mus2inc_ap.add_argument('--name')
        mus2inc_ap.add_argument('--allow-len-mismatch',
                                action='store_true')
        mus2inc_ap.add_argument('--shared-lib', action='store_true')
        mus2inc_ap.add_argument('--use-shared', metavar='NAME')
        mus2inc_ap.add_argument('--self-test', action='store_true')
        m_args = mus2inc_ap.parse_args(mus2inc_args[1:])

        # Вызов mus2inc.main с подменой argv
        old_argv = sys.argv
        sys.argv = mus2inc_args
        try:
            mus2inc.main()
        finally:
            sys.argv = old_argv

        print(f'  -> {args.output}')

    finally:
        # Убираем временные файлы
        for p in (tmp_mus, tmp_rep):
            if os.path.exists(p):
                os.remove(p)

    # ── 4. verify (опционально) ───────────────────────────────────
    if args.verify:
        rc = txt2mus.verify(args.txt, txt, rep_text)
        if rc:
            sys.exit(rc)


if __name__ == '__main__':
    main()
