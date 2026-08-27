import json
import unittest

from core.services.productos_sync_service import ProductosSyncService
from core.services.sync_errors import SynchronizationReadError
from core.services.sync_summary import SyncRunSummary


class RecordingLogger:
    def __init__(self):
        self.messages = []

    def info(self, template, payload):
        self.messages.append(template % payload)


class SyncRunSummaryTests(unittest.TestCase):
    def test_success_summary_contains_only_structured_operational_data(self):
        summary = SyncRunSummary("productos_completo", run_id="run-1")
        summary.set_counts(productos_guardados=2, precios_adicionales=3)
        summary.finish_success()
        logger = RecordingLogger()

        summary.log(logger)

        payload = json.loads(logger.messages[0].split(" | ", 1)[1])
        self.assertEqual(payload["ejecucion_id"], "run-1")
        self.assertEqual(payload["estado"], "success")
        self.assertEqual(payload["cantidades"]["productos_guardados"], 2)
        self.assertEqual(payload["cantidades"]["operaciones_rechazadas"], 0)
        self.assertIsNone(payload["codigo_error"])
        self.assertNotIn("productos", payload)

    def test_error_summary_records_code_without_exception_message(self):
        summary = SyncRunSummary("productos_completo", run_id="run-2")
        error = SynchronizationReadError(
            "password=secreto",
            resource="articulos",
            operation="leer_origen",
        )

        summary.finish_error(error)
        payload = summary.as_dict()

        self.assertEqual(payload["estado"], "error")
        self.assertEqual(payload["codigo_error"], "sync_read_error")
        self.assertEqual(payload["cantidades"]["operaciones_rechazadas"], 1)
        self.assertNotIn("secreto", json.dumps(payload))

    def test_product_wrapper_preserves_result_and_exposes_summary(self):
        service = ProductosSyncService.__new__(ProductosSyncService)
        result = {
            "articulos": [1, 2],
            "precios_adicionales": [1],
            "ofertas_activas": [1],
            "ofertas_plu": {"total_ofertas": 1},
            "total": 2,
        }

        returned = service._ejecutar_con_resumen(
            "productos_completo",
            lambda: result,
        )

        self.assertIs(returned, result)
        summary = service.last_sync_summary.as_dict()
        self.assertEqual(summary["estado"], "success")
        self.assertEqual(summary["cantidades"]["articulos_leidos"], 2)
        self.assertEqual(summary["cantidades"]["ofertas_ofplu"], 1)

    def test_product_wrapper_records_structured_error_and_reraises(self):
        service = ProductosSyncService.__new__(ProductosSyncService)
        error = SynchronizationReadError(
            "fallo de prueba",
            resource="articulos",
            operation="leer_origen",
        )

        with self.assertRaises(SynchronizationReadError):
            service._ejecutar_con_resumen(
                "productos_completo",
                lambda: (_ for _ in ()).throw(error),
            )

        summary = service.last_sync_summary.as_dict()
        self.assertEqual(summary["estado"], "error")
        self.assertEqual(summary["codigo_error"], "sync_read_error")


if __name__ == "__main__":
    unittest.main()
