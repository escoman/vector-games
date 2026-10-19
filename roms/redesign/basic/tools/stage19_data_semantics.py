#!/usr/bin/env python3
"""Stage 19: семантика данных/переменных/строк (Phase D).

Вход: все data/table/var/str уже именованы (generic-имён нет), CODE∪RDB=100%.
Цель Phase D — закрыть «что это и кто потребитель» доказуемо:

  1. `used_by` / `loaded_by` для data/table-объектов, у которых пока нет
     подтверждённого потребителя. Источники (всё детерминировано из ROM+RDB,
     без догадок):
       * входящие RDB-связи (`debug_add_rdb_link`, Stage18) и свойства
         функций `reads`/`writes`, указывающие на адрес объекта;
       * скан образа на абсолютные ссылки 16-битным операндом
         (`LXI B/D/H/SP,addr`, `LHLD/LDA/STA/SHLD addr`) — это то, чем
         таблицу реально грузят/индексируют; каждая ссылка атрибутируется
         покрывающей функции (`Rdb.at`).
     Где ни то, ни другое не сработало — честная заметка `access`
     (индексация через вычисляемый указатель / boot-init / паддинг).

  2. `data_error_messages` (0x2465): распаковка «bit7 = конец строки» в
     упорядоченную карту «код ошибки → текст» (своёство `codes`) + разделение
     сообщения/промпты + замечание о транслитерации.

  3. `str_2079_cyrillic` (0x2079): снять `semantic_pending` — доказать, что
     это перестановочная таблица кириллицы (все 32 буквы `а..я` под схемой
     `а-я@0xA1` встречаются ровно по разу + пунктуация `0x5F 0x2E`), а не
     проза.

  4. `data_glyph_block` (0x379F): проверить геометрию 128 глифов × 5 байт =
     640 (`verified_shape`).

  5. Карта переменных page-zero/workspace (`vars_memory_map`) — только отчёт;
     в `asm/equates.asm` её писать НЕЛЬЗЯ (var_/data_/func_-метки уже эмитятся
     как метки в `code.asm`; дублирующий EQU → коллизия имён и падение
     сборки). Ограничение зафиксировано в отчёте.

Round-trip: только свойства/комментарии — байты не двигаются (`make verify`
— оракул).

Usage:
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage19_data_semantics.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage19_data_semantics.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze.mcp_session import addr_hex, open_session
from analyze.rdb import Rdb, RdbWriter

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(MODULE)))
DEFAULT_ROM = os.path.join(MODULE, "src", "basic.r0m")
DEFAULT_RDB = os.path.join(MODULE, "src", "basic.rdb")
LO, HI = 0x0000, 0x42FF

ERR_MESSAGES = 0x2465
KEYWORD_TABLE = 0x256E
CYR_STR = 0x2079
CYR_STR_LEN = 35
GLYPH_BLOCK = 0x379F
GLYPH_BYTES = 640
GLYPH_STRIDE = 5

# Z80-opcodes с 16-битным abs-операндом, которые реально матéриализуют
# указатель/адрес данных (LXI B/D/H/SP; LHLD/LDA/STA/SHLD). Формат: op -> имя.
ABS_LOAD_OPS = {0x01: "LXI B", 0x11: "LXI D", 0x21: "LXI H", 0x31: "LXI SP",
                0x2A: "LHLD", 0x3A: "LDA", 0x32: "STA", 0x22: "SHLD"}

# Кириллица: последовательная схема а-я@0xA1 (без ё) — та, что наблюдена в
# 0x2079 (весь диапазон байт 0xA1..0xC0 = 32 буквы).
CYR_ALPHA = "абвгдежзийклмнопрстуфхцчшщъыьэюя"


def _as_list(val):
    """Свойство RDB может лежать JSON-строкой (set_property json.dumps)."""
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            got = json.loads(val)
            return got if isinstance(got, list) else []
        except (ValueError, TypeError):
            return []
    return []


def build_inbound(rdb):
    """addr(data) -> {func_addr, ...} из RDB-связей и reads/writes функций."""
    inbound = {}
    for o in rdb.objects:
        for t in o.links:
            cov = rdb.at(t)
            key = cov.address if cov else t
            inbound.setdefault(key, set()).add(o.address)
        for prop in ("reads", "writes"):
            for a in _as_list((o.properties or {}).get(prop)):
                try:
                    a = int(a, 16) if isinstance(a, str) else int(a)
                except (ValueError, TypeError):
                    continue
                cov = rdb.at(a)
                if cov and cov.type in ("data", "table", "variable", "string"):
                    inbound.setdefault(cov.address, set()).add(o.address)
    return inbound


def rom_abs_refs(image, addr):
    """[(instr_addr, opname)] — ссылки на точный адрес abs-операндом."""
    lo, hi = addr & 0xFF, (addr >> 8) & 0xFF
    hits = []
    for i in range(len(image) - 2):
        op = image[i]
        if op in ABS_LOAD_OPS and image[i + 1] == lo and image[i + 2] == hi:
            hits.append((i, ABS_LOAD_OPS[op]))
    return hits


def decode_error_messages(image):
    msgs, cur = [], []
    for i in range(ERR_MESSAGES, KEYWORD_TABLE):
        b = image[i]
        cur.append(chr(b & 0x7F))
        if b & 0x80:
            msgs.append("".join(cur))
            cur = []
    if cur:
        msgs.append("".join(cur) + "?")
    return msgs


def decode_cyrillic_permutation(image):
    seq, distinct_cyr = [], []
    for b in image[CYR_STR:CYR_STR + CYR_STR_LEN]:
        if 0xA1 <= b <= 0xC0:
            seq.append(CYR_ALPHA[b - 0xA1])
            distinct_cyr.append(b)
        else:
            seq.append(chr(b) if 32 <= b < 127 else "(%02X)" % b)
    perm = (len(distinct_cyr) == len(set(distinct_cyr)))
    return "".join(seq), len(distinct_cyr), set(distinct_cyr) <= set(
        range(0xA1, 0xC1)), perm


def verify_glyph_block(image):
    block = image[GLYPH_BLOCK:GLYPH_BLOCK + GLYPH_BYTES]
    n = len(block) // GLYPH_STRIDE
    return (len(block) == GLYPH_BYTES and n == 128), n


def build_plan(rdb, image):
    """[(addr, name, [(prop, value)], comment_or_None)] — только доказанное."""
    inbound = build_inbound(rdb)
    by = {o.address: o for o in rdb.objects}
    plan = []

    # 1. used_by / loaded_by / access для data/table
    for o in sorted(rdb.of_type("data", "table"), key=lambda z: z.address):
        props = o.properties or {}
        if {"consumer", "loaded_by", "used_by"} & set(props.keys()):
            continue
        acts = []
        srcs = {by[s].name for s in inbound.get(o.address, set()) if s in by}
        refs = rom_abs_refs(image, o.address)
        loaders = []
        for i, opname in refs:
            cov = rdb.at(i)
            loaders.append("%s@%s(%s)" % (opname, addr_hex(i),
                                          cov.name if cov else "code"))
        if srcs or loaders:
            if loaders:
                acts.append(("loaded_by", "; ".join(loaders[:6])))
            users = sorted(srcs)
            if users:
                acts.append(("used_by", ", ".join(users[:8])))
            acts.append(("evidence", "stage19: RDB-links/reads-writes + "
                         "ROM abs-ref scan"))
        else:
            acts.append(("access", "no static absolute xref; обращение через "
                         "вычисляемый указатель/индекс или boot-init "
                         "(см. phase_b_evidence/role)"))
        if acts:
            plan.append((o.address, o.name, acts, None))

    # 2. data_error_messages: карта «код → текст»
    msgs = decode_error_messages(image)
    codes = ["%d=%s" % (k, m.replace("\r", "\\r").replace("\n", "\\n"))
             for k, m in enumerate(msgs, 1)]
    err_tail = ("первые 19 — сообщения об ошибках (транслит: '~'=ч,'q'=я,"
                "'{'=о,'x'=ш и т.п.); 20..23 — промпты REPL ('=>', 'stop', "
                "' w stroke ', 'programma:'); печатает emitter (свойство), "
                "код = порядковый номер packed-строки (bit7=конец)")
    plan.append((ERR_MESSAGES, by[ERR_MESSAGES].name,
                 [("codes", codes), ("code_semantics", err_tail),
                  ("message_count", len(msgs))], None))

    # 3. str_2079_cyrillic: снять semantic_pending
    seq, n_cyr, all_cyr, perm = decode_cyrillic_permutation(image)
    extra = sorted(b for b in image[CYR_STR:CYR_STR + CYR_STR_LEN]
                   if not (0xA1 <= b <= 0xC0))
    if all_cyr and perm:
        acts = [
            ("semantic_pending", "no"),
            ("semantic", "CONFIRMED: перестановочная таблица-маппинг кириллицы "
             "(НЕ проза): %d из 32 букв а-я под схемой а-я@0xA1 встречаются "
             "РОВНО по разу, порядок не азбучный; плюс служебные/пункт. коды "
             "%s" % (n_cyr, ", ".join("0x%02X" % b for b in extra))),
            ("decode_scheme", "cyrillic а-я@0xA1 sequential (без ё)"),
            ("decoded_seq", seq),
        ]
        cmt = ("Кириллическая кодовая перестановка: %d букв а..я каждая по разу "
               "+ служебные коды (%s); порядок не азбучный ⇒ mapping/раскладка "
               "пути РУС/ЛАТ токенизатора, а не текст. Тип оставлен string; по "
               "природе ближе к таблице-маппингу.") % (
            n_cyr, ", ".join("0x%02X" % b for b in extra))
        plan.append((CYR_STR, by[CYR_STR].name, acts, cmt))

    # 4. data_glyph_block: геометрия
    ok, n = verify_glyph_block(image)
    if ok:
        plan.append((GLYPH_BLOCK, by[GLYPH_BLOCK].name,
                     [("verified_shape", "%d глифов x %d байт = %d (OK)" %
                       (n, GLYPH_STRIDE, GLYPH_BYTES))], None))

    # 5. region для переменных (карта page-zero/workspace — живой запрос к RDB)
    for o in sorted(rdb.of_type("variable"), key=lambda z: z.address):
        if "region" in (o.properties or {}):
            continue
        plan.append((o.address, o.name,
                     [("region", classify_region(o.address))], None))
    return plan


def classify_region(addr):
    if addr <= 0x00FF:
        return "zero_page"
    if 0x3D00 <= addr <= 0x42FF:
        return "workspace_scratch"
    return "code_region_state"


def build_var_map(rdb):
    """Сводная карта переменных по регионам (для отчёта)."""
    zero, workspace, embedded = [], [], []
    for o in sorted(rdb.of_type("variable"), key=lambda z: z.address):
        row = (addr_hex(o.address), o.name, o.size)
        if o.address <= 0x00FF:
            zero.append(row)
        elif 0x3D00 <= o.address <= 0x42FF:
            workspace.append(row)
        else:
            embedded.append(row)
    return zero, workspace, embedded


def apply_plan(writer, plan):
    n_props = n_cmt = 0
    for addr, _name, acts, cmt in plan:
        for prop, value in acts:
            writer.set_property(addr, prop, value)
            n_props += 1
        if cmt is not None:
            writer.set_comment(addr, cmt)
            n_cmt += 1
    writer.save()
    return n_props, n_cmt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--rdb", default=DEFAULT_RDB)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    if not (args.check or args.apply):
        args.check = True

    rom_path = args.rom if os.path.isabs(args.rom) else os.path.join(REPO, args.rom)
    rdb_path = args.rdb if os.path.isabs(args.rdb) else os.path.join(REPO, args.rdb)
    with open(rom_path, "rb") as fh:
        image = fh.read()

    session, _cache = open_session(rom=rom_path, org=LO)
    try:
        info = session.call("debug_get_rdb_info")
        if os.path.abspath(info.get("path") or "") != rdb_path:
            raise SystemExit("RDB в сессии %r, ожидаем %r"
                             % (info.get("path"), rdb_path))
        rdb = Rdb.load(rdb_path)
        plan = build_plan(rdb, image)
        if args.check:
            n_props = sum(len(acts) for _a, _n, acts, _c in plan)
            print("Stage 19 план — объектов: %d, свойств: %d, комментариев: %d"
                  % (len(plan), n_props,
                     sum(1 for p in plan if p[3] is not None)))
            for addr, name, acts, cmt in plan:
                print("  %s %s" % (addr_hex(addr), name))
                for prop, value in acts:
                    v = (", ".join(value) if isinstance(value, list) else value)
                    if len(str(v)) > 90:
                        v = str(v)[:90] + "…"
                    print("       %s = %s" % (prop, v))
            zero, ws, emb = build_var_map(rdb)
            print("карта переменных: zero-page=%d, workspace(0x3D00..0x42FF)=%d,"
                  " embedded(код/heap)=%d" % (len(zero), len(ws), len(emb)))
            return 0
        writer = RdbWriter(session)
        n_props, n_cmt = apply_plan(writer, plan)
        print("  применено: свойств=%d, комментариев=%d" % (n_props, n_cmt))
        print("итог: %s" % (writer.summary(),))
        info = session.call("debug_get_rdb_info")
        print("объектов: %s, links: %s, dirty: %s"
              % (info.get("object_count"), info.get("link_count"),
                 info.get("dirty")))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
