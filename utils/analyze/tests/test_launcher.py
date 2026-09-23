#!/usr/bin/env python3
"""Приёмочные тесты launcher'а `run_pipeline.sh` (ТЗ Launcher §35).

Группы:
* Profile   — известный профиль даёт правильные пути (--rom/--rdb/--config),
              неизвестный → exit 2 + список Available ROMs (§11);
* Paths     — запуск из корня репозитория и из другого каталога (§7—§8);
* Arguments — --apply/--dry-run/--resume/--clean/--only/--from/--until
              доходят до pipeline без изменений (§3/§4/§20);
* Missing files — отсутствие ROM / pipeline.py / pipeline.json → exit 3
              с каноническими ERROR-сообщениями (§9—§14);
* Exit code — launcher возвращает код pipeline (§26);
* Ctrl-C    — SIGINT не подавляется, pipeline получает сигнал (§27).

Сервер не нужен: в stub-репозитории роль `analyze.cli` играет запись,
которая дарит argv и окружение в JSON-файл (заодно проверяет §23 —
передачу окружения). Реальный репозиторий прогоняется только через
`--list` (stages печатаются без MCP-сеанса).

Запуск:
    python3 utils/analyze/tests/test_launcher.py
"""
from __future__ import annotations

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
import _bootstrap as B  # noqa: E402

LAUNCHER = os.path.join(B.PKG, "run_pipeline.sh")

# Профили ТЗ §5/§29: имя → (путь rom внутри репозитория, путь config).
PROFILES = {
    "riseout": ("roms/redesign/riseout/src/riseout.rom",
                "roms/redesign/riseout/pipeline.json"),
    "putup": ("roms/redesign/putup/src/putup.rom",
              "roms/redesign/putup/pipeline.json"),
    "testay": ("roms/redesign/testay/src/TESTAY.ROM",
               "roms/redesign/testay/pipeline.json"),
}

# Заглушка пакета analyze: пишет argv/окружение в capture-файл; exit code,
# сон и marker управляются переменными окружения (их обязан донести launcher).
STUB_CLI = '''"""Заглушка analyze.cli для тестов run_pipeline.sh (только тесты)."""
import json, os, sys, time
data = {"argv": sys.argv[1:],
        "pythonpath": os.environ.get("PYTHONPATH"),
        "custom": os.environ.get("V06C_STUB_CUSTOM")}
marker = os.environ.get("V06C_STUB_MARKER")
if marker:
    with open(marker, "w") as fh:
        fh.write("ready")
if os.environ.get("V06C_STUB_SLEEP"):
    time.sleep(float(os.environ["V06C_STUB_SLEEP"]))
capture = os.environ.get("V06C_STUB_CAPTURE")
if capture:
    with open(capture, "w") as fh:
        json.dump(data, fh)
sys.exit(int(os.environ.get("V06C_STUB_RC") or 0))
'''


class LauncherTestCase(unittest.TestCase):
    """Общие помощники: запуск subprocess'ом, чтение capture-файла."""

    def run_launcher(self, args, launcher=None, cwd=None, extra_env=None):
        launcher = launcher or self.launcher
        env = dict(os.environ)
        env.update(extra_env or {})
        proc = subprocess.Popen([launcher] + list(args), cwd=cwd, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        return (proc.returncode,
                out.decode("utf-8", "replace"),
                err.decode("utf-8", "replace"))

    def read_capture(self):
        with open(self.capture, encoding="utf-8") as fh:
            return json.load(fh)

    def flag_value(self, argv, flag):
        """Значение флага в argv заглушки (или None, если флага нет)."""
        if flag in argv:
            index = argv.index(flag)
            if index + 1 < len(argv):
                return argv[index + 1]
        return None


class StubRepoTest(LauncherTestCase):
    """Все проверки §35 на фальшивом репозитории — без сервера и ROM."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="v06c-launcher-")
        # Кладём launcher в stub-репозиторий: §7—§8 — REPO считается от
        # расположения скрипта, значит «репозиторием» станет self.tmp.
        fake_utils = os.path.join(self.tmp, "utils", "analyze")
        os.makedirs(fake_utils)
        self.launcher = os.path.join(fake_utils, "run_pipeline.sh")
        shutil.copyfile(LAUNCHER, self.launcher)
        os.chmod(self.launcher, 0o755)
        with open(os.path.join(fake_utils, "pipeline.py"), "w") as fh:
            fh.write("# existence check для §10\n")
        with open(os.path.join(fake_utils, "__init__.py"), "w") as fh:
            fh.write("")
        with open(os.path.join(fake_utils, "cli.py"), "w") as fh:
            fh.write(STUB_CLI)
        self.capture = os.path.join(self.tmp, "captured.json")
        # Фикстуры профилей: пустые rom-файлы + минимальные pipeline.json.
        for name, (rom_rel, config_rel) in PROFILES.items():
            rom = os.path.join(self.tmp, *rom_rel.split("/"))
            config = os.path.join(self.tmp, *config_rel.split("/"))
            os.makedirs(os.path.dirname(rom), exist_ok=True)
            os.makedirs(os.path.dirname(config), exist_ok=True)
            with open(rom, "wb") as fh:
                fh.write(b"\x00\xC9\x00")           # «ROM» из трёх байт
            with open(config, "w") as fh:
                fh.write("{}\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, True)

    # -- Profile ------------------------------------------------------------

    def test_known_profile_resolves_paths(self):
        """известный профиль → правильные --rom/--config; --rdb по соседу."""
        # putup: создаём rdb-соседа → должен уйти в --rdb.
        putup_rom = os.path.join(self.tmp, *PROFILES["putup"][0].split("/"))
        with open(os.path.splitext(putup_rom)[0] + ".rdb", "w") as fh:
            fh.write("{}")
        for name in ("riseout", "putup", "testay"):
            with self.subTest(profile=name):
                rc, _out, err = self.run_launcher(
                    [name, "--list"],
                    extra_env={"V06C_STUB_CAPTURE": self.capture})
                self.assertEqual(rc, 0, err[-400:])
                argv = self.read_capture()["argv"]
                self.assertEqual(argv[0], "pipeline")
                self.assertEqual(self.flag_value(argv, "--rom"),
                                 os.path.join(self.tmp,
                                             *PROFILES[name][0].split("/")))
                self.assertEqual(self.flag_value(argv, "--config"),
                                 os.path.join(self.tmp,
                                             *PROFILES[name][1].split("/")))
                expected_rdb = os.path.splitext(
                    self.flag_value(argv, "--rom"))[0] + ".rdb"
                if os.path.isfile(expected_rdb):
                    self.assertEqual(self.flag_value(argv, "--rdb"),
                                     expected_rdb)          # §5: RDB-сосед
                else:
                    self.assertIsNone(self.flag_value(argv, "--rdb"),
                                      "RDB нет — не передаём (§13)")
                self.assertEqual(self.flag_value(argv, "--results"),
                                 ".scratch/pipeline/" + name)

    def test_unknown_profile_exit_2(self):
        """§11: неизвестный профиль → exit 2 + список доступных."""
        rc, _out, err = self.run_launcher(["zzz"])
        self.assertEqual(rc, 2)
        self.assertIn("Unknown ROM profile: zzz", err)
        self.assertIn("Available ROMs:", err)
        for name in PROFILES:
            self.assertIn(name, err)

    def test_no_args_usage_exit_1(self):
        """§26: usage-ошибка без аргументов → 1."""
        rc, _out, err = self.run_launcher([])
        self.assertEqual(rc, 1)
        self.assertIn("Available ROMs:", err)

    # -- Arguments ----------------------------------------------------------

    def test_arguments_forwarded_verbatim(self):
        """§3/§4/§20: все мандатные флаги доходят до pipeline без изменений."""
        flags = ["--resume", "--verbose", "--dry-run", "--apply",
                 "--only", "seed_rdb", "--from", "coverage",
                 "--until", "rdb_lint", "--clean"]
        rc, _out, err = self.run_launcher(["putup"] + flags,
                                          extra_env={"V06C_STUB_CAPTURE":
                                                     self.capture})
        self.assertEqual(rc, 0, err[-400:])
        argv = self.read_capture()["argv"]
        for flag in flags:
            self.assertIn(flag, argv)
        # порядок хвоста сохранён: flags идут как переданы, после --config
        tail = argv[argv.index("--config") + 2:]
        self.assertEqual(tail, flags)

    def test_environment_passthrough(self):
        """§23: окружение пользователя сохраняется, PYTHONPATH — utils stub'а."""
        rc, _out, err = self.run_launcher(
            ["putup"], extra_env={"V06C_STUB_CAPTURE": self.capture,
                                  "V06C_STUB_CUSTOM": "передано"})
        self.assertEqual(rc, 0, err[-400:])
        captured = self.read_capture()
        self.assertEqual(captured["custom"], "передано")
        self.assertEqual(captured["pythonpath"],
                         os.path.join(self.tmp, "utils"))

    # -- Paths --------------------------------------------------------------

    def test_run_from_other_directory(self):
        """§7/§8/§35: запуск не из корня — пути от расположения скрипта."""
        elsewhere = os.path.join(self.tmp, "где-то")
        os.makedirs(elsewhere)
        rc, _out, err = self.run_launcher(
            ["putup"], cwd=elsewhere,
            extra_env={"V06C_STUB_CAPTURE": self.capture})
        self.assertEqual(rc, 0, err[-400:])
        argv = self.read_capture()["argv"]
        self.assertEqual(self.flag_value(argv, "--rom"),
                         os.path.join(self.tmp, *PROFILES["putup"][0].split("/")))

    def test_path_mode_backward_compatible(self):
        """Режим пути (наследие предыдущего ТЗ): rom-путь вместо профиля."""
        rom = os.path.join(self.tmp, *PROFILES["putup"][0].split("/"))
        rc, _out, err = self.run_launcher([rom],
                                          extra_env={"V06C_STUB_CAPTURE":
                                                     self.capture})
        self.assertEqual(rc, 0, err[-400:])
        argv = self.read_capture()["argv"]
        self.assertEqual(self.flag_value(argv, "--rom"), rom)
        self.assertIsNone(self.flag_value(argv, "--config"),
                          "в режиме пути config не подключается")
        self.assertEqual(self.flag_value(argv, "--results"),
                         ".scratch/pipeline/putup")   # stem, нижним регистром

    # -- Missing files ------------------------------------------------------

    def test_missing_rom_exit_3(self):
        """§12: ROM отсутствует → ERROR + exit 3, pipeline не стартует."""
        os.remove(os.path.join(self.tmp, *PROFILES["putup"][0].split("/")))
        rc, _out, err = self.run_launcher(
            ["putup"], extra_env={"V06C_STUB_CAPTURE": self.capture})
        self.assertEqual(rc, 3)
        self.assertIn("ERROR: ROM not found", err)
        self.assertFalse(os.path.isfile(self.capture))   # stub не запускался

    def test_missing_config_exit_3(self):
        """§14: нет pipeline.json профиля → exit 3 без запуска pipeline."""
        os.remove(os.path.join(self.tmp, *PROFILES["testay"][1].split("/")))
        rc, _out, err = self.run_launcher(
            ["testay"], extra_env={"V06C_STUB_CAPTURE": self.capture})
        self.assertEqual(rc, 3)
        self.assertIn("ERROR: pipeline configuration not found", err)
        self.assertFalse(os.path.isfile(self.capture))

    def test_missing_pipeline_py_exit_3(self):
        """§10: нет pipeline.py → exit 3."""
        os.remove(os.path.join(self.tmp, "utils", "analyze", "pipeline.py"))
        rc, _out, err = self.run_launcher(["putup"])
        self.assertEqual(rc, 3)
        self.assertIn("ERROR: pipeline.py not found", err)

    def test_missing_rdb_is_not_error(self):
        """§13: RDB-соседа нет — НЕ ошибка (riseout-сценарий, seed родит)."""
        rc, _out, err = self.run_launcher(
            ["testay"], extra_env={"V06C_STUB_CAPTURE": self.capture})
        self.assertEqual(rc, 0, err[-400:])
        self.assertIn("ещё не создан", err)               # §25: показываем

    # -- Вывод §25 ----------------------------------------------------------

    def test_startup_summary_printed(self):
        """§25: сводка ROM/RDB/CONFIG/ARGS + Starting pipeline... до запуска."""
        rc, out, err = self.run_launcher(["putup"])
        self.assertEqual(rc, 0)
        for token in ("ROM:    putup", "RDB:", "CONFIG:",
                      "Starting pipeline..."):
            self.assertIn(token, err)
        self.assertNotIn("Starting pipeline...", out)     # stdout чист

    # -- Exit codes §26 ------------------------------------------------------

    def test_pipeline_exit_code_preserved(self):
        """§26: ненулевой код pipeline проходит через launcher как есть."""
        rc, _out, _err = self.run_launcher(
            ["putup"], extra_env={"V06C_STUB_RC": "7"})
        self.assertEqual(rc, 7)

    # -- Ctrl-C §27 ----------------------------------------------------------

    def test_sigint_not_swallowed(self):
        """§27: SIGINT доходит до pipeline (launcher его не перехватывает)."""
        marker = os.path.join(self.tmp, "stub-ready")
        env = dict(os.environ)
        env.update({"V06C_STUB_MARKER": marker, "V06C_STUB_SLEEP": "30"})
        proc = subprocess.Popen([self.launcher, "putup"], cwd=self.tmp,
                                env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        deadline = time.time() + 20
        while time.time() < deadline and not os.path.isfile(marker):
            time.sleep(0.1)
        self.assertTrue(os.path.isfile(marker),
                        "stub не вышел на связь — проверять нечего")
        proc.send_signal(signal.SIGINT)
        try:
            proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.fail("launcher пережил SIGINT и висит (§27 нарушен)")
        self.assertNotEqual(proc.returncode, 0)
        with open(LAUNCHER, encoding="utf-8") as fh:
            self.assertNotIn("trap ", fh.read(),
                             "launcher не должен вешать trap на сигналы")


class RealRepoLauncherTest(LauncherTestCase):
    """Тот же launcher на реальном репозитории, но только --list:
    stages печатаются без MCP-сеанса, файлы профилей не мутируются."""

    def setUp(self):
        self.launcher = LAUNCHER
        self.capture = os.devnull

    def _list_rc_and_out(self, name):
        elsewhere = tempfile.mkdtemp(prefix="v06c-launcher-cwd-")
        try:
            return self.run_launcher([name, "--list"], cwd=elsewhere)
        finally:
            shutil.rmtree(elsewhere, True)

    def test_putup_profile_list(self):
        rc, out, err = self._list_rc_and_out("putup")
        self.assertEqual(rc, 0, err[-400:])
        for stage in ("probe", "seed_rdb", "rdb_lint", "roundtrip_verify"):
            self.assertIn(stage, out)
        self.assertIn("CONFIG:", err)

    def test_testay_profile_list(self):
        rc, _out, err = self._list_rc_and_out("testay")
        self.assertEqual(rc, 0, err[-400:])

    def test_riseout_profile_list(self):
        if not os.path.isfile(B.RISEOUT_ROM):
            self.skipTest("riseout.rom отсутствует (untracked) — SKIP §55-решение")
        rc, _out, err = self._list_rc_and_out("riseout")
        self.assertEqual(rc, 0, err[-400:])
        self.assertIn("ещё не создан", err)   # у riseout нет .rdb

    def test_unknown_profile_exit_2(self):
        rc, _out, err = self.run_launcher(["definitely-not-a-rom"])
        self.assertEqual(rc, 2)
        self.assertIn("Unknown ROM profile", err)

    def test_path_mode_list(self):
        rc, out, err = self.run_launcher([B.PUTUP_ROM, "--list"])
        self.assertEqual(rc, 0, err[-400:])
        self.assertIn("seed_rdb", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
