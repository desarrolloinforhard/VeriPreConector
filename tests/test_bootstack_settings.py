import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from FUNC import config_json
from INTERNAL_DEV.bootstack_settings import (
    guardar_envio_automatico_novedades,
    guardar_sincronizacion_automatica,
)


class ConfiguracionBootstackTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.path_patch = patch.object(
            config_json,
            "obtener_config_path",
            return_value=self.config_path,
        )
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def guardar_base(self, **valores):
        base = {
            "sincronizacion_automatica": True,
            "envio_automatico_novedades": False,
            "dato_ajeno": {"conservar": True},
        }
        base.update(valores)
        self.config_path.write_text(json.dumps(base), encoding="utf-8")

    def cargar(self):
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def test_desactivar_sincronizacion_desactiva_envio_y_conserva_datos(self):
        self.guardar_base(envio_automatico_novedades=True)

        guardar_sincronizacion_automatica(False)

        config = self.cargar()
        self.assertFalse(config["sincronizacion_automatica"])
        self.assertFalse(config["envio_automatico_novedades"])
        self.assertEqual(config["dato_ajeno"], {"conservar": True})

    def test_no_activa_envio_si_sincronizacion_esta_desactivada(self):
        self.guardar_base(sincronizacion_automatica=False)

        with self.assertRaisesRegex(ValueError, "sincronizacion desactivada"):
            guardar_envio_automatico_novedades(True)

        self.assertFalse(self.cargar()["envio_automatico_novedades"])

    def test_activa_envio_si_sincronizacion_esta_activa(self):
        self.guardar_base()

        guardar_envio_automatico_novedades(True)

        self.assertTrue(self.cargar()["envio_automatico_novedades"])

    def test_json_invalido_no_se_sobrescribe(self):
        contenido = "{invalido"
        self.config_path.write_text(contenido, encoding="utf-8")

        with self.assertRaises(json.JSONDecodeError):
            config_json.actualizar_config_parcial({"una_clave": True})

        self.assertEqual(self.config_path.read_text(encoding="utf-8"), contenido)

    def test_actualizaciones_concurrentes_conservan_ambas_claves(self):
        self.guardar_base()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(
                executor.map(
                    lambda item: config_json.actualizar_config_parcial({item[0]: item[1]}),
                    (("clave_a", 1), ("clave_b", 2)),
                )
            )

        self.assertEqual(len(resultados), 2)
        config = self.cargar()
        self.assertEqual(config["clave_a"], 1)
        self.assertEqual(config["clave_b"], 2)


if __name__ == "__main__":
    unittest.main()
