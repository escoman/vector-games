# Разбор ChatGPT библиотеки z88dk 

В актуальном `master` у z88dk уже есть **отдельный target `vector06c`**, причём он собирается именно как **8080**, а не Z80. В `cpm.cfg` есть `SUBTYPE vector06c`, а `vector06c.mak` прямо вызывает сборку target с `-m8080`. То есть z88dk уже содержит заготовку именно под классический Вектор-06Ц. ([GitHub][1])

Я разобрал структуру репозитория и отдельно `include/`. Ниже разделяю:

1. что находится в корне;
2. что имеет смысл использовать на Векторе;
3. что находится непосредственно в `include/`;
4. вложенные каталоги `include/`;
5. **отдельно — уже существующий target `vector06c`**, потому что он для нас особенно интересен.

---

# 1. Что вообще такое z88dk

z88dk — это не просто C-компилятор. Это полноценный toolchain:

```text
C
 ↓
zcc
 ↓
sccz80 / zsdcc / 80cc
 ↓
оптимизация
 ↓
z80asm
 ↓
CRT + библиотеки
 ↓
машинный код
 ↓
appmake
 ↓
образ/файл конкретной машины
```

Причём проект поддерживает семейство Z80 **и 8080/8085**. В частности, `z80asm`, `dis` и `ticks` умеют работать с 8080/8085, а `sccz80` имеет режим `-m8080`. ([GitHub][2])

Для Вектора это принципиально важно:

> **нельзя брать обычный Z80 target и просто считать, что полученный код заработает на КР580ВМ80А.**

Нам нужен именно 8080 code generation.

И z88dk это умеет.

---

# 2. Структура репозитория

В актуальном `master` основные каталоги такие: ([GitHub][2])

```text
z88dk/
├── doc/
├── examples/
├── ext/
├── include/
├── lib/
├── libsrc/
├── snap/
├── src/
├── support/
├── test/
├── testsuite/
├── win32/
│
├── Makefile
├── README.md
├── build.sh
├── set_environment.sh
├── changelog.txt
└── ...
```

Разберём каждый.

---

# 3. `doc/`

Документация проекта.

Там находятся:

* описания инструментов;
* документация компиляторов;
* документация библиотек;
* описания targets;
* руководства по classic library;
* документация по newlib;
* различные технические материалы.

### Для Вектора

**Очень полезно.**

Особенно стоит искать:

```text
doc/target/
doc/...
```

и документацию:

* `classic`
* `newlib`
* `z80asm`
* `sccz80`
* `appmake`

Но для написания собственного C→ASM toolchain для Вектора я бы в первую очередь изучал не документацию, а **существующий `vector06c` target**.

---

# 4. `examples/`

Примеры программ на C и ASM для различных машин.

z88dk сам рекомендует использовать этот каталог как исходную точку для classic library. ([GitHub][2])

### Для Вектора

Полезен для:

* синтаксиса C;
* способов вызова библиотечных функций;
* организации программ;
* примеров графики;
* работы с клавиатурой;
* игровых циклов.

Но нельзя автоматически брать пример для ZX Spectrum/MSX/CPC и считать его подходящим для Вектора.

---

# 5. `ext/`

Внешние зависимости и внешние компоненты.

Это скорее инфраструктура самого z88dk.

### Для Вектора

**Практически не нужен.**

---

# 6. `include/`

Вот это уже очень интересная директория.

Здесь находятся **C header-файлы**, то есть объявления:

```c
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <graphics.h>
```

и т. д.

Но важный момент:

> `include/*.h` — это **не сами реализации**.

Например:

```c
#include <string.h>

memcpy(dst, src, 100);
```

объявление `memcpy()` находится в `include/string.h`, а реальный машинный код находится в библиотеках `libsrc/` / `lib/`.

Это особенно важно для Вектора.

---

# 7. `lib/`

Это одна из самых важных директорий для компиляции.

В ней находятся:

```text
lib/
├── arch/
├── clibs/
├── config/
├── crt/
├── sdcc/
├── target/
├── z80rules.*
└── ...
```

`lib/config` содержит конфигурации targets, `lib/clibs` — готовые классические библиотеки, а `lib/target` — различные startup/target-specific элементы. ([GitHub][3])

### Для Вектора особенно важно

```text
lib/config/cpm.cfg
```

И там есть:

```text
SUBTYPE vector06c
```

с параметрами:

```text
-clib=8080
```

То есть z88dk уже рассматривает Vector-06C как **CP/M subtype с 8080 runtime**. ([GitHub][1])

Это очень хороший знак.

---

# 8. `libsrc/`

Это **исходники библиотек**, которые потом превращаются в библиотеки z88dk.

Структура:

```text
libsrc/
├── adt/
├── alloc/
├── arch/
├── classic/
├── compress/
├── ctype/
├── error/
├── font/
├── inttypes/
├── l/
├── libgen/
├── locale/
├── math/
├── network/
├── newlib/
├── regex/
├── setjmp/
├── sound/
├── sprites/
├── stdlib/
├── string/
├── target/
├── temp/
└── time/
```

([GitHub][4])

### Для Вектора

**Это, пожалуй, самая интересная директория после `include/`.**

Здесь можно найти:

* реализацию `memcpy`;
* `strlen`;
* `printf`;
* математические функции;
* графику;
* клавиатуру;
* звук;
* работу с памятью;
* target-specific ASM.

И самое главное:

```text
libsrc/target/vector06c/
```

уже существует. ([GitHub][5])

---

# 9. `src/`

Исходный код **самих инструментов z88dk**.

Например:

```text
src/
├── 80cc/
├── appmake/
├── common/
├── copt/
├── m4/
├── sccz80/
├── ticks/
├── ucpp/
├── z80asm/
├── z80nm/
├── z88dk-lib/
├── zcc/
├── zobjcopy/
├── zpragma/
├── zsdcc/
├── zx0/
└── zx7/
```

([GitHub][6])

### Для твоего проекта

Очень интересно:

```text
src/sccz80/
src/z80asm/
src/copt/
src/ticks/
src/zcc/
src/appmake/
```

Особенно `sccz80`, если ты хочешь понять, **как z88dk превращает C в ASM**.

---

# 10. `support/`

Вспомогательные материалы:

* benchmark;
* скрипты;
* различные вспомогательные программы;
* тестовые данные;
* вспомогательные библиотеки.

### Для Вектора

Полезен скорее для изучения производительности.

---

# 11. `test/`

Тесты отдельных компонентов.

---

# 12. `testsuite/`

Более крупный набор автоматических тестов.

Для Вектора может быть полезен, если мы захотим проверить:

```text
C → ASM → 8080
```

на большом наборе конструкций C.

---

# 13. `win32/`

Windows-specific части.

Для использования готового z88dk обычно не особо интересно.

---

# 14. Самое интересное: `libsrc/target/vector06c`

Вот здесь начинается самое полезное.

Структура:

```text
libsrc/target/vector06c/

├── games/
├── graphics/
├── input/
├── psg/
├── stdio/
│
├── asm_load_palette.asm
├── load_palette.asm
├── vector06c.lst
└── vector06c.mak
```

([GitHub][5])

Это уже **не абстрактная библиотека**, а конкретная реализация для Вектора.

---

## `vector06c.mak`

Файл сборки target.

И здесь есть крайне важная строка:

```text
buildtargetasm(...,8080,vector06c,-m8080,...)
```

То есть target компилируется именно как **8080**. ([GitHub][7])

Это подтверждает, что разработчики z88dk не просто назвали target Vector-06C, а действительно сделали для него 8080-библиотеки.

---

# 15. `vector06c/games/`

Сейчас там:

```text
joystick.asm
keys_joystick.asm
```

([GitHub][8])

### `joystick.asm`

Работа с джойстиком.

### `keys_joystick.asm`

Связывает клавиатурные/игровые функции с joystick API.

### Для тебя

**Использовать можно**, если нужен joystick.

---

# 16. `vector06c/graphics/`

Здесь:

```text
clg.asm
w_pixel.inc
w_pixladdr.asm
w_plotpixl.asm
w_pointxy.asm
w_respixl.asm
w_xorpixl.asm
```

([GitHub][9])

Это очень интересно.

### `clg.asm`

Clear graphics — очистка графического экрана.

### `w_pixladdr.asm`

Вычисление адреса пикселя.

Это особенно важно для Вектора, потому что расположение битов экрана далеко не стандартное.

### `w_plotpixl.asm`

Установка пикселя.

### `w_pointxy.asm`

Получение состояния пикселя.

### `w_respixl.asm`

Сброс пикселя.

### `w_xorpixl.asm`

XOR пикселя.

### `w_pixel.inc`

Вспомогательный ASM include с низкоуровневой логикой работы с пикселем.

---

### Для твоих задач

**Очень полезно.**

Особенно если ты хочешь делать:

* графические программы;
* игры;
* вывод спрайтов;
* свои алгоритмы рисования;
* конвертер BMP → Vector screen;
* C→ASM компилятор.

Причём `w_pixladdr.asm` стоит изучить особенно внимательно.

---

# 17. `vector06c/input/`

Файлы:

```text
in_Inkey.asm
in_KeyPressed.asm
in_LookupKey.asm
in_keytranstbl.asm
vector06c_key_interrupt.asm
```

([GitHub][10])

### `in_Inkey.asm`

Получение клавиши.

Типичная семантика:

```c
key = in_Inkey();
```

### `in_KeyPressed.asm`

Проверка, нажата ли клавиша.

### `in_LookupKey.asm`

Преобразование аппаратного/внутреннего кода клавиши в логический код.

### `in_keytranstbl.asm`

Таблица соответствий клавиш.

### `vector06c_key_interrupt.asm`

Низкоуровневая обработка клавиатуры через interrupt.

---

### Для Вектора

**Очень полезно.**

Это уже готовый код, который можно использовать вместо самостоятельного написания клавиатурного драйвера.

---

# 18. `vector06c/psg/`

Файлы:

```text
get_psg.asm
psg_init.asm
set_psg.asm
set_psg_callee.asm
```

([GitHub][11])

### `psg_init.asm`

Инициализация PSG.

### `set_psg.asm`

Запись значения в PSG-регистр.

### `set_psg_callee.asm`

Вариант функции с соглашением `__z88dk_callee`.

### `get_psg.asm`

Чтение PSG.

---

### Для Вектора

**Очень полезно.**

Если используемый Вектор имеет AY-совместимый PSG, это позволяет использовать его как основу для:

* музыки;
* эффектов;
* игровых звуков;
* проигрывания tracker-форматов.

Это особенно интересно в контексте твоего `.mus`/музыкального проекта.

---

# 19. `vector06c/stdio/`

Файлы:

```text
CRT_FONT.asm
bordercolour.asm
conio_vars.asm
generic_console.asm
generic_console_ioctl.asm
generic_console_vpeek.asm
```

([GitHub][12])

### `CRT_FONT.asm`

Шрифт консоли.

### `bordercolour.asm`

Работа с цветом рамки.

### `conio_vars.asm`

Переменные консольного драйвера.

### `generic_console.asm`

Основной консольный драйвер:

* вывод символов;
* позиционирование;
* очистка;
* текстовый экран.

### `generic_console_ioctl.asm`

Дополнительные управляющие операции консоли.

### `generic_console_vpeek.asm`

Чтение символа/содержимого экрана без обычного удаления/вывода.

---

# 20. `asm_load_palette.asm`

Низкоуровневая ASM-функция загрузки палитры.

# 21. `load_palette.asm`

C-callable оболочка над загрузкой палитры.

([GitHub][13])

### Для твоего проекта

**Очень полезно**, особенно если мы будем делать C-программы для графических режимов Вектора.

---

# 22. А теперь `include/`

Непосредственно в `include/` сейчас находятся следующие header-файлы. ([GitHub][14])

Я специально разделю их на группы.

---

# 23. Основные системные/языковые заголовки

## `assert.h`

Макросы:

```c
assert(...)
```

Проверка предположений во время выполнения.

### Вектор

Можно использовать при разработке, но в финальном ROM/игре обычно лучше отключать.

---

## `ctype.h`

Работа с символами:

```c
isdigit()
isalpha()
isalnum()
isspace()
toupper()
tolower()
```

и т. д.

### Вектор

**Да.**

Полезно для парсеров, командной строки, текстовых игр.

---

## `errno.h`

Коды ошибок:

```c
errno
```

и константы типа:

```c
EINVAL
ENOMEM
ENOENT
```

### Вектор

**Ограниченно.**

Полезно, если используется файловая/CP/M инфраструктура.

Для bare-metal ROM почти бесполезно.

---

## `features.h`

Описание возможностей конкретной платформы/библиотеки.

Используется преимущественно внутренними заголовками z88dk.

### Вектор

Самостоятельно практически не нужен.

---

## `float.h`

Параметры floating point:

```c
FLT_MAX
FLT_MIN
DBL_MAX
...
```

### Вектор

Да, **если действительно нужен float**.

Но на 8080 это будет очень дорого.

---

## `iso646.h`

Альтернативные C-операторы:

```c
and
or
xor
compl
bitand
bitor
```

и т. д.

### Вектор

Да, но практической ценности почти нет.

---

## `limits.h`

Ограничения типов:

```c
CHAR_MAX
INT_MAX
LONG_MAX
UINT_MAX
...
```

### Вектор

**Да.**

Особенно полезен для portable C-кода.

---

## `stdarg.h`

Механизм variadic functions:

```c
va_list
va_start
va_arg
va_end
```

Используется, например, для:

```c
printf(...)
```

([GitHub][15])

### Вектор

**Да.**

---

## `stdbool.h`

```c
bool
true
false
```

([GitHub][16])

### Вектор

**Да.**

---

## `stddef.h`

Основные определения C:

```c
size_t
ptrdiff_t
NULL
offsetof()
```

([GitHub][17])

### Вектор

**Обязательно.**

---

## `stdint.h`

Фиксированные целочисленные типы:

```c
uint8_t
int8_t

uint16_t
int16_t

uint32_t
int32_t
```

([GitHub][18])

### Вектор

**Один из самых полезных headers.**

Для Вектора я бы практически весь новый C-код писал через:

```c
uint8_t
uint16_t
int8_t
int16_t
```

а не через неопределённые `int`, `long` и т. п.

---

# 24. `stdio.h`

Стандартный ввод/вывод:

```c
printf()
sprintf()
snprintf()
puts()
putchar()
getchar()
fopen()
fread()
fwrite()
fclose()
...
```

([GitHub][19])

### Вектор

**Да, но с оговорками.**

Для консольных программ — вполне.

Для игр:

```c
printf()
```

может быть слишком тяжёлым.

Особенно если программа должна работать быстро.

Но `sprintf()`/`snprintf()` могут быть полезны.

---

# 25. `stdlib.h`

Большой стандартный набор:

```c
malloc()
free()
calloc()
realloc()

atoi()
atol()
strtol()

qsort()
bsearch()

rand()
srand()

abs()
labs()

exit()
```

и многое другое. ([GitHub][20])

### Вектор

**Да.**

Но:

```c
malloc()
```

на машине с 64 КБ памяти надо использовать очень осторожно.

Для игр я бы предпочитал:

```c
static uint8_t buffer[...];
```

или собственный allocator.

---

# 26. `string.h`

Строки и память:

```c
memcpy()
memmove()
memset()
memcmp()

strlen()
strcpy()
strncpy()
strcmp()
strncmp()
strcat()
strncat()
strchr()
strstr()
...
```

([GitHub][21])

### Для Вектора

**Очень важный header.**

Особенно:

```c
memcpy()
memset()
memcmp()
strlen()
```

Но здесь есть интересный момент.

z88dk имеет собственные очень оптимизированные ASM реализации этих функций.

Для 8080 мы можем посмотреть, насколько они хороши, и при необходимости написать Vector-specific версии.

---

# 27. `strings.h`

POSIX/BSD string extensions:

```c
strcasecmp()
strncasecmp()
strdup()
...
```

([GitHub][22])

### Вектор

Можно, но второстепенно.

---

# 28. `stdlib.h` + `malloc.h`

`malloc.h` содержит дополнительные интерфейсы управления heap.

### Вектор

Полезно, если мы действительно используем динамическую память.

Но для 48/64 КБ Vector-программ я бы старался минимизировать heap.

---

# 29. `alloc.h`

Специализированные механизмы выделения памяти z88dk.

([GitHub][23])

### Вектор

Интересен для больших программ, особенно игр.

Но сначала надо внимательно разобраться с моделью памяти конкретной Vector-программы.

---

# 30. `math.h`

Математика:

```c
sin()
cos()
tan()

sqrt()

pow()
log()
exp()

floor()
ceil()

fabs()

...
```

### Вектор

**Можно.**

Но floating point на 8080 очень дорог.

Для игр намного интереснее:

```text
fixed point
таблицы sin/cos
целочисленная математика
```

---

# 31. `arch.h`

Архитектурно-зависимые функции и определения.

### Для Вектора

**Полезен**, когда нужно писать код, который знает, на какой машине он выполняется.

---

# 32. `conio.h`

Низкоуровневый консольный интерфейс:

* курсор;
* текст;
* атрибуты;
* клавиатура;
* очистка экрана;
* позиционирование;
* ввод.

### Для Вектора

**Очень полезен.**

Он связан с `vector06c/stdio`.

---

# 33. `graphics.h`

Высокоуровневая графика.

В зависимости от target предоставляет API для:

```c
plot()
point()
draw()
circle()
line()
...
```

### Вектор

**Да, но нужно проверять каждую функцию.**

Vector target уже содержит собственные:

```text
w_plotpixl.asm
w_pointxy.asm
w_respixl.asm
w_xorpixl.asm
```

поэтому графический API не является полностью абстрактным — под ним есть Vector-specific реализация.

---

# 34. `games.h`

Игровые функции/интерфейсы.

### Вектор

Интересен прежде всего в сочетании с:

```text
vector06c/games/
```

То есть joystick.

---

# 35. `input.h`

Общий API устройств ввода.

### Вектор

**Да.**

Особенно интересен вместе с:

```text
libsrc/target/vector06c/input/
```

---

# 36. `interrupt.h`

Работа с interrupt routines.

([GitHub][24])

### Очень важная оговорка

Header существует общий, но **нельзя брать любой interrupt API и считать его совместимым с 8080**.

У Z80 и 8080 различаются interrupt-механизмы.

Для Вектора надо использовать только тот API/ASM, который реально генерирует 8080-код.

А существующий:

```text
vector06c_key_interrupt.asm
```

намного интереснее общего абстрактного API.

---

# 37. `intrinsic.h`

Специальные compiler intrinsics z88dk.

([GitHub][25])

Например, это позволяет получать очень низкоуровневый код из C.

### Для Вектора

**Очень интересно.**

Но именно здесь надо внимательно следить за архитектурой.

Некоторые intrinsic рассчитаны на Z80.

Для 8080 нужно смотреть generated ASM.

---

# 38. `setjmp.h`

```c
setjmp()
longjmp()
```

Механизм сохранения/восстановления контекста.

### Вектор

Работать может, но для обычных игр практически не нужен.

---

# 39. `time.h`

Работа со временем:

```c
time()
clock()
...
```

### Вектор

Зависит от runtime.

Для bare-metal игры обычно лучше иметь собственный frame counter.

Например:

```c
volatile uint16_t frame_counter;
```

---

# 40. `debug.h`

Отладочные функции z88dk.

### Вектор

Полезен во время разработки.

В production обычно не нужен.

---

# 41. `byteswap.h`

Функции перестановки endian:

```c
16-bit
32-bit
64-bit
```

### Вектор

Полезно при работе с бинарными форматами.

Особенно:

* BMP;
* WAV;
* NES data;
* собственные форматы;
* дисковые структуры.

---

# 42. `endian.h`

Определения endian-архитектуры.

### Вектор

Полезен для portable binary parsers.

---

# 43. `alloc.h`, `balloc.h`

`balloc.h` — специализированное блочное распределение памяти.

### Вектор

Интересно для игровых структур:

```text
entities
sprites
maps
nodes
objects
```

---

# 44. `algorithm.h`

Это уже не стандартный C.

В нём находится, например, реализация **A***. В самом header прямо указано, что алгоритм использует ADT priority queue и подключается через `-lalgorithm`. ([GitHub][26])

### Для Вектора

**Очень интересно для игр.**

Например:

```text
поиск пути врага
лабиринты
карты
pathfinding
```

Но A* использует динамическую память и priority queue, поэтому для 48 КБ надо оптимизировать.

---

# 45. `adt.h`

Abstract Data Types:

* queues;
* stacks;
* lists;
* heaps;
* trees;
* maps и т. д.

### Вектор

**Да**, особенно для игр.

Но нужно выбирать конкретные структуры — не тащить всю библиотеку.

---

# 46. `lib3d.h`

3D/3D utility функции.

### Вектор

Технически можно.

Практически для 8080:

> только очень оптимизированная fixed-point 3D.

Полноценные floating-point 3D здесь будут слишком дорогими.

---

# 47. `font` и `font.h`

В `include/font` находятся интерфейсы, связанные со шрифтами.

Для Вектора особенно интересно потому, что в target есть:

```text
stdio/CRT_FONT.asm
```

То есть собственный шрифт Vector console уже присутствует.

---

# 48. `compress/`

Внутри:

```text
aplib.h
zx0.h
zx1.h
zx2.h
zx7.h
```

([GitHub][27])

### `aplib.h`

APLib compression/decompression.

### `zx0.h`

ZX0.

### `zx1.h`

ZX1.

### `zx2.h`

ZX2.

### `zx7.h`

ZX7.

### Для Вектора

**Очень полезно.**

Это прямо то, что нужно для:

```text
ROM compression
level compression
graphics compression
music compression
sprite compression
map compression
```

Например:

```text
compressed screen
     ↓
ZX0 decompressor
     ↓
0xC000 / 0xE000
```

Для твоих задач это может дать огромный выигрыш по размеру ROM.

---

# 49. `sound.h`

Очень большой sound API. ([GitHub][28])

### Для Вектора

Использовать можно **только соответствующую target-реализацию**.

Для Вектора гораздо интереснее:

```text
include/psg/
libsrc/target/vector06c/psg/
```

чем абстрактный sound API.

---

# 50. `psg.h`

API для Programmable Sound Generator.

### Для Вектора

**Очень интересен.**

Особенно учитывая существующий:

```text
get_psg.asm
set_psg.asm
psg_init.asm
```

---

# 51. `im2.h`

Interrupt Mode 2.

### Для Вектора

**Не использовать.**

Это Z80-specific механизм.

У 8080 нет IM2.

---

# 52. `microc.h`

Совместимость/поддержка Micro-C.

([GitHub][29])

### Для Вектора

Практически не нужен.

---

# 53. `cpm.h`

API CP/M.

Очень большой header. ([GitHub][30])

### Для Вектора

**Очень интересен**, потому что z88dk представляет Vector-06C как CP/M subtype.

Если программа запускается под CP/M на Векторе, это может дать:

```text
файлы
диски
console
BDOS
CP/M services
```

Но если мы делаем самостоятельную ROM-программу:

> `cpm.h` уже не нужен.

---

# 54. `fcntl.h`

Файловые операции / flags:

```c
O_RDONLY
O_WRONLY
O_RDWR
O_CREAT
...
```

([GitHub][31])

### Вектор

Имеет смысл при работе через CP/M filesystem.

---

# 55. `dirent.h`

Каталоги:

```c
opendir()
readdir()
closedir()
```

### Вектор

Только если filesystem/runtime это поддерживает.

---

# 56. `unistd.h`

POSIX-like функции:

```c
read()
write()
close()
sleep()
...
```

### Вектор

Ограниченно.

Для CP/M-программы может быть полезно.

Для ROM — почти нет.

---

# 57. `dos.h`

DOS API.

### Вектор

**Не нужен.**

---

# 58. `pwd.h`

Работа с user/password database.

### Вектор

Не нужен.

---

# 59. `dirent.h`

Filesystem directory API.

### Вектор

Только CP/M/совместимый runtime.

---

# 60. `termcap.h`

Описание возможностей терминала.

### Вектор

Для собственной консоли почти не нужен.

---

# 61. `curses.h`

Полноценный terminal UI API.

([GitHub][32])

### Вектор

Теоретически можно использовать поверх консольного драйвера.

Практически:

> для игр лучше напрямую работать с `conio.h`.

---

# 62. `regexp.h`

Regular expressions.

### Вектор

Работать может, но совершенно не приоритетная вещь.

---

# 63. `libgen.h`

Разбор путей/имён файлов.

### Вектор

Только файловые приложения.

---

# 64. `stropts.h`

System V streams/stream ioctl API.

([GitHub][33])

### Вектор

Не нужен.

---

# 65. `sys/`

Это уже системные headers.

В нём находится низкоуровневая инфраструктура:

```text
sys/types.h
sys/compiler.h
...
```

Например `algorithm.h` напрямую использует:

```c
#include <sys/compiler.h>
#include <sys/types.h>
```

([GitHub][26])

### Для Вектора

**Очень важен косвенно.**

Самостоятельно туда обычно не лезем.

---

# 66. `threading/`

Поддержка потоков.

### Вектор

**Не нужна.**

У КР580ВМ80А нет нормальной аппаратной поддержки потоков, а runtime threading z88dk рассчитан на совершенно другой уровень абстракции.

---

# 67. `net/`

Сетевые API:

```text
socket
TCP
UDP
DNS
telnet
TFTP
...
```

В каталоге есть, например:

```text
socket.h
tcpsock.h
telnet.h
tftp.h
resolver.h
```

([GitHub][34])

### Вектор

Для классического Вектора:

**нет.**

Если только не писать собственный Ethernet/serial network stack.

---

# 68. `psg/`

Здесь находятся музыкальные библиотеки:

```text
PSGlib.h
arkos.h
etracker.h
vt2.h
wyz.h
```

([GitHub][35])

То есть z88dk уже имеет инфраструктуру для проигрывания различных PSG music formats.

### Для Вектора

**Очень интересно.**

Но надо проверять конкретный player.

---

# 69. `video/`

Внутри:

```text
tms99x8.h
v9938.h
```

([GitHub][36])

### Вектор

Не нужен.

Это видеочипы других компьютеров.

---

# 70. `X11/`

```text
X.h
Xlib.h
Xos.h
Xutil.h
Xz88dk.h
```

([GitHub][37])

### Вектор

**Не нужен.**

Это host/X11 API.

---

# 71. `residos/`

```text
idedos.h
package.h
```

([GitHub][38])

API операционной системы ResiDOS.

### Вектор

Не нужен.

---

# 72. Специализированные machine headers

В `include/` есть:

```text
c128.h
enterprise.h
flos.h
msx.h
nc100.h
osca.h
ozdev.h
rex/...
sos.h
ti.h
trsdos.h
tvc.h
zx81.h
zx81lowgfx.h
zxlowgfx.h
```

### Для Вектора

**Не использовать.**

Наличие header в z88dk ещё не означает, что он portable.

Это API конкретной другой машины.

---

# 73. `aztecc.h`

Совместимость с Aztec C.

### Вектор

Не нужен для нового проекта.

---

# 74. `bdscio.h`

Совместимость с BDS C I/O.

### Вектор

Интересно только при портировании старого CP/M C-кода.

---

# 75. `bgi.h`

Borland Graphics Interface compatibility.

### Вектор

Теоретически интересно для портирования старого C-кода, но **не рекомендую**.

Для Вектора лучше использовать собственный graphics API.

---

# 76. `enterprise.h`, `msx.h`, `tvc.h`, `ti.h` и т. п.

Это headers конкретных платформ.

Для нашего проекта:

```text
❌ не переносим
```

если только не портируем существующую программу с соответствующей машины.

---

# 77. Что реально брать для Вектора

Если отбросить весь огромный зоопарк z88dk, для твоего проекта я бы выделил вот это:

```text
include/
│
├── stdint.h
├── stddef.h
├── stdbool.h
├── stdarg.h
├── limits.h
├── stdlib.h
├── string.h
├── strings.h
├── ctype.h
├── assert.h
├── errno.h
├── math.h
│
├── conio.h
├── graphics.h
├── input.h
├── games.h
├── psg.h
├── sound.h
│
├── intrinsic.h
├── interrupt.h
├── arch.h
│
└── compress/
    ├── zx0.h
    ├── zx1.h
    ├── zx2.h
    ├── zx7.h
    └── aplib.h
```

А из `libsrc`:

```text
libsrc/
├── string/
├── stdlib/
├── math/
├── compress/
├── ctype/
├── alloc/
│
└── target/vector06c/
    ├── games/
    ├── graphics/
    ├── input/
    ├── psg/
    └── stdio/
```

---

# 78. И вот что особенно интересно

Сейчас картина для Вектора выглядит примерно так:

```text
                   z88dk
                     │
                     ▼
                    zcc
                     │
                     ▼
                  sccz80
                     │
                     │ -m8080
                     ▼
                8080 ASM
                     │
                     ▼
                  copt
                     │
                     ▼
                 z80asm
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
    generic 8080          vector06c ASM
          │                     │
          └──────────┬──────────┘
                     ▼
                 linker
                     │
                     ▼
                  binary
```

И `vector06c` уже содержит target-specific ASM для:

```text
клавиатуры
графики
консоли
PSG
joystick
палитры
```

Причём весь target собирается как `8080`. ([GitHub][5])

---

# 79. Самое важное ограничение

Есть одна тонкость, которую я бы **обязательно учитывал в нашем дальнейшем проекте**.

z88dk появился как toolkit для большого количества Z80-систем. Поэтому огромное количество библиотек написано в расчёте на:

```text
Z80
```

а не:

```text
8080
```

В частности, наличие:

```c
#include <intrinsic.h>
```

или:

```c
#include <graphics.h>
```

**не гарантирует**, что конкретная функция генерирует 8080-compatible code.

Поэтому для Вектора правильный подход:

> **каждую используемую библиотечную функцию проверять на конечный ASM.**

И особенно внимательно смотреть на:

```text
IX/IY
LD A,(IX+d)
EXX
DJNZ
BIT
SET
RES
IM 0/1/2
LDIR
CPIR
```

и прочие Z80 instructions.

Для классического Вектора допустим только код, который реально исполняется КР580ВМ80А.

---

# 80. Но есть отличная новость для твоего C→ASM проекта

Я бы вообще **не стал писать компилятор C с нуля**.

У нас уже есть:

```text
z88dk
   +
vector06c target
   +
8080 backend
```

То есть можно сделать гораздо интереснее:

```text
              C source
                 │
                 ▼
             z88dk/sccz80
                 │
                 ▼
            8080 ASM
                 │
                 ▼
       наш Vector optimizer
                 │
                 ▼
        наш Vector runtime
                 │
                 ▼
            Vector ROM
```

А ещё интереснее — использовать z88dk как **эталонный C compiler backend**, а потом постепенно заменять его собственными компонентами.

---

# 81. Что я бы изучил первым

В твоём случае я бы шёл **не по всему z88dk**, а вот в таком порядке:

### №1

```text
lib/config/cpm.cfg
```

Найти и полностью разобрать:

```text
SUBTYPE vector06c
```

Потому что это точка входа target.

### №2

```text
libsrc/target/vector06c/vector06c.mak
```

Здесь уже видно:

```text
8080
-m8080
```

и список всех Vector ASM. ([GitHub][7])

### №3

```text
libsrc/target/vector06c/graphics/
```

Особенно:

```text
w_pixladdr.asm
w_plotpixl.asm
w_pointxy.asm
```

Это даст нам реальную модель экрана.

### №4

```text
libsrc/target/vector06c/input/
```

Чтобы понять клавиатуру.

### №5

```text
libsrc/target/vector06c/stdio/
```

Чтобы понять текстовый режим.

### №6

```text
libsrc/target/vector06c/psg/
```

Чтобы понять звук.

### №7

```text
src/sccz80/
```

Чтобы понять, **какой именно ASM генерируется из C**.

### №8

```text
libsrc/string/
libsrc/stdlib/
libsrc/math/
```

Чтобы определить, какие стандартные функции можно безопасно использовать на 8080.

---

## И ещё один очень интересный вывод

Похоже, что **нам вообще не придётся придумывать Vector-06C target с нуля**.

В z88dk уже есть:

```text
+ cpm
+ subtype=vector06c
+ clib=8080
+ vector06c ASM
+ keyboard
+ graphics
+ PSG
+ joystick
+ palette
```

То есть следующий разумный шаг — **не просто читать z88dk, а разобрать существующий `vector06c` target до уровня каждой функции**: какие C-функции он экспортирует, какие адреса портов использует, какую модель видеопамяти предполагает, как устроен CRT, какой адрес загрузки программы и какой формат `.COM`/raw binary получается.

Это уже позволит нам понять, **насколько существующий z88dk target пригоден именно для написания нормальных C-программ/игр для классического Вектора-06Ц и что в нём нужно переделать для 48К/64К и наших графических режимов 256×256/512×256**.

[1]: https://github.com/z88dk/z88dk/blob/master/lib/config/cpm.cfg?utm_source=chatgpt.com "z88dk/lib/config/cpm.cfg at master · z88dk/z88dk · GitHub"
[2]: https://github.com/z88dk/z88dk "GitHub - z88dk/z88dk: The development kit for over a hundred z80 family machines - c compiler, assembler, linker, libraries. · GitHub"
[3]: https://github.com/z88dk/z88dk/tree/master/lib "z88dk/lib at master · z88dk/z88dk · GitHub"
[4]: https://github.com/z88dk/z88dk/tree/master/libsrc "z88dk/libsrc at master · z88dk/z88dk · GitHub"
[5]: https://github.com/z88dk/z88dk/tree/master/libsrc/target/vector06c "z88dk/libsrc/target/vector06c at master · z88dk/z88dk · GitHub"
[6]: https://github.com/z88dk/z88dk/tree/master/src "z88dk/src at master · z88dk/z88dk · GitHub"
[7]: https://github.com/z88dk/z88dk/blob/master/libsrc/target/vector06c/vector06c.mak "z88dk/libsrc/target/vector06c/vector06c.mak at master · z88dk/z88dk · GitHub"
[8]: https://github.com/z88dk/z88dk/tree/master/libsrc/target/vector06c/games "z88dk/libsrc/target/vector06c/games at master · z88dk/z88dk · GitHub"
[9]: https://github.com/z88dk/z88dk/tree/master/libsrc/target/vector06c/graphics "z88dk/libsrc/target/vector06c/graphics at master · z88dk/z88dk · GitHub"
[10]: https://github.com/z88dk/z88dk/tree/master/libsrc/target/vector06c/input "z88dk/libsrc/target/vector06c/input at master · z88dk/z88dk · GitHub"
[11]: https://github.com/z88dk/z88dk/tree/master/libsrc/target/vector06c/psg "z88dk/libsrc/target/vector06c/psg at master · z88dk/z88dk · GitHub"
[12]: https://github.com/z88dk/z88dk/tree/master/libsrc/target/vector06c/stdio "z88dk/libsrc/target/vector06c/stdio at master · z88dk/z88dk · GitHub"
[13]: https://github.com/z88dk/z88dk/blob/master/libsrc/target/vector06c/asm_load_palette.asm "z88dk/libsrc/target/vector06c/asm_load_palette.asm at master · z88dk/z88dk · GitHub"
[14]: https://github.com/z88dk/z88dk/tree/master/include "z88dk/include at master · z88dk/z88dk · GitHub"
[15]: https://github.com/z88dk/z88dk/blob/master/include/stdarg.h "z88dk/include/stdarg.h at master · z88dk/z88dk · GitHub"
[16]: https://github.com/z88dk/z88dk/blob/master/include/stdbool.h "z88dk/include/stdbool.h at master · z88dk/z88dk · GitHub"
[17]: https://github.com/z88dk/z88dk/blob/master/include/stddef.h "z88dk/include/stddef.h at master · z88dk/z88dk · GitHub"
[18]: https://github.com/z88dk/z88dk/blob/master/include/stdint.h "z88dk/include/stdint.h at master · z88dk/z88dk · GitHub"
[19]: https://github.com/z88dk/z88dk/blob/master/include/stdio.h "z88dk/include/stdio.h at master · z88dk/z88dk · GitHub"
[20]: https://github.com/z88dk/z88dk/blob/master/include/stdlib.h "z88dk/include/stdlib.h at master · z88dk/z88dk · GitHub"
[21]: https://github.com/z88dk/z88dk/blob/master/include/string.h "z88dk/include/string.h at master · z88dk/z88dk · GitHub"
[22]: https://github.com/z88dk/z88dk/blob/master/include/strings.h "z88dk/include/strings.h at master · z88dk/z88dk · GitHub"
[23]: https://github.com/z88dk/z88dk/blob/master/include/alloc.h "z88dk/include/alloc.h at master · z88dk/z88dk · GitHub"
[24]: https://github.com/z88dk/z88dk/blob/master/include/interrupt.h "z88dk/include/interrupt.h at master · z88dk/z88dk · GitHub"
[25]: https://github.com/z88dk/z88dk/blob/master/include/intrinsic.h "z88dk/include/intrinsic.h at master · z88dk/z88dk · GitHub"
[26]: https://github.com/z88dk/z88dk/blob/master/include/algorithm.h "z88dk/include/algorithm.h at master · z88dk/z88dk · GitHub"
[27]: https://github.com/z88dk/z88dk/tree/master/include/compress "z88dk/include/compress at master · z88dk/z88dk · GitHub"
[28]: https://github.com/z88dk/z88dk/blob/master/include/sound.h "z88dk/include/sound.h at master · z88dk/z88dk · GitHub"
[29]: https://github.com/z88dk/z88dk/blob/master/include/microc.h "z88dk/include/microc.h at master · z88dk/z88dk · GitHub"
[30]: https://github.com/z88dk/z88dk/blob/master/include/cpm.h "z88dk/include/cpm.h at master · z88dk/z88dk · GitHub"
[31]: https://github.com/z88dk/z88dk/blob/master/include/fcntl.h "z88dk/include/fcntl.h at master · z88dk/z88dk · GitHub"
[32]: https://github.com/z88dk/z88dk/blob/master/include/curses.h "z88dk/include/curses.h at master · z88dk/z88dk · GitHub"
[33]: https://github.com/z88dk/z88dk/blob/master/include/stropts.h "z88dk/include/stropts.h at master · z88dk/z88dk · GitHub"
[34]: https://github.com/z88dk/z88dk/tree/master/include/net "z88dk/include/net at master · z88dk/z88dk · GitHub"
[35]: https://github.com/z88dk/z88dk/tree/master/include/psg "z88dk/include/psg at master · z88dk/z88dk · GitHub"
[36]: https://github.com/z88dk/z88dk/tree/master/include/video "z88dk/include/video at master · z88dk/z88dk · GitHub"
[37]: https://github.com/z88dk/z88dk/tree/master/include/X11 "z88dk/include/X11 at master · z88dk/z88dk · GitHub"
[38]: https://github.com/z88dk/z88dk/tree/master/include/residos "z88dk/include/residos at master · z88dk/z88dk · GitHub"
