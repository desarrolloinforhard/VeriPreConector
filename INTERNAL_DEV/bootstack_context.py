"""Contexto de solo lectura para el shell experimental Bootstack."""

from __future__ import annotations

from dataclasses import dataclass
import getpass

from FUNC.config_json import cargar_config
from core.versioning import obtener_version


MODULOS = ("productos", "publicidad", "configuracion")
PERMISOS_DEFAULT = {modulo: True for modulo in MODULOS}


@dataclass(frozen=True)
class ContextoBootstack:
    usuario_windows: str
    version: str
    permisos: dict[str, bool]
    sincronizacion_automatica: bool


def resolver_permisos(
    config: dict,
    usuario_windows: str,
) -> dict[str, bool]:
    """Replica la lectura de permisos legacy sin completar ni guardar config."""
    perfiles = config.get("perfiles_usuario", {})
    perfil = perfiles.get(usuario_windows) or perfiles.get("default", {})
    modulos = perfil.get("modulos", {})
    return {
        modulo: bool(modulos.get(modulo, PERMISOS_DEFAULT[modulo]))
        for modulo in MODULOS
    }


def cargar_contexto_bootstack() -> ContextoBootstack:
    """Carga usuario, version y permisos sin modificar archivos persistentes."""
    usuario = (getpass.getuser() or "default").strip().lower() or "default"
    config = cargar_config()
    return ContextoBootstack(
        usuario_windows=usuario,
        version=obtener_version(),
        permisos=resolver_permisos(config, usuario),
        sincronizacion_automatica=bool(config.get("sincronizacion_automatica", False)),
    )
