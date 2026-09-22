"""Единые шаблоны имён RDB (ТЗ §28).

Это ЕДИНСТВЕННОЕ место, где решается, как выглядит имя. Скрипты не имеют
права изобретать свои варианты: они зовут `propose()` / `is_unknown()` /
`validate()`.

Соглашение (совпадает с фактическим putup.rdb и конвенцией Stage 0–13):

    func_*    функция (код, вызывается)
    data_*    данные (массив, таблица инициализации, буфер)
    str_*     строка (терминируемая, читается текстовым кодом)
    music_*   последовательность игрового музыкального байткода
    var_*     переменная рантайма (изменяется CPU)
    lbl_*     метка (затравка control flow, кода без отдельной функции)
    *_unknown недообследованная область; суффикс обязан стоять последним

Тип `table` в RDB имени с отдельным префиксом не получает: в putup.rdb все
8 таблиц называются `data_*`, поэтому ожидаемый префикс для table — `data_`.

Допустимые тела: `[a-z0-9_]+`, без заглавных, без пробелов, длина ≤ 32,
начинаться с буквы. Адрес в имени запрещён — он живёт в поле address
(исторические `func_load_gfx_2761` уже нарушают правило; `validate()`
сообщает о нём как о warning, чтобы не ломать существующие RDB).
"""
from __future__ import annotations

import re

# type в RDB (строчными, как их хранит отладчик) → обязательный префикс имени.
TYPE_PREFIX = {
    "function": "func_",
    "code": "func_",
    "label": "lbl_",
    "data": "data_",
    "table": "data_",
    "string": "str_",
    "music": "music_",
    "variable": "var_",
}

PREFIX_TYPE = {
    "func_": "function",
    "lbl_": "label",
    "data_": "data",
    "str_": "string",
    "music_": "music",
    "var_": "variable",
}

KINDS = tuple(PREFIX_TYPE)
UNKNOWN_SUFFIX = "_unknown"
MAX_NAME = 32
BODY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def prefix_for(kind):
    """Префикс по типу RDB (независимо от регистра)."""
    key = (kind or "").strip().lower()
    if key not in TYPE_PREFIX:
        raise ValueError("неизвестный тип RDB: %r (ожидан один из %s)"
                         % (kind, ", ".join(sorted(TYPE_PREFIX))))
    return TYPE_PREFIX[key]


def type_for(name):
    """Тип RDB по имени или None, если префикс не распознан."""
    for prefix, kind in PREFIX_TYPE.items():
        if name.startswith(prefix):
            return kind
    return None


def slugify(text, limit=24):
    """'Load GFX block' -> 'load_gfx_block'; не-ASCII отсекается."""
    text = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        return ""
    if len(text) > limit:
        text = text[:limit].rstrip("_")
    if text and text[0].isdigit():
        text = "x" + text
    return text


def propose(kind, hint=None, addr=None, unknown=False):
    """Собрать имя по шаблону.

        propose("function", "draw game objects")   -> func_draw_game_objects
        propose("data", addr=0x3041)               -> data_3041
        propose("data", unknown=True, addr=0x2100) -> data_2100_unknown
    """
    prefix = prefix_for(kind)
    body = slugify(hint)
    if not body and addr is not None:
        body = "%04X" % (int(addr) & 0xFFFF)
        body = body.lower()
    if not body:
        body = "item"
    name = prefix + body
    if len(name) > MAX_NAME:
        name = name[:MAX_NAME].rstrip("_")
    if unknown and not name.endswith(UNKNOWN_SUFFIX):
        name = name + UNKNOWN_SUFFIX
        if len(name) > MAX_NAME:
            stem = name[: MAX_NAME - len(UNKNOWN_SUFFIX)].rstrip("_")
            name = stem + UNKNOWN_SUFFIX
    return name


def unknown_for(kind, addr):
    """Каноническое имя недообследованной области: <prefix><addr>_unknown."""
    return propose(kind, addr=addr, unknown=True)


def is_unknown(name):
    return bool(name) and name.endswith(UNKNOWN_SUFFIX)


def strip_unknown(name):
    return name[: -len(UNKNOWN_SUFFIX)] if is_unknown(name) else name


def validate(name, kind=None):
    """Проверка имени на соответствие шаблону.

    Возвращает список проблем: ("error"|"warning", текст). Пустой список —
    имя корректно.
    """
    problems = []
    if not name:
        return [("error", "имя пустое")]
    if not BODY_RE.match(name):
        problems.append(("error",
                         "имя %r не соответствует ^[a-z][a-z0-9_]*$" % name))
    if len(name) > MAX_NAME:
        problems.append(("warning", "имя %r длиннее %d символов" % (name, MAX_NAME)))
    prefix = None
    for candidate in PREFIX_TYPE:
        if name.startswith(candidate):
            prefix = candidate
            break
    if prefix is None:
        problems.append(("error", "нет стандартного префикса (%s)"
                         % ", ".join(sorted(PREFIX_TYPE))))
    elif kind:
        expected = prefix_for(kind)
        if expected != prefix:
            problems.append(("error", "префикс %r не соответствует типу %r "
                                      "(ожидался %r)" % (prefix, kind, expected)))
    if prefix and strip_unknown(name) == prefix.rstrip("_"):
        problems.append(("warning", "имя %r — голый префикс без описательной "
                                   "части" % name))
    digits = re.search(r"_[0-9a-f]{3,4}$", strip_unknown(name))
    if digits:
        problems.append(("warning", "в имени %r есть адресный хвост %r — адрес "
                                    "должен жить в поле address" % (name, digits.group(0)[1:])))
    return problems


# ---------------------------------------------------------------------------
# Технические имена затравок и алиасы (ТЗ Stage 6.27 §31, §15, §16).
# ---------------------------------------------------------------------------

def technical_function_name(address):
    """Детерминированное имя функции по адресу: func_1234.

    Не зависит от порядка обнаружения: одно и то же имя на один адрес при
    любом количестве прогонов (ТЗ §32).
    """
    return propose("function", addr=address)


def technical_label_name(address):
    """Детерминированное имя метки по адресу: lbl_1234.

    Префикс `lbl_`, а не `label_`: единый источник истины для имён — этот
    модуль (TYPE_PREFIX["label"] == "lbl_"), иначе имя не пройдёт validate().
    """
    return propose("label", addr=address)


def normalize_alias(text):
    """'Scan Keyboard' -> 'scan_keyboard'; не-ASCII и мусор обрезаются."""
    return slugify(text, limit=MAX_NAME)


def is_valid_alias(alias, kind=None):
    """Годен ли alias как дополнительное имя объекта.

    Алиас — это семантическое имя (часто без префикса типа), поэтому к нему
    НЕ применяется обязательный префикс primary-имени. Но форма обязана быть
    корректной: `[a-z][a-z0-9_]*`, длина <= MAX_NAME. Если алиас всё же
    начинается с известного префикса и известен тип объекта — префикс обязан
    типу соответствовать (иначе это имя другого типа, не алиас этого).
    """
    if not alias or not BODY_RE.match(alias):
        return False
    if len(alias) > MAX_NAME:
        return False
    prefix = next((p for p in PREFIX_TYPE if alias.startswith(p)), None)
    if prefix is not None and kind:
        expected = TYPE_PREFIX.get((kind or "").strip().lower())
        if expected is not None and expected != prefix:
            return False
    return True
