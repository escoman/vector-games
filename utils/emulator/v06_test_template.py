#!/usr/bin/env python3
"""Template for C/reference-model vs 8080 ASM regression tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v06_emu import Emulator8080, TestCase, TestRunner, ReferenceResult, MemoryExpectation, format_mismatch

ASM = "your_routine.asm"


def reference(case, initial_memory):
    # Independent Python implementation of the C algorithm.
    # Do not read emulator state here.
    # Return expected memory/register/write trace as needed.
    return ReferenceResult(
        memory=(),
        registers=None,
        writes=(),
    )


def main():
    emu = Emulator8080()
    asm = emu.load_asm(ASM)
    runner = TestRunner(emu)

    cases = [
        TestCase(
            name="basic case",
            entry="your_entry_label",
            args=(0x1234, 0x0056),
            initial_memory={0x6000: 0x00},
            memory=(
                # MemoryExpectation(0x6000, 0x12, description="..."),
            ),
            expected_registers={
                # "a": 0x12,
                # "hl": ...  # use h/l separately for now
            },
        ),
    ]

    results = runner.run_all(cases, reference=reference, trace=True)
    failed = False
    for result in results:
        print(format_mismatch(result))
        if not result.passed:
            failed = True
            # On failure, the complete instruction trace is available here:
            for t in runner.emulator.cpu.trace[-20:]:
                pre=t["pre"]
                post=t["post"]
                print(f"  step={t['step']:6d} PC={t['pc']:04X} OP={t['opcode']:02X} "
                      f"SP={pre['sp']:04X}->{post['sp']:04X} "
                      f"A={pre['a']:02X}->{post['a']:02X} "
                      f"HL={pre['h']:02X}{pre['l']:02X}->{post['h']:02X}{post['l']:02X}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
