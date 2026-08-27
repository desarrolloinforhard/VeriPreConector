import unittest

from core.services.ofertas_plu_sync_service import OfertasPLUSyncService
from core.services.ofertas_service import OfertasService
from core.services.sync_errors import (
    SynchronizationPersistenceError,
    SynchronizationReadError,
)


class FakeOfertasDAO:
    def __init__(self):
        self.atipicas = {}
        self.ofertap = {}
        self.mix = {}
        self.calls = []

    def productos_atipicas_por_ccoddiv(self, ccoddiv):
        self.calls.append(("atipicas", ccoddiv))
        return self.atipicas.get(ccoddiv, [])

    def productos_ofertap(self, noferta):
        self.calls.append(("ofertap", noferta))
        return self.ofertap.get(noferta, [])

    def productos_mix_canasta(self, noferta):
        self.calls.append(("mix", noferta))
        return self.mix.get(noferta, [])


class FakeSybaseDAO:
    def __init__(self, cabeceras=None, parametros=None, productos=None):
        self.cabeceras = cabeceras or []
        self.parametros = parametros or []
        self.productos = productos or []

    def listar_ofplu_cabeceras(self):
        return self.cabeceras

    def listar_ofplu_parametros(self, nofertas):
        return self.parametros

    def listar_ofplu_proyecciones_atipicas(self, nofertas):
        return self.productos


class FailingSybaseDAO(FakeSybaseDAO):
    def __init__(self, error):
        super().__init__()
        self.error = error

    def listar_ofplu_cabeceras(self):
        raise self.error


class FakeSQLiteDAO:
    def __init__(self, succeeds=True):
        self.snapshots = []
        self.succeeds = succeeds

    def reemplazar_snapshot(self, ofertas, parametros, productos):
        self.snapshots.append((ofertas, parametros, productos))
        return self.succeeds


def product_row(cref="A1", description="Producto", price=80):
    return (cref, description, 100, price, 20, None)


def parameter_row(
    noferta=7,
    variable="SIGNO",
    cp0="Y",
    cp1="2",
    cp2="PORCENTAJE",
    cp3="-",
    cp4="1500",
    cp5="UNIT",
):
    return (
        "OFPLU",
        noferta,
        1,
        variable,
        cp0,
        cp1,
        cp2,
        cp3,
        cp4,
        cp5,
        None,
        None,
        None,
        None,
        "detalle",
        "uid",
        "2026-08-01",
    )


def offer_product_row(noferta="007", cref="A1", code="779000000001"):
    return (
        cref,
        code,
        "Producto",
        80,
        20,
        "2026-08-01",
        "2026-08-31",
        noferta,
        "O",
        "A",
        1,
        2,
        "detalle",
        "uid",
        "2026-08-01",
    )


class OfertasServiceTests(unittest.TestCase):
    def test_ofplu_prefers_padded_atipicas_variant(self):
        dao = FakeOfertasDAO()
        dao.atipicas["007"] = [product_row()]

        result = OfertasService(dao).traer_productos(
            {"tipo": "OFPLU", "noferta": 7}
        )

        self.assertEqual(result["modo"], "ATIPICAS(CCODDIV=007)")
        self.assertEqual(result["items"][0]["cref"], "A1")
        self.assertEqual(
            dao.calls,
            [("atipicas", "7"), ("atipicas", "007")],
        )

    def test_ofplu_uses_ofertap_only_when_atipicas_has_no_items(self):
        dao = FakeOfertasDAO()
        dao.ofertap[7] = [product_row(price=75)]

        result = OfertasService(dao).traer_productos(
            {"tipo": "OFPLU", "noferta": 7}
        )

        self.assertEqual(result["modo"], "OFERTAP_FALLBACK")
        self.assertEqual(result["items"][0]["precio_oferta"], 75)

    def test_ofcanasta_falls_back_to_mix_canas(self):
        dao = FakeOfertasDAO()
        dao.mix[9] = [product_row(cref="M1")]

        result = OfertasService(dao).traer_productos(
            {"tipo": "OFCANASTA", "noferta": 9}
        )

        self.assertEqual(result["modo"], "MIX_CANAS")
        self.assertEqual(result["items"][0]["cref"], "M1")

    def test_unknown_offer_type_is_explicitly_rejected(self):
        result = OfertasService(FakeOfertasDAO()).traer_productos(
            {"tipo": "PSO", "noferta": 1}
        )

        self.assertEqual(result, {"modo": "TIPO_NO_SOPORTADO", "items": []})


class OfertasPLUSyncServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = OfertasPLUSyncService.__new__(OfertasPLUSyncService)

    def test_signo_parameter_keeps_business_fields_and_visible_value(self):
        result = self.service._normalizar_parametros([parameter_row()])

        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertEqual(item["relacion"], "Y")
        self.assertEqual(item["cantidad"], 2)
        self.assertEqual(item["tipo_valor"], "PORCENTAJE")
        self.assertEqual(item["signo"], "-")
        self.assertEqual(item["valor_raw"], 1500.0)
        self.assertEqual(item["valor_visible"], 15.0)
        self.assertEqual(item["modo"], "UNIT")

    def test_disable_parameter_marks_offer_as_disabled(self):
        parameters = self.service._normalizar_parametros(
            [parameter_row(variable=" disable ")]
        )
        headers = [
            (7, "OFPLU", "Promo", "2026-08-01", "2026-08-31", "uid", None)
        ]

        offers = self.service._normalizar_cabeceras(headers, parameters)

        self.assertFalse(offers[7]["habilitada"])

    def test_products_ignore_invalid_or_unknown_offer_references(self):
        rows = [
            offer_product_row("007", "A1"),
            offer_product_row("999", "B1"),
            offer_product_row("PSO", "C1"),
            offer_product_row("007", ""),
        ]

        result = self.service._normalizar_productos(rows, {7})

        self.assertEqual([item["cref"] for item in result], ["A1"])

    def test_products_are_deduplicated_by_offer_and_source_keys(self):
        row = offer_product_row("007", "A1")

        result = self.service._normalizar_productos([row, row], {7})

        self.assertEqual(len(result), 1)

    def test_empty_source_replaces_snapshot_with_empty_collections(self):
        sqlite_dao = FakeSQLiteDAO()
        service = OfertasPLUSyncService.__new__(OfertasPLUSyncService)
        service.sybase_dao = FakeSybaseDAO()
        service.sqlite_dao = sqlite_dao
        progress = []

        result = service.sincronizar(lambda message, current, total: progress.append(
            (message, current, total)
        ))

        self.assertEqual(result["total_ofertas"], 0)
        self.assertEqual(sqlite_dao.snapshots, [([], [], [])])
        self.assertEqual(progress[-1][1:], (100, 100))

    def test_sync_persists_a_consistent_normalized_snapshot(self):
        sqlite_dao = FakeSQLiteDAO()
        service = OfertasPLUSyncService.__new__(OfertasPLUSyncService)
        service.sybase_dao = FakeSybaseDAO(
            cabeceras=[
                (7, " OFPLU ", " Promo ", "2026-08-01", "2026-08-31", " uid ", None)
            ],
            parametros=[parameter_row()],
            productos=[offer_product_row()],
        )
        service.sqlite_dao = sqlite_dao

        result = service.sincronizar()

        self.assertEqual(result["total_ofertas"], 1)
        self.assertEqual(result["ofertas"][0]["tipo_oferta"], "OFPLU")
        self.assertEqual(result["productos"][0]["noferta"], 7)
        self.assertEqual(sqlite_dao.snapshots[0][0], result["ofertas"])
        self.assertEqual(sqlite_dao.snapshots[0][1], result["parametros"])
        self.assertEqual(sqlite_dao.snapshots[0][2], result["productos"])
        summary = service.last_sync_summary.as_dict()
        self.assertEqual(summary["estado"], "success")
        self.assertEqual(summary["cantidades"]["ofertas"], 1)
        self.assertEqual(summary["cantidades"]["parametros"], 1)
        self.assertEqual(summary["cantidades"]["productos"], 1)

    def test_empty_sync_propagates_snapshot_persistence_failure(self):
        service = OfertasPLUSyncService.__new__(OfertasPLUSyncService)
        service.sybase_dao = FakeSybaseDAO()
        service.sqlite_dao = FakeSQLiteDAO(succeeds=False)

        with self.assertRaisesRegex(RuntimeError, "snapshot local de OFPLU"):
            service.sincronizar()

    def test_populated_sync_propagates_snapshot_persistence_failure(self):
        service = OfertasPLUSyncService.__new__(OfertasPLUSyncService)
        service.sybase_dao = FakeSybaseDAO(
            cabeceras=[
                (7, "OFPLU", "Promo", "2026-08-01", "2026-08-31", "uid", None)
            ],
            parametros=[parameter_row()],
            productos=[offer_product_row()],
        )
        service.sqlite_dao = FakeSQLiteDAO(succeeds=False)

        with self.assertRaises(SynchronizationPersistenceError) as raised:
            service.sincronizar()

        self.assertEqual(raised.exception.resource, "ofertas_ofplu")
        self.assertEqual(service.last_sync_summary.status, "error")
        self.assertEqual(
            service.last_sync_summary.error_code,
            "sync_persistence_error",
        )

    def test_source_read_error_keeps_original_cause(self):
        cause = OSError("origen no disponible")
        service = OfertasPLUSyncService.__new__(OfertasPLUSyncService)
        service.sybase_dao = FailingSybaseDAO(cause)
        service.sqlite_dao = FakeSQLiteDAO()

        with self.assertRaises(SynchronizationReadError) as raised:
            service.sincronizar()

        self.assertIs(raised.exception.__cause__, cause)
        self.assertEqual(raised.exception.code, "sync_read_error")
        self.assertEqual(raised.exception.operation, "leer_origen")


if __name__ == "__main__":
    unittest.main()
