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