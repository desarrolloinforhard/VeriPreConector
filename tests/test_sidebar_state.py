import unittest
import inspect
from unittest.mock import Mock, patch

import GUI.GUI_MAIN as gui_main_module
from GUI.GUI_MAIN import GUI_MAIN
from GUI.CONTENIDO_PRODUCTO import ContenidoProducto
from GUI.CONTENIDO_PUBLICIDAD import ContenidoPublicidad
from GUI.GUI_CONFIG import GUI_CONFIG
from core.ui.theme_tokens import FONT_LABEL_BOLD
from core.ui.ttk_theme import SMARTPRICE_DARK_THEME, SMARTPRICE_LIGHT_THEME
from core.ui.ttk_theme import SMARTPRICE_DARK_BORDER, SMARTPRICE_DARK_CARD, SMARTPRICE_DARK_SURFACE


class SidebarStateTest(unittest.TestCase):
    def test_tema_interfaz_normaliza_valores_persistidos(self):
        self.assertEqual(GUI_MAIN._resolver_tema_interfaz("oscuro"), "oscuro")
        self.assertEqual(GUI_MAIN._resolver_tema_interfaz("dark"), "oscuro")
        self.assertEqual(GUI_MAIN._resolver_tema_interfaz("valor-invalido"), "claro")
        self.assertEqual(GUI_MAIN._nombre_tema_ttk("oscuro"), SMARTPRICE_DARK_THEME)
        self.assertEqual(GUI_MAIN._nombre_tema_ttk("claro"), SMARTPRICE_LIGHT_THEME)
        self.assertTrue(
            GUI_MAIN._ruta_logo_sidebar("oscuro").endswith("INFORHARD_TEMA_OSCURO.png")
        )
        self.assertTrue(
            GUI_MAIN._ruta_logo_sidebar("claro").endswith("INFORHARD_TEMA_CLARO.png")
        )
        self.assertEqual(GUI_MAIN._dimensiones_logo_sidebar(158, 28), (158, 21))
        self.assertEqual(GUI_MAIN._dimensiones_logo_sidebar(120, 18), (120, 16))

    def test_paleta_sidebar_oscura_conserva_contraste_corporativo(self):
        gui = GUI_MAIN.__new__(GUI_MAIN)

        gui._configurar_paleta_sidebar("oscuro")

        self.assertEqual(gui.sidebar_bg, SMARTPRICE_DARK_CARD)
        self.assertEqual(gui.sidebar_card, SMARTPRICE_DARK_CARD)
        self.assertEqual(gui.sidebar_bg, gui.sidebar_card)
        self.assertEqual(gui.sidebar_card_active, "#149455")
        self.assertEqual(gui.sidebar_text_active, "#ffffff")
        self.assertEqual(gui.sidebar_border, SMARTPRICE_DARK_BORDER)
        self.assertNotEqual(gui.sidebar_card, gui.sidebar_card_hover)

    def test_tabla_productos_usa_verde_para_seleccion_en_ambos_temas(self):
        clara = ContenidoProducto._paleta_tabla_productos("claro")
        oscura = ContenidoProducto._paleta_tabla_productos("oscuro")

        self.assertEqual(clara["selected_background"], "#149455")
        self.assertEqual(oscura["selected_background"], "#149455")
        self.assertEqual(oscura["selected_foreground"], "#ffffff")
        self.assertEqual(oscura["section_border"], SMARTPRICE_DARK_BORDER)
        self.assertEqual(oscura["section_label"], "#F4FBF7")
        self.assertNotEqual(oscura["background"], oscura["stripe"])
        self.assertEqual(oscura["background"], SMARTPRICE_DARK_SURFACE)
        self.assertEqual(oscura["header_card"], SMARTPRICE_DARK_SURFACE)
        self.assertEqual(oscura["header_border"], SMARTPRICE_DARK_BORDER)
        self.assertEqual(oscura["table_heading"], "#16211C")
        self.assertEqual(clara["table_heading"], "#F6F8F7")
        self.assertNotEqual(oscura["table_heading"], oscura["selected_background"])

    def test_indicadores_de_productos_separan_titulo_y_valor(self):
        self.assertEqual(
            ContenidoProducto._valor_indicador_estado("Oferta precio: NO"),
            "NO",
        )
        self.assertEqual(
            ContenidoProducto._valor_indicador_estado("Precios adicionales: SI (3)"),
            "SI (3)",
        )
        self.assertEqual(ContenidoProducto._valor_indicador_estado("-"), "-")

    def test_flecha_de_productos_contrasta_con_cada_tema(self):
        self.assertEqual(ContenidoProducto._color_flecha_volver("oscuro"), "#F4FBF7")
        self.assertEqual(ContenidoProducto._color_flecha_volver("claro"), "#087A46")

    def test_productos_formatea_precios_con_convencion_local(self):
        self.assertEqual(ContenidoProducto._formatear_precio_local(1525.63), "$1.525,63")
        self.assertEqual(ContenidoProducto._formatear_precio_local("$1,525.63"), "$1.525,63")
        self.assertEqual(ContenidoProducto._formatear_precio_local("$1.525,63"), "$1.525,63")

    def test_resumen_home_lee_publicidades_sin_modificar_configuracion(self):
        self.assertTrue(hasattr(gui_main_module, "SMARTPRICE_DARK_SURFACE"))
        config = {
            "publicidades": {
                "grupo_activo": "general",
                "grupos": {"general": {"items": {"a": {}, "b": {}}}},
                "globales": {"g": {}},
                "biblioteca": {
                    "a": {"cambios_pendientes": True},
                    "b": {"cambios_pendientes": False},
                },
                "historial_envios": [{"fecha": "2026-08-24 18:00"}],
            }
        }

        resumen = GUI_MAIN._resumen_publicidades_home(config)

        self.assertEqual(resumen[:3], (2, 1, 1))
        self.assertEqual(resumen[3]["fecha"], "2026-08-24 18:00")

    def test_paleta_home_oscura_separa_fondo_tarjeta_y_borde(self):
        paleta = GUI_MAIN._paleta_home("oscuro")

        self.assertEqual(paleta["fondo"], "#0E1512")
        self.assertEqual(paleta["tarjeta"], "#111A16")
        self.assertEqual(paleta["borde"], "#1F2B26")
        self.assertEqual(paleta["status_fondo"], "#0B1210")
        self.assertEqual(paleta["status_borde"], "#1F2B26")

    def test_paleta_home_clara_separa_barra_de_estado(self):
        paleta = GUI_MAIN._paleta_home("claro")

        self.assertEqual(paleta["status_fondo"], "#ECEEED")
        self.assertEqual(paleta["status_borde"], "#D8E1DC")

    def test_alerta_home_resuelve_pendientes_y_catalogo(self):
        texto, color = GUI_MAIN._estado_alerta_home(0, None)
        self.assertEqual(texto, "Sin publicidades pendientes · catálogo sin actualizar")
        self.assertEqual(color, "#7D9188")

        texto, color = GUI_MAIN._estado_alerta_home(3, "2026-08-24")
        self.assertIn("3 publicidades pendientes", texto)
        self.assertEqual(color, "#E5A50A")

    def test_home_formatea_fechas_para_lectura_humana(self):
        self.assertEqual(
            GUI_MAIN._formatear_fecha_home("2026-08-08 10:02:53"),
            "08/08/2026 10:02",
        )
        self.assertEqual(
            GUI_MAIN._formatear_fecha_home("2026-08-08 19:04:53", solo_hora=True),
            "19:04",
        )
        self.assertEqual(GUI_MAIN._formatear_fecha_home(None, solo_hora=True), "--:--")

    def test_icono_inicio_existe_y_tiene_transparencia(self):
        from ASSETS.path_img import PNG_Inicio
        from PIL import Image

        with Image.open(PNG_Inicio()) as imagen:
            self.assertEqual(imagen.mode, "RGBA")
            self.assertEqual(imagen.getpixel((0, 0))[3], 0)

    def test_publicidad_oscura_no_crea_paneles_blancos(self):
        oscura = ContenidoPublicidad._paleta_publicidad("oscuro")

        self.assertEqual(oscura["item_selected"], "#149455")
        self.assertNotEqual(oscura["card_bg"], "#ffffff")
        self.assertNotEqual(oscura["page_bg"], "#ffffff")
        self.assertNotEqual(oscura["card_bg"], oscura["page_bg"])

    def test_sidebar_oscuro_usa_blanco_en_acciones_inferiores(self):
        gui = GUI_MAIN.__new__(GUI_MAIN)

        gui._configurar_paleta_sidebar("oscuro")

        self.assertEqual(gui.sidebar_muted, "#ffffff")
        self.assertEqual(gui.sidebar_brand, "#ffffff")

    def test_publicidad_distribuye_botonera_en_columnas_uniformes(self):
        botones = [Mock() for _ in range(8)]
        frames = [Mock(), Mock()]

        ContenidoPublicidad._distribuir_botones_uniformes(botones, frames, 4)

        for frame in frames:
            self.assertEqual(frame.columnconfigure.call_count, 4)
        for boton in botones:
            boton.grid.assert_called_once()
            self.assertEqual(boton.grid.call_args.kwargs["sticky"], "ew")

    def test_publicidad_explica_resolucion_que_requiere_revision(self):
        publicidad = ContenidoPublicidad.__new__(ContenidoPublicidad)
        publicidad.biblioteca_metadata = {
            "promo.png": {
                "existe": True,
                "estado": "NUEVO",
                "tipo": "imagen",
                "width": 640,
                "height": 480,
            }
        }

        self.assertEqual(publicidad._texto_estado_item("promo.png"), "REVISAR")
        self.assertEqual(
            publicidad._detalle_estado_item("promo.png"),
            "640×480 · menor a 800×600",
        )

    def test_publicidad_muestra_dimensiones_en_tarjeta_valida(self):
        publicidad = ContenidoPublicidad.__new__(ContenidoPublicidad)
        publicidad.biblioteca_metadata = {
            "marca.png": {
                "existe": True,
                "estado": "NUEVO",
                "tipo": "imagen",
                "width": 1920,
                "height": 1080,
            }
        }

        self.assertEqual(publicidad._texto_estado_item("marca.png"), "NUEVO")
        self.assertEqual(publicidad._detalle_estado_item("marca.png"), "1920×1080")

    def test_publicidad_cuenta_tarjetas_repetidas_como_envios_independientes(self):
        publicidad = ContenidoPublicidad.__new__(ContenidoPublicidad)
        publicidad.items = [
            {"filepath": "a.png"},
            {"filepath": "b.png"},
            {"filepath": "a.png"},
            {"filepath": "b.png"},
        ]
        publicidad.biblioteca_metadata = {
            "a.png": {"cambios_pendientes": True},
            "b.png": {"cambios_pendientes": True},
        }
        publicidad.grupo_activo_id = "default"
        publicidad.cols = 5
        publicidad.combo_grupos = Mock()
        publicidad.combo_grupos.get.return_value = "General"
        publicidad.asegurar_config_publicidades = Mock(return_value={
            "grupos": {"default": {"nombre": "General"}},
            "globales": {},
        })
        publicidad.pastillas_resumen = {
            clave: Mock() for clave in ("grupo", "globales", "envio", "pendientes")
        }
        publicidad.lbl_estado_pie = Mock()
        publicidad.btn_validar_pie = Mock()
        publicidad.btn_enviar_pie = Mock()
        publicidad.canvas = Mock()
        publicidad.empty_window_id = 1
        publicidad.drop_window_id = 2
        publicidad.contenedor = Mock()

        publicidad._actualizar_contadores_desde_grilla()

        publicidad.pastillas_resumen["grupo"].configure.assert_called_with(text="DEL GRUPO  4")
        publicidad.pastillas_resumen["envio"].configure.assert_called_with(text="AL ENVIAR  4")
        publicidad.pastillas_resumen["pendientes"].configure.assert_called_with(text="PENDIENTES  4")
        publicidad.btn_enviar_pie.configure.assert_called_with(state="normal")

    def test_alternar_tema_persiste_y_actualiza_el_control(self):
        gui = GUI_MAIN.__new__(GUI_MAIN)
        gui.tema_interfaz = "claro"
        gui.sidebar_collapsed = False
        gui.config_data = {}
        gui.ventana_creacion_caja = Mock()
        gui.boton_tema = Mock()
        gui.DICT_WIDGETS = Mock()
        gui.contenido_productos = None
        gui.contenido_publicidad = None
        gui._suspender_redibujado_ventana = Mock(return_value=None)
        gui._reanudar_redibujado_ventana = Mock()

        with patch.object(
            gui_main_module,
            "actualizar_config_parcial",
            return_value={"tema_interfaz": "oscuro"},
        ) as actualizar:
            gui.alternar_tema_interfaz()

        actualizar.assert_called_once_with({"tema_interfaz": "oscuro"})
        gui.ventana_creacion_caja.theme_use.assert_called_once_with(SMARTPRICE_DARK_THEME)
        gui.boton_tema.configure.assert_any_call(
            text="☀  Modo claro", anchor="w", padx=8
        )
        self.assertEqual(gui.tema_interfaz, "oscuro")

    def test_boton_tema_compacto_muestra_solo_icono(self):
        gui = GUI_MAIN.__new__(GUI_MAIN)
        gui.tema_interfaz = "claro"
        gui.sidebar_collapsed = True
        gui.boton_tema = Mock()

        gui._render_boton_tema()

        gui.boton_tema.configure.assert_called_once_with(
            text="☾", anchor="center", padx=0
        )

    def test_acerca_de_dispone_del_token_de_etiqueta(self):
        self.assertEqual(gui_main_module.FONT_LABEL_BOLD, FONT_LABEL_BOLD)

    def crear_gui(self):
        gui = GUI_MAIN.__new__(GUI_MAIN)
        gui.sidebar_collapsed_width = 68
        gui.sidebar_collapsed_item_width = 52
        return gui

    def test_dimensiones_expandidas_se_conservan(self):
        gui = self.crear_gui()
        render = gui._resolver_render_sidebar(176, 158, False)
        self.assertEqual(render["sidebar_width"], 176)
        self.assertEqual(render["item_width"], 158)
        self.assertTrue(render["show_logo"])
        self.assertTrue(render["show_text"])
        self.assertEqual(render["toggle_text"], "‹")

    def test_dimensiones_compactas_son_estables(self):
        gui = self.crear_gui()
        render = gui._resolver_render_sidebar(176, 158, True)
        self.assertEqual(render["sidebar_width"], 68)
        self.assertEqual(render["item_width"], 52)
        self.assertFalse(render["show_logo"])
        self.assertFalse(render["show_text"])
        self.assertEqual(render["toggle_text"], "☰")

    def test_alternar_menu_invalida_layout_y_vuelve_a_expandir(self):
        gui = self.crear_gui()
        gui.sidebar_collapsed = False
        gui.sidebar_expanded_width = 176
        gui.sidebar_item_width = 158
        gui._sidebar_render_state = (1,)
        gui._main_layout_state = (1,)
        gui.boton_toggle_menu = Mock()
        gui._aplicar_layout_responsivo = Mock()

        gui.alternar_menu_lateral()
        self.assertTrue(gui.sidebar_collapsed)
        gui.boton_toggle_menu.configure.assert_called_with(text="☰")
        self.assertIsNone(gui._sidebar_render_state)
        self.assertIsNone(gui._main_layout_state)

        gui.alternar_menu_lateral()
        self.assertFalse(gui.sidebar_collapsed)
        gui.boton_toggle_menu.configure.assert_called_with(text="‹")
        self.assertEqual(gui._aplicar_layout_responsivo.call_count, 2)

    def test_veinte_ciclos_mantienen_estado_y_simbolo_deterministas(self):
        gui = self.crear_gui()
        gui.sidebar_collapsed = False
        gui.sidebar_expanded_width = 176
        gui.sidebar_item_width = 158
        gui._sidebar_render_state = None
        gui._main_layout_state = None
        gui.boton_toggle_menu = Mock()
        gui._aplicar_layout_responsivo = Mock()

        for _ in range(20):
            gui.alternar_menu_lateral()

        self.assertFalse(gui.sidebar_collapsed)
        gui.boton_toggle_menu.configure.assert_called_with(text="‹")
        self.assertEqual(gui._aplicar_layout_responsivo.call_count, 20)

    def test_render_expandido_restablece_control_atomico(self):
        gui = GUI_MAIN.__new__(GUI_MAIN)
        button = Mock()
        button.sidebar_text = "Configuración"

        gui._render_footer_action(button, button, button, False)

        button.configure.assert_called_once_with(
            text="Configuración",
            compound="left",
            anchor="w",
            padx=8,
        )

    def test_hover_compacto_no_toca_etiqueta_oculta(self):
        gui = self.crear_gui()
        gui.sidebar_collapsed = True
        gui.sidebar_card_hover = "#hover"
        gui.sidebar_card = "#normal"
        gui.sidebar_brand = "#brand"
        gui.sidebar_muted = "#muted"
        button = Mock()

        gui._hover_footer_action(button, button, button, True)

        button.configure.assert_called_once_with(bg="#hover", fg="#brand")

    def test_render_compacto_vacia_texto_y_expandido_lo_restablece(self):
        gui = self.crear_gui()
        button = Mock()
        button.sidebar_text = "Acerca de"

        gui._render_footer_action(button, button, button, True)
        button.configure.assert_called_with(
            text="", compound="none", anchor="center", padx=0
        )

        gui._render_footer_action(button, button, button, False)
        button.configure.assert_called_with(
            text="Acerca de", compound="left", anchor="w", padx=8
        )

    def test_configuracion_usa_navegacion_vertical_sin_notebook(self):
        fuente = inspect.getsource(GUI_CONFIG.__init__)
        fuente_cambio = inspect.getsource(GUI_CONFIG._mostrar_seccion_configuracion)
        self.assertIn("frame_config_nav", fuente)
        self.assertIn("_crear_navegacion_configuracion", fuente)
        self.assertNotIn("ttk.Notebook", fuente)
        self.assertIn("grid_remove", fuente_cambio)
        self.assertNotIn("pack_forget", fuente_cambio)

    def test_configuracion_muestra_dispositivo_inicial_y_guia_plegable(self):
        fuente_lista = inspect.getsource(GUI_CONFIG._poblar_lista_dispositivos_config)
        fuente_guia = inspect.getsource(GUI_CONFIG._alternar_guia_imagenes)
        self.assertIn("selection_set", fuente_lista)
        self.assertIn("_seleccionar_dispositivo_lista", fuente_lista)
        self.assertIn("pack_forget", fuente_guia)


if __name__ == "__main__":
    unittest.main()
