"""Contexto de solo lectura para el shell experimental Bootstack."""

from __future__ import annotations

from dataclasses import dataclass
import getpass

from FUNC.config_json import cargar_config
from core.versioning import obtener_version


MODULOS = ("productos", "publicidad", "configuracion")
PERMISOS_DEFAULT = {modulo: True for modulo in MODULOS}
FEATURE_FLAG_ABOUT = "ui_bootstack_about"
FEATURE_FLAG_CONFIG_SIMPLE = "ui_bootstack_config_simple"
FEATURE_FLAG_CONFIG_SYNC_WRITE = "ui_bootstack_config_sync_write"


@dataclass(frozen=True)
class ContextoBootstack:
    usuario_windows: str
    version: str
    permisos: dict[str, bool]
    sincronizacion_automatica: bool
    piloto_acerca_habilitado: bool
    piloto_config_simple_habilitado: bool
    piloto_config_sync_write_habilitado: bool


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
        piloto_acerca_habilitado=bool(config.get(FEATURE_FLAG_ABOUT, False)),
        piloto_config_simple_habilitado=bool(config.get(FEATURE_FLAG_CONFIG_SIMPLE, False)),
        piloto_config_sync_write_habilitado=bool(
            config.get(FEATURE_FLAG_CONFIG_SYNC_WRITE, False)
        ),
    )
