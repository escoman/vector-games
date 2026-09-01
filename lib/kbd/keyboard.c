/*
 * keyboard.c — ввод с клавиатуры Вектора-06Ц (библиотека vector-games).
 *
 * Матрицу 8×8 опрашивает kbdscan.asm (последовательность проверена на
 * эмуляторе: CW 0x8A в порт 0, маски строк в порт 3, столбцы из порта
 * 2; после опроса восстанавливаются CW 0x88 и регистр строки экрана
 * graph_scroll_row). kbd_scan() декодирует снимок kbd_rows[] в код
 * первой нажатой клавиши: бит 1 = клавиша нажата.
 *
 * Обходимся без прерываний: kbd_scan() вызывается из основного цикла.
 */

#include "v06.h"

/* Опрос матрицы в kbdscan.asm: заполняет kbd_rows[8] (1 = нажата) */
extern void kbd_scan_rows(void);
extern unsigned char kbd_rows[8];

/* Коды клавиш по матрице (строка*8 + столбец), раскладка без shift.
 * Таблица совпадает с z88dk in_keytranstbl; 0 = служебная/нет кода. */
static const unsigned char kbd_codes[64] = {
    /* строка 0: TAB ПС ВК ЗАБ ← ↑ → ↓ */
     7, 127,  13,  12,   8,  11,   9,  10,
    /* строка 1: - ^\ СТОП(ESC) Ф1 Ф2 Ф3 Ф4 Ф5 */
     0,   0,  27, 128, 129, 130, 131, 132,
    /* строка 2: 0 1 2 3 4 5 6 7 */
    '0', '1', '2', '3', '4', '5', '6', '7',
    /* строка 3: 8 9 : ; , = . / */
    '8', '9', ':', ';', ',', '=', '.', '/',
    /* строка 4: @ A B C D E F G */
    '@', 'a', 'b', 'c', 'd', 'e', 'f', 'g',
    /* строка 5: H I J K L M N O */
    'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
    /* строка 6: P Q R S T U V W */
    'p', 'q', 'r', 's', 't', 'u', 'v', 'w',
    /* строка 7: X Y Z [ \ ] ~ ПРОБЕЛ */
    'x', 'y', 'z', '[', '\\', ']', '~', ' ',
};

/* Однократный опрос матрицы: код первой нажатой клавиши или 0 */
unsigned char kbd_scan(void)
{
    unsigned char code = 0;
    unsigned char row;
    unsigned char cols;
    unsigned char col;

    kbd_scan_rows();

    for (row = 0; row < 8u; ++row) {
        cols = kbd_rows[row];           /* 1 = нажата */
        if (cols != 0u) {
            col = 0;
            while ((cols & 1u) == 0u) {
                cols >>= 1;
                ++col;
            }
            code = kbd_codes[row * 8u + col];
            break;
        }
    }
    return code;
}

/* Ждёт нажатия указанной клавиши и возвращается.
 * Опрос синхронизирован с кадровым счётчиком (50 Гц),
 * фронт-детектор: реагирует только на нажатие, не на удержание. */
void kbd_wait_key(unsigned char key)
{
    unsigned char cur = 0, prev = 0;
    unsigned int last = frame_count;
    while (cur != key) {
        while (frame_count == last)
            ;
        last = frame_count;
        cur = kbd_scan();
        if (cur != 0 && cur != prev && cur == key)
            break;
        prev = cur;
    }
}
