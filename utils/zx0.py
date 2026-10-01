#!/usr/bin/env python3
"""zx0.py — компрессор ZX0 для сборки ROM Вектора-06Ц.

Сжимает произвольные байтовые данные (партитуры music.c, экраны и т.п.)
в формат ZX0 «standard». Распаковка на цели — 8080-декодер
lib/unpack/zx0.asm (порт эталонного DeZX dzx0_standard от Einar Saukas /
Ivan Gorodetsky, лежит в дереве z88dk: _DEVELOPMENT/compress/zx0/8080).

Модуль содержит ТОЧНУЮ Python-модель целевого 8080-декодера
(``dzx0_standard``), побайтово повторяющую поток состояний ассемблера:
битовый буфер-аккумулятор с часовым битом 0x80, interlaced Elias-gamma,
встроенный (interlaced) байт смещения. Поэтому поток, который выдаёт
``compress``, гарантированно читается и ассемблером на Векторе.

Формат ZX0 «standard» (см. dzx0.asm):
  * Литералы:                 Elias(len)  byte[len]
  * Повтор с тем же смещением: бит 0, Elias(len)
  * Повтор с новым смещением:  бит 1, Elias(msb) <байт смещения> Elias(len)
  * Конец потока (EOF):        бит 1, Elias(256)  (msb lo == 0)
Младший бит встроенного байта смещения «переплетён» с первым битом
Elias-кода длины (interlaced).

Использование (библиотека):
    from zx0 import compress, decompress
    packed = compress(data)
    assert decompress(packed) == data

CLI:
    python3 utils/zx0.py c input.bin output.zx0   # сжать
    python3 utils/zx0.py d input.zx0 output.bin    # распаковать
    python3 utils/zx0.py --self-test               # round-trip тесты
"""

import sys

# ---------------------------------------------------------------------------
# Elias-gamma (interlaced), как в dzx0.asm
# ---------------------------------------------------------------------------


def _elias_gamma(value):
    """Биты interlaced Elias-gamma для value >= 1.

    Декодер (dzx0s_elias_loop) читает ПАРАМИ: флаг-бит (1 -> вернуть
    накопленное, 0 -> продолжить), затем бит данных: value = value*2 +
    data_bit. Старт value = 1. Пусть m = floor(log2(value)); тогда
    value = 2^m + rem, rem = value - 2^m (0 <= rem < 2^m). Код: m пар
    «0 data_i» (data_i = биты rem, старший первым) и завершающий «1».
    Всего 2m+1 бит. Возвращаем список битов MSB-first.
    """
    if value < 1:
        raise ValueError('elias: значение должно быть >= 1')
    m = value.bit_length() - 1      # floor(log2(value))
    rem = value - (1 << m)          # 0 .. 2^m - 1
    bits = []
    for i in range(m):
        bits.append(0)                          # флаг «продолжить»
        bits.append((rem >> (m - 1 - i)) & 1)   # бит данных
    bits.append(1)                              # терминальный флаг
    return bits


# ---------------------------------------------------------------------------
# побитовый вывод со вставкой сырых байтов (байт смещения interlaced)
# ---------------------------------------------------------------------------


class _BitWriter:
    """Поток ZX0: биты Elias и сырые байты (литералы/смещение) делят ОДИН
    указатель чтения HL в декодере.

    Ключевая тонкость формата: декодер читает биты Elias из
    аккумулятора, который подгружает из HL ЦЕЛЫЕ байты, а литералы и байт
    смещения читает из HL напрямую (mov a,m / ldir). Когда после Elias
    идут сырые байты, в аккумуляторе остаются НЕДОЧИТАННЫЕ биты текущего
    байта — декодер использует их уже ПОСЛЕ сырых байтов. Значит в потоке
    частично заполненный «битовый» байт ФИЗИЧЕСКИ стоит ПЕРЕД сырыми
    байтами, но его младшие (ещё не записанные) биты — это содержимое,
    логически идущее ПОСЛЕ них.

    Поэтому: put_bit дописывает биты в текущий ОТКРЫТЫЙ байт (открывая
    новый в конце потока по мере заполнения); put_raw_byte дописывает сырой
    байт В КОНЕЦ, оставляя открытый битовый байт недозаполненным — его
    остаток будет дозаписан следующими put_bit. Выравнивание по границе
    байта НЕ требуется.
    """

    def __init__(self):
        self.out = bytearray()
        self.cur_index = -1     # индекс открытого битового байта, -1 если нет
        self.cur_nbits = 0      # сколько битов уже записано в out[cur_index]

    def put_bit(self, b):
        if self.cur_index == -1:            # открыть новый битовый байт
            self.out.append(0)
            self.cur_index = len(self.out) - 1
            self.cur_nbits = 0
        self.out[self.cur_index] |= (b & 1) << (7 - self.cur_nbits)
        self.cur_nbits += 1
        if self.cur_nbits == 8:             # байт заполнен — закрыть
            self.cur_index = -1
            self.cur_nbits = 0

    def put_bits(self, bits):
        for b in bits:
            self.put_bit(b)

    def put_raw_byte(self, value):
        """Дописать сырой байт (литерал или байт смещения) в конец потока.

        Открытый битовый байт (если есть) остаётся открытым и стоит в
        потоке РАНЬШЕ этого сырого байта: его остаток декодер прочитает
        из аккумулятора уже после сырого байта.
        """
        self.out.append(value & 0xFF)


# ---------------------------------------------------------------------------
# Точная модель целевого 8080-декодера (dzx0.asm, forward, standard)
# ---------------------------------------------------------------------------


def dzx0_standard(data, limit=None):
    """Python-двойник dzx0_standard (DeZX, forward). Повторяет поток
    состояний 8080-ассемблера: битовый буфер `a` с часовым битом 0x80,
    interlaced Elias-gamma, встроенный байт смещения, обратное смещение
    в «стеке». Возвращает распакованные байты.

    data: bytes/bytearray сжатого потока (без заголовка длин).
    limit: ожидаемая длина результата (для самопроверки), или None.
    """
    data = bytes(data)
    src = 0                     # HL — указатель в сжатом потоке
    out = bytearray()           # память назначения; dst == len(out)
    a = 0x80                    # битовый буфер-аккумулятор (часовой бит)
    last_offset = 0xFFFF        # значение в «стеке» (обратное смещение)

    def getbit():
        """add a; jnz skip; mov a,m; inx h; ral. Возвращает бит (carry)."""
        nonlocal a, src
        cy = (a >> 7) & 1           # add a: carry = старший бит
        a = (a << 1) & 0xFF
        if a == 0:                  # jnz skip -> иначе перезагрузка
            a = data[src]           # mov a,m
            src += 1                # inx h
            new_cy = (a >> 7) & 1   # ral: carry = старший бит загруженного
            a = ((a << 1) | cy) & 0xFF
            cy = new_cy
        return cy

    def elias_loop(value):
        """dzx0s_elias_loop: bit==1 -> вернуть; bit==0 -> value<<=1,
        затем bit (1 -> value+=1), и снова."""
        while True:
            if getbit() == 1:       # rc
                return value
            value = (value << 1) & 0xFFFF
            if getbit() == 1:       # jnc skip / inr e
                value += 1

    def elias():
        """dzx0s_elias: inr e (value=1) затем elias_loop."""
        return elias_loop(1)

    def elias_backtrack(value):
        """dzx0s_elias_backtrack: value<<=1, bit (1 -> +=1), elias_loop."""
        value = (value << 1) & 0xFFFF
        if getbit() == 1:
            value += 1
        return elias_loop(value)

    def ldir_literals(n):
        """Копировать n байт из src(HL) в out(BC)."""
        nonlocal src
        for _ in range(n):
            out.append(data[src])
            src += 1

    def copy_back(n):
        """Копировать n байт из (dst - distance) в dst, distance =
        0x10000 - last_offset. Побайтно, с перекрытием (RLE-совпадения)."""
        distance = (0x10000 - last_offset) & 0xFFFF
        s = len(out) - distance
        for _ in range(n):
            out.append(out[s])
            s += 1

    def new_offset():
        """dzx0s_new_offset: прочитать новое смещение и длину, сделать
        copy_back. Возвращает True при EOF (младший байт Elias == 0)."""
        nonlocal src, last_offset
        v = elias()
        e_v = v & 0xFF
        # xra a; sub e; rz -> EOF, если младший байт значения == 0
        if e_v == 0:
            return True
        # mov d,a; ...; xra a; sub e; mov e,d; mov d,a
        a_sub = (256 - e_v) & 0xFF
        # rar (carry=1 от sub e): D = (a_sub>>1)|0x80, carry = a_sub&1
        d_new = ((a_sub >> 1) | 0x80) & 0xFF
        cy_rar = a_sub & 1
        # mov a,m; rar -> E = (M>>1)|(cy_rar<<7), carry = M&1
        m = data[src]
        src += 1
        e_new = ((m >> 1) | (cy_rar << 7)) & 0xFF
        cy_m = m & 1
        last_offset = ((d_new << 8) | e_new) & 0xFFFF
        # lxi d,1; cnc dzx0s_elias_backtrack; inx d
        value = 1
        if cy_m == 0:
            value = elias_backtrack(value)
        copy_back(value + 1)
        return False

    # dzx0s_literals: первый блок — всегда литералы (стартовый бит опущен).
    length = elias()
    ldir_literals(length)

    # Конечный автомат: после литералов бит 1=new_offset, 0=то же смещение;
    # после copy бит 0=литералы, 1=new_offset (dzx0s_copy -> jnc literals).
    after_literals = True
    while True:
        bit = getbit()
        if after_literals:
            if bit == 1:
                if new_offset():
                    break
                after_literals = False
            else:
                length = elias()
                copy_back(length)
                after_literals = False
        else:
            if bit == 0:
                length = elias()
                ldir_literals(length)
                after_literals = True
            else:
                if new_offset():
                    break
                after_literals = False

    if limit is not None and len(out) != limit:
        raise ValueError(
            f'распаковка дала {len(out)} байт, ожидалось {limit}')
    return bytes(out)


def decompress(data, expected_len=None):
    """Публичный алиас распаковщика (модель == целевой ассемблер)."""
    return dzx0_standard(data, limit=expected_len)


# ---------------------------------------------------------------------------
# LZ77-парсер (greedy + хеш-цепочки), учитывающий грамматику ZX0
# ---------------------------------------------------------------------------

MAX_OFFSET = 0x7FFF     # 32767; 32768 вырождается в EOF
MAX_MATCH = 0xFFFF      # длина совпадения ограничена 16 бит (Elias)
MIN_MATCH = 2


def _parse(data):
    """Разбить data на токены: [('lit', bytes) | ('match', length, offset)].
    Чередование литералов и совпадений; допускается два совпадения подряд
    (грамматика ZX0 это разрешает через new_offset после copy)."""
    n = len(data)
    tokens = []
    lit_start = 0
    pos = 0

    # Хеш-цепочки: 3-байтовый хеш -> последняя позиция.
    hbits = 12
    hsize = 1 << hbits
    head = [-1] * hsize
    prev = [-1] * n

    def h3(i):
        return ((data[i] << 8) ^ (data[i + 1] << 4) ^ data[i + 2]) & (hsize - 1)

    while pos < n:
        best_len = 0
        best_off = 0
        if pos + 2 < n:
            hv = h3(pos)
            cand = head[hv]
            # ограничим число проверяемых кандидатов (скорость vs. степень)
            tries = 64
            while cand >= 0 and (pos - cand) <= MAX_OFFSET and tries > 0:
                tries -= 1
                if data[cand] == data[pos]:
                    # считаем длину совпадения
                    ln = 0
                    limit = min(MAX_MATCH, n - pos)
                    while ln < limit and data[cand + ln] == data[pos + ln]:
                        ln += 1
                    if ln > best_len:
                        best_len = ln
                        best_off = pos - cand
                        if best_len >= limit:
                            break
                cand = prev[cand]
            # вставляем текущую позицию в цепочку
            prev[pos] = head[hv]
            head[hv] = pos

        if best_len >= MIN_MATCH and best_off >= 1:
            # emit pending literals
            if pos > lit_start:
                tokens.append(('lit', bytes(data[lit_start:pos])))
            tokens.append(('match', best_len, best_off))
            # регистрируем позиции, покрытые совпадением, в хеше
            for k in range(pos + 1, min(pos + best_len, n - 2)):
                if k + 2 < n:
                    hk = h3(k)
                    prev[k] = head[hk]
                    head[hk] = k
            pos += best_len
            lit_start = pos
        else:
            pos += 1

    if lit_start < n:
        tokens.append(('lit', bytes(data[lit_start:n])))
    return tokens


# ---------------------------------------------------------------------------
# сериализация токенов в поток ZX0
# ---------------------------------------------------------------------------


def _emit_new_offset(w, offset, length):
    """Записать токен «новое смещение» (без ведущего бита 1).

    offset: дистанция назад (1..MAX_OFFSET). length: >= 2.
    Бит 1 (переход в new_offset) пишет вызывающий.
    """
    # R = (0x10000 - offset) & 0xFFFF; D_new = R>>8 (0x80..0xFF), E_new = R&0xFF
    r = (0x10000 - offset) & 0xFFFF
    d_new = r >> 8
    e_new = r & 0xFF
    # a_sub = (256 - e_v) & 0xFF, при этом d_new = (a_sub>>1)|0x80, cy_rar = a_sub&1
    # => a_sub = ((d_new & 0x7F) << 1) | (e_new >> 7)
    a_sub = (((d_new & 0x7F) << 1) | (e_new >> 7)) & 0xFF
    e_v = (256 - a_sub) & 0xFF
    if e_v == 0:
        raise ValueError(f'смещение {offset} вырождается в EOF')
    cy_rar = a_sub & 1
    # m = ((e_new & 0x7F) << 1) | cy_m, где cy_m = бит interlace длины
    value = length - 1          # декодер: length = value + 1
    if value < 1 or value > 0xFFFF:
        raise ValueError(f'длина {length} вне диапазона new-offset')
    g = _elias_gamma(value)
    cy_m = g[0]                 # первый бит Elias(value): 0 -> backtrack, 1 -> конец
    m = ((e_new & 0x7F) << 1) | cy_m
    w.put_bits(_elias_gamma(e_v))
    # M — сырой байт: декодер читает его из HL (mov a,m); остаток открытого
    # битового байта (биты длины) будет прочитан из аккумулятора ПОСЛЕ M.
    w.put_raw_byte(m)
    w.put_bits(g[1:])           # остальные биты длины идут уже из потока


def compress(data):
    """Сжать data (bytes) в поток ZX0 «standard» (bytes).

    Результат читается dzx0_standard() и целевым dzx0.asm без заголовка;
    длина распакованных данных известна вызывающему (хранится отдельно).
    """
    data = bytes(data)
    w = _BitWriter()

    if not data:
        # Пустые данные: литеральный блок невозможен (len>=1). Формат ZX0
        # не кодирует пустой поток; вызывающий не должен сжимать пустоту.
        raise ValueError('compress: пустые данные не поддерживаются')

    tokens = _parse(data)

    # Первый токен обязан быть литералами (декодер стартует с literals).
    if not tokens or tokens[0][0] != 'lit':
        # теоретически недостижимо: совпадение не может precede литералы
        raise ValueError('compress: поток должен начинаться с литералов')

    first = tokens[0]
    w.put_bits(_elias_gamma(len(first[1])))
    w.out.extend(first[1])

    last_offset = None          # «последнее смещение» декодера (0xFFFF -> нет)
    state = 'after_literals'

    for t in tokens[1:]:
        if t[0] == 'match':
            _, length, offset = t
            if state == 'after_literals':
                # бит 0 -> то же смещение, бит 1 -> новое
                if last_offset is not None and offset == last_offset:
                    w.put_bit(0)
                    w.put_bits(_elias_gamma(length))
                else:
                    w.put_bit(1)
                    _emit_new_offset(w, offset, length)
                    last_offset = offset
            else:  # after_match: доступен только new_offset (бит 1)
                w.put_bit(1)
                _emit_new_offset(w, offset, length)
                last_offset = offset
            state = 'after_match'
        else:  # literals
            if state == 'after_match':
                w.put_bit(0)    # -> литералы
            # after_literals не может идти сразу за литералами
            w.put_bits(_elias_gamma(len(t[1])))
            w.out.extend(t[1])
            state = 'after_literals'

    # EOF: бит 1 (new_offset) + Elias(256)
    w.put_bit(1)
    w.put_bits(_elias_gamma(256))

    # Незакрытый битовый байт уже лежит в out с нулевыми младшими битами;
    # декодер останавливается на EOF (rz), хвостовые биты игнорируются.
    return bytes(w.out)


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------


def _self_test():
    import os
    import random

    cases = []

    # 1) синтетика: граничные случаи
    cases.append(b'A')
    cases.append(b'AB')
    cases.append(b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')       # RLE
    cases.append(bytes(range(256)))                          # все байты
    cases.append(b'abcabcabcabcabcabcabcabcabcabc')         # повторы
    cases.append(b'aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeeeeeeee')
    # длинный период
    period = bytes((i * 37 + 11) & 0xFF for i in range(200))
    cases.append(period * 40)

    # 2) псевдослучайные данные (несжимаемые)
    rnd = random.Random(1234)
    cases.append(bytes(rnd.getrandbits(8) for _ in range(1000)))
    # 3) случайные с повторяющимися блоками (сжимаемые)
    base = bytes(rnd.getrandbits(8) for _ in range(64))
    blob = bytearray()
    for _ in range(200):
        if rnd.random() < 0.5:
            blob += base[rnd.randrange(0, 40):rnd.randrange(40, 64)]
        else:
            blob.append(rnd.getrandbits(8))
    cases.append(bytes(blob))

    # 4) реальные партитуры ducktales2 (если доступны)
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    inc_dirs = [
        os.path.join(root, 'roms', 'musics', 'ducktales2', 'rom_data'),
        os.path.join(root, 'roms', 'musics', 'castlevania', 'rom_data'),
    ]
    inc_files = []
    for d in inc_dirs:
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.endswith('.inc'):
                    inc_files.append(os.path.join(d, fn))
    # берём байты массивов из .inc как сырые данные (простой парсер)
    import re
    for path in inc_files[:20]:
        try:
            text = open(path, 'r', encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        for m in re.finditer(r'\{([^{}]*)\}', text):
            body = m.group(1)
            nums = re.findall(r'0x([0-9A-Fa-f]{2})|\b(\d{1,3})\b', body)
            vals = []
            ok = True
            for hexv, decv in nums:
                if hexv:
                    vals.append(int(hexv, 16))
                elif decv:
                    v = int(decv)
                    if v > 255:
                        ok = False
                        break
                    vals.append(v)
            if ok and 16 <= len(vals) <= 65535:
                cases.append(bytes(vals))

    print(f'zx0 self-test: {len(cases)} наборов данных')
    total_in = 0
    total_out = 0
    for i, data in enumerate(cases):
        packed = compress(data)
        unpacked = decompress(packed, expected_len=len(data))
        assert unpacked == data, (
            f'НАБОР {i}: round-trip не совпал '
            f'(len={len(data)}, packed={len(packed)})')
        total_in += len(data)
        total_out += len(packed)
        print(f'  [{i:2d}] {len(data):6d} -> {len(packed):6d} '
              f'({100.0 * len(packed) / max(1, len(data)):5.1f}%) OK')

    ratio = 100.0 * total_out / max(1, total_in)
    print(f'ИТОГО: {total_in} -> {total_out} ({ratio:.1f}%)')
    print('Все round-trip проверки пройдены.')


def main(argv):
    if len(argv) >= 2 and argv[1] == '--self-test':
        _self_test()
        return 0
    if len(argv) == 4 and argv[1] in ('c', 'd'):
        mode, inp, outp = argv[1], argv[2], argv[3]
        with open(inp, 'rb') as f:
            data = f.read()
        if mode == 'c':
            res = compress(data)
        else:
            res = decompress(data)
        with open(outp, 'wb') as f:
            f.write(res)
        print(f'{mode}: {len(data)} -> {len(res)} ({outp})')
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
