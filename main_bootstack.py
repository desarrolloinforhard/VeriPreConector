r"""Entry point experimental de SmartPrice sobre Bootstack.

No reemplaza a ``main.py`` ni conecta aun servicios productivos.

Uso visual:
    .\.venv\Scripts\python.exe main_bootstack.py

Smoke test:
    .\.venv\Scripts\python.exe main_bootstack.py --smoke
"""

from __future__ import annotations

import argparse

from INTERNAL_DEV.bootstack_context import (
    FEATURE_FLAG_ABOUT,
    FEATURE_FLAG_CONFIG_SIMPLE,
    cargar_contexto_bootstack,
)
from INTERNAL_DEV.bootstack_theme import instalar_tema_smartprice
from INTERNAL_DEV.poc_bootstack_appshell import construir_shell


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Shell experimental Bootstack de SmartPrice")
    parser.add_argument("--smoke", action="store_true", help="Construye y cierra la UI sin ejecutar mainloop")
    parser.add_argument(
        "--about-pilot",
        action="store_true",
        help="Activa el piloto Acerca de solo para esta ejecucion, sin guardar configuracion",
    )
    parser.add_argument(
        "--config-pilot",
        action="store_true",
        help="Activa Configuracion informativa solo para esta ejecucion",
    )
    args = parser.parse_args(argv)

    contexto = cargar_contexto_bootstack()
    config_piloto_habilitado = (
        contexto.piloto_config_simple_habilitado or args.config_pilot
    )
    piloto_habilitado = (
        contexto.piloto_acerca_habilitado
        or config_piloto_habilitado
        or args.about_pilot
        or args.smoke
    )
    if not piloto_habilitado:
        print(
            "Piloto Bootstack desactivado. Use --about-pilot o habilite "
            f"{FEATURE_FLAG_ABOUT}=true o {FEATURE_FLAG_CONFIG_SIMPLE}=true "
            "en la configuracion de prueba."
        )
        return

    instalar_tema_smartprice()
    shell = construir_shell(
        contexto.permisos,
        usar_tema_marca=True,
        usuario=contexto.usuario_windows,
        version=contexto.version,
        sincronizacion_automatica=contexto.sincronizacion_automatica,
        solo_acerca=True,
        incluir_config_simple=config_piloto_habilitado,
    )
    if args.smoke:
        shell.destroy()
        print("MAIN_BOOTSTACK_SMOKE_OK")
        return
    shell.run()


if __name__ == "__main__":
    main()
