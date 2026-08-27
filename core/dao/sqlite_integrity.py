class SQLiteIntegrityAuditor:
    CHECKS = (
        (
            "precio_sin_producto",
            "producto_precios",
            """
            SELECT p.codigo, COUNT(*)
            FROM producto_precios p
            LEFT JOIN productos producto ON producto.codigo = p.codigo
            WHERE producto.codigo IS NULL
            GROUP BY p.codigo
            """,
        ),
        (
            "parametro_ofplu_sin_cabecera",
            "ofertas_plu_parametros",
            """
            SELECT p.noferta, COUNT(*)
            FROM ofertas_plu_parametros p
            LEFT JOIN ofertas_plu oferta ON oferta.noferta = p.noferta
            WHERE oferta.noferta IS NULL
            GROUP BY p.noferta
            """,
        ),
        (
            "producto_ofplu_sin_cabecera",
            "ofertas_plu_productos",
            """
            SELECT p.noferta, p.cref, COUNT(*)
            FROM ofertas_plu_productos p
            LEFT JOIN ofertas_plu oferta ON oferta.noferta = p.noferta
            WHERE oferta.noferta IS NULL
            GROUP BY p.noferta, p.cref
            """,
        ),
        (
            "codigo_producto_duplicado",
            "productos",
            """
            SELECT codigo, COUNT(*)
            FROM productos
            WHERE codigo IS NOT NULL AND TRIM(codigo) <> ''
            GROUP BY codigo
            HAVING COUNT(*) > 1
            """,
        ),
        (
            "oferta_ofplu_duplicada",
            "ofertas_plu",
            """
            SELECT noferta, COUNT(*)
            FROM ofertas_plu
            GROUP BY noferta
            HAVING COUNT(*) > 1
            """,
        ),
        (
            "precio_adicional_duplicado",
            "producto_precios",
            """
            SELECT codigo, tipo_precio, categoria, origen, orden, cantidad,
                   titulo, nroprecio, COUNT(*)
            FROM producto_precios
            GROUP BY codigo, tipo_precio, categoria, origen, orden, cantidad,
                     titulo, nroprecio
            HAVING COUNT(*) > 1
            """,
        ),
        (
            "producto_ofplu_duplicado",
            "ofertas_plu_productos",
            """
            SELECT noferta, cref, ccoddiv, cclavec, cclavea, COUNT(*)
            FROM ofertas_plu_productos
            GROUP BY noferta, cref, ccoddiv, cclavec, cclavea
            HAVING COUNT(*) > 1
            """,
        ),
    )

    def __init__(self, db):
        self.db = db

    def audit(self):
        issues = []
        for code, table, sql in self.CHECKS:
            for row in self.db.ejecutar_consulta(sql) or []:
                issues.append(
                    {
                        "codigo": code,
                        "tabla": table,
                        "clave": tuple(row[:-1]),
                        "cantidad": int(row[-1]),
                    }
                )

        return {
            "ok": not issues,
            "total_inconsistencias": sum(issue["cantidad"] for issue in issues),
            "inconsistencias": issues,
        }
