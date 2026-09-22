"""АБИ функций: статика + динамика → кандидаты параметров (ТЗ §20, §19).

Что модуль считает и чем это не является «разбором».

Статика — по тексту листинга, который вернул отладчик
(`debug_get_function_context` → instructions[].text):

* какое имя регистра встречается в позиции «читается» раньше, чем в позиции
  «пишется», — кандидат на входной параметр;
* где регистр пишется в последний раз до конца тела — кандидат на результат;
* пары PUSH/POP и их порядок — кандидат на соглашение о сохраняемых регистрах;
* LDA/STA/LHLD/SHLD с абсолютным адресом — «аргумент через память».

Позиции «читается/пишется» берутся из документации по процессору
(docs/VECTOR_CPU_COMMANDS.md §4), а не из собственного декодера: байты здесь
не разбираются, граф потока управления не строится, обход тела — линейный в
том порядке, который отдал сервер. Поэтому выход модуля — CANDIDATE, а не
«у функции два параметра».

Динамика — наблюдения с точек останова (ТЗ §19):

* несколько срабатываний функции подряд → значения AF/BC/DE/HL/SP;
* регистр, который МЕНЯЕТСЯ между срабатываниями, пока остальные константны,
  — сильный кандидат на вход;
* по слову по адресу SP судим о входе: похоже на адрес возврата внутри
  образа ROM ⇒ вызов был `CALL`, не похоже ⇒ `JMP`/хвостовой переход
  (Stage 6 так же считал чистый стек на 0x0E85).

Слияние: совпало с динамикой → `high`, только статика при >=2 срабатываниях →
`medium`, иначе `low`. Семантику («это индекс операции») назначает AI.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

from analyze.mcp_session import (addr_hex, bytes_of, envelope, open_session,
                                to_addr)
from analyze.probe import parse_key_specs, run_for
from analyze.rdb import Rdb

REGISTERS = ("A", "B", "C", "D", "E", "H", "L")
PAIRS = {"BC": ("B", "C"), "DE": ("D", "E"), "HL": ("H", "L"), "SP": (),
         "PSW": ("A",)}
# LDAX/STAX пишутся одной буквой, а адресуют пару (docs §4)
PAIR_LETTER = {"B": "BC", "D": "DE", "H": "HL"}
# (mnemonic) → (читаемые позиции, пишемые позиции). Позиция — "op0"/"op1"
# (операнд листинга), имя регистра (неявный операнд) или "SP"/"STACK".
# docs/VECTOR_CPU_COMMANDS.md §4
ROLES = {
    "MOV": (("op1",), ("op0",)),
    "MVI": (("imm",), ("op0",)),
    "LXI": ((), ("op0",)),
    "LDA": ((), ("A",)),
    "STA": (("A",), ()),
    "LHLD": ((), ("H", "L")),
    "SHLD": (("H", "L"), ()),
    "LDAX": (("op0",), ("A",)),
    "STAX": (("A", "op0"), ()),
    "INX": (("op0",), ("op0",)),
    "DCX": (("op0",), ("op0",)),
    "INR": (("op0",), ("op0",)),
    "DCR": (("op0",), ("op0",)),
    "DAD": (("op0", "H", "L"), ("H", "L")),
    "ADD": (("op0",), ("A",)),
    "ADC": (("op0",), ("A",)),
    "SUB": (("op0",), ("A",)),
    "SBB": (("op0",), ("A",)),
    "ANA": (("op0",), ("A",)),
    "XRA": (("op0",), ("A",)),
    "ORA": (("op0",), ("A",)),
    "CMP": (("op0",), ()),
    "ADI": (("imm",), ("A",)),
    "ACI": (("imm",), ("A",)),
    "SUI": (("imm",), ("A",)),
    "SBI": (("imm",), ("A",)),
    "ANI": (("imm",), ("A",)),
    "XRI": (("imm",), ("A",)),
    "ORI": (("imm",), ("A",)),
    "CPI": (("imm",), ()),
    "RLC": (("A",), ("A",)),
    "RRC": (("A",), ("A",)),
    "RAL": (("A",), ("A",)),
    "RAR": (("A",), ("A",)),
    "CMA": (("A",), ("A",)),
    "DAA": (("A",), ("A",)),
    "CMC": ((), ()),
    "STC": ((), ()),
    "PUSH": (("op0", "SP"), ()),
    "POP": (("SP",), ("op0",)),
    "XTHL": (("SP", "H", "L"), ("H", "L")),
    "SPHL": (("H", "L"), ("SP",)),
    "PCHL": (("H", "L"), ()),
    "XCHG": (("D", "E", "H", "L"), ("D", "E", "H", "L")),
    "IN": ((), ("A",)),
    "OUT": (("A",), ()),
    "RET": (("SP",), ()),
    "CALL": ((), ("SP",)),
    "RST": ((), ("SP",)),
}
BRANCHES = ("JMP", "JNZ", "JZ", "JC", "JNC", "JP", "JM", "JPE", "JPO")
# Условные формы CALL/RET в таблице не перечисляются: роли у них такие же,
# как у базовой мнемоники (docs/VECTOR_CPU_COMMANDS.md §4).
CONDITIONALS = ("NZ", "Z", "NC", "C", "PO", "PE", "P", "M")
NO_ROLES = ("NOP", "EI", "DI", "HLT", "CMC", "STC")
MEMORY_OPS = {"LDA": "read", "STA": "write", "LHLD": "read", "SHLD": "write"}
WORD_RE = re.compile(r"^[0-9A-Fa-f]{2,4}$")


def role_entry(mnemonic):
    """Запись ROLES для мнемоники, возможно условной (CZ → CALL, RN → RET)."""
    if mnemonic in ROLES:
        return ROLES[mnemonic]
    for base, conditional in (("CALL", "C"), ("RET", "R")):
        for suffix in CONDITIONALS:
            if mnemonic == conditional + suffix:
                return ROLES[base]
    return None


def split_text(text):
    """'MOV A,L' → ('MOV', ['A', 'L']). Разбор текстовой формы, не байтов."""
    text = (text or "").split(";")[0].strip()
    if not text:
        return "", []
    head, _, rest = text.partition(" ")
    operands = [item.strip() for item in rest.split(",")] if rest.strip() else []
    return head.upper(), [item.upper() for item in operands if item.strip()]


def expand(token):
    """Имя операнда → 8-битные регистры, которых он касается."""
    token = (token or "").upper()
    if token in PAIRS:
        return set(PAIRS[token])
    if token in ("M", "(HL)"):
        return {"H", "L"}                       # адрес в паре → H/L читаются
    if token in REGISTERS:
        return {token}
    return set()                                 # SP/PSW-служебное и прочее


def normalize(mnemonic, operands):
    """'LDAX D' → пару DE: адрес берётся из регистра-пары."""
    if mnemonic in ("LDAX", "STAX", "INX", "DCX", "DAD") and operands:
        return [PAIR_LETTER.get(operands[0], operands[0])] + operands[1:]
    return list(operands)


def roles(mnemonic, operands):
    """(читаемые токены, пишемые токены) по таблице документации."""
    entry = role_entry(mnemonic)
    if entry is None:
        return (), ()
    operands = normalize(mnemonic, operands)
    reads, writes = [], []
    for token in entry[0]:
        reads.append(operands[0] if token == "op0" else
                     operands[1] if token == "op1" and len(operands) > 1 else
                     None if token == "imm" else token)
    for token in entry[1]:
        writes.append(operands[0] if token == "op0" else
                      operands[1] if token == "op1" and len(operands) > 1 else
                      None if token == "imm" else token)
    return ([item for item in reads if item], [item for item in writes if item])


def is_immediate(mnemonic, operand):
    """Непосредственный операнд (адрес/константа) вместо регистра."""
    if operand in PAIRS or operand in REGISTERS or operand in ("M", "(HL)"):
        return False
    return bool(WORD_RE.match(operand or "")) or (operand or "").startswith("0x")


# ---------------------------------------------------------------------------
# Статика
# ---------------------------------------------------------------------------

def saved_registers(instructions):
    """Регистры, которые функция кладёт в стек и снимает обратно.

    `PUSH B` в начале и `POP B` в конце — это сохранение вызываемого, а не
    чтение параметра. Без этой поправки каждый сохраняемый регистр
    превращался бы в «вход» и в «результат».
    """
    pushed, popped = set(), set()
    for ins in instructions:
        mnemonic, operands = split_text(ins.get("text", ""))
        if mnemonic not in ("PUSH", "POP") or not operands:
            continue
        target = pushed if mnemonic == "PUSH" else popped
        for reg in expand(operands[0]):
            target.add(reg)
        # PSW = A+F: флаг не регистр, но A сохраняем как есть
    return pushed & popped


def static_signature(instructions, image_lo=0x0100, image_hi=None):
    """Линейный обход листинга функции → кандидаты входа/выхода/стека/памяти."""
    saved = saved_registers(instructions)
    written, inputs, outputs = set(), {}, {}
    last_action = {}
    stack_pairs, memory_args, unknown_mnemonics = [], [], set()
    for ins in instructions:
        address = ins.get("address")
        text = ins.get("text", "")
        mnemonic, operands = split_text(text)
        if not mnemonic:
            continue
        known = (role_entry(mnemonic) is not None or mnemonic in BRANCHES
                 or mnemonic in NO_ROLES)
        if not known:
            unknown_mnemonics.add(mnemonic)
        reads, writes = roles(mnemonic, operands)
        saving = mnemonic == "PUSH" or mnemonic == "POP"
        for token in reads:
            if is_immediate(mnemonic, token):
                continue
            for reg in expand(token):
                if saving and mnemonic == "PUSH" and reg in saved:
                    continue                    # сохранение вызываемого — не вход
                if reg in REGISTERS and reg not in written and reg not in inputs:
                    inputs[reg] = {"read_at": address, "text": text}
                last_action.setdefault(reg, []).append((address, "read", text))
        for token in writes:
            for reg in expand(token):
                if reg not in REGISTERS:
                    continue
                written.add(reg)
                if not (saving and mnemonic == "POP" and reg in saved):
                    outputs[reg] = {"written_at": address, "text": text}
                last_action.setdefault(reg, []).append((address, "write", text))
        if mnemonic in ("PUSH", "POP") and operands:
            stack_pairs.append((mnemonic.lower(), operands[0], address))
        if mnemonic in MEMORY_OPS and operands:
            pointer = to_addr(operands[0]) if WORD_RE.match(operands[0]) else None
            if pointer is not None:
                kind = MEMORY_OPS[mnemonic]
                memory_args.append({
                    "address": addr_hex(pointer), "op": mnemonic,
                    "access": kind,
                    "region": ("image" if image_hi and
                               image_lo <= pointer <= image_hi else "ram"),
                    "at": address})
        if mnemonic == "RET" or mnemonic.startswith("RET"):
            break
    return {
        "inputs": [{"register": reg, "first_read": value["read_at"],
                    "at": value["text"]} for reg, value in sorted(inputs.items())],
        "outputs": [{"register": reg, "last_write": value["written_at"],
                     "at": value["text"]} for reg, value in sorted(outputs.items())
                    if (last_action.get(reg) or [[None, "none", None]])[-1][1] == "write"],
        "stack_pairs": stack_pairs,
        "saved_registers": sorted(saved),
        "memory_arguments": memory_args,
        "unknown_mnemonics": sorted(unknown_mnemonics),
    }


# ---------------------------------------------------------------------------
# Динамика
# ---------------------------------------------------------------------------

class HitSampler:
    """Несколько срабатываний точки останова: регистры на входе в функцию."""


    def __init__(self, session, run=None, restart=None, image_lo=0x0100,
                 image_hi=0x3FFF):
        self.session = session
        self.run = run
        self.restart = restart
        self.image_lo = to_addr(image_lo)
        self.image_hi = to_addr(image_hi)

    def sample(self, address, hits=3, timeout=2.0, key_between=None, restart=True):
        # перезагрузка перед замером: служебные функции инициализации
        # (func_load_glyph_block) после первого кадра больше не вызываются,
        # и без чистого старта они дали бы hits=0
        if self.restart and restart:
            self.restart()
        address = to_addr(address)
        samples = []
        for index in range(max(1, int(hits))):
            self.session.call("debug_set_breakpoint", {"address": address})
            try:
                self.session.call("debug_run")
                cpu = self._wait_for_hit(address, timeout)
                if cpu is None:
                    samples.append({"hit": index, "hit_ok": False})
                    continue
                sample = {"hit": index, "hit_ok": True,
                          "pc": cpu.get("pc"), "sp": cpu.get("sp"),
                          "registers": {reg: cpu.get(reg.lower()) for reg in
                                        REGISTERS}}
                sample["stack"] = self._return_address(cpu.get("sp"))
                samples.append(sample)
            finally:
                self.session.call("debug_remove_breakpoint", {"address": address})
            if key_between and self.run is not None:
                self.run.pause()
                self.run.keys(key_between)
        return samples

    def _wait_for_hit(self, address, timeout):
        deadline = time.time() + float(timeout)
        state = {}
        while time.time() < deadline:
            state = self.session.call("debug_get_state")
            cpu = state.get("cpu") or {}
            if not state.get("running") and cpu.get("pc") is not None:
                if to_addr(cpu.get("pc")) == address:
                    return cpu
                return cpu                        # остановились не там — тоже сигнал
            time.sleep(0.02)
        self.session.call("debug_pause")
        return None

    def _return_address(self, sp):
        """Слово по SP: похоже на адрес возврата из образа ROM?"""
        if sp is None:
            return None
        pointer = to_addr(sp)
        try:
            data = self.session.call("debug_read_memory_range",
                                     {"address": pointer, "length": 2})
        except Exception:            # noqa: BLE001 — вне диапазона/не читается
            return {"sp": addr_hex(pointer), "word": None,
                    "looks_like_return": False}
        raw = bytes_of(data)
        if len(raw) < 2:
            return {"sp": addr_hex(pointer), "word": None,
                    "looks_like_return": False}
        word = raw[0] | (raw[1] << 8)
        return {"sp": addr_hex(pointer), "word": addr_hex(word),
                "in_image": self.image_lo <= word <= self.image_hi,
                "looks_like_return": self.image_lo <= word <= self.image_hi}


def dynamic_signature(samples, image_lo=0x0100, image_hi=0x3FFF):
    hits = [item for item in samples if item.get("hit_ok")]
    values = {}
    for reg in REGISTERS:
        seen = [to_addr(item["registers"].get(reg)) for item in hits
                if item["registers"].get(reg) is not None]
        distinct = sorted(set(seen))
        values[reg] = {"observed": [addr_hex(value) for value in seen],
                       "distinct": len(distinct),
                       "varies": len(distinct) > 1,
                       "constant": len(distinct) == 1 and len(seen) > 1}
    sp = [to_addr(item["sp"]) for item in hits if item.get("sp") is not None]
    return {
        "hits": len(hits),
        "registers": values,
        "sp_values": [addr_hex(value) for value in sp],
        "return_addresses": [item.get("stack") for item in hits],
        "entry_via_call": sum(1 for item in hits
                              if (item.get("stack") or {}).get("looks_like_return")),
        "entry_via_jmp": sum(1 for item in hits
                             if item.get("stack") and
                             not item["stack"].get("looks_like_return")),
    }


def merge(function, static, dynamic):
    """Кандидаты параметров: статика × динамика + уверенность."""
    out = []
    dynamic_registers = (dynamic or {}).get("registers", {})
    for candidate in static["inputs"]:
        reg = candidate["register"]
        observed = dynamic_registers.get(reg) or {}
        evidence = ["static: %s читается до любой записи (%s @%s)"
                    % (reg, candidate["at"], candidate["first_read"])]
        if observed.get("varies"):
            evidence.append("dynamic: значение меняется между %d срабатываниями (%s)"
                            % (observed["distinct"],
                               ",".join(observed["observed"][:4])))
            confidence = "high"
        elif observed.get("constant"):
            evidence.append("dynamic: константа во всех %d срабатываниях"
                            % (dynamic or {}).get("hits", 0))
            confidence = "medium"
        elif (dynamic or {}).get("hits", 0) >= 2:
            confidence = "medium"
        else:
            confidence = "low"
        out.append({"register": reg, "role": "input", "confidence": confidence,
                    "evidence": evidence})
    for candidate in static["outputs"]:
        out.append({"register": candidate["register"], "role": "output",
                    "confidence": "low",
                    "evidence": ["static: последняя запись в теле (%s @%s)"
                                 % (candidate["at"], candidate["last_write"])]})
    memory = static["memory_arguments"]
    if memory:
        out.append({"register": None, "role": "memory_argument",
                    "confidence": "low" if len(memory) > 2 else "medium",
                    "evidence": ["static: %s %s (%s)"
                                 % (item["op"], item["address"], item["access"])
                                 for item in memory[:8]]})
    return {
        "function": function,
        "candidates": sorted(out, key=lambda item: (item["role"],
                                                    -_rank(item["confidence"]),
                                                    item["register"] or "")),
        "status": "CANDIDATE",
        "note": "роль параметра назначает AI; здесь только наблюдения",
    }


LEVELS = ("low", "medium", "high")


def _rank(confidence):
    return LEVELS.index(confidence) if confidence in LEVELS else -1


class AbiScanner:
    def __init__(self, session, cache=None, rdb=None, image_lo=0x0100,
                 image_hi=0x3FFF):
        self.session = session
        self.cache = cache
        self.rdb = rdb
        self.image_lo = to_addr(image_lo)
        self.image_hi = to_addr(image_hi)

    def functions(self, addresses=None, all_functions=False, limit=10):
        """Список адресов: явные из CLI, иначе функции из RDB (`--all`)."""
        if addresses:
            return [to_addr(item) for item in addresses]
        if not all_functions:
            return []
        out = []
        if self.rdb is not None:
            out = [obj.address for obj in self.rdb.of_type("function", "code")]
        else:
            graph = self.session.call("debug_get_call_graph", {"limit": 0})
            for edge in graph.get("edges") or []:
                for key in ("to", "callee", "target"):
                    if edge.get(key) is not None:
                        out.append(to_addr(edge[key]))
                        break
        seen, ordered = set(), []
        for address in out:
            if address not in seen:
                seen.add(address)
                ordered.append(address)
        return ordered[:limit] if limit else ordered

    def context(self, address):
        return self.session.call("debug_get_function_context",
                                 {"address": to_addr(address)})

    def scan(self, address, hits=3, timeout=2.0, sampler=None, keys=None,
             restart=True):
        address = to_addr(address)
        context = self.context(address)
        instructions = context.get("instructions") or []
        static = static_signature(instructions, self.image_lo, self.image_hi)
        samples = sampler.sample(address, hits=hits, timeout=timeout,
                                 key_between=keys, restart=restart) if sampler else []
        dynamic = dynamic_signature(samples, self.image_lo, self.image_hi) \
            if samples else None
        result = merge({"address": addr_hex(address),
                        "name": context.get("name"),
                        "size": context.get("size"),
                        "instructions": len(instructions),
                        "is_heuristic": context.get("is_heuristic"),
                        "stack_behavior": context.get("stack_behavior"),
                        "callers": len(context.get("callers") or []),
                        "callees": len(context.get("callees") or [])},
                       static, dynamic)
        result["static"] = {"stack_pairs": static["stack_pairs"],
                            "saved_registers": static["saved_registers"],
                            "memory_arguments": static["memory_arguments"],
                            "unknown_mnemonics": static["unknown_mnemonics"]}
        result["dynamic"] = dynamic
        result["samples"] = samples
        return result


def format_report(results, header=None):
    lines = []
    if header:
        lines.append(header)
    for item in results:
        function = item["function"]
        lines.append("")
        lines.append("%s @%s  size=%s instr=%s heuristic=%s callers=%s%s"
                     % (function.get("name") or "?", function["address"],
                        function.get("size"), function.get("instructions"),
                        function.get("is_heuristic"), function.get("callers"),
                        "  hits=%s" % item["dynamic"]["hits"]
                        if item.get("dynamic") else "  hits=0"))
        if item.get("dynamic"):
            lines.append("  вход: call=%s jmp=%s sp=%s"
                         % (item["dynamic"]["entry_via_call"],
                            item["dynamic"]["entry_via_jmp"],
                            ",".join(item["dynamic"]["sp_values"][:3])))
        if item["static"]["unknown_mnemonics"]:
            lines.append("  мнемоники без ролей: %s"
                         % ", ".join(item["static"]["unknown_mnemonics"]))
        if item["static"]["stack_pairs"]:
            lines.append("  стек: " + " ".join("%s %s" % (kind, name)
                                                for kind, name, _ in
                                                item["static"]["stack_pairs"][:8]))
        if item["static"]["saved_registers"]:
            lines.append("  сохраняемых: %s (PUSH…POP, в параметры не идут)"
                         % ",".join(item["static"]["saved_registers"]))
        lines.append("  %-6s %-16s %-10s %s" % ("рег", "роль", "уверенность",
                                                "доказательства"))
        for candidate in item["candidates"][:12]:
            lines.append("  %-6s %-16s %-10s %s"
                         % (candidate["register"] or "-", candidate["role"],
                            candidate["confidence"],
                            candidate["evidence"][0][:78]))
            for extra in candidate["evidence"][1:3]:
                lines.append("  %-6s %-16s %-10s %s" % ("", "", "",
                                                        extra[:78]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.abi_scan",
        description="Кандидаты параметров функций (статика + динамика)")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--function", action="append", default=[],
                        help="адрес функции (повторяемо)")
    parser.add_argument("--all", action="store_true",
                        help="пройтись по функциям из RDB")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--hits", type=int, default=3,
                        help="срабатываний на функцию для динамики")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--run", type=float, default=2.0,
                        help="секунд прогона перед динамикой")
    parser.add_argument("--key", action="append", default=[],
                        help="клавиши между срабатываниями, '0.2:SPACE'")
    parser.add_argument("--no-dynamic", action="store_true",
                        help="только статика: точки останова не ставятся")
    parser.add_argument("--no-restart", action="store_true",
                        help="не перезагружать ROM перед каждой функцией")
    parser.add_argument("--min-confidence", default="low", choices=LEVELS)
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    session, cache = open_session(rom=args.rom, org=args.org, server=args.server,
                                  cache_dir=args.cache)
    try:
        rdb = Rdb.load(args.rdb) if args.rdb else Rdb.from_session(session)
        rom_size = os.path.getsize(args.rom)
        scanner = AbiScanner(session, cache, rdb=rdb, image_lo=args.org,
                             image_hi=args.org + rom_size - 1)
        run = None
        sampler = None
        if not args.no_dynamic:
            run = run_for(session, cache, rom=args.rom, org=args.org,
                          seconds=args.run)

            def restart():
                run.boot()
                run.run()

            sampler = HitSampler(session, run, restart=None if args.no_restart
                                 else restart, image_lo=scanner.image_lo,
                                 image_hi=scanner.image_hi)
        addresses = scanner.functions(args.function, all_functions=args.all,
                                      limit=args.limit)
        if not addresses:
            print("укажите --function АДРЕС (можно несколько) или --all",
                  file=sys.stderr)
            return 2
        keys = parse_key_specs(args.key)
        results = [scanner.scan(address, hits=args.hits, timeout=args.timeout,
                                sampler=sampler, keys=keys or None)
                   for address in addresses]
        floor = _rank(args.min_confidence)
        for item in results:
            item["candidates"] = [candidate for candidate in item["candidates"]
                                  if _rank(candidate["confidence"]) >= floor]
        out = {"rom": os.path.basename(args.rom),
               "image": [addr_hex(scanner.image_lo), addr_hex(scanner.image_hi)],
               "functions": len(results),
               "results": results}
        order = ("very_low", "low", "medium", "high")
        ranked = []
        for item in results:
            func = item["function"] or {}
            owner = "%s (%s)" % (func.get("name") or "без имени",
                                 func.get("address") or "?")
            for candidate in item["candidates"]:
                entry = dict(candidate)
                register = (candidate.get("register") or candidate.get("name")
                            or candidate.get("index") or "?")
                entry["name"] = "аргумент %s у %s" % (register, owner)
                entry["object"] = "%s · %s" % (owner, register)
                entry["detail"] = "%s: %s" % (
                    candidate.get("role") or "?",
                    "; ".join(candidate.get("evidence") or [])[:180])
                ranked.append(entry)
        ranked.sort(key=lambda c: order.index(c["confidence"])
                    if c.get("confidence") in order else -1, reverse=True)
        out = envelope(
            out, module="abi_scan", session=session, cache=cache,
            status="CANDIDATE", candidates=ranked[:8],
            verdict="функций: %d, кандидатов параметров: %d"
                    % (len(results), len(ranked)),
            note="статика и динамические наблюдения дают кандидата на параметр "
                 "с уверенностью; соглашение о вызове по этим данным не "
                 "доказывается")
        if args.json:
            print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        else:
            print(format_report(results, header="%s: %d функц."
                                % (out["rom"], out["functions"])))
            print("\n# mcp calls: %d" % out["mcp_calls"])
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
