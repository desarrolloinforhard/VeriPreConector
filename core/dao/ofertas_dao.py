class OfertasDAO:
    """
    DAO de Ofertas para Sybase ASA 9.

    Requiere que sybase_conn tenga:
        ejecutar_consulta(sql: str) -> list[tuple]
    """

    def __init__(self, sybase_conn):
        self.db = sybase_conn

    # ==========================================================
    # OFERTAT - Listar ofertas vigentes
    # ==========================================================
    def listar_ofertas_vigentes(self, limit=50):
        limit = int(limit)
        sql = f"""
        SELECT TOP {limit}
        ot.NOFERTA,
        RTRIM(ot.CTIPOOFERTA) AS CTIPOOFERTA,
        COALESCE(ot.CDETALLE_A, ot.CDETALLE) AS TITULO,
        ot.DFECHAI,
        ot.DFECHAF
        FROM DBA.OFERTAT ot
        WHERE RTRIM(ot.CTIPOOFERTA) IN ('OFPLU','OFCANASTA')
        ORDER BY ot.NOFERTA ASC;
        """
        return self._exec(sql)

    def listar_ofplu_cabeceras(self, limit=500):
        limit = int(limit)
        sql = f"""
        SELECT TOP {limit}
            ot.NOFERTA,
            RTRIM(ot.CTIPOOFERTA) AS CTIPOOFERTA,
            COALESCE(ot.CDETALLE_A, ot.CDETALLE) AS TITULO,
            CONVERT(VARCHAR, ot.DFECHAI, 120) AS DFECHAI,
            CONVERT(VARCHAR, ot.DFECHAF, 120) AS DFECHAF,
            RTRIM(ot.uid) AS uid,
            CONVERT(VARCHAR, ot.dFechaU, 120) AS DFECHAU
        FROM DBA.OFERTAT ot
        WHERE RTRIM(ot.CTIPOOFERTA) = 'OFPLU'
        ORDER BY ot.NOFERTA ASC;
        """
        return self._exec(sql)

    def listar_ofplu_parametros(self, nofertas):
        nofertas = self._int_list(nofertas)
        if not nofertas:
            return []

        valores = ",".join(str(n) for n in nofertas)
        sql = f"""
        SELECT
            RTRIM(ol.CTPOOFERTA) AS CTPOOFERTA,
            ol.NOFERTA,
            ol.NORDEN,
            RTRIM(ol.CVARIABLE) AS CVARIABLE,
            ol.CPARAMETRO0,
            ol.CPARAMETRO1,
            ol.CPARAMETRO2,
            ol.CPARAMETRO3,
            ol.CPARAMETRO4,
            ol.CPARAMETRO5,
            ol.CPARAMETRO6,
            ol.CPARAMETRO7,
            ol.CPARAMETRO8,
            ol.CPARAMETRO9,
            ol.CDETALLE,
            RTRIM(ol.uid) AS uid,
            CONVERT(VARCHAR, ol.dFechaU, 120) AS DFECHAU
        FROM DBA.OFERTAL ol
        WHERE RTRIM(ol.CTPOOFERTA) = 'ofplu'
          AND ol.NOFERTA IN ({valores})
        ORDER BY ol.NOFERTA ASC, ol.NORDEN ASC;
        """
        return self._exec(sql)

    def listar_ofplu_proyecciones_atipicas(self, nofertas):
        nofertas = self._int_list(nofertas)
        if not nofertas:
            return []

        variantes = []
        for noferta in nofertas:
            variantes.extend([str(noferta), str(noferta).zfill(3)])
        variantes = sorted(set(variantes))
        valores = ",".join(f"'{v}'" for v in variantes)

        sql = f"""
        SELECT
            a.CREF,
            RTRIM(ar.CCODEBAR) AS CODIGO,
            ar.CDETALLE AS DESCRIPCION,
            a.NPRECIO AS PRECIO_OFERTA,
            a.NDTO,
            CONVERT(VARCHAR, a.DFECINI, 120) AS DFECHAI,
            CONVERT(VARCHAR, a.DFECFIN, 120) AS DFECHAF,
            RTRIM(a.CCODDIV) AS CCODDIV,
            RTRIM(a.CCLAVEC) AS CCLAVEC,
            RTRIM(a.CCLAVEA) AS CCLAVEA,
            a.NMODOP,
            a.NMODOD,
            a.CDETALLE,
            RTRIM(a.uid) AS uid,
            CONVERT(VARCHAR, a.dFechaU, 120) AS DFECHAU
        FROM DBA.ATIPICAS a
        JOIN DBA.ARTICULO ar ON ar.CREF = a.CREF
        WHERE a.CCLAVEC = 'O'
          AND a.CCLAVEA = 'P'
          AND RTRIM(a.CCODDIV) IN ({valores})
        ORDER BY a.CREF ASC, a.dFechaU DESC;
        """
        return self._exec(sql)

    # ==========================================================
    # ATIPICAS - Productos OFPLU (por CCODDIV)
    # ==========================================================
    def productos_atipicas_por_ccoddiv(self, ccoddiv: str):
        ccoddiv = str(ccoddiv).strip()

        sql = f"""
        SELECT
            a.CREF,
            ar.CDETALLE AS DESCRIPCION,
            ar.NPVP1 AS PRECIO_LISTA,
            a.NPRECIO AS PRECIO_OFERTA,
            a.NDTO,
            ar.CIMAGEN
        FROM DBA.ATIPICAS a
        JOIN DBA.ARTICULO ar ON ar.CREF = a.CREF
        WHERE a.CCLAVEC = 'O'
        AND a.CCODDIV = '{ccoddiv}'
        AND DATE(a.DFECINI) <= CURRENT DATE
        AND (a.DFECFIN IS NULL OR DATE(a.DFECFIN) >= CURRENT DATE)
        ORDER BY a.CREF
        """

        return self._exec(sql)

    # ==========================================================
    # OFERTAP - Fallback OFPLU
    # ==========================================================
    def productos_ofertap(self, noferta: int):
        noferta = int(noferta)

        sql = f"""
        SELECT
            RTRIM(op.CPLU) AS CREF,
            ar.CDETALLE AS DESCRIPCION,
            ar.NPVP1 AS PRECIO_LISTA,
            NULL AS PRECIO_OFERTA,
            NULL AS NDTO,
            ar.CIMAGEN
        FROM DBA.OFERTAP op
        JOIN DBA.ARTICULO ar ON ar.CREF = RTRIM(op.CPLU)
        WHERE op.NOFERTA = {noferta}
        ORDER BY op.CPLU
        """

        return self._exec(sql)

    # ==========================================================
    # MIX_CANAS - OFCANASTA
    # ==========================================================
    def productos_mix_canasta(self, noferta: int):
        noferta = int(noferta)

        sql = f"""
        SELECT
            RTRIM(mc.CPLUC) AS CREF,
            ar.CDETALLE AS DESCRIPCION,
            ar.NPVP1 AS PRECIO_LISTA,
            NULL AS PRECIO_OFERTA,
            NULL AS NDTO,
            ar.CIMAGEN
        FROM DBA.MIX_CANAS mc
        JOIN DBA.ARTICULO ar ON ar.CREF = RTRIM(mc.CPLUC)
        WHERE mc.NOFERTA = {noferta}
        ORDER BY mc.CPLU, mc.CPLUC
        """

        return self._exec(sql)

    # ==========================================================
    # Helper interno
    # ==========================================================
    def _exec(self, sql: str):
        try:
            return self.db.ejecutar_consulta(sql) or []
        except Exception as e:
            print("❌ Error en OfertasDAO:", e)
            print("SQL ejecutado:")
            print(sql)
            return []

    def _int_list(self, values):
        resultado = []
        for value in values or []:
            try:
                resultado.append(int(value))
            except (TypeError, ValueError):
                continue
        return resultado
