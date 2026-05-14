class ProductosSQLiteDAO:
    def __init__(self, db):
        self.db = db

    def listar_todos(self):
        sql = "SELECT * FROM productos ORDER BY descripcion"
        return self.db.ejecutar_consulta(sql) or []

    def obtener_ultima_fecha_actualizacion(self):
        sql = "SELECT dFechaU FROM productos ORDER BY dFechaU DESC LIMIT 1"
        resultado = self.db.ejecutar_consulta(sql) or []
        if not resultado:
            return None
        return resultado[0][0]

    def eliminar_todos(self):
        return self.db.ejecutar_consulta("DELETE FROM productos")

    def reemplazar_todos(self, productos):
        self.eliminar_todos()
        sql = """
        INSERT OR REPLACE INTO productos (CREF, codigo, descripcion, precio, dfechau)
        VALUES (?, ?, ?, ?, ?)
        """
        return self.db.ejecutar_consultamany(sql, self._parametros(productos))

    def upsert_many(self, productos):
        sql = """
        INSERT INTO productos (CREF, codigo, descripcion, precio, dfechau)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(codigo) DO UPDATE SET
            CREF = excluded.CREF,
            descripcion = excluded.descripcion,
            precio = excluded.precio,
            dfechau = excluded.dfechau
        """
        return self.db.ejecutar_consultamany(sql, self._parametros(productos))

    def _parametros(self, productos):
        return [(p[0], p[2], p[1], p[3], p[4]) for p in productos]


class ProductosSybaseDAO:
    def __init__(self, db):
        self.db = db

    def listar_articulos_completos(self):
        sql = """
        SELECT CREF, CDETALLE, CCODEBAR, CTIPOIVA, NPVP1, CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
        FROM ARTICULO
        WHERE CCODEBAR IS NOT NULL AND CCODEBAR <> ''
        ORDER BY dFechaU ASC
        """
        return self.db.ejecutar_consulta(sql) or []

    def listar_articulos_actualizados_hoy(self):
        sql = """
        SELECT CREF, CDETALLE, CCODEBAR, CTIPOIVA, NPVP1, CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
        FROM ARTICULO
        WHERE CCODEBAR IS NOT NULL
        AND CCODEBAR <> ''
        AND CONVERT(DATE, dFechaU) = CONVERT(DATE, GETDATE())
        ORDER BY dFechaU DESC
        """
        return self.db.ejecutar_consulta(sql) or []

    def listar_articulos_desde_fecha(self, fecha_desde, inclusive=True):
        fecha_desde = str(fecha_desde).replace("'", "''")
        operador = ">=" if inclusive else ">"
        sql = """
        SELECT CREF, CDETALLE, CCODEBAR, CTIPOIVA, NPVP1, CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
        FROM ARTICULO
        WHERE CCODEBAR IS NOT NULL
        AND CCODEBAR <> ''
        AND CONVERT(VARCHAR, dFechaU, 120) {} '{}'
        ORDER BY dFechaU DESC
        """.format(operador, fecha_desde)
        return self.db.ejecutar_consulta(sql) or []

    def listar_codbarp_por_crefs(self, crefs, chunk_size=250):
        resultados = []
        crefs = [str(cref) for cref in crefs if cref]

        for idx in range(0, len(crefs), chunk_size):
            chunk = crefs[idx:idx + chunk_size]
            valores = ",".join(f"'{cref.replace("'", "''")}'" for cref in chunk)
            sql = f"""
            SELECT CREF, CDETALLE, CCODEBAR, CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
            FROM CODBARP
            WHERE CREF IN ({valores})
            AND CCODEBAR IS NOT NULL
            AND CCODEBAR <> ''
            ORDER BY dFechaU ASC
            """
            resultados.extend(self.db.ejecutar_consulta(sql) or [])

        return resultados

    def listar_ivas(self):
        return self.db.ejecutar_consulta("SELECT * FROM IVAS") or []
