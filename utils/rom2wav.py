#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rom2wav.py — конвертер .rom/.r0m файлов Вектор-06Ц в WAV.

Тот же алгоритм ленты v06c-rom, что и rom2mp3.py, но выход — несжатый WAV.

Зависимости: не нужны (стандартный модуль wave).

Качество WAV: 8-bit unsigned PCM, mono, тот же SAMPLE_RATE, что в rom2mp3.py.
"""

import sys, os, argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from rom2mp3 import (
    maketape_v06c_rom, byte_to_samples, lead_in_out,
    SAMPLE_RATE,
)

BITS = 8


def tape_to_wav(tape: bytes, output_path: str) -> None:
    """Байты ленты → WAV (8-bit unsigned PCM mono)."""
    import wave

    lead = lead_in_out()
    pcm = bytearray()
    pcm += lead
    for b in tape:
        pcm += byte_to_samples(b)
    pcm += lead

    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)       # mono
        wf.setsampwidth(1)       # 8 bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(pcm))


def convert_rom_to_wav(input_path: str, output_path: str,
                       tape_name: str | None = None) -> None:
    """Главная функция: ROM/R0M → WAV."""
    ext = Path(input_path).suffix.lower()
    load_addr = 0x0000 if ext == ".r0m" else 0x0100

    with open(input_path, "rb") as f:
        rom_data = f.read()

    if not rom_data:
        sys.exit(f"Ошибка: файл {input_path} пуст.")

    if tape_name is None:
        tape_name = Path(input_path).stem.upper()[:25]

    print(f"Входной файл:   {input_path}")
    print(f"Выходной файл:  {output_path}")
    print(f"Адрес загрузки: 0x{load_addr:04X}")
    print(f"Имя ленты:      {tape_name}")
    print(f"Размер данных:  {len(rom_data)} байт")

    tape = maketape_v06c_rom(rom_data, load_addr, tape_name)
    tape_to_wav(tape, output_path)
    print(f"WAV создан: {output_path}  ({BITS} bit, {SAMPLE_RATE} Hz, mono)")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Конвертер .rom/.r0m (Vector-06C) → WAV"
    )
    p.add_argument("input",  help="Входной .rom или .r0m файл")
    p.add_argument("output", nargs="?", default=None,
                   help="Выходной .wav файл (по умолчанию: <input>.wav)")
    p.add_argument("-n", "--name", default=None,
                   help="Имя ленты (макс. 25 симв., по умолчанию = имя файла)")
    args = p.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"Файл не найден: {args.input}")

    output = args.output if args.output else str(Path(args.input).with_suffix(".wav"))
    convert_rom_to_wav(args.input, output, args.name)


if __name__ == "__main__":
    main()
