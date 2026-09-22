#!/usr/bin/env python3
"""Интеграционные тесты пакета `analyze` на реальных ROM (ТЗ §32, §35).

Два уровня:

1. `ModuleIntegrationTest` — несколько модулей на `putup.rom` и `TESTAY.ROM`
   внутри ОДНОГО общего MCP-сеанса (проверяет §4 и контракт конверта §29/§30:
   статус present, `mcp_calls` целое, кандидат не повышен до факта §34).
   Требует только сервер `v06c-mcp`.

2. `PipelineIntegrationTest` — полный прогон `pipeline.py` на putup (§35:
   «putup.rom проходит полный pipeline»). Тяжёлый (~десятки секунд, зовёт
   z80asm и v06c-asm-export), поэтому включается по `V06C_ANALYZE_E2E=1`.

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
import sys
import tempfile
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


@unittest.skipUnless(os.environ.get("V06C_ANALYZE_E2E") == "1",
                     "полный пайплайн (§35) идёт только при V06C_ANALYZE_E2E=1")
@unittest.skipUnless(_putup_ready(), "нет сервера v06c-mcp или putup.rom")
class PipelineIntegrationTest(unittest.TestCase):
    """§35: putup.rom проходит полный pipeline без отказов шагов."""

    @classmethod
    def setUpClass(cls):
        from analyze import pipeline
        cls.pipeline = pipeline
        cls.tmp = tempfile.mkdtemp(prefix="v06c-int-e2e-")
        cls.results = os.path.join(cls.tmp, "results")
        cls.export = os.path.join(cls.tmp, "export")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_full_pipeline_putup(self):
        buf = io.StringIO()
        argv = ["--rom", B.PUTUP_ROM, "--rdb", B.PUTUP_RDB,
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
