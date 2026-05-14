import os
import threading
import json
import locale
import socket
import sys

import ttkbootstrap as ttk
from tkinter import messagebox

from ASSETS.path_img import *
from pystray import Icon as TrayIcon, Menu as TrayMenu, MenuItem
from FUNC.ctk_components.ctk_components import CTkLoader
from FUNC.create_widget import WidgetRegistry
from FUNC.config_json import *
# from FUNC.config_manager_json import ConfigManager
from FUNC.windows_manager import VentanaManager
from GUI.CONTENIDO_PRODUCTO import ContenidoProducto
from GUI.CONTENIDO_PUBLICIDAD import ContenidoPublicidad
from GUI.GUI_CONFIG import GUI_CONFIG
from DB.database import SQLiteDB
from DB.database_sybase import ConexionSybase
from core.logging.logger import get_logger

logger = get_logger(__name__)


def comprobar_instancia_unica(puerto=55665):
    logger.debug("Verificando instancia Ãºnica de la aplicaciÃ³n | puerto=%s", puerto)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", puerto))
        logger.info("Instancia Ãºnica confirmada. Socket de bloqueo adquirido.")
        return sock  # mantiene el socket abierto
    except OSError:
        logger.warning("Se detectÃ³ otra instancia en ejecuciÃ³n | puerto=%s", puerto)
        messagebox.showinfo(
            "AplicaciÃ³n ya en ejecuciÃ³n",
            "La aplicaciÃ³n ya estÃ¡ abierta.\nRevisÃ¡ la bandeja del sistema (icono cerca del reloj)."
        )
        sys.exit(0)


class GUI_MAIN:
    def __init__(self, version):
        logger.info("Iniciando GUI_MAIN | version=%s", version)

        self.socket_lock = comprobar_instancia_unica()
        self.DICT_WIDGETS = WidgetRegistry()
        self.VIGIA_FRAME = "INICIO"
        self.VIGIA_VOLVER = [self.VIGIA_FRAME]

        logger.debug("Cargando configuraciÃ³n JSON.")
        self.config_data = cargar_config()
        self.DICT_WIDGETS.register("CONFIG", "config_json", self.config_data)

        try:
            locale.setlocale(locale.LC_TIME, "Spanish_Spain")  # o 'es_AR.UTF-8'
            logger.debug("Locale configurado correctamente | locale=Spanish_Spain")
        except Exception:
            logger.exception("No se pudo configurar locale 'Spanish_Spain'.")

        logger.debug("Creando ventana principal ttkbootstrap.")
        self.ventana_creacion_caja = ttk.Window(themename="flatly", iconphoto=ICON())
        self.ventana_creacion_caja.title(f"VeriPre_Connector, V.{version}")
        self.ventana_creacion_caja.state("zoomed")

        self.ventana_creacion_caja.grid_columnconfigure(0, minsize=250, weight=0)
        self.ventana_creacion_caja.grid_columnconfigure(1, weight=1)
        self.ventana_creacion_caja.rowconfigure(0, weight=1)

        self.ventana_creacion_caja.protocol("WM_DELETE_WINDOW", self.ocultar_a_bandeja)

        self.DICT_WIDGETS.register("GUI_MAIN", "ventana_creacion_caja", self.ventana_creacion_caja)

        logger.debug("Inicializando conexiones de base de datos.")
        self.CONEXIONES_DBA()

        logger.debug("Inicializando variables globales.")
        self.VARIABLES_GLOBALES()

        logger.debug("Construyendo frame del menÃº.")
        self.frameMenu()

        logger.debug("Construyendo frame de contenido.")
        self.frameContenido()

        logger.debug("Creando secciÃ³n inicio.")
        self.seccion_inicio()

        logger.debug("Creando secciÃ³n productos.")
        self.seccion_productos()

        logger.debug("Creando secciÃ³n publicidad.")
        self.seccion_publicidad()

        logger.debug("Seleccionando secciÃ³n inicial.")
        self.selector_seccion()

        logger.debug("Inicializando loader CTk.")
        self.ctk_loader = CTkLoader(self.ventana_creacion_caja, opacity=0.8, width=40, height=40)
        self.DICT_WIDGETS.register("CTK_Loader_Frame", "start", self.ctk_loader.start_loader)
        self.DICT_WIDGETS.register("CTK_Loader_Frame", "stop", self.ctk_loader.stop_loader)

        logger.debug("Creando icono de bandeja.")
        self.crear_icono_bandeja()

        logger.info("AplicaciÃ³n iniciada correctamente. Entrando en mainloop.")
        self.ventana_creacion_caja.mainloop()

        logger.debug("Mainloop finalizado. Imprimiendo WidgetRegistry.")
        self.DICT_WIDGETS.print_dict()

    def ocultar_a_bandeja(self):
        logger.info("Ocultando ventana principal a bandeja del sistema.")
        self.ventana_creacion_caja.withdraw()

    def mostrar_desde_bandeja(self):
        logger.info("Accion bandeja: mostrar ventana principal.")
        self.ventana_creacion_caja.deiconify()
        self.ventana_creacion_caja.lift()
        self.ventana_creacion_caja.focus_force()
        self.ventana_creacion_caja.state("zoomed")

    def crear_icono_bandeja(self):
        from PIL import Image

        try:
            ruta_icono = os.path.join(ICON_ico())
            logger.debug("Cargando icono de bandeja | ruta=%s", ruta_icono)

            image = Image.open(ruta_icono).resize((64, 64), Image.Resampling.LANCZOS)

            def mostrar_ventana(icon, item):
                self.ventana_creacion_caja.after(0, self.mostrar_desde_bandeja)

            def salir_app(icon, item):
                logger.info("Acción bandeja: salir de la aplicación.")
                icon.stop()
                self.ventana_creacion_caja.after(0, self.ventana_creacion_caja.destroy)

            menu = TrayMenu(
                MenuItem("Mostrar ventana", mostrar_ventana, default=True),
                MenuItem("Salir", salir_app)
            )

            self.tray_icon = TrayIcon("VeriPre", image, menu=menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

            logger.info("Icono de bandeja creado correctamente.")

        except Exception:
            logger.exception("Error al crear icono de bandeja.")

    def frameMenu(self):
        logger.debug("Construyendo frameMenu.")

        self.frame_menu = ttk.Frame(
            self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"),
            bootstyle="primary"
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_menu", self.frame_menu)
        self.frame_menu.grid(row=0, column=0, sticky="NSEW")

        # LOGO
        self.frame_logo = ttk.Frame(self.frame_menu, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_logo", self.frame_logo)
        self.frame_logo.pack(fill="x")

        self.photo_logo = READ_IMG(Logo_info(), 150, 95)

        self.label_image_logo = ttk.Label(
            self.frame_logo,
            image=self.photo_logo,
            bootstyle="inverse-primary"
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "label_image_logo", self.label_image_logo)
        self.label_image_logo.pack(pady=30)

        # BOTONES OPCIONES
        self.frame_botones_opciones = ttk.Frame(self.frame_menu, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_botones_opciones", self.frame_botones_opciones)
        self.frame_botones_opciones.pack(fill="both")

        self.frame_boton_productos = ttk.Frame(self.frame_botones_opciones, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_boton_productos", self.frame_boton_productos)
        self.frame_boton_productos.pack(fill="x")

        ttk.Separator(self.frame_boton_productos, bootstyle="default").pack(fill="x")

        self.photo_productos = READ_IMG(PNG_Productos(), 50, 50)
        self.boton_productos = ttk.Button(
            self.frame_boton_productos,
            command=self.command_button_productos,
            text="Productos",
            image=self.photo_productos,
            compound="left",
            bootstyle="primary"
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "boton_productos", self.boton_productos)
        self.boton_productos.pack(fill="x")

        self.frame_boton_publicidad = ttk.Frame(self.frame_botones_opciones, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_boton_publicidad", self.frame_boton_publicidad)
        self.frame_boton_publicidad.pack(fill="x")

        ttk.Separator(self.frame_boton_publicidad, bootstyle="default").pack(fill="x")

        self.photo_publicidad = READ_IMG(PNG_Publicidad(), 50, 50)
        self.boton_publicidad = ttk.Button(
            self.frame_botones_opciones,
            command=self.command_button_publicidad,
            text="Publicidad",
            image=self.photo_publicidad,
            compound="left",
            bootstyle="primary"
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "boton_publicidad", self.boton_publicidad)
        self.boton_publicidad.pack(fill="x")

        self.frame_botones_config_info = ttk.Frame(self.frame_menu, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_botones_config_info", self.frame_botones_config_info)
        self.frame_botones_config_info.pack(pady=20, side="bottom")

        self.photo_setting = READ_IMG(PNG_Settings(), 20, 20)
        self.boton_setting = ttk.Button(
            self.frame_botones_config_info,
            image=self.photo_setting,
            command=lambda: VentanaManager.abrir_ventana("configuracion", GUI_CONFIG, self.DICT_WIDGETS)
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "boton_setting", self.boton_setting)
        self.boton_setting.pack(side="left")

        self.photo_info = READ_IMG(PNG_Info(), 20, 20)
        self.boton_info = ttk.Button(self.frame_botones_config_info, image=self.photo_info)
        self.DICT_WIDGETS.register("GUI_MAIN", "boton_info", self.boton_info)
        self.boton_info.pack(side="right")

        logger.debug("frameMenu construido correctamente.")

    def frameContenido(self):
        logger.debug("Construyendo frameContenido.")

        self.frame_contenido = ttk.Frame(
            self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"),
            bootstyle="default"
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_contenido", self.frame_contenido)
        self.frame_contenido.grid(row=0, column=1, sticky="NSEW")

        self.frame_barra_superior = ttk.Frame(self.frame_contenido, bootstyle="default")
        self.photo_back = READ_IMG(PNG_Back(), 30, 30)
        self.boton_back = ttk.Button(
            self.frame_barra_superior,
            image=self.photo_back,
            command=self.command_button_volver,
            bootstyle="primary-link"
        )
        self.boton_back.pack(side="left")

        logger.debug("frameContenido construido correctamente.")

    def command_button_productos(self):
        logger.info("NavegaciÃ³n solicitada a secciÃ³n PRODUCTOS.")
        self.VIGIA_FRAME = "BOTON_PRODUCTOS"
        self.selector_seccion()
        self.contenido_productos.cargar_productos_locales_con_loader(force=True, mostrar_sin_datos=True)

    def command_button_publicidad(self):
        logger.info("NavegaciÃ³n solicitada a secciÃ³n PUBLICIDAD.")
        self.VIGIA_FRAME = "BOTON_PUBLICIDAD"
        self.selector_seccion()

    def command_button_volver(self):
        logger.info("NavegaciÃ³n: volver a secciÃ³n anterior.")
        try:
            self.VIGIA_VOLVER.pop(-1)
            logger.debug("Historial luego de primer pop: %s", self.VIGIA_VOLVER)

            self.VIGIA_FRAME = self.VIGIA_VOLVER.pop(-1)
            logger.debug("Frame recuperado al volver: %s", self.VIGIA_FRAME)
            logger.debug("Historial luego de segundo pop: %s", self.VIGIA_VOLVER)

            self.selector_seccion()

        except Exception:
            logger.exception("Error al volver de secciÃ³n.")
            self.VIGIA_FRAME = "INICIO"
            self.VIGIA_VOLVER = ["INICIO"]
            self.selector_seccion()

    """
    def command_button_configuracion(self):
        if not self.DICT_WIDGETS.get_widget("VARIABLES_GLOBALES", "top_level_configuracion_abierta"):
            self.DICT_WIDGETS.register("VARIABLES_GLOBALES","top_level_configuracion_abierta", True)
            self.top_level_configuracion = GUI_CONFIG(self.DICT_WIDGETS)
    """

    def selector_seccion(self):
        logger.debug(
            "Seleccionando secciÃ³n | VIGIA_FRAME=%s | historial_actual=%s",
            self.VIGIA_FRAME,
            self.VIGIA_VOLVER
        )

        if self.VIGIA_FRAME == "INICIO":
            self.VIGIA_VOLVER = ["INICIO"]
            self.frame_seccion_inicio.pack(fill="both", expand=True)
            self.frame_seccion_productos.pack_forget()
            self.frame_seccion_publicidad.pack_forget()
            self.frame_barra_superior.pack_forget()

        elif self.VIGIA_FRAME == "BOTON_PRODUCTOS":
            self.frame_seccion_publicidad.pack_forget()
            self.frame_seccion_inicio.pack_forget()
            self.frame_barra_superior.pack(fill="x")
            self.frame_seccion_productos.pack(fill="both", expand=True)

        elif self.VIGIA_FRAME == "BOTON_PUBLICIDAD":
            self.frame_seccion_productos.pack_forget()
            self.frame_seccion_inicio.pack_forget()
            self.frame_barra_superior.pack(fill="x")
            self.frame_seccion_publicidad.pack(fill="both", expand=True)

        if self.VIGIA_VOLVER[-1] != self.VIGIA_FRAME and self.VIGIA_FRAME not in self.VIGIA_VOLVER:
            self.VIGIA_VOLVER.append(self.VIGIA_FRAME)

        logger.debug("SecciÃ³n aplicada | historial_resultante=%s", self.VIGIA_VOLVER)

    def seccion_inicio(self):
        logger.debug("Creando widgets de secciÃ³n INICIO.")

        self.frame_seccion_inicio = ttk.Frame(self.frame_contenido, bootstyle="default")
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_inicio", self.frame_seccion_inicio)

        self.label_inicio = ttk.Label(self.frame_seccion_inicio, text="BIENVENIDOS")
        self.label_inicio.pack(pady=20)

    def seccion_productos(self):
        logger.debug("Creando widgets de secciÃ³n PRODUCTOS.")

        self.frame_seccion_productos = ttk.Frame(self.frame_contenido, bootstyle="default")
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_productos", self.frame_seccion_productos)

        self.contenido_productos = ContenidoProducto(self.DICT_WIDGETS)
        logger.debug("ContenidoProducto inicializado correctamente.")

    def seccion_publicidad(self):
        logger.debug("Creando widgets de secciÃ³n PUBLICIDAD.")

        self.frame_seccion_publicidad = ttk.Frame(self.frame_contenido, bootstyle="default")
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_publicidad", self.frame_seccion_publicidad)

        self.contenido_publicidad = ContenidoPublicidad(self.DICT_WIDGETS)
        logger.debug("ContenidoPublicidad inicializado correctamente.")

    def CONEXIONES_DBA(self):
        ruta_db = os.path.join(os.path.dirname(__file__), "..", "db", "veripre.db")
        logger.info("Inicializando conexiones de base de datos | sqlite_path=%s", ruta_db)

        self.DICT_WIDGETS.register("DATABASE", "CONEXIONDBA", SQLiteDB(ruta_db))
        self.CONEXIONDBA = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA")
        self.CONEXIONDBA.crear_tablas()

        try:
            inserccion_sql = """
            SELECT * FROM VERIPRE_CONEXION
            """
            logger.debug("Consultando configuraciÃ³n de conexiÃ³n externa en SQLite.")
            datos_conexion = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA").ejecutar_consulta(inserccion_sql)

            if datos_conexion is not None and len(datos_conexion) > 0:
                datos_conexion = datos_conexion[0]
                conexion = {
                    "user": datos_conexion[1],
                    "password": datos_conexion[2],
                    "dsn": datos_conexion[0]
                }

                logger.info(
                    "ConfiguraciÃ³n externa encontrada | dsn=%s | user=%s",
                    conexion["dsn"],
                    conexion["user"]
                )

                self.DICT_WIDGETS.register("DATABASE", "CONEXIONDBA_SYBASE", ConexionSybase(**conexion))
                self.DICT_WIDGETS.register("DATABASE", "CONEXION_INFORHARD", True)

                logger.info("ConexiÃ³n externa Sybase registrada correctamente.")
            else:
                self.DICT_WIDGETS.register("DATABASE", "CONEXION_INFORHARD", False)
                logger.warning("No se encontraron datos de conexiÃ³n externa en VERIPRE_CONEXION.")

        except Exception:
            self.DICT_WIDGETS.register("DATABASE", "CONEXION_INFORHARD", False)
            logger.exception("Sin conexiÃ³n externa o error al configurar ConexionSybase.")

    def VARIABLES_GLOBALES(self):
        logger.debug("Registrando variables globales.")
        self.DICT_WIDGETS.register("VARIABLES_GLOBALES", "top_level_configuracion_abierta", False)
