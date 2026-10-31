"""Снять партитуру мелодии заставки H.A.T.E. из assets/HATE_title_theme.ay.

Файл .ay — это НЕ регистровый стрим AY-чипа. Внутри лежит бипер-трек:
оригинальный Z80-плеер игры (область $8000-$85C5 — те же самые коды
голосов, что в логе assets/title_music.txt) плюс полная партитура.
Объявленная длина трека — SongLength тиков по 1/50 с.

ФОРМАТ. Описание в assets/ay_format.txt неполное: в нём пропущены
TSongData и TPoints, а «таблица адресов» описана как пара указателей,
из-за чего парсер уходит в мусор. Восстановлено по
vgmrips.net/wiki/AY_File_Format (первоисточник — readme.txt пакета
Micro Speccy), порядок записей такой:

  заголовок 20 байт: 'ZXAY' 'EMUL' FileVersion PlayerVersion
      PSpecialPlayer PSAuthor PSMisc FirstSong CountSongs PSSongStruct
  затем на каждый трек (CountSongs+1) по TSongStructure:
      PSSongName PSongData
  затем TSongData:
      AChan BChan CChan Noise  (байты)
      SongLength FadeLength    (BIG-Endian слова, 1/50 с)
      HiReg LoReg              (байты: все общие регистры = Hi/Lo)
      PPoints PAddresses       (относительные слова)
  затем TPoints: Stack, Init, Inter (BIG-Endian слова)
  затем блоки: (Address, Length, DataOffset) — три BIG-Endian слова,
      DataOffset относительный, терминатор таблицы — нулевое слово.

Все указатели знаковые и считаются от позиции самого указателя.

ЗАПУСК ПЛЕЕРА (правила версии PlayerVersion=3, там же): память
$0000-$00FF заполняется $C9, $0100-$3FFF — $FF, $4000-$FFFF — $00,
в $0038 пишется $FB, затем грузятся блоки, все общие регистры =
HiReg/LoReg, I=$03, SP=Stack, PC=$0000, и по нулевому адресу собирается
цикл: если Inter=0 — `DI / CALL Init / LOOP: IM 2 / EI / HALT / JR LOOP`,
если Inter=0 нет — `DI / CALL Init / LOOP: IM 1 / EI / HALT /
CALL Inter / JR LOOP`. Для нашего файла Inter=$001B лежит в
заполненной $C9 странице, то есть CALL превращается в RET: треком рулит
маска прерываний, а патч ROM-обработчика ($0064, 300 байт) уже в блоках.

Выход — тот же формат, что и в assets/title_music.txt, поэтому
tools/gen_title_music.py проглатывает его без изменений:

    # t_state frame pc value  (speaker flips, OUT ($FE),A)
    4894556 70 $836A 18

ЧТО ДАЛ ПРОГОН (2850 кадров, 32 250 переключений -> 57.00 с). Логи ниже —
промеры, по которым правится плеер; прежний assets/title_music.txt оборван
на 2000 кадрах (38.54 с), отсюда «не хватает куска в конце».

  * ЦИКЛ = ровно 2800 кадров (56.00 с). Поиск периода по сигнатуре кадра
    (какие коды и сколько раз в нём сработали): на сдвиге 2800 совпадает
    98.0 % кадров, у соседей 2796/2804 — только 33 %.
  * Один кадр Вектора = 59 904 такта = ровно 468 единиц по 128 такта, поэтому
    любая кадровая сетка представима без дрейфа: длина цикла = 1 310 400 ед.
  * Голоса: A $82D1/$82D9 — 4571 импульса (ширина 293 такта ZX, период
    30 534..153 487); B $8333/$833B — 8211 импульса (12 057..164 918); оба
    свободные, не кадровые. Клик $836A/$8375 — 163 импульса шириной 7221 такта
    на сетке 15 кадров (127 раз) с пропусками 20 (32) и 95 (3) кадров.
  * Ударные $8389: 65 вспышек, ВСЕ по 77 переключений с одним рисунком;
    сетка ровно 40 кадров (51+8 интервалов) с тремя пропусками по 120,
    фаза — кадр 20, последний пуск на кадре 2819.97 (то есть сетка из 70
    слотов замыкается на цикле). Прежний плеер заряжал первый слот полным
    периодом, поэтому ударные начинались на 21 кадр позже.
  * ТРИ свипа — часть партитуры, а не аттракт-демо (в gen_title_music.py они
    сидели в IGNORED_PC): $83A6 50 шагов от 1304 такта с шагом -26 (9.52 мс),
    $83D1 20 шагов от 2610 с шагом -52 (11.63 мс), $83B9 19 шагов от 2435
    с шагом +52 (14.80 мс); все — меандр. Очередь внутри цикла: 5x$83A6 на
    кадрах 800, 805 ... 820, затем 5x$83D1 (830..850), затем 4x$83B9
    (860..875); группы на 1760 и 2720, следующая — на 3600 = 2800+800, то
    есть интервал между 3-й и 1-й группами 880 кадров, а не 960.

ПОЧЕМУ СБИВАЕТСЯ И ЧТО ДЕЛАТЬ. Нынешний плеер (include/beep.asm) считает
интервал ПОСЛЕ импульса: fire_x заряжает cd_x своим периодом, а следующая
запись подхватывается только на следующем шаге (mus_refill). Поэтому весь
голос сдвинут на период ПЕРВОЙ записи — клик стартует на 15 кадров позже,
а первый слот шума (mus_restart берёт mus_np целиком вместо фазы в 20
кадров) — на 21. Генератор же выбрасывал и начальный сдвиг сетки
(burst_schedule), и три свипа (IGNORED_PC).

План правки: записи с задержкой ДО импульса; привязка абсолютная
(p = round((цель - накопленное) / n), остаток не накапливается); каждый
скрипт длится ровно 1 310 400 единиц и кончается терминатором, который
отматывает указатель СВОЕГО голоса — все голоса смыкаются на одном шаге,
это и есть цикл; ударные и свипы — списки событий «отсчёт + действие»,
свипы — таблицы полупериодов битами по 32 такта (минимум ~92 такта,
хвост свипа упирается в него и усекается); прерывание по любой клавише
(kbd_any -> pl_skip) остаётся как есть. Подробно — SOUND_FIX.MD.

Запуск:
    python3 tools/ay_beeper.py                 # длина из SongLength
    python3 tools/ay_beeper.py --frames 11300  # с запасом (2 прохода)
    python3 tools/ay_beeper.py --wav           # плюс WAV для прослушивания
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = os.path.dirname(HERE)
ASSETS = os.path.join(PORT, 'assets')
SKOOLKIT = os.path.abspath(os.path.join(
    PORT, '..', '..', '..', '..', 'zx-disasm', 'skoolkit'))

if SKOOLKIT not in sys.path:
    sys.path.insert(0, SKOOLKIT)

import skoolkit                                    # noqa: E402
from skoolkit.simutils import from_memory, PC, T   # noqa: E402

CPU_HZ = 3_500_000
FRAME_DURATION = 69888          # тактов ZX на кадр (48K)
SPEAKER_BIT = 0x10


# ---------------------------------------------------------------- AY ---------
def parse_ay(path):
    """Разобрать .ay в dict: метаданные + точки входа + блоки."""
    d = open(path, 'rb').read()
    assert d[:8] == b'ZXAYEMUL', 'не AY-файл'
    be = lambda p: struct.unpack('>H', d[p:p + 2])[0]
    rel = lambda p: p + be(p)
    zstr = lambda p: d[p:d.index(0, p)].decode('latin-1')

    out = dict(ver=d[8], player=d[9], author=zstr(rel(12)),
               misc=zstr(rel(14)), nsongs=d[17] + 1)
    ss = rel(18)
    name = rel(ss)
    sd = rel(ss + 2)
    out['name'] = zstr(name)
    out['song_length'] = be(sd + 4)
    out['fade'] = be(sd + 6)
    out['hireg'], out['loreg'] = d[sd + 8], d[sd + 9]
    pt = rel(sd + 10)
    out['stack'] = struct.unpack('>H', d[pt:pt + 2])[0] & 0xFFFF
    out['init'] = struct.unpack('>H', d[pt + 2:pt + 4])[0] & 0xFFFF
    out['inter'] = struct.unpack('>H', d[pt + 4:pt + 6])[0] & 0xFFFF
    blocks = []
    i = rel(sd + 12)
    while be(i):
        addr, ln = be(i), be(i + 2)
        data = i + 4 + be(i + 4)
        assert data + ln <= len(d), 'блок %04X вылезает за файл' % addr
        blocks.append((addr, bytes(d[data:data + ln])))
        i += 6
    out['blocks'] = blocks
    return out


def build_memory(ay):
    """Собрать 48K-образ по правилам плеера версии 3."""
    mem = ([0xC9] * 0x0100 + [0xFF] * 0x3F00 + [0x00] * 0xC000)[:0x10000]
    mem[0x38] = 0xFB
    init = ay['init'] or ay['blocks'][0][0]
    inter = ay['inter']
    # DI / CALL init / LOOP: IM x / EI / HALT / (CALL inter) / JR LOOP
    boot = [0xF3, 0xCD] + list(struct.pack('<H', init))
    loop = len(boot)                       # метка LOOP
    boot += [0xED, 0x56 if inter else 0xFD, 0xFB, 0x76]
    if inter:
        boot += [0xCD] + list(struct.pack('<H', inter))
    boot += [0x18, (loop - len(boot) - 2) & 0xFF]
    for a in range(len(boot)):
        mem[a] = boot[a]
    for addr, blob in ay['blocks']:
        mem[addr:addr + len(blob)] = blob
    return mem, boot


# ------------------------------------------------------------- эмулятор ------
class BeeperTracer:
    """Ловит переключения динамика: OUT(порты чётные) бит 4."""

    def __init__(self):
        self.border = 7
        self.outfe = 0
        self.spkr = None
        self.flips = []                 # (t_state, pc, value)

    def read_port(self, registers, port):
        return 0xFF

    def write_port(self, registers, port, value, offset):
        self.outfe = value
        if port % 2 == 0 and self.spkr != value & SPEAKER_BIT:
            self.spkr = value & SPEAKER_BIT
            self.flips.append((registers[T], registers[PC], value & 0x18))


def run(ay, frames):
    mem, boot = build_memory(ay)
    lo, hi = ay['loreg'], ay['hireg']
    registers = {'A': hi, 'F': lo, 'B': hi, 'C': lo, 'D': hi, 'E': lo,
                 'H': hi, 'L': lo, 'IX': hi * 256 + lo, 'IY': hi * 256 + lo,
                 'I': 3, 'PC': 0, 'SP': ay['stack']}
    sim = from_memory(skoolkit.CSimulator, mem, registers,
                      {'iff': 0, 'im': 0, 'tstates': 0})
    tr = BeeperTracer()
    sim.set_tracer(tr)
    sim.trace(0, 0x10000, 0, frames * FRAME_DURATION, 1, None, None, None,
              None, None)
    return tr, sim, boot


def wav(path, flips):
    sys.path.insert(0, SKOOLKIT)
    from skoolkit.audio import AudioWriter, BeeperOptions
    delays = [b[0] - a[0] for a, b in zip(flips, flips[1:])]
    with open(path, 'wb') as f:
        AudioWriter().write_audio(f, delays,
                                  BeeperOptions(100, False, False, 0, False))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--src', default=os.path.join(ASSETS,
                                                  'HATE_title_theme.ay'))
    ap.add_argument('--out', default=os.path.join(ASSETS,
                                                  'title_music_ay.txt'))
    ap.add_argument('--frames', type=int, default=0,
                    help='кадров прогнать (0 = SongLength + 50)')
    ap.add_argument('--wav', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    ay = parse_ay(args.src)
    frames = args.frames or (ay['song_length'] or 5602) + 50
    tr, sim, boot = run(ay, frames)
    reg = sim.registers

    print('%s: %s' % (os.path.basename(args.src), ay['name']))
    print('  плеер v%d, автор %r, %r' % (ay['player'], ay['author'], ay['misc']))
    print('  SongLength %d тиков = %.2f с, прогон %d кадров = %.2f с'
          % (ay['song_length'], ay['song_length'] / 50.0, frames,
             frames / 50.0))
    print('  точки: SP=%04X INIT=%04X INTER=%04X, блоки: %s'
          % (ay['stack'], ay['init'], ay['inter'],
             ', '.join('%04X/%d' % (a, len(b)) for a, b in ay['blocks'])))
    print('  загрузка по 0000: ' + ' '.join('%02X' % b for b in boot))
    print('  переключений %d, время до %.2f с, PC=%04X SP=%04X I=%02X '
          'IFF=%d IM=%d'
          % (len(tr.flips), tr.flips[-1][0] / CPU_HZ if tr.flips else 0,
             reg[PC], reg[12] & 0xFFFF, reg[14], reg[26], reg[27]))
    sites = {}
    for _, pc, _ in tr.flips:
        sites[pc] = sites.get(pc, 0) + 1
    print('  переключения по кодам: ' +
          ', '.join('$%04X x%d' % (p, n)
                    for p, n in sorted(sites.items()))[:600])

    with open(args.out, 'w') as f:
        f.write('# t_state frame pc value  (speaker flips, OUT ($FE),A)\n')
        for t, pc, v in tr.flips:
            f.write('%d %d $%04X %02X\n' % (t, t // FRAME_DURATION, pc, v))
    print('  -> %s (%d строк)' % (os.path.relpath(args.out, PORT),
                                  len(tr.flips)))
    if args.wav:
        w = os.path.splitext(args.out)[0] + '.wav'
        wav(w, tr.flips)
        print('  -> %s' % os.path.relpath(w, PORT))


if __name__ == '__main__':
    main()
