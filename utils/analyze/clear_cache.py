#!/usr/bin/env python3
"""Очистка кэша доказательств анализа (пара к `evidence_cache.py`).

Кэш лежит рядом с ROM в каталоге `.analyze/cache/<stem>[-<sha[:8]>]` либо там,
куда его послал `V06C_ANALYZE_CACHE` (см. `EvidenceCache.for_rom`). Разросшийся
кэш — это тысячи JSON-конвертов; этот модуль убирает их, не трогая ни RDB, ни
результаты прогона (`*.json` в каталоге results), ни сам ROM.

    # что бы удалилось (по умолчанию ничего не удаляется — только показ):
    python3 utils/analyze/cli.py clear_cache --rom roms/redesign/putup/src/putup.rom

    # действительно удалить:
    python3 utils/analyze/cli.py clear_cache --rom … --run

    # прибрать все кэши в дереве проекта:
    python3 utils/analyze/cli.py clear_cache --scan . --run

    # удалить только конверты старше 30 дней (инкрементальная чистка):
    python3 utils/analyze/cli.py clear_cache --root .scratch/results/putup/.analyze --older-than 30 --run

Пустой ход (`--dry-run` по умолчанию) — намеренный: удаление кэша необратимо,
и пусть первым движением будет показ объёма, а не `rmtree`.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import sys
import time

from analyze.evidence_cache import DEFAULT_CACHE_ENV

# Как `for_rom`: корень кэша ROM-а = $V06C_ANALYZE_CACHE или `<каталог>/.analyze`.
CACHE_DIRNAME = ".analyze"
# Внутренности кэша: конверты доказательств, производные и журнал-указатель.
CACHE_CONTENT = ("evidence", "derived", "index.jsonl")
# Служебная «оболочка», которую можно срезать, когда она опустела: сам
# `.analyze` и промежуточный `cache`. Родитель этих имён (каталог ROM, results,
# env-корень) — граница: его не удаляем ни при каких условиях.
CACHE_SHELL_NAMES = (CACHE_DIRNAME, "cache")


def cache_root_for_rom(rom):
    """Каталог `.analyze` (или env-корень), где для этого ROM лежит кэш."""
    env = os.environ.get(DEFAULT_CACHE_ENV)
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(rom)), CACHE_DIRNAME)


def stem_of(rom):
    return os.path.splitext(os.path.basename(rom))[0]


def resolve_targets(args):
    """Список каталогов-целей на очистку (каждый — кэш одного ROM или корень)."""
    targets = []

    def add(path):
        path = os.path.abspath(path)
        if path not in targets:
            targets.append(path)

    for rom in args.rom or []:
        root = cache_root_for_rom(rom)
        cache_dir = os.path.join(root, "cache")
        # `--rom` чистит только этот ROM: подкаталоги cache/<stem>* , а не весь
        # общий env-корень (иначе снёсся бы кэш всех ROM сразу).
        if os.path.isdir(cache_dir):
            for tag in sorted(os.listdir(cache_dir)):
                if fnmatch.fnmatch(tag, "%s*" % stem_of(rom)):
                    add(os.path.join(cache_dir, tag))
        elif os.path.isdir(root) and not args.assume_root:
            # кэш мог лежать и без прослойки cache/ — покажем сам корень
            add(root)
        else:
            add(root)

    for root in args.root or []:
        add(root)

    if args.scan:
        base = os.path.abspath(args.scan)
        for dirpath, dirnames, _files in os.walk(base):
            for name in list(dirnames):
                if name == CACHE_DIRNAME:
                    add(os.path.join(dirpath, name))
                    dirnames.remove(name)      # не нырять внутрь кэша
    return targets


def dir_stats(path):
    """(файлов, байт) под деревом — для отчёта перед удалением."""
    files = size = 0
    for dirpath, _dirs, names in os.walk(path):
        for n in names:
            try:
                size += os.path.getsize(os.path.join(dirpath, n))
            except OSError:
                pass
            files += 1
    return files, size


def is_cache_like(path):
    """Похож ли каталог на кэш доказательств (защита от удаления не того)."""
    if os.path.basename(os.path.normpath(path)) == CACHE_DIRNAME:
        return True
    return any(os.path.exists(os.path.join(path, c)) for c in CACHE_CONTENT)


def prune_older_than(path, days):
    """Убрать только файлы старше `days` — вернуть число удалённых файлов."""
    cutoff = time.time() - days * 86400.0
    removed = 0
    for dirpath, _dirs, names in os.walk(path, topdown=False):
        for n in names:
            fp = os.path.join(dirpath, n)
            try:
                if os.path.getmtime(fp) < cutoff:
                    os.remove(fp)
                    removed += 1
            except OSError:
                pass
    # подчистить опустевшие каталоги evidence/derived
    for sub in ("evidence", "derived"):
        d = os.path.join(path, sub)
        if os.path.isdir(d) and not os.listdir(d):
            try:
                os.rmdir(d)
            except OSError:
                pass
    return removed


def human(n):
    for unit in ("Б", "КиБ", "МиБ", "ГиБ"):
        if n < 1024 or unit == "ГиБ":
            return "%d %s" % (n, unit) if unit == "Б" else "%.1f %s" % (n, unit)
        n /= 1024.0


def prune_cache_shell(start_path, keep=False):
    """Срезать опустевшую оболочку кэша: `…/cache` и сам `.analyze`.

    После удаления каталога `<tag>` (или прореживания до пустоты) остаётся
    пустая скорлупа. Поднимаемся по родителям, пока каталог пуст и называется
    служебно (`cache`/`.analyze`); на первой не-кэшевой директории
    останавливаемся — снести каталог с ROM или результатами права нет.
    Возвращает список удалённых каталогов.
    """
    if keep:
        return []
    removed = []
    cur = start_path
    # сам start_path мог остаться пустым (режим --older-than: файлы порезаны,
    # каталог на месте) — убираем и его, если пусто
    if os.path.isdir(cur) and not os.listdir(cur):
        try:
            os.rmdir(cur)
        except OSError:
            return removed
        removed.append(cur)
    parent = os.path.dirname(cur)
    while (os.path.basename(parent) in CACHE_SHELL_NAMES
           and os.path.isdir(parent) and not os.listdir(parent)):
        try:
            os.rmdir(parent)
        except OSError:
            break
        removed.append(parent)
        cur = parent
        parent = os.path.dirname(cur)
    return removed


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.clear_cache",
        description="Очистка кэша доказательств utils/analyze")
    parser.add_argument("--rom", action="append",
                        help="почистить кэш этого ROM (повторяемо)")
    parser.add_argument("--root", action="append",
                        help="почистить указанный каталог кэша (повторяемо)")
    parser.add_argument("--scan", default=None,
                        help="найти все .analyze в дереве и почистить их")
    parser.add_argument("--older-than", type=int, default=None, metavar="DAYS",
                        help="удалять не каталог целиком, а файлы старше N дней")
    parser.add_argument("--run", action="store_true",
                        help="выполнить удаление (по умолчанию только показ)")
    parser.add_argument("--assume-root", action="store_true",
                        help="при --rom чистить весь корень .analyze, а не "
                             "только подкаталоги этого ROM")
    parser.add_argument("--force", action="store_true",
                        help="удалять даже если каталог не похож на кэш")
    parser.add_argument("--keep-empty-parents", action="store_true",
                        help="не срезать опустевшую оболочку (…/cache и .analyze)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not (args.rom or args.root or args.scan):
        parser.error("укажите хотя бы --rom, --root или --scan")

    targets = resolve_targets(args)
    do = bool(args.run)
    rows = []
    freed = 0
    shells = 0
    for path in targets:
        if not os.path.isdir(path):
            rows.append({"path": path, "exists": False, "files": 0, "bytes": 0,
                         "action": "нет каталога"})
            continue
        if not args.force and not is_cache_like(path) and args.older_than is None:
            rows.append({"path": path, "exists": True, "files": dir_stats(path)[0],
                         "bytes": dir_stats(path)[1],
                         "action": "ПРОПУЩЕН (не похож на кэш; --force чтобы всё равно)"})
            continue
        files, size = dir_stats(path)
        if args.older_than is not None:
            action = "файлы старше %d дн." % args.older_than
            removed = prune_older_than(path, args.older_than) if do else 0
            cut = (prune_cache_shell(path, keep=args.keep_empty_parents)
                   if do else [])
            freed += 0        # объём прореженных файлов заранее не считаем
            if cut:
                action += " — оболочка срезана (%d)" % len(cut)
            shells += len(cut)
            rows.append({"path": path, "exists": True, "files": files,
                         "bytes": size, "shell_pruned": len(cut),
                         "action": (action + (" — удалено %d" % removed if do
                                              else " — показ"))})
        else:
            cut = []
            if do:
                shutil.rmtree(path)
                cut = prune_cache_shell(path, keep=args.keep_empty_parents)
                action = "УДАЛЁН" + (" — оболочка срезана (%d)" % len(cut)
                                     if cut else "")
            else:
                action = "будет удалён (--run)"
            shells += len(cut)
            freed += size
            rows.append({"path": path, "exists": True, "files": files,
                         "bytes": size, "shell_pruned": len(cut),
                         "action": action})

    if args.json:
        print(json.dumps({"mode": "run" if do else "dry-run",
                          "targets": rows, "freed_bytes": freed},
                         ensure_ascii=False, indent=2))
    else:
        print("режим: %s" % ("УДАЛЕНИЕ" if do else "только показ (--run удалит)"))
        if not rows:
            print("каталогов кэша не найдено")
        for r in rows:
            print("  %-1s %s — %d файл(ов), %s — %s"
                  % ("•", os.path.relpath(r["path"]) if r.get("exists")
                     else r["path"], r["files"], human(r["bytes"]), r["action"]))
        if do:
            print("освобождено: %s" % human(freed))
        elif freed:
            print("готово к удалению: %s (добавьте --run)" % human(freed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
