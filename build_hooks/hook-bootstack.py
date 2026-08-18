"""Incluye recursos y modulos que Bootstack carga dinamicamente."""

from PyInstaller.utils.hooks import collect_all


datas, binaries, hiddenimports = collect_all("bootstack")
