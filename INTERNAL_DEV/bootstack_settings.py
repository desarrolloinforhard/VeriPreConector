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


def guardar_envio_automatico_novedades(habilitado: bool) -> dict:
    """Persiste el envio automatico solo si la sincronizacion sigue activa."""
    habilitado = bool(habilitado)

    def validar_sincronizacion(config: dict) -> None:
        if habilitado and not bool(config.get("sincronizacion_automatica", False)):
            raise ValueError(
                "No se puede activar el envio automatico con la sincronizacion desactivada"
            )

    return actualizar_config_parcial(
        {"envio_automatico_novedades": habilitado},
        validar=validar_sincronizacion,
    )
