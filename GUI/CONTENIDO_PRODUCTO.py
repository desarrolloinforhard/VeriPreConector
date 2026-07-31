import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
import os
import requests
import threading
import time
import ttkbootstrap as ttk
from io import BytesIO
from plyer import notification
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from ASSETS.path_img import *
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import *
from core.network.dispositivo_sender import DispositivoSender
from core.network.urls_dispositivos import ENDPOINT_STATUS, VeriPreDispositivosURLBuilder
from core.services.dispositivos_envio_service import DispositivosEnvioService
from core.services.device_discovery_service import DeviceDiscoveryService
from ttkbootstrap.widgets import DateEntry
from core.dao.productos_dao import ProductosSQLiteDAO
from core.services.image_resolver import ProductImageResolver
from core.services.productos_sync_service import ProductosSyncService
from FUNC.config_json import guardar_config

#from core.network.selector_envio_dispositivos import EnvioDispositivos



class ContenidoProducto:
    AUTO_SYNC_INTERVAL_SECONDS = 5
    TABLE_HEIGHT = 24
    IMAGE_PANEL_WIDTH = 560
    IMAGE_PANEL_HEIGHT = 620
    PREVIEW_IMAGE_SIZE = (520, 520)
    DETAIL_IMAGE_SIZE = (200, 200)

    def __init__(self, DICT_WIDGETS):
        self.DICT_WIDGETS = DICT_WIDGETS
        self.config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        self._vigia_iniciado = False
        self._actualizacion_en_curso = False
        self._ultima_fecha_remota_procesada = self.config.get("ultima_sincronizacion_automatica_productos")
        self._carga_local_en_curso = False
        self._productos_cargados = False
        self._envio_auto_en_curso = False
        self.CONEXIONDBA = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA")
        self.CONEXION_INFORHARD = self.DICT_WIDGETS.get_widget("DATABASE","CONEXION_INFORHARD")
        if self.CONEXION_INFORHARD:
            self.CONEXIONDBA_SYBASE = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA_SYBASE")
        self.variables_globales()
        self.frame_producto = self.DICT_WIDGETS.get_widget("GUI_MAIN", "frame_seccion_productos")

        self.frame_producto.columnconfigure(0, weight=1)
        self.frame_producto.rowconfigure(1, weight=1)

        self.frame_header_productos = ttk.Frame(self.frame_producto)
        self.frame_header_productos.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))
        self.frame_header_productos.columnconfigure(0, weight=1)

        self.label_producto = ttk.Label(
            self.frame_header_productos,
            text="Productos",
            font=("Segoe UI", 18, "bold"),
        )
        self.label_producto.grid(row=0, column=0, sticky="w")

        self.label_producto_subtitulo = ttk.Label(
            self.frame_header_productos,
            text="Busqueda local, vista previa y envio a verificadores.",
            bootstyle="secondary",
            font=("Segoe UI", 10),
        )
        self.label_producto_subtitulo.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.crear_interfaz_table_view()

        self.frame_buttons_productos = ttk.Frame(self.frame_producto)
        self.frame_buttons_productos.grid(row=2, column=0, sticky="ew", padx=18, pady=(8, 16))
        for column in range(4):
            self.frame_buttons_productos.columnconfigure(column, weight=1)
        
        self.button_crear_datos = ttk.Button(self.frame_buttons_productos, text="Recargar Productos", command=self.command_crear_datos)
        self.button_crear_datos.grid(row=0, column=0, padx=6, sticky="ew")
        
        self.button_transmitir_novedades = ttk.Button(self.frame_buttons_productos, text="Transmitir Novedades", command=self.command_transmitir_novedades, state=DISABLED)
        self.button_transmitir_novedades.grid(row=0, column=1, padx=6, sticky="ew")

        self.button_transmitir_datos_fecha = ttk.Button(self.frame_buttons_productos, text="Transmitir por Fecha", command=self.command_transmitir_por_fecha, state=DISABLED)
        self.button_transmitir_datos_fecha.grid(row=0, column=2, padx=6, sticky="ew")
        
        self.button_transmitir_datos = ttk.Button(self.frame_buttons_productos, text="Transmitir Datos Completos", command=self.command_transmitir_datos, state=DISABLED)
        self.button_transmitir_datos.grid(row=0, column=3, padx=6, sticky="ew")
        
        # Agregar el nuevo botón en la columna 3
        #self.button_actualizar_datos = ttk.Button(self.frame_buttons_productos, text="Actualizar Datos", command=self.command_actualizar_datos, state=DISABLED)
        #self.button_actualizar_datos.grid(row=0, column=3, padx=10)

        
        self.ctk_loader =  self.DICT_WIDGETS.get_widget("VARIABLES_GLOBALES", "ctk_loader")

    def _run_en_ui(self, callback, *args, **kwargs):
        root = self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja")
        root.after(0, lambda: callback(*args, **kwargs))

    def _sync_progress(self, mensaje=None, progreso=None, total=None):
        if mensaje:
            self._run_en_ui(self.mostrar_accion, mensaje)
        if progreso is not None and total:
            self._run_en_ui(self.actualizar_barra, progreso, total)

    def _crear_productos_sync_service(self):
        return ProductosSyncService(self.CONEXIONDBA, self.CONEXIONDBA_SYBASE)

    def _crear_productos_sqlite_dao(self, conexion=None):
        return ProductosSQLiteDAO(conexion or self.CONEXIONDBA)

    def _crear_image_resolver(self, estado_callback=None):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json") or self.config
        return ProductImageResolver(
            self.CONEXIONDBA,
            config=config,
            estado_callback=estado_callback or print,
            incluir_api_propia=False,
            incluir_go_upc=False,
        )
        
        
    def crear_interfaz_table_view(self):
        self.frame_table_view = ttk.Frame(self.frame_producto)
        self.frame_table_view.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 8))
        self.frame_table_view.columnconfigure(0, weight=5, minsize=760)
        self.frame_table_view.columnconfigure(1, weight=4, minsize=420)
        self.frame_table_view.rowconfigure(0, weight=1)
        colors = self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja").style.colors
        coldata = [
            {"text": "Producto", "stretch": True},
            {"text": "Código de Barras", "stretch": True},
            {"text": "Precio", "stretch": True},
        ]

        self.frame_tabla_producto = ttk.Frame(self.frame_table_view, bootstyle="light")
        self.frame_tabla_producto.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.frame_tabla_producto.columnconfigure(0, weight=1)
        self.frame_tabla_producto.rowconfigure(0, weight=1)

        self.dt = Tableview(
            master=self.frame_tabla_producto,
            coldata=coldata,
            paginated=True,
            pagesize=100,
            searchable=True,
            autoalign=True,
            height=self.TABLE_HEIGHT,
            bootstyle=PRIMARY,
            stripecolor=(colors.light, None),
        )
        self.dt.align_heading_center(cid=0)
        self.dt.align_heading_center(cid=1)
        self.dt.align_heading_center(cid=2)
        self.dt.align_column_left(cid=0)
        self.dt.align_column_center(cid=1)
        self.dt.align_column_right(cid=2)
        self.dt.pack(fill=BOTH, expand=True, padx=0, pady=0)
        self.dt.view.bind("<<TreeviewSelect>>", self.mostrar_imagen_producto)
        self.dt.view.bind("<Double-1>", self.abrir_detalle_producto)
        
        self.frame_img_producto = ttk.Frame(
            self.frame_table_view,
            width=self.IMAGE_PANEL_WIDTH,
            height=self.IMAGE_PANEL_HEIGHT,
            bootstyle="light",
        )
        self.frame_img_producto.grid(row=0, column=1, sticky="nsew")
        self.frame_img_producto.pack_propagate(False)
        self.label_img_producto = ttk.Label(
            self.frame_img_producto, 
            text="", 
            image=self.IMG_NO_FOTO,
            anchor="center",  # Asegura que el contenido se centre
        )

        self.label_img_producto.place(relx=0.5, rely=0.45, anchor="center")
        self.label_precios_extra_estado = ttk.Label(
            self.frame_img_producto,
            text="Precios adicionales: -",
            anchor="center",
            justify="center",
            font=("Segoe UI", 10, "bold"),
        )
        self.label_precios_extra_estado.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        self.label_oferta_estado = ttk.Label(
            self.frame_img_producto,
            text="Oferta activa: -",
            anchor="center",
            justify="center",
            font=("Segoe UI", 10, "bold"),
        )
        self.label_oferta_estado.pack(side="bottom", fill="x", padx=8, pady=(0, 4))
        self._fijar_layout_productos()

    def _fijar_layout_productos(self):
        self.frame_img_producto.configure(
            width=self.IMAGE_PANEL_WIDTH,
            height=self.IMAGE_PANEL_HEIGHT,
        )
        self.dt.configure(height=self.TABLE_HEIGHT)
        try:
            self.dt.view.column("#0", width=0, minwidth=0, stretch=False)
            columnas = self.dt.view["columns"]
            anchos = (420, 220, 140)
            for columna, ancho in zip(columnas, anchos):
                self.dt.view.column(columna, width=ancho, minwidth=ancho, stretch=True)
        except Exception as e:
            print(f"No se pudo fijar el ancho de columnas: {e}")
        self.frame_table_view.update_idletasks()
        
        
    def actualizar_barra(self, progreso, total):            
        """Actualiza la barra de progreso con el porcentaje calculado."""
        porcentaje = (progreso / total) * 100
        
        barra_progreso = self.DICT_WIDGETS.get_widget("UI", "BARRA_PROGRESO")
        if barra_progreso is not None:
            barra_progreso['value'] = porcentaje  # Asegúrate de usar 'value' para actualizar la barra
            self.label_porcentaje.configure(text=f"{int(porcentaje)}%")
        else:
            self.mostrar_accion("Error: No se encontró el widget BARRA_PROGRESO.")
            
            
    def creacion_toplevel_carga_datos(self):
        # Crear ventana Toplevel
        self.top_level_carga = ttk.Toplevel()
        self.top_level_carga.title("Cargar Datos")
        
        # Congelar la ventana principal al mostrar esta ventana
        self.top_level_carga.transient(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        self.top_level_carga.grab_set()  # Esto congela la ventana principal
        self.top_level_carga.protocol("WM_DELETE_WINDOW", self.bloquear_cierre)
        
        # Posicionar la ventana en el centro
        self.top_level_carga.geometry("400x250")  # Tamaño ajustado
        self.top_level_carga.place_window_center()

        # Agregar una barra de progreso
        self.progressbar_carga = ttk.Floodgauge(self.top_level_carga, mode="determinate", bootstyle="primary")
        self.DICT_WIDGETS.register("UI", "BARRA_PROGRESO", self.progressbar_carga)
        self.progressbar_carga.pack(fill="x", expand=True, padx=20, pady=(20,10))
        
        # Label de porcentaje con tamaño mayor
        self.label_porcentaje = ttk.Label(self.top_level_carga, text="0%", anchor="center", font=("Arial", 14))
        self.label_porcentaje.pack(pady=10)

        # Entry para mostrar las acciones, con tamaño mayor y centrado
        self.entry_acciones = ttk.Entry(self.top_level_carga, state="readonly", width=40, font=("Arial", 12))
        self.entry_acciones.pack(pady=10)
        self.mostrar_accion("Iniciando la carga de datos...")
        
        
    def bloquear_cierre(self):
        pass  # No hace nada al intentar cerrar
    
    def mostrar_accion(self, texto):
        print(texto)
        """Actualiza el Entry con el texto de la acción que se está realizando."""
        self.entry_acciones.config(state="normal")
        self.entry_acciones.delete(0, "end")
        self.entry_acciones.insert(0, texto)
        self.entry_acciones.config(state="readonly")


        
#/////////////////////////////////////////// COMMAND_BUTTONS ///////////////////////////////////////////
    def _command_crear_datos_legacy(self):
        self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja").bind("<F5>", lambda event: self.command_actualizar_datos())
        if not self.CONEXION_INFORHARD:
            messagebox.showerror("Error de conexión", "No hay conexión con la base de datos.")
            return

        # Iniciar loader (en el hilo principal, así se ve)
        self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "start")()

        def tarea():
            try:
                # Paso 1: buscar artículos
                self.buscar_datos_en_tabla_ARTICULOS()

                if not self.datos_ARTICULOS:
                    if not self.config.get("sincronizacion_automatica", False):
                        messagebox.showwarning("Sin datos", "No se encontraron productos para mostrar.")
                    return


                # Paso 2: preparar datos y mostrar
                self.datos_PRODUCTOS_COMPLETOS = self.datos_ARTICULOS
                self.insertar_datos_en_table_view()

            except Exception as e:
                print(f"Error: {e}")

            finally:
                # Detener loader siempre al final
                self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "stop")()

        # Ejecutar toda la tarea en segundo plano
        threading.Thread(target=tarea, daemon=True).start()

        # Activar el vigía solo si está habilitado
        if self.config.get("sincronizacion_automatica", True) and not self._vigia_iniciado:
            self.iniciar_vigia_actualizacion_productos(intervalo=self.AUTO_SYNC_INTERVAL_SECONDS)
            self._vigia_iniciado = True

        self.button_crear_datos.config(
            state="disabled", text="Actualizar Datos", command=self.command_actualizar_datos
        )

    def command_crear_datos(self):
        self.cargar_productos_locales_con_loader(force=True, mostrar_sin_datos=True)

    def cargar_productos_locales_con_loader(self, force=False, mostrar_sin_datos=False):
        if self._carga_local_en_curso:
            return
        if self._productos_cargados and not force:
            return

        self._carga_local_en_curso = True
        self.button_crear_datos.config(state=DISABLED, text="Cargando...")
        self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja").bind(
            "<F5>",
            lambda event: self.command_actualizar_datos(),
        )

        if self.config.get("sincronizacion_automatica", True) and not self._vigia_iniciado:
            self.iniciar_vigia_actualizacion_productos(intervalo=self.AUTO_SYNC_INTERVAL_SECONDS)
            self._vigia_iniciado = True

        try:
            self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "start")()
        except Exception as e:
            print(f"No se pudo iniciar loader de productos: {e}")

        def tarea():
            try:
                self.buscar_datos_en_tabla_ARTICULOS()

                def finalizar():
                    try:
                        if not self.datos_ARTICULOS:
                            if mostrar_sin_datos:
                                messagebox.showwarning("Sin datos", "No se encontraron productos para mostrar.")
                            return

                        self.datos_PRODUCTOS_COMPLETOS = self.datos_ARTICULOS
                        self.insertar_datos_en_table_view()
                        self._productos_cargados = True
                    finally:
                        self._carga_local_en_curso = False
                        self.button_crear_datos.config(
                            state=NORMAL,
                            text="Recargar Productos",
                            command=lambda: self.cargar_productos_locales_con_loader(
                                force=True,
                                mostrar_sin_datos=True,
                            ),
                        )
                        try:
                            self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "stop")()
                        except Exception as e:
                            print(f"No se pudo detener loader de productos: {e}")

                self._run_en_ui(finalizar)
            except Exception as e:
                def finalizar_error():
                    self._carga_local_en_curso = False
                    self.button_crear_datos.config(
                        state=NORMAL,
                        text="Recargar Productos",
                        command=lambda: self.cargar_productos_locales_con_loader(
                            force=True,
                            mostrar_sin_datos=True,
                        ),
                    )
                    try:
                        self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "stop")()
                    except Exception:
                        pass
                    messagebox.showerror("Error", f"No se pudieron cargar los productos: {e}")

                self._run_en_ui(finalizar_error)

        threading.Thread(target=tarea, daemon=True).start()

    def command_transmitir_datos(self):
        self.buscar_datos_en_tabla_ARTICULOS()
        total_registros = len(self.datos_ARTICULOS)

        if total_registros == 0:
            print("No hay datos para enviar.")
            return
        sender = DispositivoSender(
            self.CONEXIONDBA,
            self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"),
            tipos_descubrir=("verificador",),
        )
        urls = sender.seleccionar_dispositivos()
        if urls:
            top_preparacion, barra_preparacion, label_preparacion = self._crear_ventana_preparacion_envio(total_registros)

            def actualizar_preparacion(progreso, total, mensaje):
                def aplicar():
                    if top_preparacion.winfo_exists():
                        barra_preparacion.configure(value=progreso, maximum=total)
                        label_preparacion.configure(text=mensaje)
                self._run_en_ui(aplicar)

            def preparar_y_enviar():
                nueva_sqlite = None
                nueva_sybase = None
                try:
                    productos = self.completar_con_imagenes(
                        self.datos_ARTICULOS,
                        progress_callback=actualizar_preparacion,
                    )

                    def finalizar():
                        if top_preparacion.winfo_exists():
                            top_preparacion.destroy()
                        sender.enviar_datos(urls, productos, modo="completo")

                    self._run_en_ui(finalizar)
                except Exception as e:
                    def mostrar_error():
                        if top_preparacion.winfo_exists():
                            top_preparacion.destroy()
                        messagebox.showerror("Error", f"No se pudieron preparar los datos completos: {e}")

                    self._run_en_ui(mostrar_error)

            threading.Thread(target=preparar_y_enviar, daemon=True).start()


        
    def command_transmitir_novedades(self):
        sender = DispositivoSender(
            self.CONEXIONDBA,
            self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"),
            tipos_descubrir=("verificador",),
        )
        urls = sender.seleccionar_dispositivos()
        print(self.productos_modificados)
        if urls:
            productos_novedades = self._obtener_productos_novedades_por_codigos(self.productos_modificados)

            print("productos_novedades", productos_novedades)

            if not productos_novedades:
                messagebox.showinfo("Sin novedades", "No hay productos modificados para transmitir.")
                return
            print("➡️ Productos a transmitir:")
            for p in productos_novedades:
                print(f"{p[0]} - {p[1]}")  # Código - Descripción
            sender.enviar_datos(urls, productos_novedades, modo="novedades")

            self.productos_modificados.clear()

    def _obtener_productos_novedades_por_codigos(self, codigos, conexion=None):
        conexion = conexion or self.CONEXIONDBA
        resolver = ProductImageResolver(
            conexion,
            config=self.DICT_WIDGETS.get_widget("CONFIG", "config_json") or self.config,
            estado_callback=print,
            incluir_api_propia=False,
            incluir_go_upc=False,
        )
        productos_novedades = []
        vistos = set()
        consulta = """
        SELECT codigo, descripcion, precio, img_base64, formato_imagen
        FROM productos
        WHERE codigo = ?
        """

        for codigo in codigos:
            codigo = str(codigo).strip()
            if not codigo or codigo in vistos:
                continue
            vistos.add(codigo)
            resultado = conexion.ejecutar_consulta(consulta, (codigo,))
            if resultado:
                codigo_prod, descripcion, precio, img_base64, formato = resultado[0]
                if not img_base64:
                    img_base64, formato = resolver.resolver(codigo_prod, img_base64, formato)
                productos_novedades.append((codigo_prod, descripcion, precio, img_base64, formato))

        return productos_novedades

    def _envio_automatico_novedades_habilitado(self):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json") or self.config
        return bool(config.get("sincronizacion_automatica", False)) and bool(
            config.get("envio_automatico_novedades", False)
        )

    def _obtener_dispositivos_online_automatico(self, conexion):
        builder = VeriPreDispositivosURLBuilder(conexion)
        dispositivos = builder.obtener_urls_api("/api/veri/batch_productos")
        online = []

        for dispositivo in dispositivos:
            try:
                base_url = dispositivo["url"].split("/api")[0]
                status = requests.get(f"{base_url}{ENDPOINT_STATUS}", timeout=2)
                if status.status_code == 200:
                    online.append(dispositivo)
                    print(f"[auto-envio] Online: {dispositivo['nombre']}")
                    continue
            except Exception:
                pass

            try:
                base_url = dispositivo["url"].split("/api")[0]
                respuesta = requests.get(f"{base_url}/", timeout=2)
                if respuesta.status_code == 200:
                    online.append(dispositivo)
                    print(f"[auto-envio] Online: {dispositivo['nombre']}")
                else:
                    print(f"[auto-envio] Offline: {dispositivo['nombre']}")
            except Exception:
                print(f"[auto-envio] Offline: {dispositivo['nombre']}")

        if online:
            return online

        print("[auto-envio] No hay dispositivos registrados online. Intentando deteccion automatica en red...")
        try:
            discovery = DeviceDiscoveryService()
            detectados = discovery.discover(progress_callback=lambda msg: print(f"[auto-envio][discovery] {msg}"))
            for disp in detectados:
                if disp.get("tipo") != "verificador":
                    continue
                online.append(
                    {
                        "nombre": disp["nombre"],
                        "url": f"http://{disp['ip']}:{disp['puerto']}/api/veri/batch_productos",
                    }
                )
                print(f"[auto-envio] Detectado: {disp['nombre']} -> {disp['ip']}:{disp['puerto']}")
        except Exception as e:
            print(f"[auto-envio] Error en deteccion automatica: {e}")

        return online

    def _enviar_novedades_automaticas(self, codigos):
        if self._envio_auto_en_curso:
            print("[auto-envio] Ya hay un envio automatico en curso. Se omite esta solicitud.")
            return

        codigos = [str(codigo) for codigo in codigos if codigo]
        if not codigos:
            return

        self._envio_auto_en_curso = True
        sqlite_thread = None
        try:
            from DB.database import SQLiteDB

            sqlite_thread = SQLiteDB(self.CONEXIONDBA.ruta_db)
            sqlite_thread.crear_tablas()

            productos = self._obtener_productos_novedades_por_codigos(codigos, sqlite_thread)
            if not productos:
                self._notificar_sistema(
                    "Envio automatico",
                    "Se detectaron novedades, pero no se encontraron productos para enviar.",
                )
                return

            dispositivos = self._obtener_dispositivos_online_automatico(sqlite_thread)
            if not dispositivos:
                self._notificar_sistema(
                    "Envio automatico",
                    "No hay dispositivos online para enviar las novedades.",
                )
                return

            self._notificar_sistema(
                "Envio automatico",
                f"Enviando {len(productos)} novedades a {len(dispositivos)} dispositivos.",
            )
            envio_service = DispositivosEnvioService(sqlite_thread)
            resultados = {}

            def enviar(dispositivo):
                def estado(mensaje):
                    print(f"[auto-envio][{dispositivo['nombre']}] {mensaje}")

                envio_service.enviar_productos(
                    dispositivo["url"],
                    productos,
                    modo="novedades",
                    estado_callback=estado,
                )

            max_workers = min(4, len(dispositivos))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(enviar, dispositivo): dispositivo
                    for dispositivo in dispositivos
                }
                for future in as_completed(futures):
                    dispositivo = futures[future]
                    try:
                        future.result()
                        resultados[dispositivo["nombre"]] = True
                    except Exception as e:
                        resultados[dispositivo["nombre"]] = False
                        print(f"[auto-envio] ERROR {dispositivo['nombre']}: {e}")

            enviados_ok = sum(1 for ok in resultados.values() if ok)
            enviados_error = len(resultados) - enviados_ok
            if enviados_error == 0:
                self.productos_modificados.difference_update(codigos)
                estado_boton = NORMAL if self.productos_modificados else DISABLED
                self._run_en_ui(self.button_transmitir_novedades.config, state=estado_boton)
                self._notificar_sistema(
                    "Envio automatico",
                    f"Novedades enviadas correctamente a {enviados_ok} dispositivos.",
                )
            else:
                self._notificar_sistema(
                    "Envio automatico",
                    f"Envio finalizado con errores. OK={enviados_ok}, ERROR={enviados_error}.",
                )
        except Exception as e:
            print(f"[auto-envio] Error general: {e}")
            self._notificar_sistema("Envio automatico", f"No se pudieron enviar novedades: {e}")
        finally:
            if sqlite_thread:
                sqlite_thread.cerrar_conexion()
            self._envio_auto_en_curso = False

    def command_transmitir_por_fecha(self):
        import locale

        locale.setlocale(locale.LC_TIME, 'Spanish_Spain')  # O 'es_AR.UTF-8' en Linux

        top = ttk.Toplevel()
        top.title("Transmitir por Rango de Fechas")
        top.geometry("400x230")
        top.place_window_center()
        top.grab_set()

        today = date.today().strftime("%Y-%m-%d")

        ttk.Label(top, text="Fecha desde:").pack(pady=(10, 0))
        date_desde = DateEntry(top, bootstyle="info", width=20, dateformat="%Y-%m-%d", firstweekday=0)
        date_desde.entry.delete(0, "end")
        date_desde.entry.insert(0, today)
        date_desde.pack()

        ttk.Label(top, text="Fecha hasta:").pack(pady=(10, 0))
        date_hasta = DateEntry(top, bootstyle="info", width=20, dateformat="%Y-%m-%d", firstweekday=0)
        date_hasta.entry.delete(0, "end")
        date_hasta.entry.insert(0, today)
        date_hasta.pack()

        def confirmar():
            f1 = date_desde.entry.get()
            f2 = date_hasta.entry.get()

            if f1 > f2:
                messagebox.showwarning("Fechas inválidas", "La fecha inicial no puede ser posterior a la final.")
                return

            f_desde = f"{f1} 00:00:00"
            f_hasta = f"{f2} 23:59:59"

            consulta = """
            SELECT codigo, descripcion, precio, img_base64, formato_imagen
            FROM productos
            WHERE dFechaU BETWEEN ? AND ?
            """
            productos = self.CONEXIONDBA.ejecutar_consulta(consulta, (f_desde, f_hasta))
            
            print(consulta, f_desde, f_hasta)

            if not productos:
                messagebox.showinfo("Sin datos", "No hay productos en ese rango de fechas.")
                return

            print(f"📦 Productos a transmitir por fecha: {len(productos)}")
            sender = DispositivoSender(
                self.CONEXIONDBA,
                self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"),
                tipos_descubrir=("verificador",),
            )
            urls = sender.seleccionar_dispositivos()
            if urls:
                sender.enviar_datos(urls, productos, modo="rango_fecha")

            top.destroy()

        ttk.Button(top, text="Transmitir", command=confirmar).pack(pady=20)

    def _crear_ventana_preparacion_envio(self, total):
        top = ttk.Toplevel(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        top.title("Preparando datos completos")
        top.geometry("420x160")
        top.place_window_center()
        top.transient(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        top.grab_set()
        top.protocol("WM_DELETE_WINDOW", self.bloquear_cierre)

        ttk.Label(
            top,
            text="Preparando productos para enviar...",
            font=("Segoe UI", 11),
            anchor="center",
        ).pack(fill="x", pady=(18, 8))

        barra = ttk.Progressbar(top, mode="determinate", maximum=max(total, 1))
        barra.pack(fill="x", padx=24, pady=8)

        label = ttk.Label(top, text=f"0 de {total}", anchor="center")
        label.pack(fill="x", pady=(4, 12))
        return top, barra, label

        
    def forzar_dias_en_espanol(self, date_entry):
        dias_es = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do']
        
        # Esperar a que se cree el pop-up
        def traducir_dias(*args):
            top = date_entry._top_cal
            headers = top.children.get('calendar').children.get('header')
            for i, label in enumerate(headers.winfo_children()):
                label.config(text=dias_es[i % 7])

        # Enganchar al evento que abre el calendario
            date_entry.entry.bind("<Button-1>", lambda e: top.after(10, traducir_dias))




            
            
    def command_actualizar_datos(self, automatico=False):
        if self._actualizacion_en_curso:
            print("ActualizaciÃ³n ya en curso. Se omite nueva solicitud.")
            return
        if not self.CONEXIONDBA_SYBASE:
            if automatico:
                return
            messagebox.showerror("Error de conexión", "No hay conexión con la base de datos Sybase.")
            return
        try:
            self._actualizacion_en_curso = True
            if not automatico:
                self.creacion_toplevel_carga_datos()
            def tarea_actualizacion():
                try:
                    self.procesar_productos_a_actualizar(automatico=automatico)
                finally:
                    self._actualizacion_en_curso = False
            threading.Thread(
                target=tarea_actualizacion,
                daemon=True
            ).start()
        except Exception as e:
            self._actualizacion_en_curso = False
            print(e)

    def procesar_productos_a_actualizar(self, automatico=False):
        resultado = self._crear_productos_sync_service().sincronizar_actualizados_hoy(
            progress_callback=None if automatico else self._sync_progress,
            incluir_ultima_fecha=not automatico,
        )
        self.datos_ARTICULOS = resultado["articulos"]
        self.datos_PRODUCTOS_COMPLETOS = resultado["productos"]
        self.productos_modificados.update(resultado["codigos"])
        if resultado["codigos"]:
            self._run_en_ui(self.button_transmitir_novedades.config, state=NORMAL)
            if automatico:
                self._notificar_sistema(
                    "Catalogo actualizado",
                    f"Se actualizaron {len(resultado['codigos'])} productos.",
                )
                if self._envio_automatico_novedades_habilitado():
                    self._enviar_novedades_automaticas(resultado["codigos"])
                self._registrar_sincronizacion_automatica_procesada(resultado)
        if not automatico:
            self._run_en_ui(self.mostrar_accion, "Proceso completo.")
        if not automatico and not self.datos_ARTICULOS:
            self._run_en_ui(messagebox.showwarning, "Sin cambios", "No se registraron cambios ha actualizar.")
        if not automatico and hasattr(self, "top_level_carga") and self.top_level_carga.winfo_exists():
            self._run_en_ui(self.top_level_carga.destroy)
        self.buscar_datos_en_tabla_ARTICULOS()
        self._run_en_ui(self.insertar_datos_en_table_view)
        self._run_en_ui(
            self.button_crear_datos.config,
            state="disabled",
            text="Actualizar Datos",
            command=self.command_actualizar_datos,
        )
        self._actualizacion_en_curso = False

    def _registrar_sincronizacion_automatica_procesada(self, resultado):
        fechas = [str(producto[4]) for producto in resultado.get("productos", []) if len(producto) > 4 and producto[4]]
        if not fechas:
            return

        fecha_procesada = max(fechas)
        self._ultima_fecha_remota_procesada = fecha_procesada
        self.config["ultima_sincronizacion_automatica_productos"] = fecha_procesada
        try:
            guardar_config(self.config)
        except Exception as e:
            print(f"No se pudo guardar ultima sincronizacion automatica: {e}")
    #/////////////////////////////////////////// DATABASE ///////////////////////////////////////////
    def buscar_datos_en_tabla_ARTICULOS(self):
        """Obtiene los artículos con códigos de barras válidos"""
        CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS = """
            SELECT * FROM productos
            WHERE codigo IS NOT NULL AND TRIM(codigo) <> ''
            ORDER BY descripcion;
        """
        self.datos_ARTICULOS = self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS)
        print(f"Productos locales encontrados: {len(self.datos_ARTICULOS)}")
        self.datos_PRODUCTOS_COMPLETOS = self.datos_ARTICULOS
        
        
    def buscar_datos_en_tabla_ARTICULOS_actualizados(self):
        """Obtiene los artículos con códigos de barras válidos y fecha de actualización de hoy."""
        CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS = """
            SELECT CREF, CDETALLE, CCODEBAR, CTIPOIVA, NPVP1, CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
            FROM ARTICULO 
            WHERE CCODEBAR IS NOT NULL 
            AND CCODEBAR <> '' 
            AND CONVERT(DATE, dFechaU) = CONVERT(DATE, GETDATE())
            ORDER BY dFechaU DESC;
            ;
        """

        try:
            # Ejecutar la consulta en Sybase y almacenar los datos
            self.datos_ARTICULOS = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(
                CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS
            )
            print(f"Total de registros actualizados: {len(self.datos_ARTICULOS)}")


        except Exception as e:
            print(f"Error al actualizar datos: {e}")
            
            
    def buscar_datos_tabla_CODBARP(self):
        """Obtiene los códigos de barra adicionales y los une con la lista de productos."""
        self.datos_PRODUCTOS_COMPLETOS = []
        
        if not self.datos_ARTICULOS:
            self.mostrar_accion("No hay datos en ARTICULO")
            return
        
        crefs = tuple(producto[0] for producto in self.datos_ARTICULOS)
        
        if not crefs:
            return 

        crefs_str = f"('{ "','".join(crefs) }')"  # Convertir a cadena de consulta válida
        CONSULTA_SQL_BUSCAR_DATOS_CODBARP = f"""
            SELECT CREF, CDETALLE, CCODEBAR, CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
            FROM CODBARP 
            WHERE CREF IN {crefs_str} AND CCODEBAR IS NOT NULL AND CCODEBAR <> ''
            ORDER BY dFechaU ASC;
        """
        
        self.mostrar_accion("Obteniendo códigos de barra adicionales...")
        datos_codbarp = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_CODBARP)
        
        codbarp_dict = {}
        if datos_codbarp:
            for cref, cdetalle, ccodebar, dfechau in datos_codbarp:
                if cref not in codbarp_dict:
                    codbarp_dict[cref] = []
                codbarp_dict[cref].append((cdetalle, ccodebar, dfechau))
        
        total_productos = len(self.datos_ARTICULOS)
        total_codigos_barra = len(datos_codbarp)
        total = total_productos + total_codigos_barra
        progreso = 0

        for idx, producto in enumerate(self.datos_ARTICULOS):
            print(f"Producto {idx}: {producto}")
            cref, cdetalle, ccodebar, ctipoiva, npvp1, dfechau = producto
            self.datos_PRODUCTOS_COMPLETOS.append(producto)
            progreso += 1
            if progreso % 10 == 0:  # Actualiza la barra cada 10 productos
                self.actualizar_barra(progreso, total)
            
            if cref in codbarp_dict:
                for cdetalle_extra, ccodebar_extra, _ in codbarp_dict[cref]:
                    self.datos_PRODUCTOS_COMPLETOS.append((cref, cdetalle_extra, ccodebar_extra, ctipoiva, npvp1, dfechau))
                    progreso += 1
                    if progreso % 10 == 0:  # Actualiza la barra cada 10 productos
                        self.actualizar_barra(progreso, total)

        self.mostrar_accion(f"{len(self.datos_PRODUCTOS_COMPLETOS)} productos completos.")


    def buscar_datos_tabla_IVAS(self):
        """Obtiene los datos de IVAS y muestra la barra de progreso mientras se realiza la consulta."""
        
        self.mostrar_accion("Obteniendo datos de IVAS...")
        
        # Iniciar la barra de progreso en 0%
        self.actualizar_barra(0, 100)

        # Simular el tiempo de espera para la consulta (esto es solo para efectos de la barra)
        # Realmente, la consulta se ejecuta de forma bloqueante, por lo que la barra de progreso puede ir del 0% al 100% al final
        try:
            CONSULTA_SQL_BUSCAR_DATOS_IVAS = f"""
                SELECT * FROM IVAS;
            """
            # Aquí ejecutamos la consulta y almacenamos los resultados
            self.datos_IVAS = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_IVAS)

            # Una vez que la consulta finalice, actualizamos el progreso al 100%
            self.actualizar_barra(100, 100)
            
            self.mostrar_accion(f"{len(self.datos_IVAS)} tipos de IVA encontrados.")
        except Exception as e:
            self.mostrar_accion(f"Error al obtener los datos de IVAS: {str(e)}")

        
    def actualizar_precios_con_iva(self):
        """Actualiza los precios de los productos agregando el IVA correspondiente y muestra el progreso."""
        iva_dict = {str(iva[0]): iva[2] for iva in self.datos_IVAS}
        productos_actualizados = []

        self.mostrar_accion("Actualizando precios con IVA...")

        total_productos = len(self.datos_PRODUCTOS_COMPLETOS)
        if total_productos == 0:
            self.mostrar_accion("No hay productos para actualizar.")
            return

        self.actualizar_barra(0, total_productos)

        for idx, producto in enumerate(self.datos_PRODUCTOS_COMPLETOS):
            codigo_iva = str(producto[3])
            precio_base = producto[4]

            porcentaje_iva = iva_dict.get(codigo_iva, 0.0)
            nuevo_precio = precio_base * (1 + porcentaje_iva / 100)

            producto_actualizado = (
                producto[0],  # cref
                producto[1],  # descripcion
                producto[2],  # codigo
                format(round(nuevo_precio, 2), ".2f"),  # precio actualizado
                producto[5],  # dfechau
            )
            print("actualizar_precios_con_iva", producto_actualizado)
            productos_actualizados.append(producto_actualizado)


            self.actualizar_barra(idx + 1, total_productos)

        self.datos_PRODUCTOS_COMPLETOS = productos_actualizados
        self.mostrar_accion(f"{len(self.datos_PRODUCTOS_COMPLETOS)} productos actualizados con IVA.")

            
        
    def insertar_o_actualizar_productos(self):
        """Inserta o actualiza los productos en la base de datos SQLite en batch con executemany()."""
        
        consulta = """
        INSERT INTO productos (CREF, codigo, descripcion, precio, dfechau) 
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(codigo) DO UPDATE SET 
            CREF = excluded.CREF,
            descripcion = excluded.descripcion,
            precio = excluded.precio,
            dfechau = excluded.dfechau
        """

        self.mostrar_accion("Insertando o actualizando productos...")

        total_productos = len(self.datos_PRODUCTOS_COMPLETOS)
        if total_productos == 0:
            self.mostrar_accion("No hay productos para insertar o actualizar.")
            return

        # Preparar los datos para el execute many
        parametros = [(p[0], p[2], p[1], p[3], p[4]) for p in self.datos_PRODUCTOS_COMPLETOS]
        print(parametros)

        try:
            self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA").ejecutar_consultamany(consulta, parametros)
            print(f"✅ {total_productos} productos insertados/actualizados correctamente.")

            # 🔹 Registrar cambios en self.productos_modificados
            for p in self.datos_PRODUCTOS_COMPLETOS:
                self.registrar_cambio_producto(p[2])  # `p[2]` es el código del producto

            self.mostrar_accion(f"{total_productos} productos procesados.")
        except Exception as e:
            print(f"❌ Error al insertar/actualizar productos: {e}")
            self.mostrar_accion("Error al procesar los productos.")

        self.actualizar_barra(total_productos, total_productos)  # Llenar barra al 100%


        
    def variables_globales(self):
        self.datos_ARTICULOS = []
        self.datos_PRODUCTOS_COMPLETOS = []
        self.IMG_NO_FOTO = READ_IMG(PNG_No_Foto(), 450, 450)
        self.BATCH_SIZE = 1000  # Tamaño del lote
        self.productos_modificados = set()  # Guardará los códigos de productos modificados

        
        
    def insertar_datos_en_table_view(self):
        try:
            codigo_seleccionado = None
            seleccion = self.dt.view.selection()
            if seleccion:
                valores = self.dt.view.item(seleccion[0]).get("values", [])
                if len(valores) > 1:
                    codigo_seleccionado = str(valores[1])

            self.dt.delete_rows()

            for producto in self.datos_PRODUCTOS_COMPLETOS:
                descripcion = str(producto[2]).strip() if producto[2] else ""
                codigo = producto[1] if producto[1] else ""
                precio = float(producto[3]) if producto[3] else 0.0
                precio_formateado = f"${precio:,.2f}"
                self.dt.insert_row("end", [descripcion, codigo, precio_formateado])
            self.dt.load_table_data()
            self.dt.configure(height=self.TABLE_HEIGHT)
            self._fijar_layout_productos()
            if codigo_seleccionado:
                for item_id in self.dt.view.get_children():
                    valores = self.dt.view.item(item_id).get("values", [])
                    if len(valores) > 1 and str(valores[1]) == codigo_seleccionado:
                        self.dt.view.selection_set(item_id)
                        self.dt.view.see(item_id)
                        break
            self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "stop")()
            self.button_transmitir_datos.config(state=NORMAL)
            self.button_transmitir_datos_fecha.config(state=NORMAL)
            self.button_transmitir_novedades.config(state=NORMAL)

        except Exception as e:
            print(f"❌ Error al insertar en la tabla: {e}")
            self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "stop")()



            
    def mostrar_imagen_producto(self, event):
        """Función para obtener y mostrar la imagen almacenada en la base de datos."""
        seleccion = self.dt.view.selection()  # Obtener selección
        if not seleccion:
            return

        item = self.dt.view.item(seleccion)  # Obtener datos de la fila seleccionada
        codigo_producto = item["values"][1]  # Obtener el código del producto
        self._actualizar_estado_precios_adicionales(codigo_producto)
        self._actualizar_estado_oferta(codigo_producto)

        try:
            img_base64, _ = self._obtener_imagen_producto(codigo_producto)
            if not img_base64:
                self.label_img_producto.config(image=self.IMG_NO_FOTO)
                return

            imagen_bytes = base64.b64decode(img_base64)
            imagen_pil = Image.open(BytesIO(imagen_bytes))
            imagen_pil.thumbnail(self.PREVIEW_IMAGE_SIZE, Image.Resampling.LANCZOS)
            imagen_tk = ImageTk.PhotoImage(imagen_pil)
            self.label_img_producto.image = imagen_tk
            self.label_img_producto.config(image=imagen_tk)

        except Exception as e:
            print(f"Error al recuperar la imagen desde la base de datos: {e}")
            self.label_img_producto.config(image=self.IMG_NO_FOTO)  # Mostrar imagen por defecto en caso de error

    def _obtener_imagen_producto(self, codigo_producto):
        consulta = "SELECT img_base64, formato_imagen FROM productos WHERE codigo = ?"
        resultado = self.CONEXIONDBA.ejecutar_consulta(consulta, (codigo_producto,))
        img_base64, tipo_imagen = (None, None)
        if resultado and resultado[0]:
            img_base64, tipo_imagen = resultado[0]
        if not img_base64:
            img_base64, tipo_imagen = self._crear_image_resolver().resolver(
                codigo_producto,
                img_base64,
                tipo_imagen,
            )
        return img_base64, tipo_imagen

    def _obtener_precios_adicionales_producto(self, codigo_producto, conexion=None):
        try:
            filas = self._crear_productos_sqlite_dao(conexion).listar_precios_adicionales_por_codigo(codigo_producto)
        except Exception as e:
            print(f"Error al obtener precios adicionales desde SQLite: {e}")
            return []

        return [
            {
                "codigo": fila[0],
                "tipo_precio": fila[1],
                "categoria": fila[2],
                "origen": fila[3],
                "orden": fila[4],
                "cantidad": fila[5],
                "titulo": fila[6],
                "detalle": fila[7],
                "precio": float(fila[8] or 0),
                "nroprecio": fila[9],
                "dfechau": fila[10],
            }
            for fila in filas
        ]

    def _actualizar_estado_precios_adicionales(self, codigo_producto):
        try:
            precios_adicionales = self._obtener_precios_adicionales_producto(codigo_producto)
            cantidad = len(precios_adicionales)
            if cantidad:
                texto = f"Precios adicionales: SI ({cantidad})"
                estilo = "success"
            else:
                texto = "Precios adicionales: NO"
                estilo = "secondary"
            self.label_precios_extra_estado.config(text=texto, bootstyle=estilo)
        except Exception as e:
            print(f"Error actualizando estado de precios adicionales: {e}")
            self.label_precios_extra_estado.config(text="Precios adicionales: error", bootstyle="danger")

    def _obtener_oferta_producto(self, codigo_producto):
        try:
            fila = self._crear_productos_sqlite_dao(self.CONEXIONDBA).obtener_oferta_por_codigo(codigo_producto)
        except Exception as e:
            print(f"Error al obtener oferta desde SQLite: {e}")
            return None

        if not fila:
            return None

        _, tiene_oferta, precio_oferta, oferta_desde, oferta_hasta, oferta_origen, oferta_ccoddiv, oferta_dto = fila
        return {
            "tiene_oferta": bool(tiene_oferta),
            "precio_oferta": float(precio_oferta or 0) if precio_oferta is not None else None,
            "oferta_desde": oferta_desde,
            "oferta_hasta": oferta_hasta,
            "oferta_origen": oferta_origen,
            "oferta_ccoddiv": oferta_ccoddiv,
            "oferta_dto": float(oferta_dto or 0) if oferta_dto is not None else None,
        }

    def _actualizar_estado_oferta(self, codigo_producto):
        try:
            oferta = self._obtener_oferta_producto(codigo_producto)
            if oferta and oferta.get("tiene_oferta"):
                precio_txt = f"${float(oferta.get('precio_oferta') or 0):,.2f}"
                texto = f"Oferta activa: SI ({precio_txt})"
                estilo = "warning"
            else:
                texto = "Oferta activa: NO"
                estilo = "secondary"
            self.label_oferta_estado.config(text=texto, bootstyle=estilo)
        except Exception as e:
            print(f"Error actualizando estado de oferta: {e}")
            self.label_oferta_estado.config(text="Oferta activa: error", bootstyle="danger")


            
    def abrir_detalle_producto(self, event):
        """Abre un top-level con los detalles del producto seleccionado o actualiza el existente."""
        
        # Verificar si ya existe un Toplevel abierto
        if hasattr(self, 'top_level_abierto') and self.top_level_abierto.winfo_exists():
            self.top_level_abierto.destroy()

        seleccion = self.dt.view.selection()  # Obtener selección
        if not seleccion:
            return

        item = self.dt.view.item(seleccion)  # Obtener datos de la fila seleccionada
        codigo_producto = item["values"][1]  # Código del producto
        descripcion_producto = item["values"][0]  # Descripción del producto
        precio_producto = item["values"][2]  # Precio del producto

        # Crear una ventana Toplevel
        top = ttk.Toplevel(self)
        top.transient(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        self.top_level_abierto = top  # Guardar referencia al Toplevel
        top.title(f"Detalle del producto {codigo_producto}")
        top.geometry("760x470")
        top.resizable(False, False)
        top.place_window_center()

        # Frame para organizar elementos
        frame_info = ttk.Frame(top, width=730, height=430)
        frame_info.pack(fill="both", padx=10, pady=10, expand=True)
        frame_info.pack_propagate(False)
        frame_info.grid_propagate(False)
        frame_info.columnconfigure(1, minsize=320)
        frame_info.columnconfigure(2, minsize=220)

        # Función para crear un Entry en modo readonly con un Label
        def crear_entry(frame, texto, valor, fila):
            ttk.Label(frame, text=texto).grid(row=fila, column=0, sticky="w", padx=5, pady=5)
            entry = ttk.Entry(frame, state="normal", width=50)  # Más ancho para mayor visibilidad
            entry.grid(row=fila, column=1, padx=5, pady=5, sticky="ew")
            entry.insert(0, valor)
            entry.config(state="readonly")  # Bloquear edición
            return entry

        # Crear los campos con sus valores
        entry_codigo = crear_entry(frame_info, "Código:", codigo_producto, 0)
        entry_descripcion = crear_entry(frame_info, "Descripción:", descripcion_producto, 1)
        entry_precio = crear_entry(frame_info, "Precio:", precio_producto, 2)
        oferta = self._obtener_oferta_producto(codigo_producto)

        # Frame para la imagen
        frame_img = ttk.Frame(
            frame_info,
            width=self.DETAIL_IMAGE_SIZE[0],
            height=self.DETAIL_IMAGE_SIZE[1],
        )
        frame_img.grid(row=0, column=2, rowspan=3, padx=10, pady=5, sticky="n")
        frame_img.grid_propagate(False)
        frame_img.pack_propagate(False)

        label_img = ttk.Label(frame_img, anchor="center")
        label_img.place(relx=0.5, rely=0.5, anchor="center")

        # Función para obtener la imagen desde la base de datos
        def cargar_imagen_desde_db():
            """Obtiene la imagen en Base64 desde la base de datos y la muestra en el label_img."""
            img_base64, _ = self._obtener_imagen_producto(codigo_producto)
            if not img_base64:
                mostrar_imagen_por_defecto()
                return

            try:
                imagen_bytes = base64.b64decode(img_base64)
                imagen_pil = Image.open(BytesIO(imagen_bytes))
                imagen_pil = imagen_pil.resize(self.DETAIL_IMAGE_SIZE)
                imagen_tk = ImageTk.PhotoImage(imagen_pil)
                label_img.config(image=imagen_tk, text="")
                label_img.image = imagen_tk
            except Exception as e:
                print(f"Error al cargar la imagen desde la base de datos: {e}")
                mostrar_imagen_por_defecto()
            return

            CONSULTA_SQL_OBTENER_IMG = """
            SELECT img_base64, formato_imagen FROM productos WHERE codigo = ?
            """
            resultado = self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_OBTENER_IMG, (codigo_producto,))

            if resultado and resultado[0]:  # Si hay datos y la imagen no es NULL
                img_base64, tipo_imagen = resultado[0]  # Extrae la primera fila correctamente

                if img_base64:  # Verificar que img_base64 no sea None
                    try:
                        # Decodificar la imagen en Base64
                        imagen_bytes = base64.b64decode(img_base64)

                        # Convertir los bytes en una imagen PIL
                        imagen_pil = Image.open(BytesIO(imagen_bytes))
                        imagen_pil = imagen_pil.resize(self.DETAIL_IMAGE_SIZE)  # Redimensionar a 200x200 píxeles

                        # Convertir la imagen PIL a un formato compatible con Tkinter
                        imagen_tk = ImageTk.PhotoImage(imagen_pil)

                        # Actualizar el widget con la imagen cargada
                        label_img.config(image=imagen_tk, text="")
                        label_img.image = imagen_tk  # Guardar referencia para evitar que la imagen sea eliminada por el recolector de basura
                    except Exception as e:
                        print(f"Error al cargar la imagen desde la base de datos: {e}")
                        mostrar_imagen_por_defecto()
                else:
                    mostrar_imagen_por_defecto()
            else:
                mostrar_imagen_por_defecto()
                


        def mostrar_imagen_por_defecto():
            """Carga una imagen por defecto si no hay imagen en la base de datos."""
            try:
                img = Image.open(PNG_No_Foto())  # Función que retorna la ruta de la imagen por defecto
                img = img.resize(self.DETAIL_IMAGE_SIZE)
                img_tk = ImageTk.PhotoImage(img)
                label_img.config(image=img_tk, text="")
                label_img.image = img_tk
            except Exception as e:
                print(f"Error al cargar la imagen por defecto: {e}")

        # Cargar imagen desde la base de datos
        cargar_imagen_desde_db()

        # Función para seleccionar y guardar nueva imagen en la BD
        ttk.Label(
            frame_info,
            text="Precios adicionales (SQLite local)",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=4, column=0, columnspan=3, sticky="w", padx=5, pady=(18, 6))

        frame_precios = ttk.Frame(frame_info)
        frame_precios.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=5, pady=(0, 8))
        frame_precios.columnconfigure(0, weight=1)

        columnas = ("titulo", "cantidad", "categoria", "precio")
        tree_precios = ttk.Treeview(frame_precios, columns=columnas, show="headings", height=6)
        tree_precios.heading("titulo", text="Titulo")
        tree_precios.heading("cantidad", text="Cantidad")
        tree_precios.heading("categoria", text="Categoria")
        tree_precios.heading("precio", text="Precio")
        tree_precios.column("titulo", width=310, anchor="w")
        tree_precios.column("cantidad", width=90, anchor="center")
        tree_precios.column("categoria", width=120, anchor="center")
        tree_precios.column("precio", width=120, anchor="e")

        scroll_precios = ttk.Scrollbar(frame_precios, orient="vertical", command=tree_precios.yview)
        tree_precios.configure(yscrollcommand=scroll_precios.set)
        tree_precios.grid(row=0, column=0, sticky="nsew")
        scroll_precios.grid(row=0, column=1, sticky="ns")

        precios_adicionales = self._obtener_precios_adicionales_producto(codigo_producto)
        if precios_adicionales:
            for precio_extra in precios_adicionales:
                titulo = precio_extra.get("titulo") or precio_extra.get("detalle") or precio_extra.get("tipo_precio")
                cantidad = precio_extra.get("cantidad") or "-"
                categoria = str(precio_extra.get("categoria") or "-").capitalize()
                precio_txt = f"${float(precio_extra.get('precio') or 0):,.2f}"
                tree_precios.insert("", "end", values=(titulo, cantidad, categoria, precio_txt))
        else:
            tree_precios.insert("", "end", values=("Sin precios adicionales sincronizados", "-", "-", "-"))

        def seleccionar_imagen():
            archivo = filedialog.askopenfilename(
                title="Seleccionar imagen",
                filetypes=[("Archivos de imagen", "*.png;*.jpg;*.jpeg;*.gif;*.webp")]
            )
            if archivo:
                try:
                    img_base64, formato_imagen, resumen_imagen = self._preparar_imagen_producto_para_db(archivo)

                    CONSULTA_SQL_GUARDAR_IMG = """
                    UPDATE productos SET img_base64 = ?, formato_imagen = ? WHERE codigo = ?
                    """
                    self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_GUARDAR_IMG, (img_base64, formato_imagen, codigo_producto))

                    cargar_imagen_desde_db()
                    self.registrar_cambio_producto(codigo_producto)
                    print(f"Imagen guardada correctamente en la base de datos. {resumen_imagen}")
                    messagebox.showinfo("Imagen de producto", f"Imagen optimizada y guardada.\n{resumen_imagen}")

                except Exception as e:
                    print(f"Error al guardar la imagen en la base de datos: {e}")

        # Botón para cargar nueva imagen
        btn_cargar_img = ttk.Button(frame_info, text="Cargar Imagen", command=seleccionar_imagen)
        btn_cargar_img.grid(row=3, column=2, padx=5, pady=5)

        ttk.Label(
            frame_info,
            text="Oferta activa (SQLite local)",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=6, column=0, columnspan=3, sticky="w", padx=5, pady=(12, 6))

        frame_oferta = ttk.Frame(frame_info)
        frame_oferta.grid(row=7, column=0, columnspan=3, sticky="ew", padx=5, pady=(0, 6))
        frame_oferta.columnconfigure(0, weight=1)
        frame_oferta.columnconfigure(1, weight=1)
        frame_oferta.columnconfigure(2, weight=1)
        frame_oferta.columnconfigure(3, weight=1)

        oferta_activa = bool(oferta and oferta.get("tiene_oferta"))
        precio_oferta = f"${float(oferta.get('precio_oferta') or 0):,.2f}" if oferta_activa else "-"
        oferta_desde = str((oferta or {}).get("oferta_desde") or "-")
        oferta_hasta = str((oferta or {}).get("oferta_hasta") or "-")
        oferta_origen = str((oferta or {}).get("oferta_origen") or "-")
        oferta_ccoddiv = str((oferta or {}).get("oferta_ccoddiv") or "-")

        ttk.Label(frame_oferta, text="Activa").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(frame_oferta, text="Precio oferta").grid(row=0, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(frame_oferta, text="Desde").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        ttk.Label(frame_oferta, text="Hasta").grid(row=0, column=3, sticky="w", padx=4, pady=2)
        ttk.Label(
            frame_oferta,
            text="SI" if oferta_activa else "NO",
            bootstyle="warning" if oferta_activa else "secondary",
        ).grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(frame_oferta, text=precio_oferta).grid(row=1, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(frame_oferta, text=oferta_desde).grid(row=1, column=2, sticky="w", padx=4, pady=2)
        ttk.Label(frame_oferta, text=oferta_hasta).grid(row=1, column=3, sticky="w", padx=4, pady=2)
        ttk.Label(frame_oferta, text=f"Origen: {oferta_origen}").grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=2)
        ttk.Label(frame_oferta, text=f"CCODDIV: {oferta_ccoddiv}").grid(row=2, column=2, columnspan=2, sticky="w", padx=4, pady=2)

    def registrar_cambio_producto(self, codigo_producto):
            """Registra que un producto ha sido modificado."""
            self.productos_modificados.add(codigo_producto)
            self.button_transmitir_novedades.config(state=NORMAL)  # Habilitar botón automáticamente
    
    def guardar_imagen_en_db(self, codigo_producto, ruta_imagen):
        """Convierte la imagen a Base64 y la guarda en la base de datos."""
        if not os.path.exists(ruta_imagen):
            print("Error: La imagen no existe.")
            return

        img_base64, tipo_imagen, _resumen_imagen = self._preparar_imagen_producto_para_db(ruta_imagen)

        try:
            CONSULTA_SQL_ACTUALIZAR_IMG = """
            UPDATE productos 
            SET img_base64 = ?, formato_imagen = ? 
            WHERE codigo = ?
            """
            self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_ACTUALIZAR_IMG, (img_base64, tipo_imagen, codigo_producto))
            print("Imagen guardada correctamente en la base de datos.")

        except Exception as e:
            print(f"Error al guardar en la base de datos: {e}")

    def _preparar_imagen_producto_para_db(self, ruta_imagen):
        img = Image.open(ruta_imagen)
        ancho_original, alto_original = img.size

        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")

        if img.mode == "RGBA":
            fondo = Image.new("RGB", img.size, (255, 255, 255))
            fondo.paste(img, mask=img.split()[3])
            img = fondo
        else:
            img = img.convert("RGB")

        maximo = (1400, 1400)
        objetivo = (1000, 1000)

        if img.width > maximo[0] or img.height > maximo[1]:
            img.thumbnail(maximo, Image.Resampling.LANCZOS)

        img.thumbnail(objetivo, Image.Resampling.LANCZOS)

        calidad = 88
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=calidad, optimize=True)
        contenido = buffer.getvalue()

        while len(contenido) > 700 * 1024 and calidad > 65:
            calidad -= 5
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=calidad, optimize=True)
            contenido = buffer.getvalue()

        img_base64 = base64.b64encode(contenido).decode("utf-8")
        resumen = (
            f"Original: {ancho_original}x{alto_original}px | "
            f"Final: {img.width}x{img.height}px | "
            f"Peso: {len(contenido) / 1024:.0f} KB | Formato: JPEG"
        )
        return img_base64, "jpg", resumen

    def _notificar_sistema(self, titulo, mensaje):
        try:
            notification.notify(
                title=titulo,
                message=mensaje,
                timeout=5,
                app_icon=ICON_ico(),
            )
        except Exception as e:
            print(f"No se pudo mostrar notificacion: {e}")

    def iniciar_vigia_actualizacion_productos(self, intervalo=AUTO_SYNC_INTERVAL_SECONDS):
        def vigia():
            print("🟢 Vigía activado (modo automático)")  # Línea fija que queda

            puntos = ["", ".", "..", "..."]
            anim_index = 0

            while True:
                if not self.config.get("sincronizacion_automatica", True):
                    print("⏸️ Vigía pausado por configuración. Esperando activación...")
                    time.sleep(5)
                    continue

                try:
                    print(f"\rRevisión en progreso{puntos[anim_index % 4]}   ", end="")
                    anim_index += 1

                    # ✅ Nueva conexión SQLite (segura para este hilo)
                    from DB.database import SQLiteDB
                    nueva_sqlite = SQLiteDB(self.CONEXIONDBA.ruta_db)
                    sql_local = "SELECT dFechaU FROM productos ORDER BY dFechaU DESC LIMIT 1"
                    res_local = nueva_sqlite.ejecutar_consulta(sql_local)
                    fecha_local = res_local[0][0] if res_local else "2000-01-01 00:00:00"

                    # ✅ Nueva conexión Sybase (segura para este hilo)
                    from DB.database_sybase import ConexionSybase
                    nueva_sybase = ConexionSybase(
                        user=self.CONEXIONDBA_SYBASE.usuario,
                        password=self.CONEXIONDBA_SYBASE.contrasena,
                        dsn=self.CONEXIONDBA_SYBASE.dsn_name
                    )
                    sql_sybase = """
                    SELECT MAX(dFechaU) FROM ARTICULO 
                    WHERE CCODEBAR IS NOT NULL AND CCODEBAR <> ''
                    """
                    res_sybase = nueva_sybase.ejecutar_consulta(sql_sybase)
                    fecha_remota = res_sybase[0][0] if res_sybase else None

                    if fecha_remota:
                        fmt = "%Y-%m-%d %H:%M:%S"
                        f_local = datetime.strptime(str(fecha_local), fmt)
                        f_remota = datetime.strptime(str(fecha_remota), fmt)

                        fecha_remota_key = str(fecha_remota)
                        if f_remota > f_local and fecha_remota_key != self._ultima_fecha_remota_procesada:
                            self._ultima_fecha_remota_procesada = fecha_remota_key
                            print("🟡 Nueva actualización detectada. Ejecutando actualización...")
                            self._notificar_sistema(
                                "Actualizacion automatica",
                                "Se detectaron cambios en productos. Actualizando catalogo...",
                            )
                            self._run_en_ui(self.command_actualizar_datos, True)
                            continue

                except Exception as e:
                    print(f"❌ Vigía error: {e}")
                finally:
                    if nueva_sqlite:
                        try:
                            nueva_sqlite.cerrar_conexion()
                        except Exception:
                            pass
                    if nueva_sybase:
                        try:
                            nueva_sybase.desconectar()
                        except Exception:
                            pass

                time.sleep(intervalo)

        threading.Thread(target=vigia, daemon=True).start()

    def completar_con_imagenes(self, productos, progress_callback=None):
        productos_con_imagen = []
        total = len(productos)
        omitidos = 0
        resolver = self._crear_image_resolver()

        for idx, prod in enumerate(productos, start=1):
            if len(prod) >= 6:
                codigo = prod[1]
                descripcion = prod[2]
                precio = prod[3]
                img_base64 = prod[4]
                formato = prod[5]
            elif len(prod) >= 5:
                codigo = prod[0]
                descripcion = prod[1]
                precio = prod[2]
                img_base64 = prod[3]
                formato = prod[4]
            else:
                codigo = prod[1]
                descripcion = prod[2]
                precio = prod[3]
                consulta = "SELECT img_base64, formato_imagen FROM productos WHERE codigo = ?"
                resultado = self.CONEXIONDBA.ejecutar_consulta(consulta, (codigo,))
                if resultado and resultado[0]:
                    img_base64, formato = resultado[0]
                else:
                    img_base64, formato = None, None

            codigo = str(codigo).strip() if codigo is not None else ""
            if not codigo:
                omitidos += 1
                continue

            if not img_base64:
                img_base64, formato = resolver.resolver(codigo, img_base64, formato)

            productos_con_imagen.append((
                codigo,
                descripcion,
                precio,
                img_base64,
                formato
            ))

            if progress_callback and (idx == 1 or idx % 100 == 0 or idx == total):
                progress_callback(idx, total, f"Preparados {idx} de {total} productos")

        if omitidos and progress_callback:
            progress_callback(total, total, f"Se omitieron {omitidos} productos sin codigo")

        return productos_con_imagen
