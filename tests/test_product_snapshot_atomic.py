import logging
import tempfile
import unittest
from pathlib import Path

from DB.database import SQLiteDB
from core.dao.productos_dao import ProductosSQLiteDAO
from core.dao.snapshot_validation import SnapshotValidationError
from core.services.productos_sync_service import ProductosSyncService


def product(code, price=100, extra_prices=None):
    return {
        "cref": f"REF-{code}",
        "codigo": code,
        "descripcion": f"Producto {code}",
        "precio": price,
        "dfechau": "2026-08-27 10:00:00",
        "precios_adicionales": extra_prices or [],
    }


def extra_price(code, price=90):
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


def simple_offer(code, price=75):
    return {
        "cref": f"REF-{code}",
        "precio_oferta": price,
        "oferta_desde": "2026-08-01",
        "oferta_hasta": "2026-08-31",
        "oferta_origen": "ATIPICAS",
        "oferta_ccoddiv": "PSO",
        "oferta_dto": 25,
    }


class AtomicProductSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "products.db"
        self.db = SQLiteDB(str(path))
        self.db.crear_tabla_VERIPRE_productos()
        self.db.crear_tabla_VERIPRE_producto_precios()
        self.dao = ProductosSQLiteDAO(self.db)

    def tearDown(self):
        self.db.cerrar_conexion()
        self.temp_dir.cleanup()

    def test_success_replaces_products_and_extra_prices_together(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [product("OLD")],
                [extra_price("OLD")],
            )
        )

        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [product("NEW", 120)],
                [extra_price("NEW", 110)],
            )
        )

        products = self.dao.listar_todos()
        prices = self.dao.listar_precios_adicionales_por_codigo("NEW")
        self.assertEqual([row[1] for row in products], ["NEW"])
        self.assertEqual([row[0] for row in prices], ["NEW"])
        self.assertEqual(self.dao.listar_precios_adicionales_por_codigo("OLD"), [])

    def test_invalid_extra_price_rolls_back_entire_snapshot(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [product("OLD")],
                [extra_price("OLD")],
            )
        )
        invalid_price = extra_price("NEW")
        invalid_price["codigo"] = None

        with self.assertRaisesRegex(SnapshotValidationError, r"precios\[0\].codigo"):
            self.dao.reemplazar_snapshot(
                [product("NEW")],
                [invalid_price],
            )

        products = self.dao.listar_todos()
        self.assertEqual([row[1] for row in products], ["OLD"])
        self.assertEqual(
            [row[0] for row in self.dao.listar_precios_adicionales_por_codigo("OLD")],
            ["OLD"],
        )
        self.assertEqual(self.dao.listar_precios_adicionales_por_codigo("NEW"), [])

    def test_empty_snapshot_clears_products_and_prices(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [product("OLD")],
                [extra_price("OLD")],
            )
        )

        self.assertTrue(self.dao.reemplazar_snapshot([], []))

        self.assertEqual(self.dao.listar_todos(), [])
        self.assertEqual(self.dao.listar_precios_adicionales_por_codigo("OLD"), [])

    def test_incremental_prices_only_replace_target_codes(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [product("A"), product("B")],
                [extra_price("A", 90), extra_price("B", 80)],
            )
        )

        self.assertTrue(
            self.dao.upsert_precios_adicionales(
                [extra_price("A", 70)],
                codigos_objetivo=["A"],
            )
        )

        self.assertEqual(
            [row[8] for row in self.dao.listar_precios_adicionales_por_codigo("A")],
            [70],
        )
        self.assertEqual(
            [row[8] for row in self.dao.listar_precios_adicionales_por_codigo("B")],
            [80],
        )

    def test_invalid_incremental_price_rolls_back_target_deletion(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [product("A"), product("B")],
                [extra_price("A", 90), extra_price("B", 80)],
            )
        )
        invalid_price = extra_price("A", 70)
        invalid_price["codigo"] = None

        with self.assertRaisesRegex(SnapshotValidationError, r"precios\[0\].codigo"):
            self.dao.upsert_precios_adicionales(
                [invalid_price],
                codigos_objetivo=["A"],
            )

        self.assertEqual(
            [row[8] for row in self.dao.listar_precios_adicionales_por_codigo("A")],
            [90],
        )
        self.assertEqual(
            [row[8] for row in self.dao.listar_precios_adicionales_por_codigo("B")],
            [80],
        )

    def test_empty_incremental_prices_remove_only_target_code(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [product("A"), product("B")],
                [extra_price("A", 90), extra_price("B", 80)],
            )
        )

        self.assertTrue(
            self.dao.upsert_precios_adicionales(
                [],
                codigos_objetivo=["A"],
            )
        )

        self.assertEqual(self.dao.listar_precios_adicionales_por_codigo("A"), [])
        self.assertEqual(
            [row[8] for row in self.dao.listar_precios_adicionales_por_codigo("B")],
            [80],
        )

    def test_simple_offer_snapshot_moves_offer_atomically(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [product("A"), product("B")],
                [],
            )
        )
        self.assertTrue(self.dao.reemplazar_snapshot_ofertas([simple_offer("A")]))

        self.assertTrue(self.dao.reemplazar_snapshot_ofertas([simple_offer("B", 60)]))

        offer_a = self.dao.obtener_oferta_por_codigo("A")
        offer_b = self.dao.obtener_oferta_por_codigo("B")
        self.assertEqual(offer_a[1], 0)
        self.assertIsNone(offer_a[2])
        self.assertEqual(offer_b[1], 1)
        self.assertEqual(offer_b[2], 60)

    def test_failed_simple_offer_update_rolls_back_clear(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [product("A"), product("B")],
                [],
            )
        )
        self.assertTrue(self.dao.reemplazar_snapshot_ofertas([simple_offer("A")]))
        self.db.ejecutar_consulta(
            """
            CREATE TRIGGER reject_b_offer
            BEFORE UPDATE OF TIENE_OFERTA ON productos
            WHEN NEW.CREF = 'REF-B' AND NEW.TIENE_OFERTA = 1
            BEGIN
                SELECT RAISE(ABORT, 'oferta rechazada');
            END
            """
        )

        self.assertFalse(self.dao.reemplazar_snapshot_ofertas([simple_offer("B")]))

        offer_a = self.dao.obtener_oferta_por_codigo("A")
        offer_b = self.dao.obtener_oferta_por_codigo("B")
        self.assertEqual(offer_a[1], 1)
        self.assertEqual(offer_a[2], 75)
        self.assertEqual(offer_b[1], 0)

    def test_empty_simple_offer_snapshot_clears_previous_offers(self):
        self.assertTrue(self.dao.reemplazar_snapshot([product("A")], []))
        self.assertTrue(self.dao.reemplazar_snapshot_ofertas([simple_offer("A")]))

        self.assertTrue(self.dao.reemplazar_snapshot_ofertas([]))

        offer = self.dao.obtener_oferta_por_codigo("A")
        self.assertEqual(offer[1], 0)
        self.assertIsNone(offer[2])

    def test_duplicate_product_code_is_rejected_before_replacing_snapshot(self):
        self.assertTrue(self.dao.reemplazar_snapshot([product("OLD")], []))

        with self.assertRaisesRegex(SnapshotValidationError, "duplica codigo"):
            self.dao.reemplazar_snapshot(
                [product("NEW"), product("NEW", 120)],
                [],
            )

        self.assertEqual([row[1] for row in self.dao.listar_todos()], ["OLD"])

    def test_orphan_extra_price_is_rejected_before_replacing_snapshot(self):
        self.assertTrue(self.dao.reemplazar_snapshot([product("OLD")], []))

        with self.assertRaisesRegex(SnapshotValidationError, "no existe en productos"):
            self.dao.reemplazar_snapshot(
                [product("NEW")],
                [extra_price("UNKNOWN")],
            )

        self.assertEqual([row[1] for row in self.dao.listar_todos()], ["OLD"])

    def test_unknown_simple_offer_reference_preserves_previous_offer(self):
        self.assertTrue(self.dao.reemplazar_snapshot([product("A")], []))
        self.assertTrue(self.dao.reemplazar_snapshot_ofertas([simple_offer("A")]))

        with self.assertRaisesRegex(SnapshotValidationError, "no existe en productos"):
            self.dao.reemplazar_snapshot_ofertas([simple_offer("UNKNOWN")])

        self.assertEqual(self.dao.obtener_oferta_por_codigo("A")[1:3], (1, 75))


class FakeProductsDAO:
    def __init__(self, result=True):
        self.snapshots = []
        self.result = result

    def reemplazar_snapshot(self, products, prices):
        self.snapshots.append((products, prices))
        return self.result

    def reemplazar_snapshot_ofertas(self, offers):
        return self.result


class FullSyncIntegrationTests(unittest.TestCase):
    def test_full_sync_uses_one_atomic_snapshot_call(self):
        service = ProductosSyncService.__new__(ProductosSyncService)
        service.sqlite_dao = FakeProductsDAO()
        service._sync_snapshot_ofertas = lambda offers, callback=None: None
        resolved = [product("NEW", extra_prices=[extra_price("NEW")])]

        total = service._guardar_productos(
            resolved,
            [],
            {},
            replace_all=True,
        )

        self.assertEqual(total, 1)
        self.assertEqual(len(service.sqlite_dao.snapshots), 1)
        saved_products, saved_prices = service.sqlite_dao.snapshots[0]
        self.assertEqual(saved_products, resolved)
        self.assertEqual(saved_prices, [extra_price("NEW")])

    def test_full_sync_stops_when_atomic_snapshot_fails(self):
        service = ProductosSyncService.__new__(ProductosSyncService)
        service.sqlite_dao = FakeProductsDAO(result=False)
        offer_sync_calls = []
        service._sync_snapshot_ofertas = lambda offers, callback=None: offer_sync_calls.append(offers)

        with self.assertRaisesRegex(RuntimeError, "reemplazar atomicamente"):
            service._guardar_productos(
                [product("NEW")],
                [],
                {},
                replace_all=True,
            )

        self.assertEqual(offer_sync_calls, [])

    def test_offer_sync_stops_when_atomic_snapshot_fails(self):
        service = ProductosSyncService.__new__(ProductosSyncService)
        service.sqlite_dao = FakeProductsDAO(result=False)

        with self.assertRaisesRegex(RuntimeError, "snapshot local de ofertas"):
            service._sync_snapshot_ofertas(
                {"REF-A": simple_offer("A")}
            )


if __name__ == "__main__":
    unittest.main()
