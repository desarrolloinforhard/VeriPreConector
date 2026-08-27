import logging
import tempfile
import time
import unittest
from pathlib import Path

from DB.database import SQLiteDB


class SQLiteIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "indexes.db"
        self.db = SQLiteDB(str(path))
        self.db.crear_tabla_VERIPRE_productos()
        self.db.crear_tabla_VERIPRE_producto_precios()
        self.db.crear_tabla_VERIPRE_ofertas_plu()
        self.db.crear_tabla_VERIPRE_ofertas_plu_productos()

    def tearDown(self):
        self.db.cerrar_conexion()
        self.temp_dir.cleanup()

    def test_frequent_queries_use_the_expected_indexes(self):
        plans = {
            "idx_productos_dfechau_codigo": self._plan(
                """
                SELECT codigo FROM productos
                WHERE dFechaU >= ?
                ORDER BY dFechaU, codigo
                """,
                ("2026-08-01",),
            ),
            "idx_producto_precios_codigo_orden": self._plan(
                """
                SELECT codigo, precio FROM producto_precios
                WHERE codigo = ?
                ORDER BY orden, cantidad, titulo
                """,
                ("A",),
            ),
            "idx_ofertas_plu_productos_codigo_noferta": self._plan(
                """
                SELECT noferta, cref FROM ofertas_plu_productos
                WHERE codigo = ?
                ORDER BY noferta
                """,
                ("A",),
            ),
        }

        for index_name, plan in plans.items():
            self.assertIn(index_name, plan)
            self.assertNotIn("SCAN ", plan)

    def test_existing_database_receives_indexes_without_losing_rows(self):
        self.db.ejecutar_consulta(
            "INSERT INTO productos (CREF, codigo, descripcion, precio, dFechaU) "
            "VALUES ('REF-A', 'A', 'Producto A', 100, '2026-08-01')"
        )

        self.db.crear_tabla_VERIPRE_productos()
        self.db.crear_tabla_VERIPRE_producto_precios()
        self.db.crear_tabla_VERIPRE_ofertas_plu_productos()

        self.assertEqual(
            self.db.ejecutar_consulta("SELECT codigo FROM productos"),
            [("A",)],
        )
        names = {
            row[1]
            for table in ("productos", "producto_precios", "ofertas_plu_productos")
            for row in self.db.ejecutar_consulta(f"PRAGMA index_list({table})")
        }
        self.assertTrue(
            {
                "idx_productos_dfechau_codigo",
                "idx_producto_precios_codigo_orden",
                "idx_ofertas_plu_productos_codigo_noferta",
            }.issubset(names)
        )

    def test_code_index_reduces_repeated_lookup_time(self):
        rows = [
            (
                f"REF-{index}",
                f"CODE-{index:05d}",
                "npvp2",
                "minorista",
                "test",
                1,
                2,
                "Llevando x 2",
                90,
            )
            for index in range(12000)
        ]
        connection = self.db.conectar()
        connection.executemany(
            """
            INSERT INTO producto_precios
                (CREF, codigo, tipo_precio, categoria, origen, orden, cantidad,
                 titulo, precio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()
        query = "SELECT precio FROM producto_precios WHERE codigo = ?"
        params = ("CODE-11999",)

        connection.execute("DROP INDEX idx_producto_precios_codigo_orden")
        without_index = self._measure(connection, query, params)
        plan_without = self._raw_plan(connection, query, params)

        connection.execute(
            "CREATE INDEX idx_producto_precios_codigo_orden "
            "ON producto_precios(codigo, orden, cantidad, titulo)"
        )
        with_index = self._measure(connection, query, params)
        plan_with = self._raw_plan(connection, query, params)

        self.assertIn("SCAN producto_precios", plan_without)
        self.assertIn("idx_producto_precios_codigo_orden", plan_with)
        self.assertLess(with_index, without_index)

    def _plan(self, query, params):
        rows = self.db.ejecutar_consulta(f"EXPLAIN QUERY PLAN {query}", params)
        return " ".join(str(row[3]) for row in rows)

    def _raw_plan(self, connection, query, params):
        rows = connection.execute(f"EXPLAIN QUERY PLAN {query}", params).fetchall()
        return " ".join(str(row[3]) for row in rows)

    def _measure(self, connection, query, params):
        started = time.perf_counter()
        for _ in range(80):
            connection.execute(query, params).fetchall()
        return time.perf_counter() - started


if __name__ == "__main__":
    unittest.main()
