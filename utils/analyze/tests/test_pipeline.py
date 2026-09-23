#!/usr/bin/env python3
"""Юнит-тесты стандартного pipeline (ТЗ Standard Pipeline §56—§57 на уровне
без сервера): checkpoint-механика, DAG, persistence, resume, safety, dry-run,
идемпотентность аннотаций.

Сервер не поднимается: `pipeline.share` и `pipeline.module_main` подменяются
FakeSession и фиктивными main-функциями модулей. Tracked-файлы репозитория
тесты не трогают — всё во временных каталогах (решение пользователя: E2E и
юниты только на копиях).

Запуск:
    PYTHONPATH=utils python3 -m unittest discover -s utils/analyze/tests -t utils
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
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401  (кладёт utils/ в sys.path)

from analyze import pipeline, pipeline_state
from analyze import apply_annotations as ann
from analyze.capabilities import CORE_REQUIRED, CapabilityProfile
from analyze.seed_rdb import BatchSaver


# ---------------------------------------------------------------------------
# FakeSession — контракт mcp_session.McpSession на уровне юнитов
# ---------------------------------------------------------------------------

class FakeSession(object):
    """call/snapshot/since/stats/tools + «RDB на диске» вокруг .rdb-файла."""

    def __init__(self, rdb_path=None, objects=3, tools=None):
        self.rdb_path = rdb_path
        self.objects = objects
        self.links = 0
        self.calls = []
        self.save_broken = False       # имитация битого save (ТЗ §6)
        self._proc = None
        default_tools = list(CORE_REQUIRED) + [
            "debug_add_rdb_object", "debug_update_rdb_object",
            "debug_add_rdb_link", "debug_get_rdb_object"]
        self.tools = {name: {} for name in (tools or default_tools)}

    # -- протокол сеанса ----------------------------------------------------
    def call(self, tool, arguments=None, **kwargs):
        self.calls.append((tool, dict(arguments or {})))
        if tool == "debug_get_rdb_info":
            return {"object_count": self.objects, "link_count": self.links}
        if tool == "debug_save_rdb":
            if self.save_broken:
                with open(self.rdb_path, "w", encoding="utf-8") as handle:
                    handle.write("{не json")
            else:
                self.dump_rdb()
            return {"saved": True}
        if tool == "debug_get_rdb_object":
            return {}
        return {}

    def snapshot(self):
        return {"total_calls": len(self.calls), "total_ms": 1.0,
                "total_bytes": 100, "retries": 0}

    def since(self, before, after):
        return {"total_calls": after["total_calls"] - before["total_calls"],
                "total_ms": 1.0, "total_bytes": 100, "retries": 0}

    def stats(self):
        return {"total_calls": len(self.calls), "total_ms": 1.0,
                "total_bytes": 100, "retries": 0, "server": "fake"}

    # -- вспомогательное ----------------------------------------------------
    def dump_rdb(self):
        """RDB-файл, согласованный с `self.objects` (как после save сервера)."""
        objects = [{"address": "0x%04X" % (0x100 + 2 * i),
                    "name": "func_obj_%04x" % i, "type": "function",
                    "links": []} for i in range(self.objects)]
        with open(self.rdb_path, "w", encoding="utf-8") as handle:
            json.dump({"format": "rdb", "version": 1, "objects": objects},
                      handle)

    def mutating_calls(self):
        return [tool for tool, _ in self.calls
                if tool in pipeline_state.RDB_MUTATING_TOOLS]


def write_rdb(path, objects=3):
    session = FakeSession(rdb_path=path, objects=objects)
    session.dump_rdb()


def write_rom(path, blob=b"\x00" * 64):
    with open(path, "wb") as handle:
        handle.write(blob)


def make_ctx(**over):
    """Минимальный Ctx для чистых функций build_steps/toposort."""
    ctx = pipeline.Ctx()
    ctx.rom = "/tmp/fake.rom"
    ctx.rdb = "/tmp/fake.rdb"
    ctx.org = "0x0100"
    ctx.entry = "0x0100"
    ctx.hi = "0x39FF"
    ctx.results = "/tmp/results"
    ctx.export = "/tmp/export"
    ctx.z80asm = "/bin/z80asm"
    ctx.exporter = "/bin/exporter"
    ctx.abi_limit = 4
    ctx.credits = "str_credits_koi8"
    ctx.glyph_address = over.pop("glyph_address", None)
    ctx.glyph_count = 6
    ctx.spec = over.pop("spec", "")
    ctx.runtime = False
    ctx.cache = None
    ctx.server = None
    ctx.asm_entry = "main.asm"
    ctx.dry_run = False
    ctx.persistence = dict(pipeline.DEFAULT_PERSISTENCE)
    for key, value in over.items():
        setattr(ctx, key, value)
    return ctx


# ---------------------------------------------------------------------------
# pipeline_state: атомарность / verify / validate_resume (ТЗ §6—§11)
# ---------------------------------------------------------------------------

class PipelineStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmp, "pipeline_state.json")
        self.rom = os.path.join(self.tmp, "fake.rom")
        self.rdb = os.path.join(self.tmp, "fake.rdb")
        write_rom(self.rom)
        write_rdb(self.rdb, objects=4)

    def tearDown(self):
        pipeline_state.clear_active()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_checkpoint_atomic(self):
        state = pipeline_state.make_state(rom="fake.rom", rdb="fake.rdb")
        path = pipeline_state.write_checkpoint(self.state_path, state)
        self.assertEqual(path, self.state_path)
        self.assertFalse(os.path.exists(self.state_path + ".tmp"))
        got = pipeline_state.read_checkpoint(self.state_path)
        self.assertEqual(got["version"], pipeline_state.STATE_VERSION)
        for key in ("rom", "rom_sha256", "rdb", "rdb_sha256",
                    "last_completed_stage", "completed_stages", "current_stage",
                    "current_batch", "processed_objects", "pending_objects",
                    "checkpoint_time", "rdb_objects", "rdb_links", "status",
                    "dry_run"):
            self.assertIn(key, got)

    def test_read_checkpoint_corrupted(self):
        with open(self.state_path, "w", encoding="utf-8") as handle:
            handle.write("{битый json")
        with self.assertRaises(pipeline_state.CheckpointCorrupted) as caught:
            pipeline_state.read_checkpoint(self.state_path)
        self.assertEqual(caught.exception.code, "CHECKPOINT_CORRUPTED")
        state = pipeline_state.make_state(rom="a", rdb="b")
        state["version"] = 99
        with open(self.state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        with self.assertRaises(pipeline_state.CheckpointCorrupted):
            pipeline_state.read_checkpoint(self.state_path)
        self.assertIsNone(pipeline_state.read_checkpoint(
            os.path.join(self.tmp, "нет-такого.json")))

    def test_verify_saved_rdb_cases(self):
        ok, detail = pipeline_state.verify_saved_rdb(self.rdb, expected=4)
        self.assertTrue(ok)
        self.assertEqual(detail["objects"], 4)
        missing = os.path.join(self.tmp, "нет.rdb")
        ok, detail = pipeline_state.verify_saved_rdb(missing)
        self.assertFalse(ok)
        self.assertTrue(detail["error"].startswith("RDB_CORRUPTED"))
        empty = os.path.join(self.tmp, "empty.rdb")
        open(empty, "w").close()
        ok, detail = pipeline_state.verify_saved_rdb(empty)
        self.assertFalse(ok)
        self.assertIn("нулевой", detail["error"])
        broken = os.path.join(self.tmp, "broken.rdb")
        with open(broken, "w", encoding="utf-8") as handle:
            handle.write("}{")
        ok, detail = pipeline_state.verify_saved_rdb(broken)
        self.assertFalse(ok)
        self.assertTrue(detail["error"].startswith("RDB_CORRUPTED"))
        ok, detail = pipeline_state.verify_saved_rdb(self.rdb, expected=99)
        self.assertFalse(ok)
        self.assertTrue(detail["error"].startswith("SAVE_VERIFY_FAILED"))
        ok, _ = pipeline_state.verify_saved_rdb(self.rdb, minimum=5)
        self.assertFalse(ok)
        ok, _ = pipeline_state.verify_saved_rdb(self.rdb, minimum=2)
        self.assertTrue(ok)

    def _state(self, **over):
        state = pipeline_state.make_state(
            rom=os.path.basename(self.rom), rdb=os.path.basename(self.rdb),
            rom_sha256=pipeline_state.file_sha256(self.rom),
            rdb_sha256=pipeline_state.file_sha256(self.rdb),
            completed_stages=["probe"])
        state.update(over)
        return state

    def test_validate_resume_ok(self):
        completed = pipeline_state.validate_resume(
            self._state(), self.rom, self.rdb)
        self.assertEqual(completed, ["probe"])

    def test_validate_resume_checkpoint_missing(self):
        with self.assertRaises(pipeline_state.PipelineFatal) as caught:
            pipeline_state.validate_resume(None, self.rom, self.rdb)
        self.assertEqual(caught.exception.code, "CHECKPOINT_MISSING")

    def test_validate_resume_rom_mismatch(self):
        state = self._state()
        state["rom_sha256"] = "0" * 64
        with self.assertRaises(pipeline_state.PipelineFatal) as caught:
            pipeline_state.validate_resume(state, self.rom, self.rdb)
        self.assertEqual(caught.exception.code, "ROM_MISMATCH")
        # ROM-файл вообще исчез — тоже ROM_MISMATCH.
        with self.assertRaises(pipeline_state.PipelineFatal) as caught:
            pipeline_state.validate_resume(
                self._state(), os.path.join(self.tmp, "нет.rom"), self.rdb)
        self.assertEqual(caught.exception.code, "ROM_MISMATCH")

    def test_validate_resume_rdb_missing_and_changed(self):
        state = self._state()
        os.remove(self.rdb)
        with self.assertRaises(pipeline_state.PipelineFatal) as caught:
            pipeline_state.validate_resume(state, self.rom, self.rdb)
        self.assertEqual(caught.exception.code, "RDB_MISSING")
        write_rdb(self.rdb, objects=9)          # изменённый вне pipeline
        with self.assertRaises(pipeline_state.PipelineFatal) as caught:
            pipeline_state.validate_resume(state, self.rom, self.rdb)
        self.assertEqual(caught.exception.code, "RDB_CHANGED_OUTSIDE_PIPELINE")

    def test_validate_resume_order_rom_before_rdb(self):
        # ROM и RDB оба изменены — первым обязан сработать ROM_MISMATCH (§23).
        write_rdb(self.rdb, objects=9)
        state = self._state()
        state["rom_sha256"] = "0" * 64
        with self.assertRaises(pipeline_state.PipelineFatal) as caught:
            pipeline_state.validate_resume(state, self.rom, self.rdb)
        self.assertEqual(caught.exception.code, "ROM_MISMATCH")

    def test_validate_resume_capabilities(self):
        caps = CapabilityProfile({name: {} for name in CORE_REQUIRED
                                  if name != "debug_save_rdb"})
        with self.assertRaises(pipeline_state.PipelineFatal) as caught:
            pipeline_state.validate_resume(
                self._state(), self.rom, self.rdb, caps=caps,
                required=("debug_save_rdb",))
        self.assertEqual(caught.exception.code, "REQUIRED_CAPABILITY_MISSING")

    def test_checkpoint_active_hook(self):
        self.assertIsNone(pipeline_state.checkpoint_active())  # no-op без set
        state = pipeline_state.make_state(
            rom=os.path.basename(self.rom), rdb=os.path.basename(self.rdb),
            rdb_path=self.rdb)
        pipeline_state.set_active(self.state_path, state)
        write_rdb(self.rdb, objects=6)
        path = pipeline_state.checkpoint_active(current_stage="seed_rdb",
                                                current_batch=2)
        self.assertEqual(path, self.state_path)
        got = pipeline_state.read_checkpoint(self.state_path)
        self.assertEqual(got["rdb_sha256"], pipeline_state.file_sha256(self.rdb))
        self.assertEqual(got["rdb_objects"], 6)
        self.assertEqual(got["current_stage"], "seed_rdb")
        self.assertEqual(got["current_batch"], 2)
        pipeline_state.clear_active()
        self.assertIsNone(pipeline_state.checkpoint_active())

    def test_remove_checkpoint_keeps_rdb(self):
        pipeline_state.write_checkpoint(
            self.state_path, pipeline_state.make_state(rom="a", rdb="b"))
        with open(self.state_path + ".tmp", "w") as handle:
            handle.write("x")
        self.assertTrue(pipeline_state.remove_checkpoint(self.state_path))
        self.assertFalse(os.path.exists(self.state_path))
        self.assertFalse(os.path.exists(self.state_path + ".tmp"))
        self.assertTrue(os.path.isfile(self.rdb))       # RDB не тронут
        self.assertFalse(pipeline_state.remove_checkpoint(self.state_path))


# ---------------------------------------------------------------------------
# DAG: toposort / expand_only / режимные флаги (ТЗ §14—§22)
# ---------------------------------------------------------------------------

class PipelineDagTest(unittest.TestCase):
    def test_toposort_deps_first(self):
        steps = pipeline.toposort(pipeline.build_steps(make_ctx()))
        order = [step.key for step in steps]
        def before(a, b):
            self.assertLess(order.index(a), order.index(b),
                            "%s обязан идти раньше %s" % (a, b))
        before("probe", "coverage")
        before("probe", "disassembly")
        before("coverage", "seed_rdb")
        before("disassembly", "seed_rdb")
        before("seed_rdb", "rdb_lint")
        before("seed_rdb", "io_signature")
        before("strings_scan", "vram_credits")
        before("rdb_lint", "export_asm")
        before("syntax_check", "roundtrip_verify")
        before("probe", "memory_diff")

    def test_music_and_glyph_optional(self):
        plain = [s.key for s in pipeline.build_steps(make_ctx())]
        self.assertNotIn("music2midi", plain)
        self.assertNotIn("glyph_scan", plain)
        with_music = [s.key for s in pipeline.build_steps(
            make_ctx(spec="/tmp/music_spec.json"))]
        self.assertIn("music2midi", with_music)
        with_glyph = [s.key for s in pipeline.build_steps(
            make_ctx(glyph_address="0x2706"))]
        self.assertIn("glyph_scan", with_glyph)

    def test_annotations_wires_export(self):
        ctx = make_ctx(annotations="/tmp/annotations.json")
        steps = pipeline.toposort(pipeline.build_steps(ctx))
        order = [step.key for step in steps]
        self.assertIn("apply_annotations", order)
        self.assertLess(order.index("seed_rdb"),
                        order.index("apply_annotations"))
        self.assertLess(order.index("apply_annotations"),
                        order.index("export_asm"))
        by_key = {step.key: step for step in steps}
        self.assertTrue(by_key["apply_annotations"].mutates_rdb)
        self.assertIn("apply_annotations", by_key["export_asm"].depends_on)

    def test_mutators_flagged(self):
        by_key = {step.key: step for step in pipeline.build_steps(make_ctx())}
        self.assertTrue(by_key["seed_rdb"].mutates_rdb)
        self.assertFalse(by_key["rdb_lint"].mutates_rdb)
        self.assertFalse(by_key["probe"].mutates_rdb)

    def test_expand_only_adds_ancestors(self):
        steps = pipeline.build_steps(make_ctx())
        picked = pipeline.expand_only(steps, ["rdb_lint"])
        keys = {step.key for step in picked}
        self.assertIn("rdb_lint", keys)
        self.assertIn("seed_rdb", keys)          # предок подтянут (§22)
        self.assertIn("probe", keys)
        self.assertNotIn("music2midi", keys)
        with self.assertRaises(SystemExit):
            pipeline.expand_only(steps, ["no_such_stage"])

    def test_effective_argv_mode_flags(self):
        step = pipeline.Step("seed_rdb", ["--rom", "{rom}"],
                             mutates_rdb=True)
        ctx = make_ctx()
        argv = step.effective_argv(ctx)
        self.assertIn("--apply", argv)           # дефолт = apply (§25)
        self.assertIn("--save-every", argv)
        self.assertEqual(argv[argv.index("--save-every") + 1], "10")
        self.assertNotIn("--dry-run", argv)
        ctx.dry_run = True
        argv = step.effective_argv(ctx)
        self.assertIn("--dry-run", argv)
        self.assertNotIn("--apply", argv)
        # read-only stage не получает режимных флагов вообще
        ro = pipeline.Step("rdb_lint", ["--rdb", "{rdb}"])
        self.assertNotIn("--apply", ro.effective_argv(make_ctx()))


class StageArgsTest(unittest.TestCase):
    """stage_args из конфига: «поглубже» без разрастания CLI."""

    def test_replace_existing_value(self):
        argv = ["--max-depth", "6", "--rom", "x.rom"]
        pipeline.apply_stage_args(argv, {"--max-depth": "12"})
        self.assertEqual(argv.count("--max-depth"), 1)
        self.assertEqual(argv[argv.index("--max-depth") + 1], "12")

    def test_append_missing_value(self):
        argv = ["--rom", "x.rom"]
        pipeline.apply_stage_args(argv, {"--max-instructions": "100000"})
        self.assertEqual(argv[-2:], ["--max-instructions", "100000"])

    def test_equals_form_replaced(self):
        argv = ["--min-len=4"]
        pipeline.apply_stage_args(argv, {"--min-len": "3"})
        self.assertEqual(argv, ["--min-len=3"])

    def test_bool_flag_added_once(self):
        argv = ["--runtime"]
        pipeline.apply_stage_args(argv, {"--runtime": None, "--force": True})
        self.assertEqual(argv.count("--runtime"), 1)
        self.assertIn("--force", argv)

    def test_list_value_repeats_flag(self):
        # --key это action="append": список должен дать флаг по разу на элемент
        argv = ["--rom", "x.rom"]
        pipeline.apply_stage_args(argv, {"--key": ["0.5:SPACE", "1:LEFT"]})
        self.assertEqual(argv,
                         ["--rom", "x.rom", "--key", "0.5:SPACE",
                          "--key", "1:LEFT"])

    def test_effective_argv_wires_stage_args(self):
        step = pipeline.Step("seed_rdb",
                             ["--rom", "{rom}", "--max-depth", "6"],
                             mutates_rdb=True)
        ctx = make_ctx(stage_args={"seed_rdb": {"--max-depth": "12"}})
        argv = step.effective_argv(ctx)
        self.assertEqual(argv[argv.index("--max-depth") + 1], "12")
        self.assertEqual(argv.count("--max-depth"), 1)
        self.assertIn("--apply", argv)           # режимные флаги на месте
        # чужая стадия не получает ничего (--json добавляет сам Step.argv)
        self.assertEqual(step.effective_argv(make_ctx()),
                         ["--json", "--rom", "/tmp/fake.rom", "--max-depth", "6",
                          "--apply", "--save-every", "10"])


# ---------------------------------------------------------------------------
# Прогон main() на FakeSession: basic / safety / persistence / resume / dry-run
# ---------------------------------------------------------------------------

class PipelineRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.rom = os.path.join(self.tmp, "fake.rom")
        self.rdb = os.path.join(self.tmp, "fake.rdb")
        write_rom(self.rom)
        write_rdb(self.rdb, objects=3)
        self.results = os.path.join(self.tmp, "results")
        self.session = FakeSession(rdb_path=self.rdb, objects=3)
        self.session.dump_rdb()
        self.invoked = []
        self.argvs = {}
        self.behaviors = {}
        self.share_entries = 0
        # pipeline.share и module_main подменяем на всё время теста
        patch_share = unittest.mock.patch.object(pipeline, "share",
                                                 self._fake_share)
        patch_main = unittest.mock.patch.object(pipeline, "module_main",
                                                self._fake_module_main)
        patch_backoff = unittest.mock.patch.object(pipeline, "RETRY_BACKOFF",
                                                   (0.0, 0.0, 0.0))
        patch_share.start()
        patch_main.start()
        patch_backoff.start()
        self.addCleanup(unittest.mock.patch.stopall)
        pipeline_state.clear_active()

    def tearDown(self):
        pipeline_state.clear_active()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- каркас --------------------------------------------------------------
    @contextlib.contextmanager
    def _fake_share(self, rom=None, org=0, **kwargs):
        self.share_entries += 1
        self.session.close = lambda: None
        yield self.session

    def _fake_module_main(self, module):
        def run(argv):
            self.invoked.append(module)
            self.argvs[module] = list(argv)
            behavior = self.behaviors.get(module) or _default_behavior
            payload, rc = behavior(list(argv), self.session, module)
            print(json.dumps(payload, ensure_ascii=False))
            return rc
        return run

    def _run(self, extra_argv):
        argv = ["--rom", self.rom, "--rdb", self.rdb,
                "--results", self.results, "--json"] + list(extra_argv)
        out, err = io.StringIO(), io.StringIO()
        saved = (sys.stdout, sys.stderr)
        sys.stdout, sys.stderr = out, err
        try:
            rc = pipeline.main(argv)
        finally:
            sys.stdout, sys.stderr = saved
        text = out.getvalue()
        self.last_out = text
        summary = json.loads(text[text.index("{"):]) if "{" in text else {}
        return rc, summary, err.getvalue()

    def _state(self):
        return pipeline_state.read_checkpoint(
            os.path.join(self.results, pipeline_state.STATE_FILENAME))

    def _set_rdb_objects(self, count):
        """Имитация реального посева: серверные счётчики и файл согласованы."""
        def behavior(argv, session, module):
            if "--apply" in argv:
                session.objects += count
                session.dump_rdb()
                return ({"module": module, "status": "OK",
                         "functions_added": count, "labels_added": 0,
                         "links_added": 0, "batches": 1, "saves": 1}, 0)
            return ({"module": module, "status": "CANDIDATE"}, 0)
        self.behaviors["seed_rdb"] = behavior

    # -- Basic (ТЗ §14—§18, §21—§22) ----------------------------------------
    def test_basic_apply_run(self):
        rc, summary, err = self._run(["--only", "probe,coverage,seed_rdb"])
        self.assertEqual(rc, 0)
        # seed_rdb тянет предка disassembly (§22: deps подтягиваются сами)
        self.assertEqual(self.invoked,
                         ["probe", "coverage", "disassembly", "seed_rdb"])
        self.assertEqual(summary["mode"], "apply")
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["status"], "SUCCESS")
        for key in ("probe", "coverage", "seed_rdb"):
            self.assertTrue(os.path.isfile(
                os.path.join(self.results, "%s.json" % key)))
        state = self._state()
        self.assertEqual(sorted(state["completed_stages"]),
                         ["coverage", "disassembly", "probe", "seed_rdb"])
        self.assertEqual(state["last_completed_stage"], "seed_rdb")
        self.assertIsNone(state["current_stage"])
        # отчёты прогона (§36—§41) идут рядом с results
        with open(os.path.join(self.results, "pipeline.md"),
                  encoding="utf-8") as handle:
            md = handle.read()
        self.assertIn("## Stages", md)
        self.assertIn("| seed_rdb | SUCCESS", md)
        self.assertIn("apply (мутации разрешены)", md)
        with open(os.path.join(self.results, "pipeline.json"),
                  encoding="utf-8") as handle:
            doc = json.load(handle)
        self.assertEqual(doc["version"], 1)
        self.assertEqual(doc["status"], "SUCCESS")
        self.assertEqual(doc["stages"]["seed_rdb"]["status"], "SUCCESS")
        self.assertTrue(doc["checkpoint_log"])

    def test_cli_conflict_apply_dry_run(self):
        with self.assertRaises(SystemExit):
            self._run(["--apply", "--dry-run"])

    def test_blocked_on_failed_parent(self):
        self.behaviors["seed_rdb"] = _failed_behavior
        rc, summary, err = self._run(["--only", "probe,coverage,seed_rdb,"
                                                  "rdb_lint"])
        self.assertEqual(rc, 1)
        self.assertIn("→ rdb_lint BLOCKED", err)
        self.assertNotIn("rdb_lint", self.invoked)   # потомок не запускался (§22)
        self.assertEqual(summary["status"], "FAILED")
        # FAILED без исключения — не retry: ровно один запуск mutator-стейджа
        self.assertEqual(self.invoked.count("seed_rdb"), 1)

    def test_from_until_slice(self):
        rc, summary, err = self._run(["--from", "coverage",
                                      "--until", "seed_rdb"])
        self.assertEqual(rc, 0)
        self.assertNotIn("probe", self.invoked)
        self.assertEqual(self.invoked, ["coverage", "disassembly", "seed_rdb"])

    def test_unknown_from_stage(self):
        with self.assertRaises(SystemExit):
            self._run(["--from", "nope"])

    def test_list_no_session(self):
        rc, _, _ = self._run(["--list"])
        self.assertEqual(rc, 0)
        self.assertIn("seed_rdb", self.last_out)      # stages в stdout
        self.assertEqual(self.share_entries, 0)        # сервер не поднимался

    # -- Persistence (ТЗ §3—§8) ----------------------------------------------
    def test_persist_cycle_after_mutator(self):
        self._set_rdb_objects(5)
        rc, summary, _ = self._run(["--only", "probe,coverage,seed_rdb"])
        self.assertEqual(rc, 0)
        saves = [t for t, _ in self.session.calls if t == "debug_save_rdb"]
        self.assertEqual(len(saves), 1)              # ровно один save на stage
        state = self._state()
        self.assertEqual(state["rdb_objects"], 8)    # 3 base + 5 посев
        self.assertEqual(state["rdb_sha256"], pipeline_state.file_sha256(self.rdb))
        # seed получил --apply и --save-every из политики (дефолт 10)
        self.assertIn("--apply", self.argvs["seed_rdb"])
        self.assertIn("10", self.argvs["seed_rdb"])

    def test_verify_catches_broken_save(self):
        self._set_rdb_objects(2)
        original = self.session.dump_rdb
        self.session.save_broken = True              # save пишет мусор на диск
        rc, summary, err = self._run(["--only", "probe,coverage,seed_rdb"])
        self.assertEqual(rc, 1)
        self.assertIn("STOP RDB_CORRUPTED", err)
        state = self._state()
        self.assertNotIn("seed_rdb", state["completed_stages"])
        self.session.save_broken = False
        original()

    def test_readonly_stage_gets_checkpoint(self):
        rc, _, _ = self._run(["--only", "probe"])
        self.assertEqual(rc, 0)
        self.assertEqual([t for t, _ in self.session.calls
                          if t == "debug_save_rdb"], [])
        state = self._state()
        self.assertEqual(state["completed_stages"], ["probe"])

    # -- Resume (ТЗ §9—§11, §23) ---------------------------------------------
    def test_resume_skips_completed(self):
        self._run(["--only", "probe,coverage"])
        self.invoked = []
        rc, summary, err = self._run(["--only", "probe,coverage,seed_rdb",
                                      "--resume"])
        self.assertEqual(rc, 0)
        # seed_rdb тянет незнакомый предок disassembly — он идёт; подтверждённые
        # probe/coverage пропущены (§9: resume догоняет только недетое)
        self.assertEqual(self.invoked, ["disassembly", "seed_rdb"])
        self.assertEqual(summary["skipped"], 2)
        self.assertIn("уже готов, resume", err)

    def test_resume_distrusts_missing_artifact(self):
        self._run(["--only", "probe,coverage"])
        os.remove(os.path.join(self.results, "coverage.json"))
        self.invoked = []
        rc, _, _ = self._run(["--only", "probe,coverage", "--resume"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.invoked, ["coverage"])   # без артефакта — повтор (§9)

    def test_resume_interrupted_stage_restarts(self):
        # Авария посреди seed_rdb: checkpoint подтверждает probe, текущий
        # stage seed_rdb с батчем — при resume он перезапускается с нуля.
        self._run(["--only", "probe"])
        state = self._state()
        state.update({"completed_stages": ["probe"], "current_stage": "seed_rdb",
                      "current_batch": 2, "processed_objects": 20,
                      "pending_objects": 5, "status": "running"})
        pipeline_state.write_checkpoint(
            os.path.join(self.results, pipeline_state.STATE_FILENAME), state)
        self.invoked = []
        rc, summary, _ = self._run(["--only", "probe", "--resume"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.invoked, [])             # probe подтверждён
        state = self._state()
        self.assertIsNone(state["current_stage"])
        self.assertEqual(state["last_completed_stage"], "probe")

    def test_clean_removes_only_checkpoint(self):
        self._run(["--only", "probe"])
        rdb_before = pipeline_state.file_sha256(self.rdb)
        # --clean вместе с --resume: checkpoint удалён — возобновлять нечего,
        # это CHECKPOINT_MISSING (fatal), а не тихий старт заново.
        rc, _, err = self._run(["--only", "probe", "--clean", "--resume"])
        self.assertEqual(rc, 1)
        self.assertIn("STOP CHECKPOINT_MISSING", err)
        self.assertEqual(pipeline_state.file_sha256(self.rdb), rdb_before)
        self.assertFalse(os.path.exists(
            os.path.join(self.results, pipeline_state.STATE_FILENAME)))

    # -- Safety (ТЗ §23, §30) -------------------------------------------------
    def _make_resume_state(self):
        self._run(["--only", "probe"])
        # «внешний мир»: после первого прогона всё, что заметит второй
        # прогон, должно относиться только к нему.
        self.share_entries = 0
        self.invoked = []
        del self.session.calls[:]
        return os.path.join(self.results, pipeline_state.STATE_FILENAME)

    def test_safety_rom_mismatch_before_mcp(self):
        path = self._make_resume_state()
        self.invoked = []
        state = pipeline_state.read_checkpoint(path)
        state["rom_sha256"] = "0" * 64
        pipeline_state.write_checkpoint(path, state)
        rc, _, err = self._run(["--only", "probe", "--resume"])
        self.assertEqual(rc, 1)
        self.assertIn("STOP ROM_MISMATCH", err)
        self.assertEqual(self.invoked, [])
        self.assertEqual(self.share_entries, 0)        # ни одного MCP-вызова

    def test_safety_rdb_changed_outside_pipeline(self):
        path = self._make_resume_state()
        write_rdb(self.rdb, objects=12)                # правка вне pipeline
        rc, _, err = self._run(["--only", "probe", "--resume"])
        self.assertEqual(rc, 1)
        self.assertIn("STOP RDB_CHANGED_OUTSIDE_PIPELINE", err)
        self.assertEqual(self.session.mutating_calls(), [])
        self.assertEqual(self.share_entries, 0)        # стоп до любого MCP-сеанса

    def test_safety_checkpoint_corrupted(self):
        path = self._make_resume_state()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{{{битый")
        rc, _, err = self._run(["--only", "probe", "--resume"])
        self.assertEqual(rc, 1)
        self.assertIn("STOP CHECKPOINT_CORRUPTED", err)
        self.assertEqual(self.share_entries, 0)

    def test_safety_missing_capability(self):
        self.session.tools.pop("debug_save_rdb")
        rc, _, err = self._run(["--only", "probe"])
        self.assertEqual(rc, 1)
        self.assertIn("STOP REQUIRED_CAPABILITY_MISSING", err)
        self.assertEqual(self.invoked, [])

    def test_retry_recoverable_then_success(self):
        attempts = {"n": 0}
        def flaky(argv, session, module):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RuntimeError("IMCP_TIMEOUT: обрыв")   # STEP_EXCEPTION
            return ({"module": module, "status": "OK"}, 0)
        self.behaviors["probe"] = flaky
        rc, summary, _ = self._run(["--only", "probe"])
        self.assertEqual(rc, 0)
        self.assertEqual(attempts["n"], 2)
        self.assertEqual(summary["status"], "SUCCESS")

    # -- Dry-run (ТЗ §24—§25) --------------------------------------------------
    def test_dry_run_strict_readonly(self):
        rdb_before = pipeline_state.file_sha256(self.rdb)
        rc, summary, _ = self._run(["--dry-run", "--only",
                                    "probe,coverage,seed_rdb"])
        self.assertEqual(rc, 0)
        self.assertEqual(summary["mode"], "dry-run")
        self.assertIn("--dry-run", self.argvs["seed_rdb"])
        self.assertNotIn("--apply", self.argvs["seed_rdb"])
        self.assertEqual(self.session.mutating_calls(), [])
        self.assertEqual(pipeline_state.file_sha256(self.rdb), rdb_before)
        self.assertTrue(self._state()["dry_run"])

    def test_dry_run_guard_stops_runaway_module(self):
        def runaway(argv, session, module):
            session.call("debug_add_rdb_object", {"address": 0x150})
            return ({"module": module, "status": "OK"}, 0)
        self.behaviors["seed_rdb"] = runaway
        rdb_before = pipeline_state.file_sha256(self.rdb)
        rc, summary, err = self._run(["--dry-run", "--only", "probe,seed_rdb"])
        self.assertEqual(rc, 1)
        self.assertIn("STOP DRY_RUN_VIOLATION", err)
        self.assertIn("DRY_RUN_VIOLATION", summary["fatal"])
        self.assertEqual(pipeline_state.file_sha256(self.rdb), rdb_before)

    def test_dry_run_survives_swallowed_violation(self):
        # Худший случай: модуль проглотил исключение guard-а в свой except —
        # pipeline обязан увидеть отметку на сеансе и всё равно остановиться.
        def swallowing(argv, session, module):
            try:
                session.call("debug_save_rdb")
            except Exception:
                pass
            return ({"module": module, "status": "CANDIDATE"}, 0)
        self.behaviors["seed_rdb"] = swallowing
        rc, _, err = self._run(["--dry-run", "--only", "probe,seed_rdb"])
        self.assertEqual(rc, 1)
        self.assertIn("STOP DRY_RUN_VIOLATION", err)

    # -- Конфиг (ТЗ §46—§48) ---------------------------------------------------
    def test_config_limits_stages_and_persistence(self):
        cfg_path = os.path.join(self.tmp, "run.json")
        with open(cfg_path, "w", encoding="utf-8") as handle:
            json.dump({"stages": ["probe", "coverage"],
                       "persistence": {"max_unsaved_objects": 4}}, handle)
        rc, _, _ = self._run(["--config", cfg_path])
        self.assertEqual(rc, 0)
        self.assertEqual(sorted(self.invoked), ["coverage", "probe"])
        # --only stage, отсечённого конфигом, — ошибка CLI, а не тихий прогон
        with self.assertRaises(SystemExit):
            self._run(["--config", cfg_path, "--only", "seed_rdb"])

    def test_config_bad_json_exits(self):
        cfg_path = os.path.join(self.tmp, "bad.json")
        with open(cfg_path, "w", encoding="utf-8") as handle:
            handle.write("не json")
        with self.assertRaises(SystemExit):
            self._run(["--config", cfg_path])


def _default_behavior(argv, session, module):
    return ({"module": module, "status": "OK"}, 0)


def _failed_behavior(argv, session, module):
    return ({"module": module, "status": "FAILED",
             "error": "посев не сошёлся"}, 1)


# ---------------------------------------------------------------------------
# apply_annotations: валидация, применение, идемпотентность (ТЗ §28—§29)
# ---------------------------------------------------------------------------

class FakeWriter(object):
    """RdbWriter-контракт в памяти: ensure/exists/alias/link/save."""

    def __init__(self):
        self.records = {}
        self.saves = 0
        self.dry_run = False

    def ensure_object(self, address, name, type, size=None, comment=None,
                      properties=None):
        created = address not in self.records
        rec = self.records.setdefault(address, {"links": [], "aliases": []})
        rec.update({"name": name, "type": type})
        if size is not None:
            rec["size"] = size
        if comment is not None:
            rec["comment"] = comment
        return {"created": created}

    def exists(self, address):
        rec = self.records.get(address)
        if not rec:
            return {}
        return {"address": address, "name": rec["name"],
                "links": list(rec["links"])}

    def add_alias(self, address, alias):
        rec = self.records[address]
        if alias in rec["aliases"]:
            return {"added": False}
        rec["aliases"].append(alias)
        return {"added": True}

    def add_link(self, source, target):
        rec = self.records[source]
        if target not in rec["links"]:
            rec["links"].append(target)
        return {}

    def save(self):
        self.saves += 1


GOOD_FILE = {"objects": [
    {"address": "0x0120", "name": "data_font", "type": "data", "size": 256,
     "comment": "шрифт", "aliases": ["main_font"],
     "links": [{"to": "0x0110", "kind": "points_to"}]},
    {"address": "0x0110", "name": "func_entry_helper", "type": "function"},
]}


class AnnotationsTest(unittest.TestCase):
    def test_validate_normalizes_and_sorts(self):
        objects, errors = ann.validate_annotations(GOOD_FILE, 0x0100, 0x39FF)
        self.assertEqual(errors, [])
        self.assertEqual([o["address"] for o in objects], [0x0110, 0x0120])
        self.assertEqual(objects[1]["links"], [(0x0110, "points_to")])
        self.assertEqual(objects[1]["aliases"], ["main_font"])

    def test_validate_rejects_everything_before_apply(self):
        bad = {"objects": [
            {"address": "0x9FFF", "name": "data_far", "type": "data"},      # вне ROM
            {"address": "0x0130", "name": "func_ok", "type": "quantum"},     # тип
            {"address": "0x0140", "name": "данные", "type": "data"},         # имя
            {"address": "0x0150", "name": "data_self", "type": "data",
             "links": [{"to": "0x0150"}]},                                   # self-link
            {"address": "0x0110", "name": "data_dup", "type": "data"},       # дубль
        ]}
        objects, errors = ann.validate_annotations(bad, 0x0100, 0x01FF)
        self.assertEqual(objects, [])                  # ни одного применения
        self.assertGreaterEqual(len(errors), 4)

    def test_validate_not_a_dict(self):
        objects, errors = ann.validate_annotations({"objects": 5}, None, None)
        self.assertEqual(objects, [])
        self.assertTrue(errors)

    def test_apply_idempotent(self):
        writer = FakeWriter()
        objects, errors = ann.validate_annotations(GOOD_FILE, 0x0100, 0x39FF)
        first = ann.apply_annotations(writer, objects)
        self.assertEqual(first["objects_added"], 2)
        self.assertEqual(first["links_added"], 1)
        self.assertEqual(first["aliases_added"], 1)
        second = ann.apply_annotations(writer, objects)
        self.assertEqual(second["objects_added"], 0)   # без дублей (§12)
        self.assertEqual(second["objects_updated"], 2)
        self.assertEqual(second["links_added"], 0)
        self.assertEqual(second["aliases_added"], 0)

    def test_apply_feeds_batch_saver(self):
        writer = FakeWriter()
        saver = BatchSaver(writer, every=2)
        objects, _ = ann.validate_annotations(GOOD_FILE, 0x0100, 0x39FF)
        ann.apply_annotations(writer, objects, saver=saver)
        # 4 изменения (2 объекта + alias + link) при every=2 → минимум 2 save
        self.assertGreaterEqual(saver.batches, 2)
        self.assertGreaterEqual(writer.saves, 2)


# ---------------------------------------------------------------------------
# Seed-хелперы pipeline-обвязки
# ---------------------------------------------------------------------------

class StageResultTest(unittest.TestCase):
    def test_partial_is_ok_but_failed_is_not(self):
        self.assertTrue(pipeline.StageResult(pipeline.PARTIAL).ok)
        self.assertTrue(pipeline.StageResult(pipeline.SKIPPED).ok)
        self.assertFalse(pipeline.StageResult(pipeline.FAILED).ok)
        self.assertFalse(pipeline.StageResult(pipeline.BLOCKED).ok)

    def test_collect_counts_per_module(self):
        counts = pipeline._collect_counts(
            {"functions_added": 3, "labels_added": 2, "links_added": 7},
            "seed_rdb")
        self.assertEqual(counts["objects_added"], 5)
        self.assertEqual(counts["links_added"], 7)
        self.assertTrue(counts["changed"])
        counts = pipeline._collect_counts(
            {"objects_added": 0, "objects_updated": 4, "links_added": 0},
            "apply_annotations")
        self.assertEqual(counts["objects_updated"], 4)
        self.assertTrue(counts["changed"])   # update — тоже изменение RDB
        counts = pipeline._collect_counts({"status": "CANDIDATE"},
                                          "apply_annotations")
        self.assertFalse(counts["changed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
