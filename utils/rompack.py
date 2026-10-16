#!/usr/bin/env python3
"""rompack.py — упаковка ROM Вектора-06Ц в самораспаковывающийся образ .r0m.

Берёт обычный .rom (образ, грузимый в 0x0100 и исполняемый с него), сжимает
его ZX0-потоком «backward» (utils/zx0.py::compress_backwards) и оборачивает в
крошечный 8080-stub (lib/unpack/unpack_r0m.asm). Полученный файл .r0m ядро
эмулятора грузит по адресу 0x0000 и запускает с него: stub обратнораспаковывает
оригинал обратно в 0x0100 и передаёт ему управление.

Почему именно .r0m / 0x0000 (см. vector-psp src/emulator.cpp::get_rom_org):
адрес загрузки берётся из предпоследнего символа имени — для «.r0m» это '0' →
org 0x0000, загрузка идёт через ResetMode::LOADROM, который ОТКЛЮЧАЕТ boot, так
что 0x0000.. — обычная RAM. Раз место назначения приковано к 0x0100, а поток
лежит НИЖЕ (с 0x0000), обратная распаковка безопасна «по себе»: write-указатель
всё время строже выше непрочитанного read-указателя, отдельная staging-память
не нужна, и сам stub (код ниже 0x0100) не затирается.

Раскладка упакованного .r0m (всё от 0x0000):
    stub (bootstrap + backward-ядро, собран в org 0x0000)  ~116 байт, const
    сжатый поток ZX0 backward                               stream_len байт
    хвост: orig_len(16, LE) + MAGIC 'VZPK'                 6 байт — метка/размер

Stub исполняется ровно там, где собран (org 0x0000), поэтому его внутренние
CALL/JMP резолвятся без relocation — ОДИН проход сборки. Rompack подставляет
только два 16-битных immediates (размер кода от них не зависит):
    -Dsrc_last = S + stream_len - 1     (адрес последнего байта потока)
    -Ddst_last = 0x0100 + orig_len - 1  (адрес последнего байта оригинала)

Валидация раскладки (до записи; обратная in-place требует поток НИЖЕ назначения):
    S          <  0x0100            (низ потока ниже низа dst → зазор > 0)
    src_last   <  STUB_SP - MARGIN  (поток не залезает в стек stub)
    dst_last   <  STUB_SP - MARGIN  (оригинал не залезает в стек stub)
    S + stream_len + tail <= 0x10000(образ целиком влезает в 64 КБ)
где STUB_SP = 0xFF00 (вершина стека, задаётся в stub), MARGIN = 64.

Использование:
    python3 utils/rompack.py in.rom -o out.r0m [--verify]
    python3 utils/rompack.py --self-test

Идемпотентность: если вход уже упакован (MAGIC в хвосте), повторная упаковка
не выполняется — образ копируется как есть (защита от двойной упаковки).
"""
import argparse
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import zx0  # noqa: E402

STUB_ASM = os.path.join(ROOT, 'lib', 'unpack', 'unpack_r0m.asm')
MAGIC = b'VZPK'
TAIL_LEN = 6                    # orig_len(2) + MAGIC(4)
ENTRY_ORG = 0x0000              # .r0m грузится и стартует с 0x0000
DST_ORG = 0x0100                # оригинал распаковывается в 0x0100
STUB_SP = 0xFF00                # вершина стека stub (должна совпасть с asm)
STACK_MARGIN = 64               # запас под стек декодера выше dst/src


def find_z80asm(explicit=None):
    """Путь к z80asm: --z80asm > $Z88DK/bin > локальный тулчейн репозитория."""
    if explicit:
        return explicit
    env = os.environ.get('Z88DK')
    if env:
        cand = os.path.join(env, 'bin', 'z80asm')
        if os.path.exists(cand):
            return cand
    cand = os.path.join(ROOT, 'z88dk', 'bin', 'z80asm')
    if os.path.exists(cand):
        return cand
    return 'z80asm'             # пусть ищет в PATH


def is_packed(data):
    return len(data) >= TAIL_LEN and data[-4:] == MAGIC


def read_orig_len(data):
    return struct.unpack('<H', data[-6:-4])[0]


def assemble_stub(z80asm, src_last, dst_last):
    """Собрать stub (bootstrap + backward-ядро) в org 0x0000. Размер постоянен
    и не зависит от src_last/dst_last (это только 16-битные immediates)."""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, 'stub.bin')
        cmd = [z80asm, '-b', '-m=8080_strict',
               f'-Dsrc_last={src_last}',
               f'-Ddst_last={dst_last}',
               '-o=' + out, STUB_ASM]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError('z80asm не собрал stub:\n' + res.stdout +
                               res.stderr)
        with open(out, 'rb') as f:
            return f.read()


def validate(orig_len, stream_len, stub_size):
    src_last = stub_size + stream_len - 1
    dst_last = DST_ORG + orig_len - 1
    if stub_size >= DST_ORG:
        return (f'stub вырос за векторную страницу: size={stub_size} >= 0x100. '
                f'Низ потока не ниже назначения — обратная распаковка нестабильна.')
    src_last = stub_size + stream_len - 1
    dst_last = DST_ORG + orig_len - 1
    if src_last >= dst_last:
        return (f'поток не сжался и перекрывает назначение сверху: '
                f'src_last=0x{src_last:04X} >= dst_last=0x{dst_last:04X} '
                f'(stream={stream_len} >= orig={orig_len}). Обратная in-place '
                f'распаковка невозможна — данные несжимаемы.')
    if DST_ORG + orig_len > STUB_SP - STACK_MARGIN:
        return (f'оригинал залезает в стек stub: dst_end=0x{DST_ORG+orig_len:04X} '
                f'> 0x{STUB_SP-STACK_MARGIN:04X}. Уменьшите ROM или поднимите '
                f'STUB_SP в unpack_r0m.asm.')
    if src_last > STUB_SP - STACK_MARGIN:
        return (f'поток залезает в стек stub: src_last=0x{src_last:04X} > '
                f'0x{STUB_SP-STACK_MARGIN:04X}. Слишком большой образ.')
    if stub_size + stream_len + TAIL_LEN > 0x10000:
        return ('упакованный образ не влезает в 64 КБ по адресу 0x0000 '
                f'(size={stub_size + stream_len + TAIL_LEN}).')
    return None


def pack(data, z80asm=None, verbose=True):
    """Упаковать образ data → самораспаковывающийся .r0m (bytes)."""
    if is_packed(data):
        if verbose:
            print('уже упакован — пропускаю')
        return data
    orig_len = len(data)
    if orig_len == 0:
        raise ValueError('пустой образ не упаковывается')
    stream = zx0.compress_backwards(data)
    stream_len = len(stream)
    asm = find_z80asm(z80asm)
    # 1-й проход: дознать фиксированный размер stub S (immediates не влияют).
    stub_size = len(assemble_stub(asm, 0, 0))
    err = validate(orig_len, stream_len, stub_size)
    if err:
        raise ValueError(err)
    src_last = stub_size + stream_len - 1
    dst_last = DST_ORG + orig_len - 1
    # 2-й проход: те же параметры, что сшеёт поток и оригинал по местам.
    stub = assemble_stub(asm, src_last, dst_last)
    if len(stub) != stub_size:
        raise RuntimeError(f'размер stub поплыл: {len(stub)} != {stub_size}')
    packed = stub + stream + struct.pack('<H', orig_len) + MAGIC
    if verbose:
        pct = 100.0 * len(packed) / orig_len
        print(f'rompack: {orig_len} -> {len(packed)} байт ({pct:.1f}%), '
              f'stub={stub_size} stream={stream_len} '
              f'dst=[0x{DST_ORG:04X}..0x{dst_last:04X}] '
              f'src=[0x{stub_size:04X}..0x{src_last:04X}]')
    return packed


# ---------------------------------------------------------------------------
# Проверка в эмуляторе: прогнать stub с 0x0000 и сверить распакованный оригинал.
# ---------------------------------------------------------------------------
def verify(packed, orig, max_steps=40_000_000):
    """Загрузить packed в 0x0000, исполнять stub до перехода в 0x0100 (RET ядра),
    сверить mem[0x0100 : 0x0100+len(orig)] с оригиналом. Это end-to-end проверка
    stub + backward-ядра + потока в реальной in-place раскладке."""
    sys.path.insert(0, os.path.join(ROOT, 'utils', 'emulator'))
    from v06_emu import CPU8080
    cpu = CPU8080()
    for i, b in enumerate(packed):
        cpu.mem[ENTRY_ORG + i] = b
    cpu.pc = ENTRY_ORG
    cpu.sp = STUB_SP
    cpu.halted = False
    cpu.steps = 0
    steps = cpu.run_until(max_steps=max_steps, stop_pc=DST_ORG)
    if steps is None or cpu.pc != DST_ORG:
        raise RuntimeError(f'stub не перешёл в 0x{DST_ORG:04X} за '
                           f'{max_steps} шагов (pc=0x{cpu.pc:04X}, '
                           f'steps={cpu.steps})')
    got = bytes(cpu.mem[DST_ORG:DST_ORG + len(orig)])
    if got != orig:
        j = next((k for k in range(len(orig)) if got[k] != orig[k]), len(orig))
        raise RuntimeError(f'распакованный образ не совпал с оригиналом: '
                           f'первое расхождение @+0x{j:04X} '
                           f'(stub выдал 0x{got[j]:02X}, ждал 0x{orig[j]:02X})')
    return cpu.steps


def _self_test():
    import random
    root = ROOT
    print('rompack self-test (.r0m backward)')

    # 1) синтетика: сжимаемые профили данных (in-place раскладка требует, чтобы
    #    поток был не выше назначения — раздутые случайные данные сюда не берём).
    cases = []
    rnd = random.Random(4242)
    cases.append(b'\x00' * 512)                         # много нулей
    cases.append(bytes(range(256)) * 4)                 # период
    cases.append(b'A' + bytes(rnd.choice([0x00, 0xFF, 0x41]) for _ in range(900)))
    # псевдо-ROM: код+данные с повторами таблиц
    prog = bytearray(b'\xc3\x00\x01')                   # JP 0x0100
    for _ in range(200):
        prog += bytes(rnd.choice([0x06, 0x3E, 0x32, 0xC3]) for _ in range(3))
        prog += bytes(rnd.getrandbits(8) for _ in range(rnd.randrange(1, 8)))
    prog += b'\x00' * 64
    cases.append(bytes(prog))

    for i, data in enumerate(cases):
        packed = pack(data, verbose=False)
        assert is_packed(packed), 'нет метки упаковки'
        assert read_orig_len(packed) == len(data), 'orig_len в хвосте неверен'
        steps = verify(packed, data)
        print(f'  [{i}] orig={len(data):6d} packed={len(packed):6d} '
              f'({100.0*len(packed)/len(data):5.1f}%) verify OK '
              f'({steps} шагов)')

    # 2) идемпотентность: повторная упаковка не меняет образ
    again = pack(packed, verbose=False)
    assert again == packed, 'повторная упаковка должна быть no-op'
    print('  идемпотентность OK')

    # 3) реальный ROM проекта, если собран
    real = os.path.join(root, 'roms', 'tests', 'cls', 'cls.rom')
    if os.path.exists(real):
        data = open(real, 'rb').read()
        packed = pack(data, verbose=False)
        verify(packed, data)
        print(f'  cls.rom: {len(data)} -> {len(packed)} '
              f'({100.0*len(packed)/len(data):.1f}%) verify OK')
    else:
        print('  cls.rom не найден — реальный тест пропущен (соберите make)')

    # 4) отказ раскладки: оригинал перерастает стек stub (dst_end > 0xFF40)
    try:
        pack(b'\x00' * 65100, verbose=False)
        raise AssertionError('должен был отказать по раскладке (dst в стек)')
    except ValueError as e:
        print(f'  отказ раскладки OK: {e}')

    print('Все проверки rompack пройдены.')
    return 0


def out_r0m_name(in_path):
    """foo.rom -> foo.r0m (для --verify/дефолтного имени)."""
    base, _ = os.path.splitext(in_path)
    return base + '.r0m'


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Упаковка ROM Вектора-06Ц в самораспаковывающийся .r0m '
                    '(backward, грузится в 0x0000).')
    ap.add_argument('inp', nargs='?', help='входной .rom (обычный образ)')
    ap.add_argument('-o', '--out', help='выходной .r0m')
    ap.add_argument('--z80asm', help='путь к z80asm (по умолчанию из $Z88DK)')
    ap.add_argument('--verify', action='store_true',
                    help='прогнать stub в эмуляторе и сверить образ')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not args.inp:
        ap.error('нужен входной .rom (или --self-test)')
    out = args.out or out_r0m_name(args.inp)

    with open(args.inp, 'rb') as f:
        data = f.read()
    was_packed = is_packed(data)
    packed = pack(data, z80asm=args.z80asm)
    if args.verify and not was_packed:
        verify(packed, data)
        print('verify OK: эмулятор восстановил оригинал из .r0m')
    with open(out, 'wb') as f:
        f.write(packed)
    if not was_packed:
        pct = 100.0 * len(packed) / len(data)
        print(f'{args.inp} -> {out}: {len(data)} -> {len(packed)} '
              f'байт ({pct:.1f}%)')
    else:
        print(f'{args.inp} уже упакован — скопирован в {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
