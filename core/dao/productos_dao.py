from core.dao.snapshot_validation import (
    normalize_sqlite_date,
    validate_incremental_prices,
    validate_product_snapshot,
    validate_simple_offers,
)


class ProductosSQLiteDAO:
    CLEAR_OFFERS_SQL = """
        UPDATE productos
        SET
            TIENE_OFERTA = 0,
            PRECIO_OFERTA = NULL,
            OFERTA_DESDE = NULL,
            OFERTA_HASTA = NULL,
            OFERTA_ORIGEN = NULL,
            OFERTA_CCODDIV = NULL,
            OFERTA_DTO = NULL
    """
    APPLY_OFFERS_SQL = """
        UPDATE productos
        SET
            TIENE_OFERTA = 1,
            PRECIO_OFERTA = ?,
            OFERTA_DESDE = ?,
            OFERTA_HASTA = ?,
            OFERTA_ORIGEN = ?,
            OFERTA_CCODDIV = ?,
            OFERTA_DTO = ?
        WHERE CREF = ?
    """
    UPSERT_PRODUCTOS_SQL = """
        INSERT INTO productos (
            CREF, codigo, descripcion, precio, dfechau,
            TIENE_OFERTA, PRECIO_OFERTA, OFERTA_DESDE, OFERTA_HASTA,
            OFERTA_ORIGEN, OFERTA_CCODDIV, OFERTA_DTO
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(codigo) DO UPDATE SET
            CREF = excluded.CREF,
            descripcion = excluded.descripcion,
            precio = excluded.precio,
            dfechau = excluded.dfechau,
            TIENE_OFERTA = excluded.TIENE_OFERTA,
            PRECIO_OFERTA = excluded.PRECIO_OFERTA,
            OFERTA_DESDE = excluded.OFERTA_DESDE,
            OFERTA_HASTA = excluded.OFERTA_HASTA,
            OFERTA_ORIGEN = excluded.OFERTA_ORIGEN,
            OFERTA_CCODDIV = excluded.OFERTA_CCODDIV,
            OFERTA_DTO = excluded.OFERTA_DTO
    """
    INSERT_PRECIOS_SQL = """
        INSERT INTO producto_precios (
            CREF, codigo, tipo_precio, categoria, origen, orden, cantidad,
            titulo, detalle, precio, nroprecio, dfechau
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def __init__(self, db):
        self.db = db

    def listar_todos(self):
        sql = """
        SELECT
            CREF,
            codigo,
            descripcion,
            precio,
            dFechaU,
            TIENE_OFERTA,
            PRECIO_OFERTA,
            OFERTA_DESDE,
            OFERTA_HASTA,
            OFERTA_ORIGEN,
            OFERTA_CCODDIV,
            OFERTA_DTO
        FROM productos
        ORDER BY descripcion
        """
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
        INSERT OR REPLACE INTO productos (
            CREF, codigo, descripcion, precio, dfechau,
            TIENE_OFERTA, PRECIO_OFERTA, OFERTA_DESDE, OFERTA_HASTA,
            OFERTA_ORIGEN, OFERTA_CCODDIV, OFERTA_DTO
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.db.ejecutar_consultamany(sql, self._parametros(productos))

    def reemplazar_snapshot(self, productos, precios):
        validate_product_snapshot(productos, precios)

        def reemplazar(cursor):
            cursor.execute("DELETE FROM producto_precios")
            cursor.execute("DELETE FROM productos")
            if productos:
                cursor.executemany(
                    self.UPSERT_PRODUCTOS_SQL,
                    self._parametros(productos),
                )
            if precios:
                cursor.executemany(
                    self.INSERT_PRECIOS_SQL,
                    self._parametros_precios_adicionales(precios),
                )
            return True

        return bool(self.db.ejecutar_en_transaccion(reemplazar))

    def upsert_many(self, productos):
        return self.db.ejecutar_consultamany(
            self.UPSERT_PRODUCTOS_SQL,
            self._parametros(productos),
        )

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

        filas = self.db.ejecutar_consulta("SELECT codigo FROM productos") or []
        validate_incremental_prices(precios, codigos, (fila[0] for fila in filas))

        if not codigos:
            return self._insertar_precios_adicionales(precios)

        def actualizar(cursor):
            placeholders = ",".join("?" for _ in codigos)
            cursor.execute(
                f"DELETE FROM producto_precios WHERE codigo IN ({placeholders})",
                tuple(codigos),
            )
            if precios:
                cursor.executemany(
                    self.INSERT_PRECIOS_SQL,
                    self._parametros_precios_adicionales(precios),
                )
            return True

        return bool(self.db.ejecutar_en_transaccion(actualizar))

    def listar_precios_adicionales_por_codigo(self, codigo):
        sql = """
        SELECT codigo, tipo_precio, categoria, origen, orden, cantidad, titulo, detalle, precio, nroprecio, dFechaU
        FROM producto_precios
        WHERE codigo = ?
        ORDER BY orden ASC, cantidad ASC, titulo ASC
        """
        return self.db.ejecutar_consulta(sql, (codigo,)) or []

    def listar_precios_adicionales_por_codigos(self, codigos):
        codigos = [str(codigo).strip() for codigo in (codigos or []) if str(codigo).strip()]
        if not codigos:
            return []

        placeholders = ",".join("?" for _ in codigos)
        sql = f"""
        SELECT codigo, tipo_precio, categoria, origen, orden, cantidad, titulo, detalle, precio, nroprecio, dFechaU
        FROM producto_precios
        WHERE codigo IN ({placeholders})
        ORDER BY codigo ASC, orden ASC, cantidad ASC, titulo ASC
        """
        return self.db.ejecutar_consulta(sql, tuple(codigos)) or []

    def listar_codigos_desde_fecha(self, fecha_desde, inclusive=True):
        fecha_txt = str(fecha_desde).strip() if fecha_desde else ""
        if not fecha_txt:
            return []

        operador = ">=" if inclusive else ">"
        sql = f"""
        SELECT DISTINCT codigo
        FROM productos
        WHERE codigo IS NOT NULL
          AND TRIM(codigo) <> ''
          AND dFechaU IS NOT NULL
          AND TRIM(dFechaU) <> ''
          AND dFechaU {operador} ?
        ORDER BY dFechaU ASC, codigo ASC
        """
        filas = self.db.ejecutar_consulta(sql, (fecha_txt,)) or []
        return [str(fila[0]).strip() for fila in filas if fila and fila[0]]

    def obtener_oferta_por_codigo(self, codigo):
        sql = """
        SELECT
            codigo,
            TIENE_OFERTA,
            PRECIO_OFERTA,
            OFERTA_DESDE,
            OFERTA_HASTA,
            OFERTA_ORIGEN,
            OFERTA_CCODDIV,
            OFERTA_DTO
        FROM productos
        WHERE codigo = ?
        """
        resultado = self.db.ejecutar_consulta(sql, (codigo,)) or []
        return resultado[0] if resultado else None

    def listar_ofertas_por_codigos(self, codigos):
        codigos = [str(codigo).strip() for codigo in (codigos or []) if str(codigo).strip()]
        if not codigos:
            return []

        placeholders = ",".join("?" for _ in codigos)
        sql = f"""
        SELECT
            codigo,
            TIENE_OFERTA,
            PRECIO_OFERTA,
            OFERTA_DESDE,
            OFERTA_HASTA,
            OFERTA_ORIGEN,
            OFERTA_CCODDIV,
            OFERTA_DTO
        FROM productos
        WHERE codigo IN ({placeholders})
        ORDER BY codigo ASC
        """
        return self.db.ejecutar_consulta(sql, tuple(codigos)) or []

    def limpiar_snapshot_ofertas(self):
        return self.db.ejecutar_consulta(self.CLEAR_OFFERS_SQL)

    def aplicar_snapshot_ofertas_por_cref(self, ofertas):
        if not ofertas:
            return True

        parametros = self._parametros_ofertas(ofertas)
        if not parametros:
            return True
        return self.db.ejecutar_consultamany(self.APPLY_OFFERS_SQL, parametros)

    def reemplazar_snapshot_ofertas(self, ofertas):
        filas = self.db.ejecutar_consulta("SELECT CREF FROM productos") or []
        validate_simple_offers(ofertas, (fila[0] for fila in filas))
        parametros = self._parametros_ofertas(ofertas)

        def reemplazar(cursor):
            cursor.execute(self.CLEAR_OFFERS_SQL)
            if parametros:
                cursor.executemany(self.APPLY_OFFERS_SQL, parametros)
            return True

        return bool(self.db.ejecutar_en_transaccion(reemplazar))

    def _parametros_ofertas(self, ofertas):
        return [
            (
                oferta.get("precio_oferta"),
                normalize_sqlite_date(oferta.get("oferta_desde")),
                normalize_sqlite_date(oferta.get("oferta_hasta")),
                oferta.get("oferta_origen"),
                oferta.get("oferta_ccoddiv"),
                oferta.get("oferta_dto"),
                oferta.get("cref"),
            )
            for oferta in ofertas
            if oferta.get("cref")
        ]

    def _insertar_precios_adicionales(self, precios):
        if not precios:
            return True

        return self.db.ejecutar_consultamany(
            self.INSERT_PRECIOS_SQL,
            self._parametros_precios_adicionales(precios),
        )

    def _parametros(self, productos):
        parametros = []

        for producto in productos:
            if isinstance(producto, dict):
                parametros.append(
                    (
                        producto.get("cref"),
                        producto.get("codigo"),
                        producto.get("descripcion"),
                        producto.get("precio"),
                        normalize_sqlite_date(producto.get("dfechau")),
                        1 if producto.get("tiene_oferta") else 0,
                        producto.get("precio_oferta"),
                        normalize_sqlite_date(producto.get("oferta_desde")),
                        normalize_sqlite_date(producto.get("oferta_hasta")),
                        producto.get("oferta_origen"),
                        producto.get("oferta_ccoddiv"),
                        producto.get("oferta_dto"),
                    )
                )
            else:
                parametros.append(
                    (
                        producto[0],
                        producto[2],
                        producto[1],
                        producto[3],
                        normalize_sqlite_date(producto[4]),
                        0,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                    )
                )

        return parametros

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
                normalize_sqlite_date(precio.get("dfechau")),
            )
            for precio in precios
        ]


class ProductosSybaseDAO:
    def __init__(self, db):
        self.db = db

    def obtener_marcas_remotas_catalogo(self):
        consultas = {
            "productos": """
                SELECT MAX(CONVERT(VARCHAR, dFechaU, 120))
                FROM DBA.ARTICULO
                WHERE CCODEBAR IS NOT NULL AND CCODEBAR <> ''
            """,
            "codigos": """
                SELECT MAX(CONVERT(VARCHAR, dFechaU, 120))
                FROM DBA.CODBARP
            """,
            "packs": """
                SELECT MAX(CONVERT(VARCHAR, dFechaU, 120))
                FROM DBA.PACKS_MINI
            """,
            "ofertas_precio": """
                SELECT MAX(CONVERT(VARCHAR, dFechaU, 120))
                FROM DBA.ATIPICAS
                WHERE CCLAVEC = 'O'
            """,
            "ofertas_plu_detalle": """
                SELECT MAX(CONVERT(VARCHAR, dFechaU, 120))
                FROM DBA.OFERTAT
            """,
            "ofertas_plu_config": """
                SELECT MAX(CONVERT(VARCHAR, dFechaU, 120))
                FROM DBA.OFERTAL
            """,
        }
        marcas = {}
        for clave, sql in consultas.items():
            resultado = self.db.ejecutar_consulta(sql) or []
            marcas[clave] = resultado[0][0] if resultado and resultado[0] else None
        return marcas

    def obtener_marca_remota_catalogo(self):
        marcas = [marca for marca in self.obtener_marcas_remotas_catalogo().values() if marca]
        if not marcas:
            return None
        return max(str(marca) for marca in marcas)

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
        FROM DBA.ARTICULO
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
        FROM DBA.ARTICULO
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
        FROM DBA.ARTICULO
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
            FROM DBA.CODBARP
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
            FROM DBA.PACKS_MINI
            WHERE CREF IN ({valores})
            ORDER BY CREF ASC, dFechaU ASC
            """
            resultados.extend(self.db.ejecutar_consulta(sql) or [])

        return resultados

    def listar_ofertas_atipicas_activas(self):
        sql = """
        SELECT
            a.CREF,
            a.NPRECIO,
            a.NDTO,
            CONVERT(VARCHAR, a.DFECINI, 120) AS OFERTA_DESDE,
            CONVERT(VARCHAR, a.DFECFIN, 120) AS OFERTA_HASTA,
            a.CCODDIV,
            a.CCLAVEC
        FROM DBA.ATIPICAS a
        WHERE a.CCLAVEC = 'O'
          AND (
                RTRIM(a.CCODDIV) = 'PSO'
                OR a.CCLAVEA IS NULL
                OR RTRIM(a.CCLAVEA) <> 'P'
              )
          AND DATE(a.DFECINI) <= CURRENT DATE
          AND (a.DFECFIN IS NULL OR DATE(a.DFECFIN) >= CURRENT DATE)
        ORDER BY a.CREF ASC, a.DFECINI DESC, a.DFECFIN DESC, a.NPRECIO ASC
        """
        return self.db.ejecutar_consulta(sql) or []

    def listar_ivas(self):
        return self.db.ejecutar_consulta("SELECT * FROM DBA.IVAS") or []
