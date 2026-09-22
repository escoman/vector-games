#!/usr/bin/env python3
"""Тесты посева RDB (ТЗ §40, §41).

Два уровня:

* Юнит (без эмулятора): `build_plan` — чистая функция, поэтому 40.1—40.6, 40.9
  и приоритеты/размеры/evidence проверяются на подставном `CodeAnalysis` и `Rdb`.
  Идемпотентность записи (40.10) и алиасы (40.7, 40.8) — на fake-бэкенде,
  который эмулирует ответы `debug_*` в памяти (без нового debugger-API).
* Интеграция (нужен `v06c-mcp`): dry-run `SeedRdb.run` два раза даёт одинаковые
  числа (детерминизм §32) и достигает fixpoint.

Пропуск, а не падение: без сервера интеграционный тест скипается.

Запуск:
    python3 utils/analyze/tests/test_seed_rdb.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap as B  # noqa: E402  (кладёт utils/ в sys.path и даёт пути)

from analyze import disassembly, naming, rdb_lint, seed_rdb
from analyze.mcp_session import McpError, to_addr
from analyze.rdb import Rdb, RdbObject, RdbWriter


# ---------------------------------------------------------------------------
# Подставные данные: разбор без MCP.
# ---------------------------------------------------------------------------
def _analysis(refs):
    """CodeAnalysis из списка (from, to, type) — build_plan читает только references."""
    payload = {
        "references": [{"from": a, "to": b, "type": t} for a, b, t in refs],
        "instructions": [],
        "ranges": [],
    }
    return disassembly.CodeAnalysis([0x0100], payload, "debug_analyze_code")


def _addrs(records, key):
    return sorted(to_addr(r["address"]) for r in records[key])


# ---------------------------------------------------------------------------
# Fake-бэкенд отладчика (эмулирует debug_*-инструменты в памяти, ТЗ §30).
# ---------------------------------------------------------------------------
class FakeRdbSession(object):
    def __init__(self, objects=None):
        self.objects = {}
        self.saved = 0
        for obj in objects or []:
            self._register(obj)

    def _register(self, obj):
        addr = to_addr(obj["address"])
        stored = self.objects.setdefault(addr, self._blank(addr))
        stored.update({k: v for k, v in obj.items() if k in stored})

    @staticmethod
    def _blank(addr):
        return {"address": addr, "name": None, "type": None, "size": 0,
                "comment": "", "links": [], "properties": {}}

    def call(self, tool, args=None):
        args = args or {}
        if tool == "debug_get_rdb_object":
            addr = to_addr(args.get("address"))
            if addr not in self.objects:
                # живой сервер отвечает ошибкой not_found, а не пустым JSON
                raise McpError(tool, "No RDB object at address", kind="not_found")
            return dict(self.objects[addr])
        if tool == "debug_list_rdb_objects":
            return {"objects": [dict(o) for o in self.objects.values()]}
        if tool == "debug_get_rdb_info":
            return {}
        if tool == "debug_add_rdb_object":
            addr = to_addr(args["address"])
            stored = self.objects.setdefault(addr, self._blank(addr))
            stored["name"] = args.get("name")
            stored["type"] = args.get("type")
            stored["size"] = int(args.get("size") or 0)
            return dict(stored)
        if tool == "debug_update_rdb_object":
            addr = to_addr(args["address"])
            stored = self.objects.setdefault(addr, self._blank(addr))
            for key in ("name", "type", "size"):
                if key in args:
                    stored[key] = args[key]
            return dict(stored)
        if tool == "debug_set_rdb_property":
            addr = to_addr(args["address"])
            stored = self.objects.setdefault(addr, self._blank(addr))
            stored["properties"][args["property"]] = args["value"]
            return dict(stored)
        if tool == "debug_set_rdb_comment":
            addr = to_addr(args["address"])
            stored = self.objects.setdefault(addr, self._blank(addr))
            stored["comment"] = args.get("comment", "")
            return dict(stored)
        if tool == "debug_add_rdb_link":
            src = to_addr(args["source"])
            stored = self.objects.setdefault(src, self._blank(src))
            target = to_addr(args["target"])
            if target not in stored["links"]:          # дубликаты срезает отладчик
                stored["links"].append(target)
            return dict(stored)
        if tool == "debug_save_rdb":
            self.saved += 1
            return {"saved": True}
        raise AssertionError("неожиданный вызов: %s" % tool)

    # снимок модели для сравнения идемпотентности
    def snapshot(self):
        out = {}
        for addr, stored in self.objects.items():
            out[addr] = (
                stored["name"], stored["type"], int(stored["size"] or 0),
                tuple(sorted(stored["links"])),
                tuple(naming_obj_aliases(stored)),
            )
        return out


def naming_obj_aliases(stored):
    """Алиасы объекта как нормализованный кортеж (парсит list/JSON-строку)."""
    return RdbObject(stored["address"], stored["name"] or "x",
                     stored["type"] or "data",
                     properties=stored["properties"]).get_aliases()


# ---------------------------------------------------------------------------
# 40.1—40.6, 40.9 — build_plan (чистая функция)
# ---------------------------------------------------------------------------
class SeedPlanTest(unittest.TestCase):
    def test_40_1_entry_becomes_function(self):
        plan = seed_rdb.build_plan([0x0100], _analysis([]), Rdb([]))
        self.assertEqual(_addrs(plan, "functions"), [0x0100])
        self.assertEqual(plan["functions"][0]["name"], "func_0100")
        self.assertEqual(plan["functions"][0]["type"], "function")

    def test_40_2_call_becomes_function(self):
        plan = seed_rdb.build_plan([0x0100], _analysis([(0x0100, 0x2000, "call")]),
                                   Rdb([]))
        self.assertIn(0x2000, _addrs(plan, "functions"))
        self.assertNotIn(0x2000, _addrs(plan, "labels"))

    def test_40_3_jump_becomes_label(self):
        plan = seed_rdb.build_plan([0x0100], _analysis([(0x0100, 0x3000, "jump")]),
                                   Rdb([]))
        self.assertIn(0x3000, _addrs(plan, "labels"))
        self.assertEqual([l["name"] for l in plan["labels"] if l["address"] == 0x3000],
                         ["lbl_3000"])

    def test_40_4_conditional_jump_becomes_label(self):
        plan = seed_rdb.build_plan([0x0100],
                                   _analysis([(0x0100, 0x3000, "conditional_jump")]),
                                   Rdb([]))
        self.assertIn(0x3000, _addrs(plan, "labels"))

    def test_40_5_duplicate_targets_collapse_to_one_object(self):
        plan = seed_rdb.build_plan(
            [0x0100], _analysis([(0x0100, 0x2000, "call"),
                                 (0x0110, 0x2000, "call")]), Rdb([]))
        funcs = [f for f in plan["functions"] if f["address"] == 0x2000]
        self.assertEqual(len(funcs), 1)

    def test_40_6_existing_object_not_renamed(self):
        rdb = Rdb([RdbObject(0x2000, "keyboard_handler", "function")])
        plan = seed_rdb.build_plan([0x0100], _analysis([(0x0100, 0x2000, "call")]),
                                   rdb)
        self.assertNotIn(0x2000, _addrs(plan, "functions"))
        self.assertEqual(plan["existing_objects"], 1)
        self.assertIn("existing object", [s["reason"] for s in plan["skipped"]])

    def test_40_9_branch_inside_function_not_new_object(self):
        rdb = Rdb([RdbObject(0x1000, "func_1000", "function", size=0x40)])
        plan = seed_rdb.build_plan([0x1000],
                                   _analysis([(0x1000, 0x1020, "conditional_jump")]),
                                   rdb)
        self.assertNotIn(0x1020, _addrs(plan, "labels"))
        self.assertEqual([c["address"] for c in plan["conflicts"]], ["0x1020"])

    def test_function_wins_over_label_for_same_address(self):
        plan = seed_rdb.build_plan(
            [0x0100], _analysis([(0x0100, 0x8000, "call"),
                                 (0x0200, 0x8000, "jump"),
                                 (0x0300, 0x8000, "conditional_jump")]), Rdb([]))
        self.assertIn(0x8000, _addrs(plan, "functions"))
        self.assertNotIn(0x8000, _addrs(plan, "labels"))

    def test_size_is_unknown_and_evidence_recorded(self):
        plan = seed_rdb.build_plan([0x0100], _analysis([(0x0150, 0x2000, "call")]),
                                   Rdb([]))
        func = [f for f in plan["functions"] if f["address"] == 0x2000][0]
        self.assertEqual(func["size"], 0)                 # ТЗ §25: не выдумываем
        self.assertEqual(func["evidence"]["seed_source"], "debug_analyze_code")
        self.assertEqual(func["evidence"]["seed_evidence"], "call")
        self.assertEqual(func["evidence"]["seed_from"], "0x0150")

    def test_links_dedup_and_no_self_link(self):
        plan = seed_rdb.build_plan(
            [0x0100], _analysis([(0x0100, 0x2000, "call"),
                                 (0x0100, 0x2000, "call"),
                                 (0x0100, 0x0100, "call")]), Rdb([]))
        links = [(l["source"], l["target"]) for l in plan["links"]]
        self.assertEqual(links.count((0x0100, 0x2000)), 1)
        self.assertNotIn((0x0100, 0x0100), links)

    def test_option_flags_gate_roles(self):
        analysis = _analysis([(0x0100, 0x2000, "call"), (0x0100, 0x3000, "jump")])
        no_func = seed_rdb.build_plan([0x0100], analysis, Rdb([]),
                                      seed_rdb.SeedOptions(functions=False))
        self.assertEqual(_addrs(no_func, "functions"), [])
        no_lbl = seed_rdb.build_plan([0x0100], analysis, Rdb([]),
                                     seed_rdb.SeedOptions(labels=False))
        self.assertEqual(_addrs(no_lbl, "labels"), [])
        no_link = seed_rdb.build_plan([0x0100], analysis, Rdb([]),
                                      seed_rdb.SeedOptions(links=False))
        self.assertEqual(no_link["links"], [])

    def test_plan_is_deterministic_under_reference_order(self):
        refs = [(0x0100, 0x2000, "call"), (0x0110, 0x3000, "jump"),
                (0x0120, 0x4000, "call")]
        a = seed_rdb.build_plan([0x0100], _analysis(refs), Rdb([]))
        b = seed_rdb.build_plan([0x0100], _analysis(list(reversed(refs))), Rdb([]))
        self.assertEqual(_addrs(a, "functions"), _addrs(b, "functions"))
        self.assertEqual(_addrs(a, "labels"), _addrs(b, "labels"))
        self.assertEqual([(l["source"], l["target"]) for l in a["links"]],
                         [(l["source"], l["target"]) for l in b["links"]])

    def test_classify_reference(self):
        self.assertEqual(seed_rdb.classify_reference("call"), "function")
        self.assertEqual(seed_rdb.classify_reference("RST"), "function")
        self.assertEqual(seed_rdb.classify_reference("jump"), "label")
        self.assertEqual(seed_rdb.classify_reference("conditional_jump"), "label")
        self.assertIsNone(seed_rdb.classify_reference("data_ref"))
        self.assertIsNone(seed_rdb.classify_reference(None))


# ---------------------------------------------------------------------------
# 40.7, 40.8 — алиасы (модель + писатель)
# ---------------------------------------------------------------------------
class AliasModelTest(unittest.TestCase):
    def test_40_7_add_alias_in_memory(self):
        obj = RdbObject(0x2000, "func_2000", "function")
        self.assertTrue(obj.add_alias("keyboard_handler"))
        self.assertEqual(obj.aliases, ["keyboard_handler"])

    def test_40_8_duplicate_alias_not_added(self):
        obj = RdbObject(0x2000, "func_2000", "function")
        obj.add_alias("keyboard_handler")
        self.assertFalse(obj.add_alias("keyboard_handler"))
        self.assertEqual(obj.aliases, ["keyboard_handler"])

    def test_primary_name_not_stored_as_alias(self):
        obj = RdbObject(0x2000, "func_2000", "function")
        self.assertFalse(obj.add_alias("func_2000"))
        self.assertEqual(obj.aliases, [])

    def test_aliases_load_from_disk_and_json_string(self):
        import json
        disk = RdbObject(0x2000, "func_2000", "function",
                         properties={"aliases": ["b", "a"]})
        self.assertEqual(disk.aliases, ["a", "b"])           # sorted, стабильно
        as_str = RdbObject(0x2000, "func_2000", "function",
                           properties={"aliases": json.dumps(["b", "a", "a"])})
        self.assertEqual(as_str.aliases, ["a", "b"])

    def test_old_rdb_without_aliases_loads_unchanged(self):
        obj = RdbObject(0x2000, "func_2000", "function")
        self.assertEqual(obj.aliases, [])
        self.assertFalse(obj.has_alias("anything"))


class AliasWriterTest(unittest.TestCase):
    def test_add_and_dedup_alias_via_writer(self):
        session = FakeRdbSession([{"address": 0x2000, "name": "func_2000",
                                   "type": "function"}])
        writer = RdbWriter(session, dry_run=False)
        self.assertTrue(writer.add_alias(0x2000, "scan_keyboard")["added"])
        self.assertFalse(writer.add_alias(0x2000, "scan_keyboard")["added"])
        self.assertEqual(writer.aliases(0x2000), ["scan_keyboard"])

    def test_add_alias_rejects_primary_name(self):
        session = FakeRdbSession([{"address": 0x2000, "name": "func_2000",
                                   "type": "function"}])
        writer = RdbWriter(session, dry_run=False)
        self.assertFalse(writer.add_alias(0x2000, "func_2000")["added"])

    def test_add_alias_rejects_wrong_type_prefix(self):
        session = FakeRdbSession([{"address": 0x2000, "name": "func_2000",
                                   "type": "function"}])
        writer = RdbWriter(session, dry_run=False)
        with self.assertRaises(ValueError):
            writer.add_alias(0x2000, "data_handler")   # data_ префикс не для function

    def test_add_alias_to_missing_raises(self):
        writer = RdbWriter(FakeRdbSession([]), dry_run=False)
        with self.assertRaises(ValueError):
            writer.add_alias(0x1234, "orphan")

    def test_remove_alias(self):
        session = FakeRdbSession([{"address": 0x2000, "name": "func_2000",
                                   "type": "function",
                                   "properties": {"aliases": ["a", "b"]}}])
        writer = RdbWriter(session, dry_run=False)
        self.assertTrue(writer.remove_alias(0x2000, "a")["removed"])
        self.assertEqual(writer.aliases(0x2000), ["b"])
        self.assertFalse(writer.remove_alias(0x2000, "zzz")["removed"])


# ---------------------------------------------------------------------------
# 40.10 — идемпотентность записи через apply_plan
# ---------------------------------------------------------------------------
class ApplyIdempotencyTest(unittest.TestCase):
    def _run(self, session):
        rdb = Rdb.from_session(session)
        analysis = _analysis([(0x0100, 0x2000, "call"), (0x0110, 0x3000, "jump"),
                              (0x2000, 0x4000, "call")])
        plan = seed_rdb.build_plan([0x0100], analysis, rdb)
        writer = RdbWriter(session, dry_run=False)
        counts = seed_rdb.apply_plan(writer, plan)
        writer.save()
        return counts

    def test_second_seed_changes_nothing(self):
        session = FakeRdbSession([])
        first = self._run(session)
        snap1 = session.snapshot()
        second = self._run(session)
        snap2 = session.snapshot()
        self.assertEqual(snap1, snap2)                       # RDB1 == RDB2
        self.assertGreater(first["functions_added"], 0)      # в первый раз есть
        # во второй раз ни один объект не создан заново (все уже существуют)
        self.assertEqual(second["functions_added"], 0)
        self.assertEqual(second["labels_added"], 0)
        self.assertEqual(
            sum(1 for a in session.objects.values()),
            len(snap1))

    def test_no_duplicate_links_after_two_runs(self):
        session = FakeRdbSession([])
        self._run(session)
        self._run(session)
        for stored in session.objects.values():
            self.assertEqual(len(stored["links"]), len(set(stored["links"])))

    def test_apply_creates_expected_objects(self):
        session = FakeRdbSession([{"address": 0x2000, "name": "keyboard_handler",
                                   "type": "function"}])
        counts = self._run(session)
        # 0x2000 уже был → не пересоздан; добавлены entry 0x0100, func 0x4000
        # и метка 0x3000 (только jump-ссылка → label, ТЗ §8)
        self.assertIn(0x0100, session.objects)
        self.assertEqual(session.objects[0x2000]["name"], "keyboard_handler")
        self.assertGreaterEqual(counts["functions_added"], 2)
        self.assertGreaterEqual(counts["labels_added"], 1)


# ---------------------------------------------------------------------------
# §28 — линт новых сущностей
# ---------------------------------------------------------------------------
class LintAliasLinkTest(unittest.TestCase):
    def _codes(self, rdb):
        findings, _ = rdb_lint.lint_rdb(rdb)
        return {f.code for f in findings}

    def test_detects_duplicate_and_collision_alias(self):
        rdb = Rdb([
            RdbObject(0x100, "func_0100", "function",
                      properties={"aliases": ["dup", "dup"]}),
            RdbObject(0x200, "func_0200", "function",
                      properties={"aliases": ["func_0100"]}),   # = чужое имя
        ])
        codes = self._codes(rdb)
        self.assertIn("duplicate_alias", codes)
        self.assertIn("alias_collision", codes)

    def test_detects_invalid_alias_and_self_link(self):
        rdb = Rdb([RdbObject(0x100, "func_0100", "function",
                             properties={"aliases": ["Not-Snake"]},
                             links=[0x100])])
        codes = self._codes(rdb)
        self.assertIn("alias_invalid", codes)
        self.assertIn("self_link", codes)

    def test_detects_duplicate_link(self):
        rdb = Rdb([RdbObject(0x100, "func_0100", "function", links=[0x900, 0x900])])
        self.assertIn("duplicate_link", self._codes(rdb))

    def test_detects_nesting(self):
        rdb = Rdb([
            RdbObject(0x1000, "func_outer", "function", size=0x40),
            RdbObject(0x1010, "func_inner", "function", size=0x05),
            RdbObject(0x2000, "data_block", "data", size=0x20),
            RdbObject(0x2005, "lbl_inside", "label", size=1),
        ])
        codes = self._codes(rdb)
        self.assertIn("function_inside_function", codes)
        self.assertIn("label_inside_unrelated", codes)


# ---------------------------------------------------------------------------
# §31 — naming для затравок и алиасов
# ---------------------------------------------------------------------------
class NamingSeedTest(unittest.TestCase):
    def test_technical_names_pass_validate(self):
        for addr in (0x0100, 0x2000, 0xabcd):
            fname = naming.technical_function_name(addr)
            lname = naming.technical_label_name(addr)
            self.assertEqual([p for p in naming.validate(fname, "function")
                              if p[0] == "error"], [])
            self.assertEqual([p for p in naming.validate(lname, "label")
                              if p[0] == "error"], [])

    def test_is_valid_alias(self):
        self.assertTrue(naming.is_valid_alias("keyboard_scan"))       # без префикса
        self.assertTrue(naming.is_valid_alias("func_scan", "function"))
        self.assertFalse(naming.is_valid_alias("data_scan", "function"))  # чужой тип
        self.assertFalse(naming.is_valid_alias("Bad-Name"))
        self.assertFalse(naming.is_valid_alias(""))


# ---------------------------------------------------------------------------
# §41 — интеграция (нужен v06c-mcp): детерминизм + fixpoint на putup и TESTAY
# ---------------------------------------------------------------------------
def _server_ready():
    return os.access(B.MCP_SERVER, os.X_OK) and os.path.isfile(B.PUTUP_ROM)


def _testay_ready():
    return os.access(B.MCP_SERVER, os.X_OK) and os.path.isfile(B.TESTAY_ROM)


@unittest.skipUnless(_server_ready(), "нужен v06c-mcp и putup.rom")
class SeedIntegrationTest(unittest.TestCase):
    def _dry_run(self, session, cache, rom, rdb_path):
        from analyze.coverage import CoverageEngine
        static = disassembly.StaticAnalysis(session, cache)
        coverage = CoverageEngine(session, cache, static=static)
        rdb = Rdb.load(rdb_path) if rdb_path else Rdb.from_session(session)
        writer = RdbWriter(session, dry_run=True)         # dry-run: putup.rdb не трогаем
        engine = seed_rdb.SeedRdb(session, static=static, coverage=coverage)
        return engine.run([0x0100], 0x0100, 0x0100 + os.path.getsize(rom) - 1,
                          rdb, writer)

    def _deterministic_to_fixpoint(self, session, cache, rom, rdb_path):
        first = self._dry_run(session, cache, rom, rdb_path)
        second = self._dry_run(session, cache, rom, rdb_path)
        for key in ("functions_added", "labels_added", "links_added"):
            self.assertEqual(first[key], second[key], "рассинхрон по %s" % key)
        self.assertTrue(first["fixpoint"], "посев не сошёлся к fixpoint")
        self.assertGreaterEqual(first["functions_added"], 0)
        return first

    def test_dry_run_is_deterministic_and_reaches_fixpoint(self):
        from analyze import mcp_session
        session, cache = mcp_session.open_session(rom=B.PUTUP_ROM, org=0x0100,
                                                  server=B.MCP_SERVER)
        try:
            self._deterministic_to_fixpoint(session, cache, B.PUTUP_ROM,
                                            B.PUTUP_RDB)
        finally:
            session.close()

    @unittest.skipUnless(_testay_ready(), "нужен TESTAY.ROM")
    def test_dry_run_on_testay_in_same_session_shape(self):
        """§41: второй ROM в том же фреймворке — переносимость посева."""
        from analyze import mcp_session
        session, cache = mcp_session.open_session(rom=B.TESTAY_ROM, org=0x0100,
                                                  server=B.MCP_SERVER)
        try:
            run = self._deterministic_to_fixpoint(
                session, cache, B.TESTAY_ROM,
                B.TESTAY_RDB if os.path.isfile(B.TESTAY_RDB) else None)
            self.assertIn("entry_points", run)
        finally:
            session.close()


@unittest.skipUnless(os.environ.get("V06C_ANALYZE_E2E") == "1",
                     "применение посева (§43) идёт только при V06C_ANALYZE_E2E=1")
@unittest.skipUnless(_server_ready() and os.path.isfile(B.PUTUP_RDB),
                     "нужен v06c-mcp, putup.rom и putup.rdb")
class SeedApplyAcceptanceTest(unittest.TestCase):
    """§43 acceptance: apply на копию putup → PASS/fixpoint, повтор идемпотентен,
    сохранённый RDB валиден и без дублей адресов/алиасов/ссылок."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="v06c-seed-apply-")
        cls.rom = os.path.join(cls.tmp, "putup.rom")
        cls.rdb = os.path.join(cls.tmp, "putup.rdb")
        shutil.copyfile(B.PUTUP_ROM, cls.rom)
        shutil.copyfile(B.PUTUP_RDB, cls.rdb)   # сервер подхватит .rdb рядом с .rom

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def _apply(self):
        buf = io.StringIO()
        argv = ["--rom", self.rom, "--rdb", self.rdb, "--org", "0x0100",
                "--entry", "0x0100", "--apply", "--json"]
        with contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(buf):
            rc = seed_rdb.main(argv)
        self.assertEqual(rc, 0, "apply не должен падать")
        return json.loads(buf.getvalue())

    def test_apply_acceptance_putup(self):
        base_findings, base_summary = rdb_lint.lint_rdb(Rdb.load(B.PUTUP_RDB))
        first = self._apply()
        self.assertEqual(str(first["status"]).upper(), "PASS")
        self.assertTrue(first["fixpoint"], "§43: fixpoint = true")
        model1 = Rdb.load(self.rdb)

        second = self._apply()                    # повтор — идемпотентность
        self.assertEqual(second["functions_added"], 0)
        self.assertEqual(second["labels_added"], 0)
        model2 = Rdb.load(self.rdb)
        snap = lambda m: sorted((o.address, o.name, o.type, o.get_aliases())
                                for o in m.objects)
        self.assertEqual(snap(model1), snap(model2), "повторный посев изменил RDB")

        findings, summary = rdb_lint.lint_rdb(model1)
        codes = {f.code for f in findings}
        for dup in ("duplicate_address", "duplicate_alias", "duplicate_link",
                    "alias_collision", "self_link"):
            self.assertNotIn(dup, codes, "§43: дубли/коллизии должны отсутствовать")
        # в базовом putup.rdb уже есть находки ручного хозяйства (bad_name с
        # hex-буквами, overlap); приёмка §43 — «посев не добавил ни одной новой
        # ошибки», а не «идеального RDB не существовало до нас».
        self.assertEqual(summary["by_severity"]["error"],
                         base_summary["by_severity"]["error"],
                         "посев добавил новые ERROR-находки")


if __name__ == "__main__":
    unittest.main(verbosity=2)
