"""Incluye los recursos que ttkbootstrap 2.x carga en tiempo de ejecución."""

from PyInstaller.utils.hooks import collect_data_files


datas = collect_data_files("ttkbootstrap")
