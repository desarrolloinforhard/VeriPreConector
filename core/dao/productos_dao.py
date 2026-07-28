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
        self.db.ejecutar_consulta("DELETE FROM producto_precios")
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

    def reemplazar_precios_adicionales(self, precios):
        self.db.ejecutar_consulta("DELETE FROM producto_precios")
        return self._insertar_precios_adicionales(precios)

    def upsert_precios_adicionales(self, precios, codigos_objetivo=None):
        codigos = sorted(
            {
                str(codigo).strip()
                for codigo in (codigos_objetivo or [])
                if str(codigo).strip()
            }
        )
        if not codigos:
            codigos = sorted({str(precio["codigo"]).strip() for precio in precios if precio.get("codigo")})

        if codigos:
            placeholders = ",".join("?" for _ in codigos)
            sql_delete = f"DELETE FROM producto_precios WHERE codigo IN ({placeholders})"
            self.db.ejecutar_consulta(sql_delete, tuple(codigos))

        return self._insertar_precios_adicionales(precios)

    def listar_precios_adicionales_por_codigo(self, codigo):
        sql = """
        SELECT codigo, tipo_precio, categoria, origen, orden, cantidad, titulo, detalle, precio, nroprecio, dFechaU
        FROM producto_precios
        WHERE codigo = ?
        ORDER BY orden ASC, cantidad ASC, titulo ASC
        """
        return self.db.ejecutar_consulta(sql, (codigo,)) or []

    def _insertar_precios_adicionales(self, precios):
        if not precios:
            return True

        sql = """
        INSERT INTO producto_precios (
            CREF, codigo, tipo_precio, categoria, origen, orden, cantidad,
            titulo, detalle, precio, nroprecio, dfechau
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.db.ejecutar_consultamany(sql, self._parametros_precios_adicionales(precios))

    def _parametros(self, productos):
        return [(p[0], p[2], p[1], p[3], p[4]) for p in productos]

    def _parametros_precios_adicionales(self, precios):
        return [
            (
                precio.get("cref"),
                precio.get("codigo"),
                precio.get("tipo_precio"),
                precio.get("categoria"),
                precio.get("origen"),
                precio.get("orden", 0),
                precio.get("cantidad"),
                precio.get("titulo"),
                precio.get("detalle"),
                precio.get("precio"),
                precio.get("nroprecio"),
                precio.get("dfechau"),
            )
            for precio in precios
        ]


class ProductosSybaseDAO:
    def __init__(self, db):
        self.db = db

    def listar_articulos_completos(self):
        sql = """
        SELECT
            CREF,
            CDETALLE,
            CCODEBAR,
            CTIPOIVA,
            NPVP1,
            NPVP2,
            NPVP3,
            NPVP4,
            NPVP5,
            NPREMAYOR1,
            NPREMAYOR2,
            NPREMAYOR3,
            NPREMAYOR4,
            NPREMAYOR5,
            CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
        FROM ARTICULO
        WHERE CCODEBAR IS NOT NULL AND CCODEBAR <> ''
        ORDER BY dFechaU ASC
        """
        return self.db.ejecutar_consulta(sql) or []

    def listar_articulos_actualizados_hoy(self):
        sql = """
        SELECT
            CREF,
            CDETALLE,
            CCODEBAR,
            CTIPOIVA,
            NPVP1,
            NPVP2,
            NPVP3,
            NPVP4,
            NPVP5,
            NPREMAYOR1,
            NPREMAYOR2,
            NPREMAYOR3,
            NPREMAYOR4,
            NPREMAYOR5,
            CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
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
        SELECT
            CREF,
            CDETALLE,
            CCODEBAR,
            CTIPOIVA,
            NPVP1,
            NPVP2,
            NPVP3,
            NPVP4,
            NPVP5,
            NPREMAYOR1,
            NPREMAYOR2,
            NPREMAYOR3,
            NPREMAYOR4,
            NPREMAYOR5,
            CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
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
            chunk_escapado = [cref.replace("'", "''") for cref in chunk]
            valores = ",".join(f"'{cref}'" for cref in chunk_escapado)
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

    def listar_packs_mini_por_crefs(self, crefs, chunk_size=250):
        resultados = []
        crefs = [str(cref) for cref in crefs if cref]

        for idx in range(0, len(crefs), chunk_size):
            chunk = crefs[idx:idx + chunk_size]
            chunk_escapado = [cref.replace("'", "''") for cref in chunk]
            valores = ",".join(f"'{cref}'" for cref in chunk_escapado)
            sql = f"""
            SELECT
                CREF,
                CANTIDAD,
                NROPRECIO,
                NPRECIO,
                CDETALLE,
                CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
            FROM PACKS_MINI
            WHERE CREF IN ({valores})
            ORDER BY CREF ASC, dFechaU ASC
            """
            resultados.extend(self.db.ejecutar_consulta(sql) or [])

        return resultados

    def listar_ivas(self):
        return self.db.ejecutar_consulta("SELECT * FROM IVAS") or []
