from core.dao.ofertas_dao import OfertasDAO
from core.dao.ofertas_plu_sqlite_dao import OfertasPLUSQLiteDAO
from core.logging.logger import get_logger
from core.services.barcode_normalizer import limpiar_codigo

logger = get_logger(__name__)


class OfertasPLUSyncService:
    def __init__(self, sqlite_db, sybase_db):
        self.sqlite_db = sqlite_db
        self.sybase_db = sybase_db
        self.sqlite_dao = OfertasPLUSQLiteDAO(sqlite_db)
        self.sybase_dao = OfertasDAO(sybase_db)

    def sincronizar(self, progress_callback=None):
        self._notify(progress_callback, "Sincronizando ofertas OFPLU...", 0, 100)

        cabeceras = self.sybase_dao.listar_ofplu_cabeceras()
        nofertas = [fila[0] for fila in cabeceras if fila and fila[0] is not None]

        if not nofertas:
            self._reemplazar_snapshot([], [], [])
            self._notify(progress_callback, "No se encontraron ofertas OFPLU.", 100, 100)
            return {"ofertas": [], "parametros": [], "productos": [], "total_ofertas": 0}

        self._notify(progress_callback, f"{len(nofertas)} cabeceras OFPLU encontradas.", 20, 100)

        parametros_rows = self.sybase_dao.listar_ofplu_parametros(nofertas)
        productos_rows = self.sybase_dao.listar_ofplu_proyecciones_atipicas(nofertas)

        parametros_normalizados = self._normalizar_parametros(parametros_rows)
        ofertas_normalizadas = self._normalizar_cabeceras(cabeceras, parametros_normalizados)
        productos_normalizados = self._normalizar_productos(productos_rows, set(ofertas_normalizadas.keys()))

        ofertas_payload = list(ofertas_normalizadas.values())
        self._notify(progress_callback, "Persistiendo snapshot local de OFPLU...", 80, 100)
        self._reemplazar_snapshot(
            ofertas_payload,
            parametros_normalizados,
            productos_normalizados,
        )
        self._notify(
            progress_callback,
            f"Snapshot OFPLU actualizado: {len(ofertas_payload)} ofertas, {len(parametros_normalizados)} parametros, {len(productos_normalizados)} productos.",
            100,
            100,
        )

        return {
            "ofertas": ofertas_payload,
            "parametros": parametros_normalizados,
            "productos": productos_normalizados,
            "total_ofertas": len(ofertas_payload),
        }

    def _reemplazar_snapshot(self, ofertas, parametros, productos):
        if not self.sqlite_dao.reemplazar_snapshot(ofertas, parametros, productos):
            raise RuntimeError("no se pudo reemplazar el snapshot local de OFPLU")

    def _normalizar_cabeceras(self, cabeceras, parametros_normalizados):
        deshabilitadas = {
            int(param["noferta"])
            for param in parametros_normalizados
            if param.get("deshabilitada")
        }
        parametros_por_oferta = {}
        for param in parametros_normalizados:
            noferta = int(param["noferta"])
            parametros_por_oferta.setdefault(noferta, []).append(param)

        ofertas = {}
        for fila in cabeceras:
            noferta, tipo_oferta, detalle, fecha_inicio, fecha_fin, uid, dfechau = fila
            noferta_int = int(noferta)
            params = parametros_por_oferta.get(noferta_int, [])
            ccoddiv = self._resolver_ccoddiv(params, noferta_int)
            ofertas[noferta_int] = {
                "noferta": noferta_int,
                "tipo_oferta": (tipo_oferta or "").strip(),
                "detalle": (detalle or "").strip(),
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "habilitada": noferta_int not in deshabilitadas,
                "ccoddiv": ccoddiv,
                "origen": "OFPLU",
                "uid": (uid or "").strip() or None,
                "dfechau": dfechau,
            }
        return ofertas

    def _normalizar_parametros(self, rows):
        resultado = []
        for row in rows or []:
            (
                _tipo,
                noferta,
                orden,
                variable,
                cp0,
                cp1,
                cp2,
                cp3,
                cp4,
                cp5,
                cp6,
                cp7,
                cp8,
                cp9,
                detalle,
                uid,
                dfechau,
            ) = row

            variable_normalizada = (variable or "").strip().upper()
            valor_raw = self._to_float_nullable(cp4)
            tipo_valor = (cp2 or "").strip() if cp2 is not None else None
            if not tipo_valor and valor_raw is not None:
                tipo_valor = "IMPORTE"

            item = {
                "noferta": int(noferta),
                "orden": self._to_int(orden),
                "variable": variable_normalizada,
                "cparametro0": self._to_text(cp0),
                "cparametro1": self._to_text(cp1),
                "cparametro2": self._to_text(cp2),
                "cparametro3": self._to_text(cp3),
                "cparametro4": self._to_text(cp4),
                "cparametro5": self._to_text(cp5),
                "cparametro6": self._to_text(cp6),
                "cparametro7": self._to_text(cp7),
                "cparametro8": self._to_text(cp8),
                "cparametro9": self._to_text(cp9),
                "hora_desde": None,
                "hora_hasta": None,
                "acumulador": None,
                "modifica_subtotal": None,
                "mixmatch_generico": None,
                "deshabilitada": variable_normalizada == "DISABLE",
                "relacion": None,
                "cantidad": None,
                "tipo_valor": None,
                "signo": None,
                "valor_raw": valor_raw,
                "valor_visible": round(valor_raw / 100, 2) if valor_raw is not None else None,
                "modo": None,
                "detalle": (detalle or "").strip() or None,
                "uid": (uid or "").strip() or None,
                "dfechau": dfechau,
            }

            if variable_normalizada == "HORA":
                item["hora_desde"] = self._to_text(cp0)
                item["hora_hasta"] = self._to_text(cp1)
            elif variable_normalizada == "ACUMREC":
                item["acumulador"] = self._to_text(cp0)
            elif variable_normalizada == "MODIF_SUBT":
                item["modifica_subtotal"] = self._to_text(cp0)
            elif variable_normalizada == "MIXMATCH_GENERICO":
                item["mixmatch_generico"] = self._to_text(cp0)
            elif variable_normalizada == "SIGNO":
                item["relacion"] = self._to_text(cp0)
                item["cantidad"] = self._to_int_nullable(cp1)
                item["tipo_valor"] = tipo_valor
                item["signo"] = self._to_text(cp3)
                item["modo"] = self._to_text(cp5)

            resultado.append(item)

        return resultado

    def _normalizar_productos(self, rows, nofertas_validas):
        productos = {}
        for row in rows or []:
            (
                cref,
                codigo,
                descripcion,
                precio_oferta,
                ndto,
                fecha_inicio,
                fecha_fin,
                ccoddiv,
                cclavec,
                cclavea,
                nmodop,
                nmodod,
                detalle,
                uid,
                dfechau,
            ) = row

            noferta = self._noferta_desde_ccoddiv(ccoddiv)
            if noferta is None or noferta not in nofertas_validas:
                continue

            key = (
                noferta,
                str(cref).strip() if cref is not None else "",
                (ccoddiv or "").strip(),
                (cclavec or "").strip(),
                (cclavea or "").strip(),
            )
            if not key[1]:
                continue
            if key in productos:
                continue

            productos[key] = {
                "noferta": noferta,
                "cref": key[1],
                "codigo": limpiar_codigo(codigo),
                "descripcion": (descripcion or "").strip(),
                "precio_oferta": round(self._to_float(precio_oferta), 2),
                "ndto": self._to_float(ndto),
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "ccoddiv": key[2],
                "cclavec": key[3],
                "cclavea": key[4],
                "nmodop": self._to_text(nmodop),
                "nmodod": self._to_text(nmodod),
                "detalle": (detalle or "").strip() or None,
                "uid": (uid or "").strip() or None,
                "dfechau": dfechau,
            }

        return list(productos.values())

    def _resolver_ccoddiv(self, params, noferta):
        return str(noferta).zfill(3) if params else str(noferta).zfill(3)

    def _noferta_desde_ccoddiv(self, ccoddiv):
        texto = (ccoddiv or "").strip()
        if not texto or not texto.isdigit():
            return None
        try:
            return int(texto)
        except ValueError:
            return None

    def _to_text(self, value):
        if value is None:
            return None
        texto = str(value).strip()
        return texto or None

    def _to_float(self, value):
        try:
            if value in (None, ""):
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _to_float_nullable(self, value):
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value):
        try:
            if value in (None, ""):
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def _to_int_nullable(self, value):
        try:
            if value in (None, ""):
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _notify(self, callback, message=None, progreso=None, total=None):
        if callback:
            callback(message, progreso, total)
        elif message:
            logger.debug("OfertasPLUSyncService | %s", message)
