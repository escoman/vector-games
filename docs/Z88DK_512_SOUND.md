# Исследования ChatGPT по z88dk относительно графического режима 512x256 и поддержки звука

После проверки исходников z88dk обнаружилась **важная вещь**: с 512×256 ситуация значительно хуже, чем я предполагал в предыдущем ответе, а со звуком — наоборот, API довольно богатый.

## 1. Режим 512×256

**Готовой поддержки именно режима 512×256 в target `vector06c` нет.**

Официальная таблица платформ z88dk для Vector-06C указывает только:

* текстовый режим: `32×32`;
* графика: `256×256`;
* звук: `PSG`.

Про `512×256` там ничего нет. ([github-wiki-see.page][1])

Это хорошо согласуется с исходниками.

### Что делает `w_pixladdr.asm`

В нём прямо написано:

```asm
; Display is 256/512 pixels wide, 256 pixels high
```

Но это **не означает полноценную поддержку двух режимов**. Функция вычисляет адрес пикселя исходя из байтовой организации видеопамяти:

```asm
ld c,l
ld a,l
rrca
rrca
rrca
and 31
add $e0
ld h,a
```

и затем:

```asm
ld a,c
and 7
xor 7
```



А самое интересное находится в `w_pixel.inc`.

Там для одного пикселя последовательно обрабатываются:

```text
Plane 0
Plane 1
Plane 2
Plane 3
```

то есть библиотека фактически рассчитана на **4 битовых плоскости**:

```asm
; Plane 1
...
; Plane 2
...
; Plane 3
```



Это соответствует обычному Vector-06C режиму 256×256×16.

### А 512×256?

В режиме 512×256 используются только две плоскости:

```text
C000
E000
```

и каждый экранный байт соответствует 8 горизонтальным пикселям.

То есть для 512×256 нужно:

```text
256×256×4 planes
        ↓
512×256×2 planes
```

У z88dk **нет отдельного переключателя screen mode**, нет функции вроде:

```c
vector06c_set_mode(512);
```

и нет отдельного pixel-addressing API для 512×256.

Поэтому:

> **готовый `plot(x,y)` нельзя считать поддержкой 512×256.**

---

## 2. Более того — здесь есть потенциальная проблема с самим target

Я бы поправил свой предыдущий ответ ещё в одном месте.

`cpm.cfg` действительно говорит:

```text
SUBTYPE vector06c ... -clib=8080
```

то есть target заявлен как 8080. ([GitHub][2])

Но Vector-specific ASM содержит инструкции **Z80**, которых нет у 8080.

Например `w_pixeladdr`:

```asm
rrca
```

— эта конкретная инструкция есть и у 8080, поэтому тут всё нормально.

Но в `w_pixel.inc` встречаются:

```asm
sbc a
djnz
```

`SBC A` и `DJNZ` — уже **Z80**, не 8080. 

А `get_psg.asm` содержит:

```asm
ld a,l
```

что также Z80-only. 

Поэтому я бы **не стал пока доверять утверждению "vector06c target полностью 8080-compatible"**. Конфигурация говорит `-clib=8080`, но часть Vector-specific library ASM явно требует аудита.

Это для нас очень важная находка.

---

# 3. А вот со звуком ситуация интересная

В `include/psg.h` Vector-06C **явно присутствует**:

```c
#ifdef __VECTOR06C__
#define psgT(hz) ((int)(110837.5 / (hz)))
#endif
```

То есть z88dk действительно знает о PSG Vector-06C. ([GitHub][3])

Причём API намного интереснее, чем просто `set_psg()`.

Есть:

```c
set_psg(reg, value)
get_psg(reg)
psg_init()
```

а также:

```c
psg_tone(channel, period)
psg_noise(period)
psg_volume(channel, volume)
psg_envelope(waveform, period, channels)
psg_channels(tone_channels, noise_channels)
```

([GitHub][3])

---

# 4. Три канала тона

Вот это уже практически готовый API для трёхканального AY-подобного PSG.

```c
psg_tone(channel, period);
```

Каналы определены:

```c
chan0 = 1
chan1 = 2
chan2 = 4
chanAll = 7
```

([GitHub][3])

То есть концептуально:

```c
psg_tone(chan0, periodA);
psg_tone(chan1, periodB);
psg_tone(chan2, periodC);
```

соответствует трём тональным генераторам:

```text
Channel A ──┐
Channel B ──┼── PSG
Channel C ──┘
```

---

# 5. Шумогенератор — тоже есть

И это самое интересное.

В `psg.h` есть:

```c
psg_noise(unsigned int period);
```

То есть программно можно задавать период шумогенератора.

А:

```c
psg_channels(tone_channels, noise_channels);
```

позволяет отдельно указать, какие каналы получают:

* tone;
* noise.

([GitHub][3])

Например концептуально:

```c
psg_channels(chan0 | chan1 | chan2, chan2);
```

означает:

```text
A = tone
B = tone
C = tone + noise
```

То есть стандартный сценарий:

```text
Channel A → мелодия
Channel B → мелодия
Channel C → шум/эффект
```

реализуется самим API.

---

# 6. Громкость

Есть:

```c
psg_volume(channel, volume);
```

То есть:

```c
psg_volume(chan0, 15);
psg_volume(chan1, 10);
psg_volume(chan2, 7);
```

### И это важно

API поддерживает **независимую громкость каждого из трёх каналов**. ([GitHub][3])

---

# 7. Envelope

Есть ещё:

```c
psg_envelope(waveform, period, channels);
```

И в header перечислены формы:

```c
envD
envU
envDD
envDUD
envDH
envUU
envUH
envUDUD
```

([GitHub][3])

То есть API предусматривает полноценный AY-style envelope.

Для музыкального движка это очень интересно.

---

# 8. Низкоуровневый доступ к регистрам

Есть:

```c
set_psg(reg, value);
get_psg(reg);
```

И вот здесь мы можем делать вообще всё напрямую.

Для Vector target `set_psg_callee.asm` пишет:

```asm
ld a,l
out ($15),a
ld a,e
out ($14),a
ret
```

То есть:

```text
$15 → выбор регистра PSG
$14 → данные PSG
```



А `get_psg()` делает обратное:

```asm
ld a,l
out ($15),a
in a,($14)
```



---

# 9. Инициализация PSG

`psg_init()` сбрасывает регистры и затем устанавливает:

```asm
R7 = %11111000
```

То есть:

```text
Tone A = enabled
Tone B = enabled
Tone C = enabled
I/O A/B = input
```



Здесь уже видно, что z88dk действительно рассматривает Vector PSG как **трёхканальный PSG с регистрами AY-подобного типа**.

---

# 10. А вот шумогенератор реализован именно через стандартную схему PSG

Из самого API:

```c
psg_noise(period);
psg_channels(tone_channels, noise_channels);
```

следует следующая модель:

```text
               ┌─ Tone A ──┐
               │            │
               ├─ Tone B ──┤
PSG ───────────┤            ├── Mixer
               ├─ Tone C ──┤
               │            │
               └─ Noise ────┘
```

и каждый канал может подключаться к tone/noise.

Это гораздо лучше, чем просто "проиграть шум".

---

# 11. Но есть очень важная оговорка

Вот тут z88dk опять имеет некоторую странность.

`include/psg.h` содержит **универсальный PSG API**, а конкретно в `libsrc/target/vector06c/psg/` я вижу только:

```text
get_psg.asm
psg_init.asm
set_psg.asm
set_psg_callee.asm
```

То есть базовые операции:

```text
read register
write register
initialize
```

есть.

А вот Vector-specific реализаций:

```text
psg_tone.asm
psg_noise.asm
psg_volume.asm
psg_channels.asm
psg_envelope.asm
```

в этом каталоге нет.

Поэтому наличие функций в `psg.h` **не означает автоматически, что все эти функции реализованы для Vector-06C**.

Это принципиальное различие.

---

# 12. Что реально можно использовать сейчас

Я бы разделил так:

| Возможность                 | z88dk Vector-06C                |
| --------------------------- | ------------------------------- |
| 256×256                     | **Да**                          |
| 256×256×16                  | **Частично/есть pixel library** |
| 512×256                     | **Нет готового режима**         |
| переключение 256/512        | **Нет готового API**            |
| работа с видеоплоскостями   | **Да, в graphics ASM**          |
| `plot()`                    | **Есть**                        |
| `point()`                   | **Есть**                        |
| `unplot()`                  | **Есть**                        |
| `xorplot()`                 | **Есть**                        |
| `fill()`                    | generic                         |
| palette                     | **Есть**                        |
| 3 tone channels             | **API есть**                    |
| PSG register access         | **Да**                          |
| PSG initialization          | **Да**                          |
| noise period API            | **есть декларация**             |
| tone/noise mixer API        | **есть декларация**             |
| volume API                  | **есть декларация**             |
| envelope API                | **есть декларация**             |
| готовый Vector noise driver | **надо дописывать/проверять**   |

---

# 13. Для твоего проекта я бы вообще не использовал готовый `graphics.h` для 512×256

Мы можем сделать гораздо лучше.

Например:

```c
#include <vector06c.h>

vector06c_mode_512();

vector06c_plot(x, y, color);
vector06c_clear(color);
vector06c_set_palette(index, rgb);
```

А внутри:

```text
512×256
   │
   ├── plane 0 → C000
   └── plane 1 → E000
```

и при этом использовать только 8080 инструкции.

---

# 14. Со звуком я бы сделал аналогично

Не пытаться тащить весь абстрактный z88dk PSG API, а сделать маленький Vector-specific API:

```c
v06c_psg_init();

v06c_tone(0, period);
v06c_tone(1, period);
v06c_tone(2, period);

v06c_volume(0, volume);
v06c_volume(1, volume);
v06c_volume(2, volume);

v06c_noise(period);

v06c_mixer(
    V06C_TONE_A |
    V06C_TONE_B |
    V06C_NOISE_C
);
```

Причём **весь runtime написать на чистом 8080 ASM**.

Это даст нам гарантированный код для КР580ВМ80А, а не ситуацию, которую мы сейчас обнаружили в z88dk, когда target объявлен как `8080`, но Vector-specific ASM содержит Z80-only инструкции.

---

## Главное резюме

**512×256:** в z88dk готовой поддержки нет. Есть общий `graphics.h` и Vector pixel driver, но он фактически ориентирован на 4 плоскости и не предоставляет полноценного Vector 512×256 API. Официальная таблица z88dk также указывает для Vector-06C только `256×256`. ([github-wiki-see.page][1])

**Трёхканальный звук:** здесь z88dk гораздо интереснее. В `psg.h` для `__VECTOR06C__` предусмотрен PSG API с тремя tone channels, noise, независимой громкостью, mixer и envelope. ([GitHub][3])

**Но:** Vector-specific реализация в `libsrc/target/vector06c/psg/` фактически содержит только низкоуровневые операции работы с PSG-регистрами и инициализацию. Поэтому полноценный C API для tone/noise на Векторе ещё нужно проверить по библиотечному линку и, скорее всего, часть функций реализовать самостоятельно. При этом имеющиеся Vector ASM надо обязательно перепроверять на чистый 8080 — там уже обнаружены Z80-инструкции. 

И вот это, на мой взгляд, **очень полезная находка для нашего C→ASM проекта**: z88dk можно использовать как основу, но `vector06c` target стоит сначала основательно исправить/дополнить — прежде всего сделать настоящий **чистый 8080 runtime + 512×256 driver + полноценный PSG/noise driver**.

[1]: https://github-wiki-see.page/m/z88dk/z88dk/wiki/platform?utm_source=chatgpt.com "platform - z88dk/z88dk GitHub Wiki"
[2]: https://github.com/z88dk/z88dk/blob/master/lib/config/cpm.cfg?utm_source=chatgpt.com "z88dk/lib/config/cpm.cfg at master · z88dk/z88dk · GitHub"
[3]: https://raw.githubusercontent.com/z88dk/z88dk/master/include/psg.h "raw.githubusercontent.com"
