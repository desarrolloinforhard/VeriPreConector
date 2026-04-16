class OfertasService:
    def __init__(self, dao):
        self.dao = dao

    def listar_ofertas(self):
        rows = self.dao.listar_ofertas_vigentes()
        ofertas = []
        for r in rows:
            noferta, tipo, titulo, desde, hasta = r
            ofertas.append({
                "noferta": int(noferta) if noferta is not None else None,
                "tipo": (tipo or "").strip(),
                "titulo": (titulo or "").strip(),
                "desde": desde,
                "hasta": hasta,
            })
        return ofertas

    def _ccoddiv_variantes(self, noferta: int):
        s = str(int(noferta))
        return [s, s.zfill(3)]

    def traer_productos(self, oferta: dict):
        tipo = (oferta.get("tipo") or "").strip().upper()
        noferta = int(oferta["noferta"])

        if tipo == "OFPLU":
            return self._traer_productos_ofplu(noferta)

        if tipo == "OFCANASTA":
            return self._traer_productos_ofcanasta(noferta)

        return {"modo": "TIPO_NO_SOPORTADO", "items": []}

    def _traer_productos_ofplu(self, noferta: int):
        # 1) Fuente principal: ATIPICAS
        for ccoddiv in self._ccoddiv_variantes(noferta):
            rows_atip = self.dao.productos_atipicas_por_ccoddiv(ccoddiv)
            items_atip = self._map_items(rows_atip)
            if items_atip:
                return {"modo": f"ATIPICAS(CCODDIV={ccoddiv})", "items": items_atip}

        # 2) Fallback: OFERTAP
        rows_ofertap = self.dao.productos_ofertap(noferta)
        items_ofertap = self._map_items(rows_ofertap)
        if items_ofertap:
            return {"modo": "OFERTAP_FALLBACK", "items": items_ofertap}

        return {"modo": "SIN_ITEMS", "items": []}

    def _traer_productos_ofcanasta(self, noferta: int):
        # 1) Fuente principal: OFERTAP
        rows_ofertap = self.dao.productos_ofertap(noferta)
        items_ofertap = self._map_items(rows_ofertap)
        if items_ofertap:
            return {"modo": "OFERTAP", "items": items_ofertap}

        # 2) Fallback: MIX_CANAS
        rows_mix = self.dao.productos_mix_canasta(noferta)
        items_mix = self._map_items(rows_mix)
        if items_mix:
            return {"modo": "MIX_CANAS", "items": items_mix}

        return {"modo": "SIN_ITEMS", "items": []}

    def _map_items(self, rows):
        items = []
        for r in rows or []:
            cref, desc, pvp1, poferta, ndto, cimagen = r
            items.append({
                "cref": (cref or "").strip(),
                "descripcion": (desc or "").strip(),
                "precio_lista": pvp1,
                "precio_oferta": poferta,
                "dto": ndto,
                "cimagen": (cimagen or "").strip() if cimagen else None,
            })
        return items