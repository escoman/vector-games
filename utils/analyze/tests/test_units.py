#!/usr/bin/env python3
"""Юнит-тесты чистых функций пакета `analyze` (без MCP-сервера).

Покрывают то, что обязано быть детерминированным и не требует эмулятора:
шаблоны имён (§28), ключ и конверт кэша доказательств (§6, §7), классификацию
результатов и сводку §30 в отчёте (§29, §34), подстановку плейсхолдеров и
порядок шагов в `pipeline`, расположение и срезание кэша в `clear_cache`,
разбор адреса и общий конверт в `mcp_session`.

Запуск:
    PYTHONPATH=utils python3 -m unittest discover -s utils/analyze/tests -t utils
или
    python3 utils/analyze/tests/test_units.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401  (кладёт utils/ в sys.path)

from analyze import naming, evidence_cache, report_gen, pipeline, clear_cache
from analyze.evidence_cache import EvidenceCache, normalize_args, _norm_scalar
from analyze import mcp_session


# ---------------------------------------------------------------------------
# naming.py — ТЗ §28
# ---------------------------------------------------------------------------
class NamingTest(unittest.TestCase):
    def test_prefix_for_case_insensitive(self):
        self.assertEqual(naming.prefix_for("function"), "func_")
        self.assertEqual(naming.prefix_for("TABLE"), "data_")   # table → data_
        self.assertEqual(naming.prefix_for(" string "), "str_")

    def test_prefix_for_unknown_raises(self):
        with self.assertRaises(ValueError):
            naming.prefix_for("quantum")

    def test_type_for(self):
        self.assertEqual(naming.type_for("func_draw_gfx"), "function")
        self.assertEqual(naming.type_for("mystery"), None)

    def test_slugify_ascii_only(self):
        self.assertEqual(naming.slugify("Load GFX block"), "load_gfx_block")
        self.assertEqual(naming.slugify("  --Weird!! Spacing-- "), "weird_spacing")
        self.assertEqual(naming.slugify(""), "")
        self.assertEqual(naming.slugify("2 fast"), "x2_fast")   # не с цифры
        self.assertTrue(len(naming.slugify("a" * 40)) <= 24)

    def test_propose_variants(self):
        self.assertEqual(naming.propose("function", "draw game objects"),
                         "func_draw_game_objects")
        self.assertEqual(naming.propose("data", addr=0x3041), "data_3041")
        self.assertEqual(naming.propose("data", unknown=True, addr=0x2100),
                         "data_2100_unknown")
        # суффикс _unknown обязан остаться целиком даже при обрезке по длине
        name = naming.propose("function", "a" * 40, unknown=True)
        self.assertTrue(name.endswith(naming.UNKNOWN_SUFFIX))
        self.assertLessEqual(len(name), naming.MAX_NAME)

    def test_unknown_for_canonical(self):
        self.assertEqual(naming.unknown_for("code", 0x12ab), "func_12ab_unknown")

    def test_validate_clean(self):
        self.assertEqual(naming.validate("func_draw_gfx", "function"), [])

    def test_validate_rejects_bad_prefix_type(self):
        problems = naming.validate("data_points", "function")
        kinds = [p[0] for p in problems]
        self.assertIn("error", kinds)          # префикс не совпадает с типом

    def test_validate_rejects_uppercase(self):
        problems = naming.validate("Func_Bad", "function")
        self.assertTrue(any(s == "error" for s, _ in problems))

    def test_validate_warns_on_address_tail(self):
        problems = naming.validate("func_load_gfx_2761")
        self.assertTrue(any(s == "warning" and "адресн" in t for s, t in problems))


# ---------------------------------------------------------------------------
# evidence_cache.py — ТЗ §6, §7, §16
# ---------------------------------------------------------------------------
class NormalizeArgsTest(unittest.TestCase):
    def test_drops_none_and_sorts_semantics(self):
        out = normalize_args({"b": 1, "a": None, "c": 3})
        self.assertEqual(out, {"b": 1, "c": 3})     # None отброшен

    def test_hex_string_becomes_int(self):
        self.assertEqual(normalize_args({"addr": "0x0100"})["addr"], 256)
        self.assertEqual(normalize_args({"addr": "0X10"})["addr"], 16)

    def test_decimals_and_plain_strings_stay(self):
        self.assertEqual(_norm_scalar("256"), "256")
        self.assertEqual(_norm_scalar(256), 256)

    def test_nested_normalized(self):
        out = normalize_args({"outer": {"inner": "0xff", "keep": None}})
        self.assertEqual(out["outer"]["inner"], 255)


class FakeSession:
    """Минимальная замена McpSession для проверки кэша без эмулятора."""
    def __init__(self):
        self.calls = 0

    def runtime_stamp(self):
        return {"pc": 0x100, "running": False, "cycles": 0, "frames": 0, "sp": 0x8000}

    def call(self, tool, args, timeout=None):
        self.calls += 1
        return {"tool": tool, "seq": self.calls}


class EvidenceCacheTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="v06c-cache-test-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def _cache(self, **kw):
        return EvidenceCache(root=os.path.join(self.root, "cache"),
                             identity={"filename": "x.rom", "size": 128,
                                       "sha256": "deadbeefcafe1234", "org": 0x0100},
                             **kw)

    def test_key_stable_and_sensitive(self):
        c = self._cache()
        k1, _ = c.key_for("debug_read_memory_range", {"address": "0x100"}, stamp=None)
        k2, _ = c.key_for("debug_read_memory_range", {"address": 256}, stamp=None)
        self.assertEqual(k1, k2)                       # "0x100" == 256 после нормализации
        k3, _ = c.key_for("debug_read_memory_range", {"address": 512}, stamp=None)
        self.assertNotEqual(k1, k3)
        s = {"pc": 1, "running": True}
        k4, _ = c.key_for("debug_read_memory_range", {"address": 256}, stamp=s)
        self.assertNotEqual(k1, k4)                    # рантайм-штамп меняет ключ

    def test_miss_then_hit(self):
        c = self._cache()
        sess = FakeSession()
        res1, env1 = c.get_or_call(sess, "debug_read_memory_range", {"address": 256})
        self.assertFalse(env1["cached"])
        self.assertEqual(sess.calls, 1)
        res2, env2 = c.get_or_call(sess, "debug_read_memory_range", {"address": 256})
        self.assertTrue(env2["cached"])                # второй раз — из кэша
        self.assertEqual(env2["source"], "CACHE")
        self.assertEqual(sess.calls, 1)                # в сервер не ходили
        self.assertEqual(c.hits, 1)
        self.assertEqual(c.misses, 1)
        self.assertEqual(res1["tool"], res2["tool"])

    def test_runtime_change_invalidates(self):
        c = self._cache()
        sess = FakeSession()
        c.get_or_call(sess, "debug_x", {"a": 1}, stamp={"pc": 1})
        c.get_or_call(sess, "debug_x", {"a": 1}, stamp={"pc": 2})
        self.assertEqual(sess.calls, 2)                # разный рантайм → два промаха
        self.assertEqual(c.misses, 2)

    def test_disabled_bypasses_server(self):
        c = self._cache(enabled=False)
        sess = FakeSession()
        _, env = c.get_or_call(sess, "debug_x", {"a": 1})
        self.assertEqual(env["source"], "MCP")
        self.assertFalse(env["cached"])
        self.assertEqual(c.bypasses, 1)

    def test_derived_and_iter(self):
        c = self._cache()
        path, _ev_id = c.save_derived("shapes", {"n": 3}, derived_from=["ev:x:1"])
        self.assertTrue(os.path.isfile(path))
        sess = FakeSession()
        _res, env = c.get_or_call(sess, "debug_read_memory_range", {"address": 256})
        ids = {e.get("evidence_id") for e in c.iter_envelopes()}
        self.assertIn(env["evidence_id"], ids)      # и evidence, и derived в обходе
        self.assertEqual(c.load(env["evidence_id"])["result"]["tool"],
                         "debug_read_memory_range")  # load резолвит evidence-id

    def test_stats_shape(self):
        c = self._cache()
        st = c.stats()
        for key in ("root", "enabled", "hits", "misses", "stores", "hit_rate", "by_tool"):
            self.assertIn(key, st)


# ---------------------------------------------------------------------------
# report_gen.py — ТЗ §29, §34
# ---------------------------------------------------------------------------
class ClassifyTest(unittest.TestCase):
    def test_status_buckets(self):
        self.assertEqual(report_gen.classify({"status": "OK"}), "facts")
        self.assertEqual(report_gen.classify({"status": "MATCHED"}), "facts")
        self.assertEqual(report_gen.classify({"status": "CANDIDATE"}), "candidates")
        self.assertEqual(report_gen.classify({"status": "MISMATCH"}), "blocked")
        # незнакомый непустой статус → unknowns, пустой → unclassified (§34)
        self.assertEqual(report_gen.classify({"status": "WEIRD"}), "unknowns")
        self.assertEqual(report_gen.classify({}), "unclassified")

    def test_collect_facts_candidates_hypotheses(self):
        results = {
            "a": {"status": "OK", "verdict": "byte-for-byte"},
            "b": {"status": "CANDIDATE", "candidates": [
                {"name": "hi-conf", "confidence": "high"},
                {"name": "lo-conf", "confidence": "low"},
            ]},
        }
        buckets = report_gen.collect(results)
        self.assertEqual(buckets["facts"][0]["module"], "a")
        # high → Inferences (candidates), low → Hypotheses.
        # В buckets["candidates"] попадает и сводка модуля (без "name") — берём
        # только записи-кандидаты.
        cand = [c["name"] for c in buckets["candidates"] if "name" in c]
        hyp = [c["name"] for c in buckets["hypotheses"] if "name" in c]
        self.assertEqual(cand, ["hi-conf"])
        self.assertEqual(hyp, ["lo-conf"])

    def test_blocked_verdict_overrides_status(self):
        buckets = report_gen.collect({"m": {"status": "OK", "verdict": "blocked: нет RDB"}})
        self.assertEqual(buckets["facts"], [])
        self.assertEqual(buckets["blocked"][0]["module"], "m")

    def test_no_status_is_unclassified_not_fact(self):
        buckets = report_gen.collect({"m": {"verdict": "что-то нашёл"}})
        self.assertEqual(buckets["facts"], [])
        self.assertEqual(buckets["unclassified"][0]["module"], "m")


class StatisticsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="v06c-stats-test-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_by_module_sum_without_file(self):
        results = {"probe": {"mcp_calls": 15}, "abi_scan": {"mcp_calls": 920},
                   "rdb_lint": {"mcp_calls": 0}}
        st = report_gen.statistics(results)
        self.assertEqual(st["total_mcp_calls"], 935)
        self.assertEqual(st["by_module"]["abi_scan"], 920)
        self.assertIn("mcp_calls_meaning", st)

    def test_stats_file_total_wins(self):
        results = {"probe": {"mcp_calls": 15}}
        path = os.path.join(self.root, "statistics.json")
        with io.open(path, "w", encoding="utf-8") as fh:
            json.dump({"total_mcp_calls": 973, "wall_ms": 27123,
                       "tools_exposed": 70}, fh)
        st = report_gen.statistics(results, stats_file=path)
        self.assertEqual(st["total_mcp_calls"], 973)           # файл важнее суммы
        self.assertEqual(st["mcp_calls_field_sum"], 15)
        self.assertEqual(st["wall_ms"], 27123)
        self.assertEqual(st["statistics_source"], path)
        self.assertNotIn("mcp_calls_meaning", st)              # не из модулей

    def test_missing_file_flagged(self):
        st = report_gen.statistics({}, stats_file=os.path.join(self.root, "nope.json"))
        self.assertIn("statistics_file_missing", st)


class RenderTest(unittest.TestCase):
    def test_all_section29_headers_present(self):
        results = {
            "probe": {"status": "OK", "verdict": "boot", "rom": "putup.rom",
                      "sha256": "aa" * 32, "mcp_calls": 15},
            "abi_scan": {"status": "CANDIDATE",
                         "candidates": [{"name": "x", "confidence": "medium"}]},
            "coverage": {"status": "PARTIAL", "blind_spots": [{"lo": 1, "hi": 2}]},
        }
        text = report_gen.render(results, goal="цель", stage="13")
        for header in ("## Goal", "## ROM", "## Method", "## Findings",
                       "## Verified Facts", "## Inferences", "## Hypotheses",
                       "## Unknowns", "## Limitations", "## Recommended Next Steps"):
            self.assertIn(header, text)
        self.assertIn("putup.rom", text)


# ---------------------------------------------------------------------------
# pipeline.py — плейсхолдеры и порядок шагов
# ---------------------------------------------------------------------------
class PipelineTest(unittest.TestCase):
    def _ctx(self, **over):
        ctx = pipeline.Ctx()
        vals = dict(rom="r.rom", rdb="r.rdb", org="0x0100", entry="0x0100",
                    hi="0x4600", results="res", export="exp", z80asm="z80asm",
                    exporter="exporter", spec="spec.json", asm_entry="main.asm",
                    cache=None, server=None, abi_limit=50,
                    glyph_address=None, glyph_count=16, credits="str_credits",
                    runtime=False)
        vals.update(over)
        for k, v in vals.items():
            setattr(ctx, k, v)
        return ctx

    def test_placeholders_split_entry_vs_asm_entry(self):
        ph = self._ctx().placeholders()
        self.assertEqual(ph["entry"], "0x0100")
        self.assertEqual(ph["asm_entry"], "main.asm")
        self.assertNotIn("cache", ph)         # None → не подставляется
        ctx = self._ctx(cache="/tmp/c", server="/srv/mcp")
        self.assertEqual(ctx.placeholders()["cache"], "/tmp/c")

    def test_step_argv_substitution(self):
        ctx = self._ctx()
        step = pipeline.Step("export_asm", ["--out", "{export}/x.bin",
                                            "--assemble", "--rom", "{rom}"])
        argv = step.argv(ctx)
        self.assertEqual(argv, ["--json", "--out", "exp/x.bin",
                                "--assemble", "--rom", "r.rom"])

    def test_step_argv_missing_placeholder_raises(self):
        step = pipeline.Step("probe", ["--rom", "{nope}"])
        with self.assertRaises(SystemExit):
            step.argv(self._ctx())

    def test_build_steps_order_and_glyph_toggle(self):
        without = [s.module for s in pipeline.build_steps(self._ctx())]
        self.assertNotIn("glyph_scan", without)
        self.assertEqual(without[0], "probe")
        self.assertIn("roundtrip_verify", without)
        self.assertIn("music2midi", without)
        with_glyph = [s.module for s in
                      pipeline.build_steps(self._ctx(glyph_address="0x2706"))]
        self.assertIn("glyph_scan", with_glyph)
        self.assertEqual(len(with_glyph), len(without) + 1)
        self.assertNotIn(None, with_glyph)         # None-шаги отфильтрованы

    def test_runtime_flag_adds_arg(self):
        steps = {s.module: s for s in pipeline.build_steps(self._ctx(runtime=True))}
        self.assertIn("--runtime", steps["music2midi"].argv(self._ctx(runtime=True)))


# ---------------------------------------------------------------------------
# clear_cache.py — расположение, защита, срезание оболочки
# ---------------------------------------------------------------------------
class ClearCacheTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="v06c-clear-test-")
        self.addCleanup(shutil.rmtree, self.root, True)
        # убрать переопределение из окружения, чтобы дефолт был предсказуем
        self._saved_env = os.environ.pop(evidence_cache.DEFAULT_CACHE_ENV, None)
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        if self._saved_env is not None:
            os.environ[evidence_cache.DEFAULT_CACHE_ENV] = self._saved_env

    def test_default_root_next_to_rom(self):
        rom = os.path.join(self.root, "src", "game.rom")
        os.makedirs(os.path.dirname(rom))
        self.assertEqual(clear_cache.cache_root_for_rom(rom),
                         os.path.join(self.root, "src", ".analyze"))

    def test_env_override(self):
        os.environ[evidence_cache.DEFAULT_CACHE_ENV] = os.path.join(self.root, "shared")
        self.assertEqual(clear_cache.cache_root_for_rom("/anywhere/x.rom"),
                         os.path.join(self.root, "shared"))

    def test_is_cache_like(self):
        real = os.path.join(self.root, "a1", ".analyze")
        os.makedirs(real)
        self.assertTrue(clear_cache.is_cache_like(real))
        inner = os.path.join(self.root, "a2", "cache", "tag")
        os.makedirs(os.path.join(inner, "evidence"))
        self.assertTrue(clear_cache.is_cache_like(inner))
        elsewhere = os.path.join(self.root, "src")
        os.makedirs(elsewhere)
        self.assertFalse(clear_cache.is_cache_like(elsewhere))

    def test_resolve_targets_rom_only_its_tag(self):
        root = os.path.join(self.root, "romdir", ".analyze", "cache")
        for tag in ("game-1111aaaa", "other-2222bbbb"):
            os.makedirs(os.path.join(root, tag, "evidence"))
        rom = os.path.join(self.root, "romdir", "game.rom")
        args = types.SimpleNamespace(rom=[rom], root=None, scan=None,
                                     assume_root=False)
        targets = clear_cache.resolve_targets(args)
        self.assertEqual(len(targets), 1)
        self.assertTrue(targets[0].endswith(os.path.join("cache", "game-1111aaaa")))

    def test_prune_cache_shell(self):
        base = os.path.join(self.root, "rom", ".analyze", "cache", "tag-1")
        os.makedirs(os.path.join(base, "evidence"))
        shutil.rmtree(base)                       # сам тег снесён (rmtree-режим)
        cut = clear_cache.prune_cache_shell(base)
        self.assertEqual(len(cut), 2)             # cache и .analyze
        self.assertFalse(os.path.exists(os.path.join(self.root, "rom", ".analyze")))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "rom")))   # граница

    def test_prune_cache_shell_keeps_nonempty_parent(self):
        cache = os.path.join(self.root, "rom", ".analyze", "cache")
        gone = os.path.join(cache, "tag-a")
        keep = os.path.join(cache, "tag-b")
        os.makedirs(gone)
        os.makedirs(os.path.join(keep, "evidence"))
        shutil.rmtree(gone)
        cut = clear_cache.prune_cache_shell(gone)
        self.assertEqual(cut, [])                 # cache не пуст → не режем
        self.assertTrue(os.path.isdir(keep))

    def test_prune_shell_keep_flag(self):
        base = os.path.join(self.root, "rom", ".analyze", "cache", "tag")
        os.makedirs(base)
        shutil.rmtree(base)
        self.assertEqual(clear_cache.prune_cache_shell(base, keep=True), [])
        self.assertTrue(os.path.isdir(os.path.join(self.root, "rom", ".analyze", "cache")))


# ---------------------------------------------------------------------------
# mcp_session.py — разбор адреса и общий конверт (§34)
# ---------------------------------------------------------------------------
class ToAddrTest(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(mcp_session.to_addr("0x0100"), 256)
        self.assertEqual(mcp_session.to_addr(256), 256)
        self.assertEqual(mcp_session.to_addr("FF"), 255)      # с буквами → hex
        self.assertEqual(mcp_session.to_addr("255"), 255)     # без букв → decimal
        self.assertIsNone(mcp_session.to_addr(None))
        self.assertIsNone(mcp_session.to_addr("  "))

    def test_rejects(self):
        with self.assertRaises(ValueError):
            mcp_session.to_addr(True)
        with self.assertRaises(ValueError):
            mcp_session.to_addr("/path/to.rom")


class EnvelopeTest(unittest.TestCase):
    def test_does_not_fabricate_status(self):
        buf = io.StringIO()
        saved = sys.stderr
        sys.stderr = buf
        try:
            out = mcp_session.envelope({"verdict": "v"}, module="m", session=None)
        finally:
            sys.stderr = saved
        self.assertNotIn("status", out)            # §34: статус не выдуман
        self.assertIn("не назвал статус", buf.getvalue())

    def test_fills_module_and_default_calls(self):
        out = mcp_session.envelope({"status": "OK"}, module="probe", session=None)
        self.assertEqual(out["module"], "probe")
        self.assertEqual(out["status"], "OK")
        self.assertEqual(out["mcp_calls"], 0)

    def test_explicit_status_wins(self):
        out = mcp_session.envelope({"status": "OK"}, module="m", status="MATCHED")
        self.assertEqual(out["status"], "MATCHED")

    def test_candidates_not_overwritten_if_present(self):
        out = mcp_session.envelope({"status": "CANDIDATE", "candidates": [{"a": 1}]},
                                   module="m", candidates=[{"b": 2}])
        self.assertEqual(out["candidates"], [{"a": 1}])   # свои остаются

    def test_requires_dict(self):
        with self.assertRaises(SystemExit):
            mcp_session.envelope(["not", "a", "dict"], module="m")


if __name__ == "__main__":
    unittest.main(verbosity=2)
