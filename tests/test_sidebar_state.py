import unittest
from unittest.mock import Mock

import GUI.GUI_MAIN as gui_main_module
from GUI.GUI_MAIN import GUI_MAIN
from core.ui.theme_tokens import FONT_LABEL_BOLD


class SidebarStateTest(unittest.TestCase):
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
