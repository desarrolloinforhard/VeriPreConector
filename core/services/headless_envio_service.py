from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from DB.database import SQLiteDB
from DB.database_sybase import ConexionSybase
from FUNC.config_json import obtener_sqlite_path
from core.network.urls_dispositivos import ENDPOINT_STATUS, VeriPreDispositivosURLBuilder
from core.services.device_discovery_service import DeviceDiscoveryService
from core.services.dispositivos_envio_service import DispositivosEnvioService
from core.services.image_resolver import ProductImageResolver
from core.services.productos_sync_service import ProductosSyncService


class HeadlessEnvioService:
    def __init__(self, db_path=None, max_workers=4, progress_callback=None):
        root_dir = Path(__file__).resolve().parents[2]
        self.db_path = str(db_path or obtener_sqlite_path() or root_dir / "DB" / "veripre.db")
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self.sqlite_db = SQLiteDB(self.db_path)
        self.sybase_db = None
        self.envio_service = DispositivosEnvioService(self.sqlite_db)
        self.config = self._cargar_config()

    def transmitir_completo(self):
        self._inicializar_sqlite()
        productos = self._obtener_productos_para_envio()
        if not productos:
            self._emitir("No hay productos locales para enviar.")
            return 1

        dispositivos = self._obtener_dispositivos_online()
        if not dispositivos:
            self._emitir("No hay dispositivos online para enviar.")
            return 2

        self._emitir(f"Enviando catalogo completo: {len(productos)} productos a {len(dispositivos)} dispositivos.")
        return self._enviar_a_dispositivos(dispositivos, productos, modo="completo")

    def transmitir_novedades(self):
        self._inicializar_sqlite()
        self.sybase_db = self._crear_conexion_sybase()
        if not self.sybase_db:
            self._emitir("No hay conexion Sybase configurada. No se pueden sincronizar novedades.")
            return 1

        try:
            resultado = ProductosSyncService(self.sqlite_db, self.sybase_db).sincronizar_actualizados_hoy(
                progress_callback=self._mostrar_progreso_sync,
            )
        finally:
            self.sybase_db.desconectar()

        codigos = resultado.get("codigos", [])
        if not codigos:
            self._emitir("No hay novedades para enviar.")
            return 0

        productos = self._obtener_productos_por_codigos(codigos)
        if not productos:
            self._emitir("Se detectaron novedades, pero no se encontraron productos locales para enviar.")
            return 1

        dispositivos = self._obtener_dispositivos_online()
        if not dispositivos:
            self._emitir("No hay dispositivos online para enviar novedades.")
            return 2

        self._emitir(f"Enviando novedades: {len(productos)} productos a {len(dispositivos)} dispositivos.")
        return self._enviar_a_dispositivos(dispositivos, productos, modo="novedades")

    def cerrar(self):
        self.sqlite_db.cerrar_conexion()
        if self.sybase_db:
            self.sybase_db.desconectar()

    def _inicializar_sqlite(self):
        self.sqlite_db.crear_tablas()

    def _crear_conexion_sybase(self):
        consulta = "SELECT dsn, user, password FROM VERIPRE_CONEXION LIMIT 1"
        datos_conexion = self.sqlite_db.ejecutar_consulta(consulta) or []
        if not datos_conexion:
            return None

        dsn, user, password = datos_conexion[0]
        return ConexionSybase(user=user, password=password, dsn=dsn)

    def _obtener_productos_para_envio(self):
        consulta = """
        SELECT codigo, descripcion, precio, img_base64, formato_imagen
        FROM productos
        WHERE codigo IS NOT NULL AND TRIM(codigo) <> ''
        ORDER BY descripcion
        """
        productos = self.sqlite_db.ejecutar_consulta(consulta) or []
        return self._resolver_imagenes_faltantes(productos)

    def _obtener_productos_por_codigos(self, codigos):
        productos = []
        vistos = set()
        consulta = """
        SELECT codigo, descripcion, precio, img_base64, formato_imagen
        FROM productos
        WHERE codigo = ?
        """
        for codigo in codigos:
            codigo = str(codigo).strip()
            if codigo in vistos:
                continue
            vistos.add(codigo)
            resultado = self.sqlite_db.ejecutar_consulta(consulta, (codigo,)) or []
            if resultado:
                productos.append(resultado[0])
        return self._resolver_imagenes_faltantes(productos)

    def _resolver_imagenes_faltantes(self, productos):
        resolver = ProductImageResolver(
            self.sqlite_db,
            config=self.config,
            estado_callback=self._emitir,
            incluir_api_propia=False,
            incluir_go_upc=False,
        )
        resultado = []
        total = len(productos)
        for idx, producto in enumerate(productos, start=1):
            codigo, descripcion, precio, img_base64, formato = producto
            if not img_base64:
                img_base64, formato = resolver.resolver(codigo, img_base64, formato)
            resultado.append((codigo, descripcion, precio, img_base64, formato))
            if idx == 1 or idx % 250 == 0 or idx == total:
                self._emitir(f"Imagenes preparadas: {idx}/{total}")
        return resultado

    def _cargar_config(self):
        try:
            import json

            config_path = Path(__file__).resolve().parents[2] / "config.json"
            if config_path.exists():
                return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            self._emitir(f"No se pudo leer config.json: {e}")
        return {}

    def _obtener_dispositivos_online(self):
        builder = VeriPreDispositivosURLBuilder(self.sqlite_db)
        dispositivos = builder.obtener_urls_api("/api/veri/batch_productos")
        online = []

        for dispositivo in dispositivos:
            if self._dispositivo_online(dispositivo):
                online.append(dispositivo)
                self._emitir(f"Online: {dispositivo['nombre']} -> {dispositivo['url']}")
            else:
                self._emitir(f"Offline: {dispositivo['nombre']} -> {dispositivo['url']}")

        if online:
            return online

        self._emitir("No hay dispositivos registrados online. Intentando deteccion automatica en red...")
        try:
            discovery = DeviceDiscoveryService()
            detectados = discovery.discover(progress_callback=lambda msg: self._emitir(f"[discovery] {msg}"))
            for disp in detectados:
                if disp.get("tipo") != "verificador":
                    continue
                dispositivo = {
                    "nombre": disp["nombre"],
                    "url": f"http://{disp['ip']}:{disp['puerto']}/api/veri/batch_productos",
                }
                online.append(dispositivo)
                self._emitir(f"Detectado: {dispositivo['nombre']} -> {dispositivo['url']}")
        except Exception as e:
            self._emitir(f"Error en deteccion automatica: {e}")

        return online

    def _dispositivo_online(self, dispositivo):
        try:
            base_url = dispositivo["url"].split("/api")[0]
            status = requests.get(f"{base_url}{ENDPOINT_STATUS}", timeout=2)
            if status.status_code == 200:
                return True
        except Exception:
            pass

        try:
            base_url = dispositivo["url"].split("/api")[0]
            respuesta = requests.get(f"{base_url}/", timeout=2)
            return respuesta.status_code == 200
        except Exception:
            return False

    def _enviar_a_dispositivos(self, dispositivos, productos, modo):
        resultados = {}

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(dispositivos))) as executor:
            futures = {
                executor.submit(self._enviar_a_dispositivo, dispositivo, productos, modo): dispositivo
                for dispositivo in dispositivos
            }

            for future in as_completed(futures):
                dispositivo = futures[future]
                try:
                    future.result()
                    resultados[dispositivo["nombre"]] = True
                    self._emitir(f"OK: {dispositivo['nombre']}")
                except Exception as e:
                    resultados[dispositivo["nombre"]] = False
                    self._emitir(f"ERROR: {dispositivo['nombre']} -> {e}")

        enviados_ok = sum(1 for ok in resultados.values() if ok)
        enviados_error = len(resultados) - enviados_ok
        self._emitir(f"Resumen envio {modo}: OK={enviados_ok}, ERROR={enviados_error}")
        return 0 if enviados_error == 0 else 3

    def _enviar_a_dispositivo(self, dispositivo, productos, modo):
        nombre = dispositivo["nombre"]

        def estado(mensaje):
            self._emitir(f"[{nombre}] {mensaje}")

        self.envio_service.enviar_productos(
            dispositivo["url"],
            productos,
            modo=modo,
            estado_callback=estado,
        )

    def _mostrar_progreso_sync(self, mensaje=None, progreso=None, total=None):
        if mensaje:
            self._emitir(f"[sync] {mensaje}")
        if progreso is not None and total:
            self._emitir(f"[sync] {progreso}/{total}")

    def _emitir(self, mensaje):
        print(mensaje)
        if self.progress_callback:
            self.progress_callback(mensaje)
