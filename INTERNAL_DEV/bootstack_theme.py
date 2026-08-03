"""Tema de marca SmartPrice para los experimentos Bootstack."""

from __future__ import annotations

from bootstack.style import Theme


SMARTPRICE_GREEN = "#149455"
SMARTPRICE_GREEN_HOVER = "#DDF4E7"
SMARTPRICE_GREEN_SURFACE = "#F3FBF6"
SMARTPRICE_TEXT = "#173227"
SMARTPRICE_MUTED = "#4F6478"
SMARTPRICE_BORDER = "#E6EDF4"
SMARTPRICE_WHITE = "#FFFFFF"


def instalar_tema_smartprice() -> Theme:
    """Registra las variantes clara y oscura sin activar una globalmente."""
    return Theme(
        name="smartprice",
        display_name="SmartPrice",
        primary=SMARTPRICE_GREEN,
        success="#1AA053",
        info="#168C78",
        warning="#E5A50A",
        danger="#C83C3C",
        neutral=SMARTPRICE_MUTED,
        light={"background": SMARTPRICE_WHITE, "foreground": SMARTPRICE_TEXT},
        dark={"background": "#10251B", "foreground": "#F4FBF7"},
        surfaces={
            "light": {
                "chrome": "#F3F6FA",
                "raised": SMARTPRICE_GREEN_SURFACE,
                "card": SMARTPRICE_WHITE,
            },
            "dark": {
                "chrome": "#142E21",
                "raised": "#193829",
                "card": "#1D402F",
            },
        },
    ).install()
