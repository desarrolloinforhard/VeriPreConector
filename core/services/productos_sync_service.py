from core.dao.productos_dao import ProductosSQLiteDAO, ProductosSybaseDAO
from core.services.barcode_normalizer import limpiar_codigo, normalizar_codigo_para_envio


class ProductosSyncService:
    PACK_NROPRECIO_MAP = {
        "00": {"tipo_precio": "npvp1", "categoria": "general", "etiqueta": "Carga de Precio", "orden_categoria": 0},
        "01": {"tipo_precio": "npvp1", "categoria": "minorista", "etiqueta": "Precio Mino1", "orden_categoria": 10},
        "02": {"tipo_precio": "npvp2", "categoria": "minorista", "etiqueta": "Precio Mino2", "orden_categoria": 11},
        "03": {"tipo_precio": "npvp3", "categoria": "minorista", "etiqueta": "Precio Mino3", "orden_categoria": 12},
        "04": {"tipo_precio": "npvp4", "categoria": "minorista", "etiqueta": "Precio Mino4", "orden_categoria": 13},
        "05": {"tipo_precio": "npvp5", "categoria": "minorista", "etiqueta": "Precio Mino5", "orden_categoria": 14},
        "11": {"tipo_precio": "npremayor1", "categoria": "mayorista", "etiqueta": "Precio Mayo1", "orden_categoria": 20},
        "12": {"tipo_precio": "npremayor2", "categoria": "mayorista", "etiqueta": "Precio Mayo2", "orden_categoria": 21},
        "13": {"tipo_precio": "npremayor3", "categoria": "mayorista", "etiqueta": "Precio Mayo3", "orden_categoria": 22},
        "14": {"tipo_precio": "npremayor4", "categoria": "mayorista", "etiqueta": "Precio Mayo4", "orden_categoria": 23},
        "15": {"tipo_precio": "npremayor5", "categoria": "mayorista", "etiqueta": "Precio Mayo5", "orden_categoria": 24},
        "99": {"tipo_precio": "precio_cliente", "categoria": "cliente", "etiqueta": "Precio Cliente", "orden_categoria": 99},
    }

    def __init__(self, sqlite_db, sybase_db):
        self.sqlite_db = sqlite_db
        self.sybase_db = sybase_db
        self.sqlite_dao = ProductosSQLiteDAO(sqlite_db)
        self.sybase_dao = ProductosSybaseDAO(sybase_db)

    def obtener_productos_locales(self):
        return self.sqlite_dao.listar_todos()

    def sincronizar_completo(self, progress_callback=None):
        articulos = self._buscar_articulos_completos()
        return self._sincronizar_articulos(
            articulos,
            replace_all=True,
            progress_callback=progress_callback,
        )

    def sincronizar_actualizados_hoy(self, progress_callback=None, incluir_ultima_fecha=True):
        articulos = self._buscar_articulos_actualizados_desde_ultima_fecha(
            incluir_ultima_fecha=incluir_ultima_fecha,
        )
        return self._sincronizar_articulos(
            articulos,
            replace_all=False,
            progress_callback=progress_callback,
        )

    def _sincronizar_articulos(self, articulos, replace_all, progress_callback=None):
        self._notify(progress_callback, "Iniciando la carga de articulos...", 0, 100)

        articulos_normalizados = self._normalizar_articulos(articulos)
        ofertas_por_cref = self._buscar_ofertas_activas(progress_callback)

        if not articulos_normalizados:
            self._sync_snapshot_ofertas(ofertas_por_cref, progress_callback)
            self._notify(progress_callback, "No hay datos en ARTICULO; se refresco snapshot de ofertas.", 100, 100)
            return {
                "articulos": [],
                "productos": [],
                "productos_resueltos": [],
                "codigos": [],
                "precios_adicionales": [],
                "ofertas_activas": list(ofertas_por_cref.values()),
                "total": 0,
            }

        self._notify(progress_callback, f"{len(articulos_normalizados)} articulos encontrados.", 50, 100)
        productos_completos = self._completar_con_codbarp(articulos_normalizados, progress_callback)
        ivas = self._buscar_ivas(progress_callback)
        packs_por_cref = self._buscar_packs_por_cref(productos_completos, progress_callback)
        productos_resueltos = self._resolver_productos(productos_completos, ivas, packs_por_cref, ofertas_por_cref, progress_callback)
        productos_legado = self._productos_resueltos_a_tuplas(productos_resueltos)
        total = self._guardar_productos(productos_resueltos, productos_legado, ofertas_por_cref, replace_all, progress_callback)

        return {
            "articulos": articulos_normalizados,
            "productos": productos_legado,
            "productos_resueltos": productos_resueltos,
            "codigos": [producto["codigo"] for producto in productos_resueltos],
            "precios_adicionales": self._flatten_precios_adicionales(productos_resueltos),
            "ofertas_activas": list(ofertas_por_cref.values()),
            "total": total,
        }

    def _buscar_articulos_completos(self):
        return self.sybase_dao.listar_articulos_completos()

    def _buscar_articulos_actualizados_hoy(self):
        return self.sybase_dao.listar_articulos_actualizados_hoy()

    def _buscar_articulos_actualizados_desde_ultima_fecha(self, incluir_ultima_fecha=True):
        fecha_desde = self.sqlite_dao.obtener_ultima_fecha_actualizacion()
        if not fecha_desde:
            return self._buscar_articulos_actualizados_hoy()
        return self.sybase_dao.listar_articulos_desde_fecha(
            fecha_desde,
            inclusive=incluir_ultima_fecha,
        )

    def _normalizar_articulos(self, articulos):
        articulos_normalizados = []
        for articulo in articulos or []:
            if not articulo or len(articulo) < 15:
                continue

            articulos_normalizados.append(
                {
                    "cref": articulo[0],
                    "descripcion": articulo[1],
                    "codigo": limpiar_codigo(articulo[2]),
                    "codigo_original": limpiar_codigo(articulo[2]),
                    "codigo_normalizado": normalizar_codigo_para_envio(articulo[2]),
                    "ctipoiva": articulo[3],
                    "precios_base": {
                        "npvp1": self._to_float(articulo[4]),
                        "npvp2": self._to_float(articulo[5]),
                        "npvp3": self._to_float(articulo[6]),
                        "npvp4": self._to_float(articulo[7]),
                        "npvp5": self._to_float(articulo[8]),
                        "npremayor1": self._to_float(articulo[9]),
                        "npremayor2": self._to_float(articulo[10]),
                        "npremayor3": self._to_float(articulo[11]),
                        "npremayor4": self._to_float(articulo[12]),
                        "npremayor5": self._to_float(articulo[13]),
                    },
                    "dfechau": articulo[14],
                }
            )

        return articulos_normalizados

    def _completar_con_codbarp(self, articulos, progress_callback=None):
        crefs = [str(producto["cref"]) for producto in articulos if producto and producto.get("cref")]
        if not crefs:
            return list(articulos)

        self._notify(progress_callback, "Obteniendo codigos de barra adicionales...", 0, 100)
        datos_codbarp = self._buscar_codbarp(crefs)

        codbarp_dict = {}
        for cref, cdetalle, ccodebar, dfechau in datos_codbarp:
            codbarp_dict.setdefault(cref, []).append((cdetalle, ccodebar, dfechau))

        total = len(articulos) + len(datos_codbarp)
        total = max(total, 1)
        progreso = 0
        productos_completos = []
        codigos_agregados = set()

        for producto in articulos:
            codigo = limpiar_codigo(producto.get("codigo"))
            codigo_normalizado = limpiar_codigo(producto.get("codigo_normalizado")) or codigo
            if codigo and codigo_normalizado not in codigos_agregados:
                productos_completos.append(producto)
                codigos_agregados.add(codigo_normalizado)
            progreso += 1
            if progreso % 10 == 0:
                self._notify(progress_callback, None, progreso, total)

            for cdetalle_extra, ccodebar_extra, dfechau_extra in codbarp_dict.get(producto["cref"], []):
                codigo_extra = limpiar_codigo(ccodebar_extra)
                codigo_extra_normalizado = normalizar_codigo_para_envio(ccodebar_extra)
                if codigo_extra and codigo_extra_normalizado not in codigos_agregados:
                    producto_extra = dict(producto)
                    producto_extra["descripcion"] = cdetalle_extra
                    producto_extra["codigo"] = codigo_extra
                    producto_extra["codigo_original"] = codigo_extra
                    producto_extra["codigo_normalizado"] = codigo_extra_normalizado
                    producto_extra["dfechau"] = dfechau_extra or producto.get("dfechau")
                    productos_completos.append(producto_extra)
                    codigos_agregados.add(codigo_extra_normalizado)
                progreso += 1
                if progreso % 10 == 0:
                    self._notify(progress_callback, None, progreso, total)

        self._notify(progress_callback, f"{len(productos_completos)} productos completos.", total, total)
        return productos_completos

    def _buscar_codbarp(self, crefs):
        return self.sybase_dao.listar_codbarp_por_crefs(crefs)

    def _buscar_ivas(self, progress_callback=None):
        self._notify(progress_callback, "Obteniendo datos de IVAS...", 0, 100)
        ivas = self.sybase_dao.listar_ivas()
        self._notify(progress_callback, f"{len(ivas)} tipos de IVA encontrados.", 100, 100)
        return ivas

    def _buscar_packs_por_cref(self, productos_completos, progress_callback=None):
        crefs = sorted({str(producto["cref"]) for producto in productos_completos if producto.get("cref")})
        if not crefs:
            return {}

        self._notify(progress_callback, "Obteniendo packs y precios adicionales...", 0, 100)
        packs = self.sybase_dao.listar_packs_mini_por_crefs(crefs)
        packs_por_cref = {}

        for cref, cantidad, nroprecio, nprecio, cdetalle, dfechau in packs:
            packs_por_cref.setdefault(cref, []).append(
                {
                    "cref": cref,
                    "cantidad": self._to_int(cantidad),
                    "nroprecio": self._normalizar_nroprecio(nroprecio),
                    "nprecio": self._to_float(nprecio),
                    "detalle": (cdetalle or "").strip(),
                    "dfechau": dfechau,
                }
            )

        self._notify(progress_callback, f"{len(packs)} registros PACKS_MINI encontrados.", 100, 100)
        return packs_por_cref

    def _buscar_ofertas_activas(self, progress_callback=None):
        self._notify(progress_callback, "Obteniendo ofertas activas desde ATIPICAS...", 0, 100)
        filas = self.sybase_dao.listar_ofertas_atipicas_activas()
        ofertas_por_cref = {}

        for cref, precio_oferta, oferta_dto, oferta_desde, oferta_hasta, oferta_ccoddiv, cclavec in filas:
            cref = str(cref).strip() if cref is not None else ""
            if not cref or cref in ofertas_por_cref:
                continue

            ofertas_por_cref[cref] = {
                "cref": cref,
                "tiene_oferta": True,
                "precio_oferta": round(self._to_float(precio_oferta), 2),
                "oferta_desde": oferta_desde,
                "oferta_hasta": oferta_hasta,
                "oferta_origen": "ATIPICAS",
                "oferta_ccoddiv": str(oferta_ccoddiv).strip() if oferta_ccoddiv is not None else None,
                "oferta_dto": self._to_float(oferta_dto),
                "cclavec": str(cclavec).strip() if cclavec is not None else None,
            }

        self._notify(progress_callback, f"{len(ofertas_por_cref)} ofertas activas encontradas.", 100, 100)
        return ofertas_por_cref

    def _resolver_productos(self, productos_completos, ivas, packs_por_cref, ofertas_por_cref, progress_callback=None):
        iva_dict = {str(iva[0]): self._to_float(iva[2]) for iva in ivas}
        productos_resueltos = []
        total = len(productos_completos)

        if total == 0:
            self._notify(progress_callback, "No hay productos para actualizar.", 100, 100)
            return []

        self._notify(progress_callback, "Actualizando precios con IVA...", 0, total)

        for idx, producto in enumerate(productos_completos):
            codigo_iva = str(producto.get("ctipoiva"))
            porcentaje_iva = iva_dict.get(codigo_iva, 0.0) or 0.0
            precios_finales = self._resolver_precios_finales(producto["precios_base"], porcentaje_iva)
            precio_principal = precios_finales.get("npvp1", 0.0)
            precios_adicionales = self._resolver_precios_adicionales_producto(
                producto,
                precios_finales,
                packs_por_cref.get(producto["cref"], []),
            )
            oferta = ofertas_por_cref.get(str(producto["cref"]).strip()) or {}

            productos_resueltos.append(
                {
                    "cref": producto["cref"],
                    "descripcion": producto["descripcion"],
                    "codigo": limpiar_codigo(producto.get("codigo")),
                    "codigo_original": limpiar_codigo(producto.get("codigo_original") or producto.get("codigo")),
                    "codigo_normalizado": limpiar_codigo(producto.get("codigo_normalizado")) or normalizar_codigo_para_envio(producto.get("codigo")),
                    "precio_num": precio_principal,
                    "precio": self._format_precio(precio_principal),
                    "dfechau": producto.get("dfechau"),
                    "precios_finales": precios_finales,
                    "precios_adicionales": precios_adicionales,
                    "tiene_oferta": bool(oferta.get("tiene_oferta")),
                    "precio_oferta": oferta.get("precio_oferta"),
                    "oferta_desde": oferta.get("oferta_desde"),
                    "oferta_hasta": oferta.get("oferta_hasta"),
                    "oferta_origen": oferta.get("oferta_origen"),
                    "oferta_ccoddiv": oferta.get("oferta_ccoddiv"),
                    "oferta_dto": oferta.get("oferta_dto"),
                }
            )

            if (idx + 1) % 10 == 0 or idx + 1 == total:
                self._notify(progress_callback, None, idx + 1, total)

        self._notify(progress_callback, f"{len(productos_resueltos)} productos actualizados con IVA.", total, total)
        return productos_resueltos

    def _resolver_precios_finales(self, precios_base, porcentaje_iva):
        precios_finales = {}
        for clave, precio_base in (precios_base or {}).items():
            precios_finales[clave] = round(self._to_float(precio_base) * (1 + porcentaje_iva / 100), 2)
        return precios_finales

    def _resolver_precios_adicionales_producto(self, producto, precios_finales, packs_producto):
        precios_adicionales = []

        for pack in packs_producto or []:
            mapping = self.PACK_NROPRECIO_MAP.get(pack["nroprecio"])
            if not mapping:
                continue

            if pack["nprecio"] > 0:
                precio_resuelto = round(pack["nprecio"], 2)
            else:
                precio_resuelto = round(precios_finales.get(mapping["tipo_precio"], 0.0), 2)

            if precio_resuelto <= 0:
                continue

            cantidad = pack["cantidad"] or None
            detalle = pack["detalle"]
            titulo = detalle or self._construir_titulo_pack(cantidad, mapping["etiqueta"])
            orden = (mapping["orden_categoria"] * 1000) + (cantidad or 0)

            precios_adicionales.append(
                {
                    "cref": producto["cref"],
                    "codigo": str(producto["codigo"]).strip(),
                    "tipo_precio": mapping["tipo_precio"],
                    "categoria": mapping["categoria"],
                    "origen": "packs_mini",
                    "orden": orden,
                    "cantidad": cantidad,
                    "titulo": titulo,
                    "detalle": detalle,
                    "precio": precio_resuelto,
                    "nroprecio": pack["nroprecio"],
                    "dfechau": pack.get("dfechau") or producto.get("dfechau"),
                }
            )

        precios_adicionales.sort(key=lambda item: (item["orden"], item.get("cantidad") or 0, item["titulo"]))
        return precios_adicionales

    def _construir_titulo_pack(self, cantidad, etiqueta):
        if cantidad:
            return f"Llevando x {cantidad}"
        return etiqueta

    def _productos_resueltos_a_tuplas(self, productos_resueltos):
        return [
            (
                producto["cref"],
                producto["descripcion"],
                producto["codigo"],
                producto["precio"],
                producto.get("dfechau"),
            )
            for producto in productos_resueltos
        ]

    def _flatten_precios_adicionales(self, productos_resueltos):
        precios = []
        for producto in productos_resueltos:
            precios.extend(producto.get("precios_adicionales", []))
        return precios

    def _guardar_productos(self, productos_resueltos, productos_legado, ofertas_por_cref, replace_all, progress_callback=None):
        if replace_all:
            guardar_productos = self.sqlite_dao.reemplazar_todos
            guardar_precios = self.sqlite_dao.reemplazar_precios_adicionales
        else:
            guardar_productos = self.sqlite_dao.upsert_many
            guardar_precios = self.sqlite_dao.upsert_precios_adicionales

        precios_adicionales = self._flatten_precios_adicionales(productos_resueltos)
        codigos_actualizados = [producto["codigo"] for producto in productos_resueltos]

        total_productos = len(productos_resueltos)
        if total_productos:
            self._notify(progress_callback, "Insertando o actualizando productos...", 0, total_productos)
            guardar_productos(productos_resueltos)
            if replace_all:
                guardar_precios(precios_adicionales)
            else:
                guardar_precios(precios_adicionales, codigos_objetivo=codigos_actualizados)
            self._notify(progress_callback, f"{total_productos} productos procesados.", total_productos, total_productos)
        else:
            self._notify(progress_callback, "No hubo productos nuevos; se actualizara snapshot de ofertas.", 100, 100)

        self._sync_snapshot_ofertas(ofertas_por_cref, progress_callback)
        return total_productos

    def _sync_snapshot_ofertas(self, ofertas_por_cref, progress_callback=None):
        self._notify(progress_callback, "Actualizando snapshot local de ofertas...", 0, 100)
        self.sqlite_dao.limpiar_snapshot_ofertas()
        self.sqlite_dao.aplicar_snapshot_ofertas_por_cref(list(ofertas_por_cref.values()))
        self._notify(progress_callback, f"Snapshot local de ofertas actualizado: {len(ofertas_por_cref)} activas.", 100, 100)

    def _normalizar_nroprecio(self, nroprecio):
        if nroprecio is None:
            return ""
        texto = str(nroprecio).strip()
        if texto.isdigit():
            return texto.zfill(2)
        return texto

    def _to_float(self, value):
        try:
            if value in (None, ""):
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _to_int(self, value):
        try:
            if value in (None, ""):
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def _format_precio(self, precio):
        return format(round(self._to_float(precio), 2), ".2f")

    def _notify(self, callback, message=None, progreso=None, total=None):
        if callback:
            callback(message, progreso, total)
