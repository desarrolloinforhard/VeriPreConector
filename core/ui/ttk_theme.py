"""Tema corporativo de SmartPrice para ttkbootstrap 2.x."""

from __future__ import annotations

import ttkbootstrap as ttk


SMARTPRICE_THEME_FAMILY = "smartprice"
SMARTPRICE_LIGHT_THEME = f"{SMARTPRICE_THEME_FAMILY}-light"
SMARTPRICE_DARK_THEME = f"{SMARTPRICE_THEME_FAMILY}-dark"

SMARTPRICE_GREEN = "#149455"
SMARTPRICE_GREEN_SUCCESS = "#1AA053"
SMARTPRICE_INFO = "#168C78"
SMARTPRICE_WARNING = "#E5A50A"
SMARTPRICE_DANGER = "#C83C3C"
SMARTPRICE_MUTED = "#4F6478"
SMARTPRICE_LIGHT_BG = "#FFFFFF"
SMARTPRICE_LIGHT_FG = "#173227"
SMARTPRICE_DARK_BG = "#08130F"
SMARTPRICE_DARK_FG = "#F4FBF7"
SMARTPRICE_DARK_SURFACE = "#0D1B15"
SMARTPRICE_DARK_CARD = "#12231C"
SMARTPRICE_DARK_HOVER = "#193329"
SMARTPRICE_DARK_BORDER = "#29453A"
SMARTPRICE_DARK_MUTED = "#8AAE9E"

_tema_registrado = False


def registrar_tema_smartprice() -> None:
    """Registra una vez las variantes clara y oscura de la marca."""
    global _tema_registrado
    if _tema_registrado:
        return

    ttk.Theme(
        name=SMARTPRICE_THEME_FAMILY,
        primary=SMARTPRICE_GREEN,
        success=SMARTPRICE_GREEN_SUCCESS,
        info=SMARTPRICE_INFO,
        warning=SMARTPRICE_WARNING,
        danger=SMARTPRICE_DANGER,
        secondary=SMARTPRICE_MUTED,
        neutral=SMARTPRICE_MUTED,
        light={"background": SMARTPRICE_LIGHT_BG, "foreground": SMARTPRICE_LIGHT_FG},
        dark={"background": SMARTPRICE_DARK_BG, "foreground": SMARTPRICE_DARK_FG},
    ).register()
    _tema_registrado = True
