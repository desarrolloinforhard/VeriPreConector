from core.dao.productos_dao import ProductosSQLiteDAO, ProductosSybaseDAO


class ProductosSyncService:
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

        if not articulos:
            self._notify(progress_callback, "No hay datos en ARTICULO", 100, 100)
            return {
                "articulos": [],
                "productos": [],
                "codigos": [],
                "total": 0,
            }

        self._notify(progress_callback, f"{len(articulos)} articulos encontrados.", 50, 100)
        productos_completos = self._completar_con_codbarp(articulos, progress_callback)
        ivas = self._buscar_ivas(progress_callback)
        productos = self._aplicar_iva(productos_completos, ivas, progress_callback)
        total = self._guardar_productos(productos, replace_all, progress_callback)

        return {
            "articulos": articulos,
            "productos": productos,
            "codigos": [producto[2] for producto in productos],
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

    def _completar_con_codbarp(self, articulos, progress_callback=None):
        crefs = [str(producto[0]) for producto in articulos if producto and producto[0]]
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
            cref, cdetalle, ccodebar, ctipoiva, npvp1, dfechau = producto
            codigo = str(ccodebar)
            if codigo not in codigos_agregados:
                productos_completos.append(producto)
                codigos_agregados.add(codigo)
            progreso += 1
            if progreso % 10 == 0:
                self._notify(progress_callback, None, progreso, total)

            for cdetalle_extra, ccodebar_extra, _ in codbarp_dict.get(cref, []):
                codigo_extra = str(ccodebar_extra)
                if codigo_extra not in codigos_agregados:
                    productos_completos.append((cref, cdetalle_extra, ccodebar_extra, ctipoiva, npvp1, dfechau))
                    codigos_agregados.add(codigo_extra)
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

    def _aplicar_iva(self, productos_completos, ivas, progress_callback=None):
        iva_dict = {str(iva[0]): iva[2] for iva in ivas}
        productos_actualizados = []
        total = len(productos_completos)

        if total == 0:
            self._notify(progress_callback, "No hay productos para actualizar.", 100, 100)
            return []

        self._notify(progress_callback, "Actualizando precios con IVA...", 0, total)

        for idx, producto in enumerate(productos_completos):
            codigo_iva = str(producto[3])
            precio_base = producto[4] or 0
            porcentaje_iva = iva_dict.get(codigo_iva, 0.0) or 0.0
            nuevo_precio = precio_base * (1 + porcentaje_iva / 100)

            productos_actualizados.append((
                producto[0],
                producto[1],
                producto[2],
                format(round(nuevo_precio, 2), ".2f"),
                producto[5],
            ))

            if (idx + 1) % 10 == 0 or idx + 1 == total:
                self._notify(progress_callback, None, idx + 1, total)

        self._notify(progress_callback, f"{len(productos_actualizados)} productos actualizados con IVA.", total, total)
        return productos_actualizados

    def _guardar_productos(self, productos, replace_all, progress_callback=None):
        if not productos:
            self._notify(progress_callback, "No hay productos para insertar o actualizar.", 100, 100)
            return 0

        if replace_all:
            guardar = self.sqlite_dao.reemplazar_todos
        else:
            guardar = self.sqlite_dao.upsert_many

        self._notify(progress_callback, "Insertando o actualizando productos...", 0, len(productos))
        guardar(productos)
        self._notify(progress_callback, f"{len(productos)} productos procesados.", len(productos), len(productos))
        return len(productos)

    def _notify(self, callback, message=None, progreso=None, total=None):
        if callback:
            callback(message, progreso, total)
