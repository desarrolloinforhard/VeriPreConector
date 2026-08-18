"""Escrituras acotadas habilitadas para los pilotos Bootstack."""

from __future__ import annotations

from FUNC.config_json import actualizar_config_parcial


def guardar_sincronizacion_automatica(habilitada: bool) -> dict:
    """Persiste la sincronizacion y conserva la invariante de envio automatico."""
    habilitada = bool(habilitada)
    cambios = {"sincronizacion_automatica": habilitada}
    if not habilitada:
        cambios["envio_automatico_novedades"] = False
    return actualizar_config_parcial(cambios)
