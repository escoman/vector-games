#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rom2mp3.py — конвертер .rom/.r0m файлов Вектор-06Ц в MP3.

Формат ленты — v06c-rom (алгоритм svofski, переписан с bin2wav.c).
  • .rom  → адрес загрузки 0x0100
  • .r0m  → адрес загрузки 0x0000

Зависимости:
  pip3 install --break-system-packages pydub
  sudo apt install ffmpeg

Качество MP3: 320 kbit/s (макс. стандартное), mono, 44100 Hz.
"""

import sys, os, argparse, struct
from pathlib import Path

try:
    from pydub import AudioSegment
except ImportError:
    sys.exit(
        "Ошибка: нужен pydub.\n"
        "  pip3 install --break-system-packages pydub\n"
        "  sudo apt install ffmpeg"
    )

# ─────────────────────────────────────────────────────────────
#  Параметры формата Vector-06C
# ─────────────────────────────────────────────────────────────
SPEED       = 10         # длительность одной фазы, сэмплов
SAMPLE_RATE = 44100      # частота дискретизации (MPEG-1 для 320 kbps)
MP3_BITRATE = 320        # качество MP3, kbit/s (макс. стандартное)

PHASE_H1 = 32            # высокий уровень для бита «1»
PHASE_L1 = 255 - 32      # низкий  уровень для бита «1»
PHASE_H0 = 255 - 32      # высокий уровень для бита «0»
PHASE_L0 = 32            # низкий  уровень для бита «0»

# ─────────────────────────────────────────────────────────────
#  Низкоуровневые построители волны
# ─────────────────────────────────────────────────────────────

def bit_to_samples(bit: int) -> bytes:
    """Один бит → SPEED*2 байтов (8-бит unsigned mono)."""
    if bit:
        return bytes([PHASE_H1] * SPEED + [PHASE_L1] * SPEED)
    else:
        return bytes([PHASE_H0] * SPEED + [PHASE_L0] * SPEED)


def byte_to_samples(b: int) -> bytes:
    """Байт → 16*SPEED сэмплов, MSB first."""
    out = bytearray()
    for _ in range(8):
        out += bit_to_samples(b & 0x80)
        b = (b << 1) & 0xFF
    return bytes(out)


def silence_bytes(n: int) -> bytes:
    """n сэмплов тишины (0x80 = середина для unsigned 8-bit)."""
    return bytes([0x80] * n)


def lead_in_out() -> bytes:
    """0.4 секунды тишины — паддинг в начале и конце (как в bin2wav)."""
    return silence_bytes(int(SAMPLE_RATE * 0.4))


# ─────────────────────────────────────────────────────────────
#  Формат ленты v06c-rom
# ─────────────────────────────────────────────────────────────

def make_preamble() -> bytes:
    """200 байт: 25×0x00, 25×0x55, … (8 групп)."""
    out = bytearray()
    for i in range(200):
        out.append(0x00 if (i // 25) % 2 == 0 else 0x55)
    return bytes(out)


def make_block_header(tape_name: str, load_addr: int,
                      nblocks: int, block: int, cs0: int) -> bytes:
    """Заголовок одного блока (40 байт)."""
    name_bytes = tape_name.encode("ascii", errors="replace")[:25]
    name_padded = name_bytes + b" " * (25 - len(name_bytes))

    hdr = bytearray()
    hdr += b"\x00" * 16                       # block preamble
    hdr += b"\x55" * 4 + b"\xE6"              # sync
    hdr += b"\x00" * 4                        # padding
    hdr += name_padded                        # 25 байт имени
    hdr += b"\x00\x00"                        # padding
    hdr.append((load_addr >> 8) & 0xFF)       # hi-byte адреса
    hdr.append(nblocks & 0xFF)                # число блоков
    hdr.append((nblocks - block) & 0xFF)      # обратный номер
    hdr.append(cs0 & 0xFF)                    # контрольная сумма
    return bytes(hdr)


def make_subblock(sblk_id: int, cs0: int, payload: bytes) -> bytes:
    """Один подблок данных (37 байт: 4+1+1+1+32+1)."""
    sb = bytearray()
    sb += b"\x00" * 4 + b"\xE6"              # sync
    sb.append(sblk_id)                        # 0x80…0x87
    sb.append(cs0 & 0xFF)                     # cs0 из заголовка
    sb += payload[:32].ljust(32, b"\x00")     # 32 байта данных
    # контрольная сумма подблока
    cs = (sblk_id + cs0 + sum(payload[:32])) & 0xFF
    sb.append(cs)
    return bytes(sb)


def maketape_v06c_rom(rom_data: bytes, load_addr: int,
                      tape_name: str) -> bytes:
    """Полный поток байт ленты для формата v06c-rom."""
    bin_size = len(rom_data)
    nblocks  = (bin_size + 255) // 256
    sofs     = 0
    out      = bytearray()

    # Preamble
    out += make_preamble()

    for block in range(nblocks):
        # --- checksum заголовка (cs0) ---
        name_bytes = tape_name.encode("ascii", errors="replace")[:25]
        name_padded = name_bytes + b" " * (25 - len(name_bytes))
        cs0 = sum(name_padded) & 0xFF
        cs0 = (cs0 + ((load_addr >> 8) & 0xFF) + nblocks + (nblocks - block)) & 0xFF

        out += make_block_header(tape_name, load_addr, nblocks, block, cs0)

        # 8 подблоков по 32 байта
        for sblk in range(0x80, 0x88):
            chunk = rom_data[sofs:sofs + 32]
            sofs += 32
            out += make_subblock(sblk, cs0, chunk)

    return bytes(out)


# ─────────────────────────────────────────────────────────────
#  Кодирование в PCM и экспорт в MP3
# ─────────────────────────────────────────────────────────────

def tape_to_pcm(tape: bytes) -> AudioSegment:
    """Байты ленты → AudioSegment (8-bit unsigned mono, 22050 Hz)."""
    pcm = bytearray()
    pcm += lead_in_out()
    for b in tape:
        pcm += byte_to_samples(b)
    pcm += lead_in_out()

    seg = AudioSegment(
        data=bytes(pcm),
        sample_width=1,        # 8 bit
        frame_rate=SAMPLE_RATE,
        channels=1
    )
    return seg


def convert_rom_to_mp3(input_path: str, output_path: str,
                       tape_name: str | None = None) -> None:
    """Главная функция: ROM/R0M → MP3."""
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
    audio = tape_to_pcm(tape)

    audio.export(output_path, format="mp3",
                 parameters=["-b:a", f"{MP3_BITRATE}k", "-ar", str(SAMPLE_RATE)])
    print(f"MP3 создан: {output_path}  ({MP3_BITRATE}k)")


# ─────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(
        description="Конвертер .rom/.r0m (Vector-06C) → MP3"
    )
    p.add_argument("input",  help="Входной .rom или .r0m файл")
    p.add_argument("output", nargs="?", default=None,
                   help="Выходной .mp3 файл (по умолчанию: <input>.mp3)")
    p.add_argument("-n", "--name", default=None,
                   help="Имя ленты (макс. 25 симв., по умолчанию = имя файла)")
    args = p.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"Файл не найден: {args.input}")

    output = args.output if args.output else str(Path(args.input).with_suffix(".mp3"))
    convert_rom_to_mp3(args.input, output, args.name)


if __name__ == "__main__":
    main()
