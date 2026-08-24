import unittest
from unittest.mock import Mock, patch

import GUI.GUI_MAIN as gui_main_module
from GUI.GUI_MAIN import GUI_MAIN
from GUI.CONTENIDO_PRODUCTO import ContenidoProducto
from GUI.CONTENIDO_PUBLICIDAD import ContenidoPublicidad
from core.ui.theme_tokens import FONT_LABEL_BOLD
from core.ui.ttk_theme import SMARTPRICE_DARK_THEME, SMARTPRICE_LIGHT_THEME


class SidebarStateTest(unittest.TestCase):
    def test_tema_interfaz_normaliza_valores_persistidos(self):
        self.assertEqual(GUI_MAIN._resolver_tema_interfaz("oscuro"), "oscuro")
        self.assertEqual(GUI_MAIN._resolver_tema_interfaz("dark"), "oscuro")
        self.assertEqual(GUI_MAIN._resolver_tema_interfaz("valor-invalido"), "claro")
        self.assertEqual(GUI_MAIN._nombre_tema_ttk("oscuro"), SMARTPRICE_DARK_THEME)
        self.assertEqual(GUI_MAIN._nombre_tema_ttk("claro"), SMARTPRICE_LIGHT_THEME)

    def test_paleta_sidebar_oscura_conserva_contraste_corporativo(self):
        gui = GUI_MAIN.__new__(GUI_MAIN)

        gui._configurar_paleta_sidebar("oscuro")

        self.assertEqual(gui.sidebar_bg, "#10251b")
        self.assertEqual(gui.sidebar_card_active, "#149455")
        self.assertEqual(gui.sidebar_text_active, "#ffffff")
        self.assertEqual(gui.sidebar_border, "#f4fbf7")
        self.assertNotEqual(gui.sidebar_card, gui.sidebar_card_hover)

    def test_tabla_productos_usa_verde_para_seleccion_en_ambos_temas(self):
        clara = ContenidoProducto._paleta_tabla_productos("claro")
        oscura = ContenidoProducto._paleta_tabla_productos("oscuro")

        self.assertEqual(clara["selected_background"], "#149455")
        self.assertEqual(oscura["selected_background"], "#149455")
        self.assertEqual(oscura["selected_foreground"], "#ffffff")
        self.assertEqual(oscura["section_border"], "#f4fbf7")
        self.assertNotEqual(oscura["background"], oscura["stripe"])

    def test_publicidad_oscura_no_crea_paneles_blancos(self):
        oscura = ContenidoPublicidad._paleta_publicidad("oscuro")

        self.assertEqual(oscura["item_selected"], "#149455")
        self.assertNotEqual(oscura["card_bg"], "#ffffff")
        self.assertNotEqual(oscura["page_bg"], "#ffffff")
        self.assertNotEqual(oscura["card_bg"], oscura["page_bg"])

    def test_publicidad_distribuye_botonera_en_columnas_uniformes(self):
        botones = [Mock() for _ in range(8)]
        frames = [Mock(), Mock()]

        ContenidoPublicidad._distribuir_botones_uniformes(botones, frames, 4)

        for frame in frames:
            self.assertEqual(frame.columnconfigure.call_count, 4)
        for boton in botones:
            boton.grid.assert_called_once()
            self.assertEqual(boton.grid.call_args.kwargs["sticky"], "ew")

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


if __name__ == "__main__":
    unittest.main()
