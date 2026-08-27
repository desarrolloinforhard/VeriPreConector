import logging
import tempfile
import unittest
from pathlib import Path

from DB.database import SQLiteDB
from core.dao.ofertas_plu_sqlite_dao import OfertasPLUSQLiteDAO
from core.dao.productos_dao import ProductosSQLiteDAO
from core.dao.snapshot_validation import SnapshotValidationError


def product(code, price):
    return {
        "cref": f"REF-{code}",
        "codigo": code,
        "descripcion": f"Producto {code}",
        "precio": price,
        "dfechau": "2026-08-27 10:00:00",
    }


def extra_price(code, price):
    return {
        "cref": f"REF-{code}",
        "codigo": code,
        "tipo_precio": "npvp2",
        "categoria": "minorista",
        "origen": "packs_mini",
        "orden": 1,
        "cantidad": 2,
        "titulo": "Llevando x 2",
        "detalle": None,
        "precio": price,
        "nroprecio": "02",
        "dfechau": "2026-08-27 10:00:00",
    }


def simple_offer(code, price):
    return {
        "cref": f"REF-{code}",
        "precio_oferta": price,
        "oferta_desde": "2026-08-01",
        "oferta_hasta": "2026-08-31",
        "oferta_origen": "ATIPICAS",
        "oferta_ccoddiv": "PSO",
        "oferta_dto": 25,
    }


def plu_offer(number, detail):
    return {
        "noferta": number,
        "tipo_oferta": "OFPLU",
        "detalle": detail,
        "fecha_inicio": "2026-08-01",
        "fecha_fin": "2026-08-31",
        "habilitada": True,
        "ccoddiv": str(number).zfill(3),
        "origen": "OFPLU",
        "uid": None,
        "dfechau": None,
    }


def plu_parameter(number):
    return {"noferta": number, "orden": 1, "variable": "SIGNO"}


def plu_product(number, code):
    return {
        "noferta": number,
        "cref": f"REF-{code}",
        "codigo": code,
        "descripcion": f"Producto {code}",
        "precio_oferta": 80,
        "ccoddiv": str(number).zfill(3),
        "cclavec": "O",
        "cclavea": "A",
    }


class SQLiteSyncCycleIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "sync-cycle.db"
        self.db = SQLiteDB(str(path))
        self.db.crear_tabla_VERIPRE_productos()
        self.db.crear_tabla_VERIPRE_producto_precios()
        self.db.crear_tabla_VERIPRE_ofertas_plu()
        self.db.crear_tabla_VERIPRE_ofertas_plu_parametros()
        self.db.crear_tabla_VERIPRE_ofertas_plu_productos()
        self.products = ProductosSQLiteDAO(self.db)
        self.plu = OfertasPLUSQLiteDAO(self.db)

    def tearDown(self):
        self.db.cerrar_conexion()
        self.temp_dir.cleanup()

    def _visible_state(self):
        return {
            "products": self.products.listar_todos(),
            "prices_a": self.products.listar_precios_adicionales_por_codigo("A"),
            "prices_b": self.products.listar_precios_adicionales_por_codigo("B"),
            "simple_offers": self.products.listar_ofertas_por_codigos(["A", "B"]),
            "plu_offers": self.plu.listar_ofertas(),
            "plu_parameters": self.plu.listar_parametros_por_oferta(7),
            "plu_products": self.plu.listar_productos_por_oferta(7),
        }

    def test_two_complete_cycles_leave_only_the_latest_consistent_state(self):
        self.assertTrue(
            self.products.reemplazar_snapshot(
                [product("A", 100), product("B", 200)],
                [extra_price("A", 90), extra_price("B", 180)],
            )
        )
        self.assertTrue(
            self.products.upsert_precios_adicionales(
                [extra_price("A", 85)],
                codigos_objetivo=["A"],
            )
        )
        self.assertTrue(
            self.products.reemplazar_snapshot_ofertas([simple_offer("A", 75)])
        )
        self.assertTrue(
            self.plu.reemplazar_snapshot(
                [plu_offer(7, "Primera promocion")],
                [plu_parameter(7)],
                [plu_product(7, "A")],
            )
        )

        self.assertEqual(
            [row[8] for row in self.products.listar_precios_adicionales_por_codigo("A")],
            [85],
        )
        self.assertEqual(
            [row[8] for row in self.products.listar_precios_adicionales_por_codigo("B")],
            [180],
        )
        self.assertEqual(self.products.obtener_oferta_por_codigo("A")[1:3], (1, 75))
        self.assertEqual([row[0] for row in self.plu.listar_ofertas_por_codigo("A")], [7])

        self.assertTrue(
            self.products.reemplazar_snapshot(
                [product("A", 110), product("C", 300)],
                [extra_price("A", 95), extra_price("C", 270)],
            )
        )
        self.assertTrue(
            self.products.reemplazar_snapshot_ofertas([simple_offer("C", 250)])
        )
        self.assertTrue(
            self.plu.reemplazar_snapshot(
                [plu_offer(8, "Segunda promocion")],
                [plu_parameter(8)],
                [plu_product(8, "C")],
            )
        )

        self.assertEqual([row[1] for row in self.products.listar_todos()], ["A", "C"])
        self.assertEqual(self.products.listar_precios_adicionales_por_codigo("B"), [])
        self.assertEqual(self.products.obtener_oferta_por_codigo("A")[1], 0)
        self.assertEqual(self.products.obtener_oferta_por_codigo("C")[1:3], (1, 250))
        self.assertEqual(self.plu.listar_ofertas_por_codigo("A"), [])
        self.assertEqual([row[0] for row in self.plu.listar_ofertas_por_codigo("C")], [8])

    def test_failed_ofplu_snapshot_preserves_catalog_prices_and_simple_offer(self):
        self.assertTrue(
            self.products.reemplazar_snapshot(
                [product("A", 100)],
                [extra_price("A", 90)],
            )
        )
        self.assertTrue(
            self.products.reemplazar_snapshot_ofertas([simple_offer("A", 75)])
        )
        self.assertTrue(
            self.plu.reemplazar_snapshot(
                [plu_offer(7, "Snapshot valido")],
                [plu_parameter(7)],
                [plu_product(7, "A")],
            )
        )

        duplicate_parameters = [plu_parameter(8), plu_parameter(8)]
        with self.assertRaisesRegex(SnapshotValidationError, r"parametros\[1\] duplica"):
            self.plu.reemplazar_snapshot(
                [plu_offer(8, "Snapshot invalido")],
                duplicate_parameters,
                [plu_product(8, "A")],
            )

        self.assertEqual([row[1] for row in self.products.listar_todos()], ["A"])
        self.assertEqual(
            [row[8] for row in self.products.listar_precios_adicionales_por_codigo("A")],
            [90],
        )
        self.assertEqual(self.products.obtener_oferta_por_codigo("A")[1:3], (1, 75))
        self.assertEqual([row[0] for row in self.plu.listar_ofertas()], [7])
        self.assertEqual([row[0] for row in self.plu.listar_ofertas_por_codigo("A")], [7])

    def test_repeating_the_same_complete_cycle_is_idempotent(self):
        products = [product("A", 100), product("B", 200)]
        prices = [extra_price("A", 90), extra_price("B", 180)]
        incremental_prices = [extra_price("A", 85)]
        simple_offers = [simple_offer("A", 75)]
        plu_offers = [plu_offer(7, "Promocion estable")]
        plu_parameters = [plu_parameter(7)]
        plu_products = [plu_product(7, "A")]

        def synchronize():
            self.assertTrue(self.products.reemplazar_snapshot(products, prices))
            self.assertTrue(
                self.products.upsert_precios_adicionales(
                    incremental_prices,
                    codigos_objetivo=["A"],
                )
            )
            self.assertTrue(
                self.products.reemplazar_snapshot_ofertas(simple_offers)
            )
            self.assertTrue(
                self.plu.reemplazar_snapshot(
                    plu_offers,
                    plu_parameters,
                    plu_products,
                )
            )

        synchronize()
        first_state = self._visible_state()
        synchronize()
        second_state = self._visible_state()

        self.assertEqual(second_state, first_state)
        self.assertEqual(len(second_state["products"]), 2)
        self.assertEqual(len(second_state["prices_a"]), 1)
        self.assertEqual(len(second_state["prices_b"]), 1)
        self.assertEqual(len(second_state["plu_offers"]), 1)
        self.assertEqual(len(second_state["plu_parameters"]), 1)
        self.assertEqual(len(second_state["plu_products"]), 1)

    def test_repeating_empty_snapshots_keeps_every_collection_empty(self):
        self.assertTrue(
            self.products.reemplazar_snapshot(
                [product("A", 100)],
                [extra_price("A", 90)],
            )
        )
        self.assertTrue(
            self.products.reemplazar_snapshot_ofertas([simple_offer("A", 75)])
        )
        self.assertTrue(
            self.plu.reemplazar_snapshot(
                [plu_offer(7, "Promocion")],
                [plu_parameter(7)],
                [plu_product(7, "A")],
            )
        )

        for _ in range(2):
            self.assertTrue(self.products.reemplazar_snapshot([], []))
            self.assertTrue(self.products.reemplazar_snapshot_ofertas([]))
            self.assertTrue(self.plu.reemplazar_snapshot([], [], []))

        self.assertEqual(self.products.listar_todos(), [])
        self.assertEqual(self.products.listar_precios_adicionales_por_codigo("A"), [])
        self.assertEqual(self.products.listar_ofertas_por_codigos(["A"]), [])
        self.assertEqual(self.plu.listar_ofertas(), [])
        self.assertEqual(self.plu.listar_parametros_por_oferta(7), [])
        self.assertEqual(self.plu.listar_productos_por_oferta(7), [])


if __name__ == "__main__":
    unittest.main()
