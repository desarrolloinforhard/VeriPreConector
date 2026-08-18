r"""POC aislado de AppShell para VPC-F2-003.

No importa ni reemplaza modulos productivos. Ejecutar con:
    .\.venv\Scripts\python.exe INTERNAL_DEV\poc_bootstack_appshell.py

Validacion sin abrir el loop principal:
    .\.venv\Scripts\python.exe INTERNAL_DEV\poc_bootstack_appshell.py --smoke
"""

from __future__ import annotations

import argparse

import bootstack as bs

try:
    from INTERNAL_DEV.bootstack_theme import instalar_tema_smartprice
except ModuleNotFoundError:
    from bootstack_theme import instalar_tema_smartprice


PERMISOS_DEMO = {
    "productos": True,
    "publicidad": True,
    "configuracion": True,
}


def construir_shell(
    permisos: dict[str, bool],
    *,
    usar_tema_marca: bool = True,
    usuario: str = "demo",
    version: str = "POC",
    sincronizacion_automatica: bool | None = None,
    solo_acerca: bool = False,
    incluir_config_simple: bool = False,
) -> bs.AppShell:
    """Construye un shell demostrativo filtrado por permisos efectivos."""
    if usar_tema_marca:
        instalar_tema_smartprice()

    with bs.AppShell(
        title="SmartPrice - POC Bootstack",
        size=(1100, 720),
        min_size=(900, 600),
        theme="smartprice-light" if usar_tema_marca else None,
        light_theme="smartprice-light",
        dark_theme="smartprice-dark",
        available_themes=("smartprice-light", "smartprice-dark"),
        show_statusbar=True,
        remember_window_state=False,
    ) as shell:
        with shell.add_toolbar() as toolbar:
            toolbar.add_sidebar_toggle()
            toolbar.add_label("SmartPrice")
            toolbar.add_spacer()
            toolbar.add_label(f"Usuario: {usuario}")
            toolbar.add_theme_toggle()

        shell.statusbar.add_text("Shell experimental - servicios productivos desconectados")
        shell.statusbar.add_text(f"SmartPrice {version} | Bootstack 0.1.6", side="right")

        with shell.page_nav() as nav:
            if permisos.get("productos") and not solo_acerca:
                with nav.add_page(
                    "productos",
                    text="Productos",
                    icon="box-seam",
                    padding=20,
                    gap=12,
                    horizontal_items="stretch",
                ):
                    bs.Label("Productos", font="heading-lg")
                    bs.DataTable(
                        columns=["codigo", "descripcion", "precio"],
                        rows=[
                            {"codigo": "779000000001", "descripcion": "Producto demo", "precio": 1000.0}
                        ],
                        searchable=True,
                        allow_filter=True,
                    )

            if permisos.get("publicidad") and not solo_acerca:
                with nav.add_page(
                    "publicidad",
                    text="Publicidad",
                    icon="images",
                    padding=20,
                    gap=12,
                    horizontal_items="stretch",
                ):
                    bs.Label("Publicidad", font="heading-lg")
                    with bs.Card(gap=8, horizontal_items="stretch"):
                        bs.Label("Placeholder de biblioteca multimedia")
                        bs.Label("El preview VLC permanece fuera de este POC.")

            if permisos.get("configuracion") and (not solo_acerca or incluir_config_simple):
                with nav.add_page(
                    "configuracion",
                    text="Configuracion",
                    icon="gear",
                    pin_to_footer=True,
                    padding=20,
                    gap=12,
                    horizontal_items="stretch",
                ):
                    bs.Label("Configuracion", font="heading-lg", accent="primary")
                    bs.Label("Vista informativa del piloto Bootstack", accent="muted")
                    bs.Divider(accent="primary")
                    tabs = bs.Tabs()
                    with tabs.add("general", label="General"):
                        with bs.Card(gap=10, horizontal_items="start", accent="primary"):
                            bs.Badge("Solo lectura", accent="primary", variant="pill")
                            bs.Label("Estado general", font="heading-sm")
                            estado_sync = (
                                "Activada" if sincronizacion_automatica else "Desactivada"
                            ) if sincronizacion_automatica is not None else "Sin conectar"
                            bs.Label(f"Version de SmartPrice: {version}")
                            bs.Label(f"Usuario Windows: {usuario}")
                            bs.Label(f"Sincronizacion automatica: {estado_sync}")
                    with tabs.add("permisos", label="Permisos"):
                        with bs.Card(gap=8, horizontal_items="start"):
                            bs.Label("Permisos efectivos del usuario", font="heading-sm")
                            for modulo in ("productos", "publicidad", "configuracion"):
                                estado = "Habilitado" if permisos.get(modulo) else "Sin acceso"
                                bs.Label(f"{modulo.capitalize()}: {estado}")
                    with tabs.add("alcance", label="Alcance"):
                        with bs.Card(gap=8, horizontal_items="stretch"):
                            bs.Label("Datos sensibles fuera de esta fase", font="heading-sm")
                            bs.Label("No se leen ni modifican DSN, credenciales, API keys o dispositivos.")
                            bs.Label("No existen botones Guardar, Limpiar o Enviar en este piloto.")
                            bs.Label("La escritura se habilitara por campo luego de validar esta lectura.", accent="muted")

            with nav.add_page(
                "acerca_de",
                text="Acerca de",
                icon="info-circle",
                pin_to_footer=True,
                padding=20,
                gap=12,
                horizontal_items="stretch",
            ):
                bs.Label("SmartPrice", font="heading-lg", accent="primary")
                bs.Label("Tecnologia para una gestion mas simple", accent="muted")
                bs.Divider(accent="primary")
                with bs.Card(gap=12, horizontal_items="start", accent="primary"):
                    bs.Label("VeriPre_Connector", font="heading-md")
                    bs.Badge("Piloto Bootstack", accent="primary", variant="pill")
                    bs.Label(f"Version: {version}")
                    bs.Label(f"Usuario Windows: {usuario}")
                    bs.Label("Interfaz experimental con identidad visual verde y blanca de Inforhard.")
                with bs.Card(gap=8, horizontal_items="stretch"):
                    bs.Label("Alcance seguro", font="heading-sm")
                    bs.Label("Esta vista es informativa y no conecta bases de datos, red ni multimedia.")
                    bs.Label("La aplicacion productiva continua iniciando exclusivamente desde main.py.")
                    bs.Label("Desactivar el feature flag devuelve el piloto a estado apagado.", accent="muted")

        pagina_inicial = None if solo_acerca else next(
            (key for key, habilitado in permisos.items() if habilitado),
            None,
        )
        shell.navigate(pagina_inicial or "acerca_de")

    return shell


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Construye y destruye el shell sin ejecutar mainloop")
    args = parser.parse_args()

    shell = construir_shell(PERMISOS_DEMO)
    if args.smoke:
        shell.destroy()
        print("POC_SMOKE_OK")
        return
    shell.run()


if __name__ == "__main__":
    main()
