class OfertasPLUSQLiteDAO:
    UPSERT_OFERTAS_SQL = """
        INSERT INTO ofertas_plu (
            noferta, tipo_oferta, detalle, fecha_inicio, fecha_fin,
            habilitada, ccoddiv, origen, uid, dfechau
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(noferta) DO UPDATE SET
            tipo_oferta = excluded.tipo_oferta,
            detalle = excluded.detalle,
            fecha_inicio = excluded.fecha_inicio,
            fecha_fin = excluded.fecha_fin,
            habilitada = excluded.habilitada,
            ccoddiv = excluded.ccoddiv,
            origen = excluded.origen,
            uid = excluded.uid,
            dfechau = excluded.dfechau
    """
    INSERT_PARAMETROS_SQL = """
        INSERT INTO ofertas_plu_parametros (
            noferta, orden, variable,
            cparametro0, cparametro1, cparametro2, cparametro3, cparametro4,
            cparametro5, cparametro6, cparametro7, cparametro8, cparametro9,
            hora_desde, hora_hasta, acumulador, modifica_subtotal, mixmatch_generico,
            deshabilitada, relacion, cantidad, tipo_valor, signo, valor_raw,
            valor_visible, modo, detalle, uid, dfechau
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    UPSERT_PRODUCTOS_SQL = """
        INSERT INTO ofertas_plu_productos (
            noferta, cref, codigo, descripcion, precio_oferta, ndto, fecha_inicio,
            fecha_fin, ccoddiv, cclavec, cclavea, nmodop, nmodod, detalle, uid, dfechau
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(noferta, cref, ccoddiv, cclavec, cclavea) DO UPDATE SET
            codigo = excluded.codigo,
            descripcion = excluded.descripcion,
            precio_oferta = excluded.precio_oferta,
            ndto = excluded.ndto,
            fecha_inicio = excluded.fecha_inicio,
            fecha_fin = excluded.fecha_fin,
            nmodop = excluded.nmodop,
            nmodod = excluded.nmodod,
            detalle = excluded.detalle,
            uid = excluded.uid,
            dfechau = excluded.dfechau
    """

    def __init__(self, db):
        self.db = db

    def limpiar_todo(self):
        self.db.ejecutar_consulta("DELETE FROM ofertas_plu_productos")
        self.db.ejecutar_consulta("DELETE FROM ofertas_plu_parametros")
        return self.db.ejecutar_consulta("DELETE FROM ofertas_plu")

    def reemplazar_snapshot(self, ofertas, parametros, productos):
        def reemplazar(cursor):
            cursor.execute("DELETE FROM ofertas_plu_productos")
            cursor.execute("DELETE FROM ofertas_plu_parametros")
            cursor.execute("DELETE FROM ofertas_plu")

            if ofertas:
                cursor.executemany(
                    self.UPSERT_OFERTAS_SQL,
                    self._parametros_ofertas(ofertas),
                )
            if parametros:
                cursor.executemany(
                    self.INSERT_PARAMETROS_SQL,
                    self._parametros_parametros(parametros),
                )
            if productos:
                cursor.executemany(
                    self.UPSERT_PRODUCTOS_SQL,
                    self._parametros_productos(productos),
                )
            return True

        return bool(self.db.ejecutar_en_transaccion(reemplazar))

    def upsert_ofertas(self, ofertas):
        if not ofertas:
            return True

        return self.db.ejecutar_consultamany(
            self.UPSERT_OFERTAS_SQL,
            self._parametros_ofertas(ofertas),
        )

    def upsert_parametros(self, parametros, nofertas_objetivo=None):
        nofertas = self._normalizar_nofertas(nofertas_objetivo)
        if not nofertas:
            nofertas = sorted({str(param.get("noferta")).strip() for param in parametros if param.get("noferta") is not None})

        if nofertas:
            placeholders = ",".join("?" for _ in nofertas)
            self.db.ejecutar_consulta(f"DELETE FROM ofertas_plu_parametros WHERE noferta IN ({placeholders})", tuple(nofertas))

        if not parametros:
            return True

        return self.db.ejecutar_consultamany(
            self.INSERT_PARAMETROS_SQL,
            self._parametros_parametros(parametros),
        )

    def upsert_productos(self, productos, nofertas_objetivo=None):
        nofertas = self._normalizar_nofertas(nofertas_objetivo)
        if not nofertas:
            nofertas = sorted({str(item.get("noferta")).strip() for item in productos if item.get("noferta") is not None})

        if nofertas:
            placeholders = ",".join("?" for _ in nofertas)
            self.db.ejecutar_consulta(f"DELETE FROM ofertas_plu_productos WHERE noferta IN ({placeholders})", tuple(nofertas))

        if not productos:
            return True

        return self.db.ejecutar_consultamany(
            self.UPSERT_PRODUCTOS_SQL,
            self._parametros_productos(productos),
        )

    def listar_ofertas(self):
        sql = """
        SELECT
            noferta, tipo_oferta, detalle, fecha_inicio, fecha_fin,
            habilitada, ccoddiv, origen, uid, dfechau
        FROM ofertas_plu
        ORDER BY noferta ASC
        """
        return self.db.ejecutar_consulta(sql) or []

    def obtener_oferta(self, noferta):
        sql = """
        SELECT
            noferta, tipo_oferta, detalle, fecha_inicio, fecha_fin,
            habilitada, ccoddiv, origen, uid, dfechau
        FROM ofertas_plu
        WHERE noferta = ?
        """
        resultado = self.db.ejecutar_consulta(sql, (noferta,)) or []
        return resultado[0] if resultado else None

    def listar_parametros_por_oferta(self, noferta):
        sql = """
        SELECT
            noferta, orden, variable,
            cparametro0, cparametro1, cparametro2, cparametro3, cparametro4,
            cparametro5, cparametro6, cparametro7, cparametro8, cparametro9,
            hora_desde, hora_hasta, acumulador, modifica_subtotal, mixmatch_generico,
            deshabilitada, relacion, cantidad, tipo_valor, signo, valor_raw,
            valor_visible, modo, detalle, uid, dfechau
        FROM ofertas_plu_parametros
        WHERE noferta = ?
        ORDER BY orden ASC, variable ASC
        """
        return self.db.ejecutar_consulta(sql, (noferta,)) or []

    def listar_productos_por_oferta(self, noferta):
        sql = """
        SELECT
            noferta, cref, codigo, descripcion, precio_oferta, ndto, fecha_inicio,
            fecha_fin, ccoddiv, cclavec, cclavea, nmodop, nmodod, detalle, uid, dfechau
        FROM ofertas_plu_productos
        WHERE noferta = ?
        ORDER BY cref ASC
        """
        return self.db.ejecutar_consulta(sql, (noferta,)) or []

    def listar_ofertas_por_codigo(self, codigo):
        sql = """
        SELECT
            p.noferta, o.tipo_oferta, o.detalle, o.fecha_inicio, o.fecha_fin,
            o.habilitada, p.cref, p.codigo, p.descripcion, p.precio_oferta, p.ndto,
            p.ccoddiv, p.cclavec, p.cclavea, p.nmodop, p.nmodod, p.detalle
        FROM ofertas_plu_productos p
        JOIN ofertas_plu o ON o.noferta = p.noferta
        WHERE p.codigo = ?
        ORDER BY o.fecha_inicio DESC, p.precio_oferta ASC
        """
        return self.db.ejecutar_consulta(sql, (codigo,)) or []

    def _normalizar_nofertas(self, nofertas):
        return sorted(
            {
                str(noferta).strip()
                for noferta in (nofertas or [])
                if str(noferta).strip()
            }
        )

    def _parametros_ofertas(self, ofertas):
        return [
            (
                oferta.get("noferta"),
                oferta.get("tipo_oferta"),
                oferta.get("detalle"),
                oferta.get("fecha_inicio"),
                oferta.get("fecha_fin"),
                1 if oferta.get("habilitada", True) else 0,
                oferta.get("ccoddiv"),
                oferta.get("origen", "OFPLU"),
                oferta.get("uid"),
                oferta.get("dfechau"),
            )
            for oferta in ofertas
        ]

    def _parametros_parametros(self, parametros):
        return [
            (
                param.get("noferta"),
                param.get("orden"),
                param.get("variable"),
                param.get("cparametro0"),
                param.get("cparametro1"),
                param.get("cparametro2"),
                param.get("cparametro3"),
                param.get("cparametro4"),
                param.get("cparametro5"),
                param.get("cparametro6"),
                param.get("cparametro7"),
                param.get("cparametro8"),
                param.get("cparametro9"),
                param.get("hora_desde"),
                param.get("hora_hasta"),
                param.get("acumulador"),
                param.get("modifica_subtotal"),
                param.get("mixmatch_generico"),
                1 if param.get("deshabilitada") else 0,
                param.get("relacion"),
                param.get("cantidad"),
                param.get("tipo_valor"),
                param.get("signo"),
                param.get("valor_raw"),
                param.get("valor_visible"),
                param.get("modo"),
                param.get("detalle"),
                param.get("uid"),
                param.get("dfechau"),
            )
            for param in parametros
        ]

    def _parametros_productos(self, productos):
        return [
            (
                item.get("noferta"),
                item.get("cref"),
                item.get("codigo"),
                item.get("descripcion"),
                item.get("precio_oferta"),
                item.get("ndto"),
                item.get("fecha_inicio"),
                item.get("fecha_fin"),
                item.get("ccoddiv"),
                item.get("cclavec"),
                item.get("cclavea"),
                item.get("nmodop"),
                item.get("nmodod"),
                item.get("detalle"),
                item.get("uid"),
                item.get("dfechau"),
            )
            for item in productos
        ]
