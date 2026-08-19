import unittest

from GUI.GUI_MAIN import GUI_MAIN


class NavegacionPrincipalTest(unittest.TestCase):
    def crear_gui(self, historial):
        gui = GUI_MAIN.__new__(GUI_MAIN)
        gui.VIGIA_VOLVER = list(historial)
        gui.VIGIA_FRAME = historial[-1] if historial else "INICIO"
        gui.selector_invocado = False

        def selector():
            gui.selector_invocado = True

        gui.selector_seccion = selector
        return gui

    def test_volver_de_publicidad_regresa_a_productos(self):
        gui = self.crear_gui(["BOTON_PRODUCTOS", "BOTON_PUBLICIDAD"])

        gui.command_button_volver()

        self.assertEqual(gui.VIGIA_FRAME, "BOTON_PRODUCTOS")
        self.assertEqual(gui.VIGIA_VOLVER, ["BOTON_PRODUCTOS"])
        self.assertTrue(gui.selector_invocado)

    def test_volver_de_productos_regresa_a_inicio(self):
        gui = self.crear_gui(["INICIO", "BOTON_PRODUCTOS"])

        gui.command_button_volver()

        self.assertEqual(gui.VIGIA_FRAME, "INICIO")
        self.assertEqual(gui.VIGIA_VOLVER, ["INICIO"])

    def test_historial_de_un_elemento_regresa_a_inicio_sin_error(self):
        gui = self.crear_gui(["BOTON_PRODUCTOS"])

        gui.command_button_volver()

        self.assertEqual(gui.VIGIA_FRAME, "INICIO")
        self.assertEqual(gui.VIGIA_VOLVER, ["INICIO"])

    def test_historial_vacio_regresa_a_inicio_sin_error(self):
        gui = self.crear_gui([])

        gui.command_button_volver()

        self.assertEqual(gui.VIGIA_FRAME, "INICIO")
        self.assertEqual(gui.VIGIA_VOLVER, ["INICIO"])


if __name__ == "__main__":
    unittest.main()
