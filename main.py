import argparse
import sys

from core.logging.logger import ProjectLogger
from core.versioning import obtener_version


__version__ = obtener_version("1.15.1")


def configurar_logger():
    ProjectLogger.configure(
        log_dir="logs",
        log_file="veripre.log",
        level=10,  # logging.DEBUG
        max_bytes=5 * 1024 * 1024,
        backup_count=5,
        console=True,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="VeriPre Connector",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--transmitir-completo",
        action="store_true",
        help="Ejecuta el envio completo sin abrir la GUI.",
    )
    group.add_argument(
        "--transmitir-novedades",
        action="store_true",
        help="Sincroniza y envia novedades sin abrir la GUI.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"VeriPre Connector {__version__}",
    )
    parser.add_argument(
        "--sin-ventana-progreso",
        action="store_true",
        help="Ejecuta el envio por consola, sin mostrar la ventana de progreso.",
    )
    args, desconocidos = parser.parse_known_args()
    if desconocidos:
        print(f"Argumentos desconocidos ignorados: {desconocidos}")
    return args


def ejecutar_headless(args):
    from core.services.headless_envio_service import HeadlessEnvioService

    service = HeadlessEnvioService()
    try:
        if args.transmitir_completo:
            return service.transmitir_completo()
        if args.transmitir_novedades:
            return service.transmitir_novedades()
        return 0
    finally:
        service.cerrar()


def ejecutar_headless_con_ventana(args):
    from core.services.headless_progress_window import HeadlessProgressWindow

    modo = "completo" if args.transmitir_completo else "novedades"
    return HeadlessProgressWindow(modo).ejecutar()


def ejecutar_gui():
    from GUI.GUI_MAIN import GUI_MAIN

    GUI_MAIN(__version__)


if __name__ == "__main__":
    configurar_logger()
    args = parse_args()

    if args.transmitir_completo or args.transmitir_novedades:
        if args.sin_ventana_progreso:
            sys.exit(ejecutar_headless(args))
        sys.exit(ejecutar_headless_con_ventana(args))

    ejecutar_gui()
