import logging
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from DB.database import SQLiteDB


class SQLiteConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "smartprice-test.db"
        self.db = SQLiteDB(str(self.db_path))
        self.db.ejecutar_consulta(
            """
            CREATE TABLE eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker INTEGER NOT NULL,
                secuencia INTEGER NOT NULL,
                valor TEXT NOT NULL,
                UNIQUE(worker, secuencia)
            )
            """
        )

    def tearDown(self):
        self.db.cerrar_conexion()
        self.temp_dir.cleanup()

    def test_connection_enables_shared_access_pragmas(self):
        busy_timeout = self.db.ejecutar_consulta("PRAGMA busy_timeout")
        foreign_keys = self.db.ejecutar_consulta("PRAGMA foreign_keys")
        journal_mode = self.db.ejecutar_consulta("PRAGMA journal_mode")

        self.assertEqual(busy_timeout, [(30000,)])
        self.assertEqual(foreign_keys, [(1,)])
        self.assertEqual(journal_mode[0][0].lower(), "wal")

    def test_concurrent_writers_keep_every_committed_row(self):
        workers = 8
        rows_per_worker = 25

        def write_rows(worker):
            for sequence in range(rows_per_worker):
                result = self.db.ejecutar_consulta(
                    "INSERT INTO eventos(worker, secuencia, valor) VALUES (?, ?, ?)",
                    (worker, sequence, f"{worker}:{sequence}"),
                )
                self.assertEqual(result, [])

        with ThreadPoolExecutor(max_workers=workers) as executor:
            list(executor.map(write_rows, range(workers)))

        count = self.db.ejecutar_consulta("SELECT COUNT(*) FROM eventos")
        duplicates = self.db.ejecutar_consulta(
            """
            SELECT worker, secuencia, COUNT(*)
            FROM eventos
            GROUP BY worker, secuencia
            HAVING COUNT(*) > 1
            """
        )

        self.assertEqual(count, [(workers * rows_per_worker,)])
        self.assertEqual(duplicates, [])

    def test_readers_can_observe_consistent_counts_during_writes(self):
        observed_counts = []

        def writer():
            for sequence in range(50):
                self.db.ejecutar_consulta(
                    "INSERT INTO eventos(worker, secuencia, valor) VALUES (1, ?, ?)",
                    (sequence, str(sequence)),
                )

        def reader():
            for _ in range(50):
                rows = self.db.ejecutar_consulta("SELECT COUNT(*) FROM eventos")
                observed_counts.append(rows[0][0])

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(writer)]
            futures.extend(executor.submit(reader) for _ in range(3))
            for future in futures:
                future.result()

        self.assertTrue(observed_counts)
        self.assertTrue(all(0 <= count <= 50 for count in observed_counts))
        self.assertEqual(
            self.db.ejecutar_consulta("SELECT COUNT(*) FROM eventos"),
            [(50,)],
        )

    def test_closed_connection_reopens_on_next_query(self):
        self.db.ejecutar_consulta(
            "INSERT INTO eventos(worker, secuencia, valor) VALUES (1, 1, 'antes')"
        )
        self.db.cerrar_conexion()

        rows = self.db.ejecutar_consulta(
            "SELECT valor FROM eventos WHERE worker = 1 AND secuencia = 1"
        )

        self.assertEqual(rows, [("antes",)])
        self.assertTrue(self.db.conexion_activa())

    def test_transaction_rolls_back_delete_when_insert_fails(self):
        self.db.ejecutar_consulta(
            "INSERT INTO eventos(worker, secuencia, valor) VALUES (1, 1, 'original')"
        )

        with self.assertRaises(sqlite3.Error):
            self.db.ejecutar_transaccion(
                "DELETE FROM eventos",
                "INSERT INTO eventos(columna_inexistente) VALUES (?)",
                [("fallo",)],
            )

        rows = self.db.ejecutar_consulta(
            "SELECT worker, secuencia, valor FROM eventos ORDER BY id"
        )
        self.assertEqual(rows, [(1, 1, "original")])

    def test_executemany_is_visible_as_one_complete_batch(self):
        batch = [(3, sequence, f"batch:{sequence}") for sequence in range(40)]

        result = self.db.ejecutar_consultamany(
            "INSERT INTO eventos(worker, secuencia, valor) VALUES (?, ?, ?)",
            batch,
        )

        self.assertTrue(result)
        self.assertEqual(
            self.db.ejecutar_consulta(
                "SELECT COUNT(*) FROM eventos WHERE worker = 3"
            ),
            [(40,)],
        )


if __name__ == "__main__":
    unittest.main()
