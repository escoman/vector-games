#!/usr/bin/env python3
"""Интеграционные тесты пакета `analyze` на реальных ROM (ТЗ §32, §35).

Два уровня:

1. `ModuleIntegrationTest` — несколько модулей на `putup.rom` и `TESTAY.ROM`
   внутри ОДНОГО общего MCP-сеанса (проверяет §4 и контракт конверта §29/§30:
   статус present, `mcp_calls` целое, кандидат не повышен до факта §34).
   Требует только сервер `v06c-mcp`.

2. `PipelineIntegrationTest` и родственный E2E-классы — полные прогоны
   `pipeline.py` на putup (§35: «putup.rom проходит полный pipeline»),
   kill→resume (§56), dry-run неизменность (§24), внешний правкой RDB,
   TESTAY и riseout (условно). Тяжёлые (~десятки секунд — минуты, зовут
   z80asm, v06c-asm-export и реальный посев), поэтому включаются по
   `V06C_ANALYZE_E2E=1`.

Железное правило E2E (решение пользователя): прогоны с мутациями идут
ТОЛЬКО по временным копиям фикстур (`B.copy_fixture`); tracked
putup.rdb/TESTAY.rdb/clrs.rdb обязаны остаться нетронутыми — финальная
проверка `B.git_clean("roms/")`.

Пропуск, а не падение: если сервер или ROM недоступны, тесты скипаются —
набор юнит-тестов остаётся полноценным сигналом для окружения без эмулятора.

Запуск:
    python3 utils/analyze/tests/test_integration.py
    V06C_ANALYZE_E2E=1 python3 utils/analyze/tests/test_integration.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap as B  # noqa: E402  (кладёт utils/ в sys.path и даёт пути)

from analyze import probe, rdb_lint, report_gen
from analyze import mcp_session


def _json_available():
    return os.access(B.MCP_SERVER, os.X_OK)


def _putup_ready():
    return _json_available() and os.path.isfile(B.PUTUP_ROM) and os.path.isfile(B.PUTUP_RDB)


def _testay_ready():
    return _json_available() and os.path.isfile(B.TESTAY_ROM)


def parse_stdout(text):
    """Вынуть JSON-конверт из stdout модуля (мусол-терпимо к префиксам)."""
    text = text.strip()
    if not text:
        raise AssertionError("модуль ничего не напечатал в stdout")
    try:
        return json.loads(text)
    except ValueError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])
    raise AssertionError("в stdout нет JSON-объекта: %r" % text[:120])


def captured_main(fn, argv):
    """Вызвать module.main(argv), вернув (код_выхода, распарсенный_конверт)."""
    buf = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(buf):
        try:
            code = fn(argv) or 0
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 0
    return code, parse_stdout(buf.getvalue())


def assert_envelope(testcase, result, module):
    """Общий контракт конверта (§29/§30) — переиспользуется обоими уровнями."""
    testcase.assertIsInstance(result, dict)
    testcase.assertEqual(result.get("module"), module)
    status = str(result.get("status") or "").upper()
    testcase.assertTrue(status, "%s обязан назвать статус (§34)" % module)
    known = set(report_gen.FACT_STATUSES + report_gen.CANDIDATE_STATUSES
                + report_gen.FAILED_STATUSES)
    testcase.assertIn(status, known, "неизвестный статус %r у %s" % (status, module))
    testcase.assertIsInstance(result.get("mcp_calls"), int)


@unittest.skipUnless(_putup_ready(), "нет сервера v06c-mcp или putup.rom")
class PutupModuleIntegrationTest(unittest.TestCase):
    """Несколько модулей на putup в одном сеансе — §4 и контракт конверта."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="v06c-int-putup-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_probe_and_rdb_lint_share_one_session(self):
        with mcp_session.share(rom=B.PUTUP_ROM, org=0x0100,
                               cache_dir=os.path.join(self.tmp, ".analyze")):
            self.assertIsNotNone(mcp_session.get_shared())   # §4: общий сеанс жив
            code, res = captured_main(probe.main, [
                "--rom", B.PUTUP_ROM, "--org", "0x0100",
                "--seconds", "1", "--json"])
            assert_envelope(self, res, "probe")
            self.assertIn(str(res["status"]).upper(), report_gen.FACT_STATUSES)
            self.assertGreaterEqual(res["mcp_calls"], 1)     # probe реально звал сервер

            # rdb_lint работает по файлам: 0 обращений к серверу, но статус есть
            code, rl = captured_main(rdb_lint.main, [
                "--rdb", B.PUTUP_RDB, "--rom", B.PUTUP_ROM, "--json"])
            assert_envelope(self, rl, "rdb_lint")
            self.assertEqual(rl["mcp_calls"], 0)

    def test_candidates_are_never_promoted_to_facts(self):
        # Линтер с находками (rc может быть 1) обязан остаться выводом/блокировкой,
        # а не фактом: classify() не кладёт CANDIDATE/MISMATCH в facts (§34).
        self.assertEqual(report_gen.classify({"status": "CANDIDATE"}), "candidates")
        self.assertEqual(report_gen.classify({"status": "MISMATCH"}), "blocked")


@unittest.skipUnless(_testay_ready(), "нет сервера v06c-mcp или TESTAY.ROM")
class TestayModuleIntegrationTest(unittest.TestCase):
    """testay — другой ROM (музыка, runtime-патч вектора): проверка переносимости."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="v06c-int-testay-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_probe_testay(self):
        code, res = captured_main(probe.main, [
            "--rom", B.TESTAY_ROM, "--org", "0x0100", "--seconds", "1", "--json"])
        assert_envelope(self, res, "probe")
        # Для testay probe может дать и CANDIDATE (винит векторный патч) — любой
        # валидный статус принимается; важно, что контракт соблюдён на втором ROM.


def _load_state(path):
    """Читаемый checkpoint или None (нет/битый — для поллинга вокруг kill)."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except ValueError:
        return None
    except (IOError, OSError):
        return None


def _rdb_addr_list(path):
    """Отпечаток RDB: отсортированные адреса объектов — сверка прогонов."""
    with io.open(path, encoding="utf-8") as fh:
        return sorted(str(o.get("address"))
                      for o in (json.load(fh).get("objects") or []))


def _lint_dup_counts(rdb, rom):
    """Счётчики находок duplicate_* из rdb_lint (проверка «без дублей» §56)."""
    _code, res = captured_main(rdb_lint.main,
                               ["--rdb", rdb, "--rom", rom, "--json"])
    by_code = (res.get("summary") or {}).get("by_code") or {}
    return dict((k, v) for k, v in by_code.items()
                if str(k).startswith("duplicate_"))


def _results_names(directory):
    return sorted(f for f in os.listdir(directory) if f.endswith(".json")
                  and f != "pipeline_state.json")


def _run_pipeline_inproc(pipeline_mod, argv):
    """pipeline.main в процессе → (rc, summary-dict, текст stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        rc = pipeline_mod.main(argv)
    try:
        summary = json.loads(out.getvalue())
    except ValueError:
        summary = {}
    return rc, summary, err.getvalue()


def _pipeline_cmd(rom, rdb, results, extra=()):
    """Командная строка pipeline как её вызывает run_pipeline.sh (подпроцесс)."""
    cmd = [sys.executable, "-m", "analyze.cli", "pipeline",
           "--rom", rom, "--results", results, "--json",
           "--only", "seed_rdb"]
    if rdb:
        cmd += ["--rdb", rdb]
    return cmd + list(extra)


_E2E = os.environ.get("V06C_ANALYZE_E2E") == "1"


@unittest.skipUnless(_E2E, "полный пайплайн (§35) идёт только при V06C_ANALYZE_E2E=1")
@unittest.skipUnless(_putup_ready(), "нет сервера v06c-mcp или putup.rom")
class PipelineIntegrationTest(unittest.TestCase):
    """§35: putup.rom проходит полный pipeline без отказов шагов.

    Прогон идёт в режиме apply (дефолт) и поэтому ТОЛЬКО по временной копии
    пары putup.rom/putup.rdb (решение пользователя): tracked-фикстура обязана
    остаться нетронутой — финальная проверка B.git_clean("roms/").
    """

    @classmethod
    def setUpClass(cls):
        from analyze import pipeline
        cls.pipeline = pipeline
        cls.tmp = tempfile.mkdtemp(prefix="v06c-int-e2e-")
        cls.rom, cls.rdb, cls.fixture_tmp = B.copy_fixture(
            B.PUTUP_ROM, B.PUTUP_RDB)
        cls.results = os.path.join(cls.tmp, "results")
        cls.export = os.path.join(cls.tmp, "export")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)
        shutil.rmtree(cls.fixture_tmp, True)

    def test_full_pipeline_putup(self):
        baseline = len(_rdb_addr_list(B.PUTUP_RDB))   # tracked-эталон (179)
        buf = io.StringIO()
        argv = ["--rom", self.rom, "--rdb", self.rdb,
                "--spec", B.PUTUP_SPEC, "--glyph-address", "0x2706",
                "--runtime", "--results", self.results, "--export", self.export,
                "--out", os.path.join(self.tmp, "Stage.md"), "--stage", "E2E",
                "--json"]
        with contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(buf):
            rc = self.pipeline.main(argv)
        self.assertEqual(rc, 0, "ни один шаг не должен упасть; stdout: %s"
                         % buf.getvalue()[:400])
        summary = json.loads(buf.getvalue())
        self.assertEqual(summary["failed"], 0)
        self.assertGreaterEqual(summary["succeeded"], 15)
        self.assertGreater(summary["total_mcp_calls"], 0)

        # статистика §30
        self.assertTrue(os.path.isfile(summary["statistics"]))
        with io.open(summary["statistics"], encoding="utf-8") as fh:
            stats = json.load(fh)
        self.assertGreater(stats["total_mcp_calls"], 0)

        # отчёт §29: все обязательные разделы на месте
        with io.open(summary["report"], encoding="utf-8") as fh:
            text = fh.read()
        for header in ("## Goal", "## ROM", "## Method", "## Findings",
                       "## Verified Facts", "## Inferences", "## Hypotheses",
                       "## Unknowns", "## Limitations",
                       "## Recommended Next Steps"):
            self.assertIn(header, text)

        # ключевые проверки: побайтовое кольцо и VRAM-кредиты — факты
        with io.open(os.path.join(self.results, "roundtrip_verify.json"),
                     encoding="utf-8") as fh:
            rt = json.load(fh)
        self.assertIn(str(rt.get("status")).upper(), report_gen.FACT_STATUSES)
        with io.open(os.path.join(self.results, "vram_credits.json"),
                     encoding="utf-8") as fh:
            vc = json.load(fh)
        self.assertEqual(str(vc.get("status")).upper(), "MATCHED")

        # acceptance apply-прогона (ТЗ §4/§24, решение пользователя): seed_rdb
        # реально посеял объекты в КОПИЮ, checkpoint подтверждает финал.
        self.assertGreater(len(_rdb_addr_list(self.rdb)), baseline,
                           "seed_rdb в apply-режиме обязан добавить объекты")
        state_path = summary["checkpoint"]
        self.assertTrue(os.path.isfile(state_path))
        state = _load_state(state_path)
        self.assertIsNotNone(state, "checkpoint после полного прогона не читается")
        self.assertEqual(state["status"], "finished")
        self.assertIn("seed_rdb", state["completed_stages"])
        self.assertFalse(state["dry_run"])
        from analyze import pipeline_state
        self.assertEqual(state["rdb_sha256"],
                         pipeline_state.file_sha256(self.rdb),
                         "checkpoint.rdb_sha256 разошёлся с диском")
        # отчёты о прогоне (§36—§41)
        self.assertTrue(os.path.isfile(summary["pipeline_report"]))
        with io.open(summary["pipeline_json"], encoding="utf-8") as fh:
            preport = json.load(fh)
        self.assertEqual(preport["version"], 1)
        self.assertIn(str(preport["stages"]["seed_rdb"]["status"]),("SUCCESS", "PARTIAL"))
        # tracked-файлы не тронуты ни при каких обстоятельствах
        self.assertTrue(B.git_clean("roms/"),
                        "E2E-прогон изменил tracked-файлы в roms/")


@unittest.skipUnless(_E2E, "идёт только при V06C_ANALYZE_E2E=1")
@unittest.skipUnless(_putup_ready(), "нет сервера v06c-mcp или putup.rom")
class PipelineKillResumeE2ETest(unittest.TestCase):
    """§56 acceptance (обязательный): kill сразу после первого mutator-
    checkpoint, --resume доводит прогон до конца; результат совпадает с
    контрольным прогоном, дублей нет, tracked-дерево чисто.
    """

    @classmethod
    def setUpClass(cls):
        from analyze import pipeline
        cls.pipeline = pipeline
        cls.tmp = tempfile.mkdtemp(prefix="v06c-e2e-kill-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def _env(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = B.UTILS + os.pathsep + env.get("PYTHONPATH", "")
        return env

    def test_kill_after_first_batch_then_resume(self):
        from analyze import pipeline_state
        dir_a = os.path.join(self.tmp, "victim")
        os.makedirs(dir_a)
        rom_a, rdb_a, _ = B.copy_fixture(B.PUTUP_ROM, B.PUTUP_RDB,
                                         dest_dir=dir_a)
        results_a = os.path.join(dir_a, "results")
        state_a = os.path.join(results_a, "pipeline_state.json")
        proc = subprocess.Popen(_pipeline_cmd(rom_a, rdb_a, results_a),
                                cwd=B.REPO, env=self._env(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Ждём первого подтверждения батча внутри seed_rdb (хук --save-every).
        deadline = time.time() + 1200
        batched = False
        while time.time() < deadline:
            st = _load_state(state_a)
            if st and st.get("current_stage") == "seed_rdb" \
                    and (st.get("current_batch") or 0) >= 1:
                batched = True
                break
            if proc.poll() is not None:
                break
            time.sleep(0.5)
        proc.send_signal(signal.SIGKILL)
        proc.communicate()                       # освобождает пайпы, дожидается смерти
        self.assertTrue(batched,
                        "не дождались checkpoint первой батчи seed_rdb — "
                        "проверять kill не на чем")
        # Атомарность (§8): после kill файл либо старый, либо новый — корректный,
        # и он согласован с сохранённым на диске RDB.
        st = _load_state(state_a)
        self.assertIsNotNone(st, "checkpoint после kill не читается")
        self.assertEqual(st.get("rdb_sha256"),
                         pipeline_state.file_sha256(rdb_a),
                         "RDB на диске разошёлся с последним checkpoint")
        # --resume тем же подпроцессом — до нулевого кода выхода.
        resumed = subprocess.Popen(
            _pipeline_cmd(rom_a, rdb_a, results_a, ["--resume"]),
            cwd=B.REPO, env=self._env(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = resumed.communicate()
        self.assertEqual(resumed.returncode, 0,
                         "resume не довёл прогон: %s" % err.decode("utf-8", "replace")[-400:])
        summary = parse_stdout(out.decode("utf-8", "replace"))
        self.assertEqual(summary["failed"], 0)
        # Контроль: тот же --only seed_rdb с нуля на свежей копии (в процессе).
        dir_c = os.path.join(self.tmp, "control")
        os.makedirs(dir_c)
        rom_c, rdb_c, _ = B.copy_fixture(B.PUTUP_ROM, B.PUTUP_RDB,
                                         dest_dir=dir_c)
        results_c = os.path.join(dir_c, "results")
        rc, _summary_c, err_c = _run_pipeline_inproc(self.pipeline, [
            "--rom", rom_c, "--rdb", rdb_c, "--results", results_c,
            "--only", "seed_rdb", "--json"])
        self.assertEqual(rc, 0, "контрольный прогон упал: %s" % err_c[-400:])
        # Совпадение с контролем: RDB, набор артефактов.
        self.assertEqual(_rdb_addr_list(rdb_a), _rdb_addr_list(rdb_c),
                         "после resume RDB отличается от контрольного прогона")
        self.assertEqual(_results_names(results_a), _results_names(results_c),
                         "набор results/*.json разошёлся с контролем")
        # Дубли: resume не добавил ничего сверх исходной фикстуры.
        base = _lint_dup_counts(B.PUTUP_RDB, B.PUTUP_ROM)
        dups_a = _lint_dup_counts(rdb_a, rom_a)
        for code in ("duplicate_address", "duplicate_alias", "duplicate_link"):
            self.assertLessEqual(dups_a.get(code, 0), base.get(code, 0),
                                 "resume породил лишние %s" % code)
        self.assertTrue(B.git_clean("roms/"),
                        "kill/resume-прогон изменил tracked-файлы в roms/")


@unittest.skipUnless(_E2E, "идёт только при V06C_ANALYZE_E2E=1")
@unittest.skipUnless(_putup_ready(), "нет сервера v06c-mcp или putup.rom")
class PipelineDryRunE2ETest(unittest.TestCase):
    """§24: --dry-run на настоящем сервере не трогает RDB байт в байт."""

    @classmethod
    def setUpClass(cls):
        from analyze import pipeline
        cls.pipeline = pipeline
        cls.tmp = tempfile.mkdtemp(prefix="v06c-e2e-dry-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_dry_run_seed_leaves_rdb_intact(self):
        from analyze import pipeline_state
        rom, rdb, fixture = B.copy_fixture(B.PUTUP_ROM, B.PUTUP_RDB,
                                           dest_dir=self.tmp)
        results = os.path.join(self.tmp, "results")
        sha_before = pipeline_state.file_sha256(rdb)
        try:
            rc, summary, err = _run_pipeline_inproc(self.pipeline, [
                "--rom", rom, "--rdb", rdb, "--results", results,
                "--only", "seed_rdb", "--dry-run", "--json"])
            self.assertEqual(rc, 0, "dry-run упал: %s" % err[-400:])
            self.assertEqual(summary["failed"], 0)
            self.assertEqual(pipeline_state.file_sha256(rdb), sha_before,
                             "--dry-run изменил RDB-файл")
            state = _load_state(summary["checkpoint"])
            self.assertIsNotNone(state)
            self.assertTrue(state["dry_run"],
                            "checkpoint обязан отметить dry_run: true")
            self.assertGreater(len(_rdb_addr_list(rdb)), 0)
        finally:
            self.assertTrue(B.git_clean("roms/"))


@unittest.skipUnless(_E2E, "идёт только при V06C_ANALYZE_E2E=1")
@unittest.skipUnless(_putup_ready(), "нет сервера v06c-mcp или putup.rom")
class PipelineExternalEditE2ETest(unittest.TestCase):
    """Мок «RDB изменён вне pipeline»: --resume обязан остановиться с
    RDB_CHANGED_OUTSIDE_PIPELINE и не произвести ни одной мутации (§23).
    Правим ТОЛЬКО временную копию — tracked-файлы неприкосновенны.
    """

    @classmethod
    def setUpClass(cls):
        from analyze import pipeline
        cls.pipeline = pipeline
        cls.tmp = tempfile.mkdtemp(prefix="v06c-e2e-extedit-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_resume_stops_on_external_rdb_edit(self):
        from analyze import pipeline_state
        # Копия — в самом тесте: после внешней правки rdb она одноразовая.
        self.fixture = B.copy_fixture(B.PUTUP_ROM, B.PUTUP_RDB)
        self.rom, self.rdb, _ = self.fixture
        self.results = os.path.join(self.fixture[2], "results")
        argv = ["--rom", self.rom, "--rdb", self.rdb,
                "--results", self.results, "--only", "probe", "--json"]
        rc, summary, err = _run_pipeline_inproc(self.pipeline, argv)
        self.assertEqual(rc, 0, "базовый --only probe упал: %s" % err[-400:])
        state_path = summary["checkpoint"]
        state_before = _load_state(state_path)
        # Внешняя правка мимо pipeline: дописываем байт в копию .rdb.
        with open(self.rdb, "ab") as fh:
            fh.write(b"\n")
        sha_edited = pipeline_state.file_sha256(self.rdb)
        rc2, summary2, err2 = _run_pipeline_inproc(
            self.pipeline, argv + ["--resume"])
        self.assertEqual(rc2, 1, "resume по внешнему правленому RDB не должен пройти")
        self.assertIn("RDB_CHANGED_OUTSIDE_PIPELINE",
                      (summary2.get("fatal") or "") + err2)
        # Остановка — до любого анализа: ничего не дописано, checkpoint тот же.
        self.assertEqual(pipeline_state.file_sha256(self.rdb), sha_edited)
        self.assertEqual(_load_state(state_path), state_before)
        self.assertTrue(B.git_clean("roms/"))

    def setUp(self):
        self.fixture = None

    def tearDown(self):
        if self.fixture:
            shutil.rmtree(self.fixture[2], True)


@unittest.skipUnless(_E2E, "идёт только при V06C_ANALYZE_E2E=1")
@unittest.skipUnless(_testay_ready(), "нет сервера v06c-mcp или TESTAY.ROM")
class TestayPipelineE2ETest(unittest.TestCase):
    """Переносимость: apply-посев на временной копии TESTAY со своим rdb."""

    @classmethod
    def setUpClass(cls):
        from analyze import pipeline
        cls.pipeline = pipeline
        cls.tmp = tempfile.mkdtemp(prefix="v06c-e2e-testay-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_seed_rdb_apply_on_copy(self):
        src_rdb = B.TESTAY_RDB if os.path.isfile(B.TESTAY_RDB) else None
        rom, rdb, _ = B.copy_fixture(B.TESTAY_ROM, src_rdb, dest_dir=self.tmp)
        argv = ["--rom", rom, "--results", os.path.join(self.tmp, "results"),
                "--only", "seed_rdb", "--json"]
        if rdb:
            argv[2:2] = ["--rdb", rdb]
        rc, summary, err = _run_pipeline_inproc(self.pipeline, argv)
        self.assertEqual(rc, 0, "TESTAY apply упал: %s" % err[-400:])
        self.assertEqual(summary["failed"], 0)
        state = _load_state(summary["checkpoint"])
        self.assertIsNotNone(state)
        self.assertIn("seed_rdb", state["completed_stages"])
        self.assertTrue(B.git_clean("roms/"))


@unittest.skipUnless(_E2E, "идёт только при V06C_ANALYZE_E2E=1")
@unittest.skipUnless(_json_available(), "нет сервера v06c-mcp")
class RiseoutFreshRdbE2ETest(unittest.TestCase):
    """riseout (§55, решение пользователя): нет файла — SKIP; есть — копия
    БЕЗ rdb, pipeline сам рождает RDB первым debug_save_rdb.
    """

    @classmethod
    def setUpClass(cls):
        from analyze import pipeline
        cls.pipeline = pipeline
        cls.tmp = tempfile.mkdtemp(prefix="v06c-e2e-riseout-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_fresh_rdb_born_via_seed(self):
        if not os.path.isfile(B.RISEOUT_ROM):
            self.skipTest("riseout.rom отсутствует — SKIP по решению (§55)")
        from analyze import pipeline_state
        original_sha = pipeline_state.file_sha256(B.RISEOUT_ROM)
        # Копия без .rdb: sidecar разрешается внутрь временного каталога.
        rom, rdb, _ = B.copy_fixture(B.RISEOUT_ROM, None, dest_dir=self.tmp)
        self.assertIsNone(rdb)
        expected_rdb = os.path.splitext(rom)[0] + ".rdb"
        self.assertFalse(os.path.isfile(expected_rdb))
        argv = ["--rom", rom, "--results", os.path.join(self.tmp, "results"),
                "--only", "seed_rdb", "--json"]
        rc, summary, err = _run_pipeline_inproc(self.pipeline, argv)
        self.assertEqual(rc, 0, "riseout apply упал: %s" % err[-400:])
        self.assertEqual(summary["failed"], 0)
        self.assertTrue(os.path.isfile(expected_rdb),
                        "первый debug_save_rdb обязан породить rdb-соседа")
        self.assertGreater(len(_rdb_addr_list(expected_rdb)), 0,
                           "свежий RDB пуст — севок ничего не добавил")
        # Исходный ROM не менялся; riseout.rdb в git не попадает (он в tmp).
        self.assertEqual(pipeline_state.file_sha256(B.RISEOUT_ROM), original_sha)
        self.assertTrue(B.git_clean("roms/"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
