import logging
import tempfile
import unittest
from pathlib import Path

from DB.database import SQLiteDB
from core.dao.sqlite_integrity import SQLiteIntegrityAuditor


class SQLiteIntegrityAuditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "integrity.db"
        self.db = SQLiteDB(str(path))
        self.db.crear_tabla_VERIPRE_productos()
        self.db.crear_tabla_VERIPRE_producto_precios()
        self.db.crear_tabla_VERIPRE_ofertas_plu()
        self.db.crear_tabla_VERIPRE_ofertas_plu_parametros()
        self.db.crear_tabla_VERIPRE_ofertas_plu_productos()
        self.auditor = SQLiteIntegrityAuditor(self.db)

    def tearDown(self):
        self.db.cerrar_conexion()
        self.temp_dir.cleanup()

    def test_empty_database_is_consistent(self):
        report = self.auditor.audit()

        self.assertTrue(report["ok"])
        self.assertEqual(report["total_inconsistencias"], 0)
        self.assertEqual(report["inconsistencias"], [])

    def test_detects_orphans_without_modifying_the_database(self):
        self.db.ejecutar_consulta(
            """
            INSERT INTO producto_precios
                (CREF, codigo, tipo_precio, categoria, origen, orden, titulo, precio)
            VALUES ('REF-X', 'X', 'npvp2', 'minorista', 'test', 1, 'Precio', 90)
            """
        )
        self.db.ejecutar_consulta(
            """
            INSERT INTO ofertas_plu_parametros (noferta, orden, variable)
            VALUES (99, 1, 'SIGNO')
            """
        )
        self.db.ejecutar_consulta(
            """
            INSERT INTO ofertas_plu_productos (noferta, cref, codigo)
            VALUES (98, 'REF-X', 'X')
            """
        )

        report = self.auditor.audit()

        self.assertFalse(report["ok"])
        self.assertEqual(
            {issue["codigo"] for issue in report["inconsistencias"]},
            {
                "precio_sin_producto",
                "parametro_ofplu_sin_cabecera",
                "producto_ofplu_sin_cabecera",
            },
        )
        self.assertEqual(
            self.db.ejecutar_consulta("SELECT codigo FROM producto_precios"),
            [("X",)],
        )

    def test_detects_duplicate_additional_prices(self):
        self.db.ejecutar_consulta(
            """
            INSERT INTO productos (CREF, codigo, descripcion, precio)
            VALUES ('REF-A', 'A', 'Producto A', 100)
            """
        )
        insert_price = """
            INSERT INTO producto_precios
                (CREF, codigo, tipo_precio, categoria, origen, orden, cantidad,
                 titulo, precio, nroprecio)
            VALUES ('REF-A', 'A', 'npvp2', 'minorista', 'test', 1, 2,
                    'Llevando x 2', 90, '02')
        """
        self.db.ejecutar_consulta(insert_price)
        self.db.ejecutar_consulta(insert_price)

        report = self.auditor.audit()

        duplicates = [
            issue
            for issue in report["inconsistencias"]
            if issue["codigo"] == "precio_adicional_duplicado"
        ]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["cantidad"], 2)


if __name__ == "__main__":
    unittest.main()
