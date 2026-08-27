import logging
import tempfile
import unittest
from pathlib import Path

from DB.database import SQLiteDB
from core.dao.ofertas_plu_sqlite_dao import OfertasPLUSQLiteDAO
from core.dao.snapshot_validation import SnapshotValidationError


def oferta(noferta, detalle):
    return {
        "noferta": noferta,
        "tipo_oferta": "OFPLU",
        "detalle": detalle,
        "fecha_inicio": "2026-08-01",
        "fecha_fin": "2026-08-31",
        "habilitada": True,
        "ccoddiv": str(noferta).zfill(3),
        "origen": "OFPLU",
        "uid": None,
        "dfechau": None,
    }


def parametro(noferta, orden=1, variable="SIGNO"):
    item = {
        "noferta": noferta,
        "orden": orden,
        "variable": variable,
    }
    return item


def producto(noferta, cref):
    return {
        "noferta": noferta,
        "cref": cref,
        "codigo": f"779{noferta:010d}",
        "descripcion": f"Producto {cref}",
        "precio_oferta": 80,
        "ccoddiv": str(noferta).zfill(3),
        "cclavec": "O",
        "cclavea": "A",
    }


class AtomicOfferSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "offers.db"
        self.db = SQLiteDB(str(path))
        self.db.crear_tabla_VERIPRE_ofertas_plu()
        self.db.crear_tabla_VERIPRE_ofertas_plu_parametros()
        self.db.crear_tabla_VERIPRE_ofertas_plu_productos()
        self.dao = OfertasPLUSQLiteDAO(self.db)

    def tearDown(self):
        self.db.cerrar_conexion()
        self.temp_dir.cleanup()

    def test_success_replaces_all_snapshot_tables_together(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [oferta(1, "anterior")],
                [parametro(1)],
                [producto(1, "A1")],
            )
        )

        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [oferta(2, "nuevo")],
                [parametro(2)],
                [producto(2, "B1")],
            )
        )

        self.assertEqual([row[0] for row in self.dao.listar_ofertas()], [2])
        self.assertEqual(
            [row[1] for row in self.dao.listar_parametros_por_oferta(2)],
            [1],
        )
        self.assertEqual(
            [row[1] for row in self.dao.listar_productos_por_oferta(2)],
            ["B1"],
        )
        self.assertEqual(self.dao.listar_parametros_por_oferta(1), [])
        self.assertEqual(self.dao.listar_productos_por_oferta(1), [])

    def test_failed_insert_rolls_back_deletes_and_partial_inserts(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [oferta(1, "anterior")],
                [parametro(1)],
                [producto(1, "A1")],
            )
        )
        duplicate_parameters = [parametro(2), parametro(2)]

        with self.assertRaisesRegex(SnapshotValidationError, r"parametros\[1\] duplica"):
            self.dao.reemplazar_snapshot(
                [oferta(2, "invalido")],
                duplicate_parameters,
                [producto(2, "B1")],
            )

        offers = self.dao.listar_ofertas()
        self.assertEqual([(row[0], row[2]) for row in offers], [(1, "anterior")])
        self.assertEqual(
            [row[1] for row in self.dao.listar_parametros_por_oferta(1)],
            [1],
        )
        self.assertEqual(
            [row[1] for row in self.dao.listar_productos_por_oferta(1)],
            ["A1"],
        )
        self.assertEqual(self.dao.listar_parametros_por_oferta(2), [])
        self.assertEqual(self.dao.listar_productos_por_oferta(2), [])

    def test_empty_snapshot_clears_all_tables_in_one_transaction(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [oferta(1, "anterior")],
                [parametro(1)],
                [producto(1, "A1")],
            )
        )

        self.assertTrue(self.dao.reemplazar_snapshot([], [], []))

        self.assertEqual(self.dao.listar_ofertas(), [])
        self.assertEqual(self.dao.listar_parametros_por_oferta(1), [])
        self.assertEqual(self.dao.listar_productos_por_oferta(1), [])

    def test_orphan_parameter_is_rejected_before_replacing_snapshot(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [oferta(1, "anterior")],
                [parametro(1)],
                [producto(1, "A1")],
            )
        )

        with self.assertRaisesRegex(SnapshotValidationError, "no existe en ofertas_plu"):
            self.dao.reemplazar_snapshot(
                [oferta(2, "nuevo")],
                [parametro(99)],
                [producto(2, "B1")],
            )

        self.assertEqual([row[0] for row in self.dao.listar_ofertas()], [1])

    def test_orphan_product_is_rejected_before_replacing_snapshot(self):
        self.assertTrue(
            self.dao.reemplazar_snapshot(
                [oferta(1, "anterior")],
                [parametro(1)],
                [producto(1, "A1")],
            )
        )

        with self.assertRaisesRegex(SnapshotValidationError, "no existe en ofertas_plu"):
            self.dao.reemplazar_snapshot(
                [oferta(2, "nuevo")],
                [parametro(2)],
                [producto(99, "B1")],
            )

        self.assertEqual([row[0] for row in self.dao.listar_ofertas()], [1])


if __name__ == "__main__":
    unittest.main()
