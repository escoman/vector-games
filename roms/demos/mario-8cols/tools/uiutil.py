#!/usr/bin/env python3
"""uiutil.py — мелочи Tk, общие у окна уровня и окна префабов.

Окна работают независимыми процессами (общего состояния нет), но разворачиваться
должны одинаково, иначе на одном WM одно вырастет до work-area, а другое
останется 1280x800 посередине экрана.
"""
import tkinter as tk


def maximize(root):
    """Штатная maximization: просим WM развернуть окно (заголовок остаётся,
    границы в work-area). Никакого geometry-форса на winfo_screenwidth/height:
    окно, ровно равное экрану, mutter рисует как fullscreen без рамок."""
    for fn in (lambda: root.state("zoomed"),
               lambda: root.attributes("-zoomed", True)):
        try:
            fn()
            return
        except tk.TclError:
            pass
