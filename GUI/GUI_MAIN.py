import os
import threading
import json
import locale
import ttkbootstrap as ttk
from ASSETS.path_img import *
from pystray import Icon as TrayIcon, Menu as TrayMenu, MenuItem
from FUNC.ctk_components.ctk_components import CTkLoader
from FUNC.create_widget import WidgetRegistry
from FUNC.config_json import *
#from FUNC.config_manager_json import ConfigManager
from FUNC.windows_manager import VentanaManager
from GUI.CONTENIDO_PRODUCTO import ContenidoProducto
from GUI.CONTENIDO_PUBLICIDAD import ContenidoPublicidad
from GUI.GUI_CONFIG import GUI_CONFIG
from DB.database import SQLiteDB
from DB.database_sybase import ConexionSybase

import socket
import sys
from tkinter import messagebox

def comprobar_instancia_unica(puerto=55665):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', puerto))
        return sock  # mantiene el socket abierto
    except OSError:
        messagebox.showinfo(
            "Aplicación ya en ejecución",
            "La aplicación ya está abierta.\nRevisá la bandeja del sistema (icono cerca del reloj)."
        )
        sys.exit(0)

class GUI_MAIN:
    def __init__(self, version):
        self.socket_lock = comprobar_instancia_unica()  # ← ¡esto es clave!
        self.DICT_WIDGETS = WidgetRegistry()
        self.VIGIA_FRAME = "INICIO"
        self.VIGIA_VOLVER = [self.VIGIA_FRAME]

        self.config_data = cargar_config()
        self.DICT_WIDGETS.register("CONFIG", "config_json", self.config_data)
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain')  # o 'es_AR.UTF-8'

        self.ventana_creacion_caja = ttk.Window(themename="flatly", iconphoto=ICON())
        self.ventana_creacion_caja.title(f"VeriPre_Connector, V.{version}")
        self.ventana_creacion_caja.state('zoomed')

        self.ventana_creacion_caja.grid_columnconfigure(0, minsize=250, weight=0)
        self.ventana_creacion_caja.grid_columnconfigure(1, weight=1)
        self.ventana_creacion_caja.rowconfigure(0, weight=1)

        self.ventana_creacion_caja.protocol("WM_DELETE_WINDOW", self.ocultar_a_bandeja)

        self.DICT_WIDGETS.register("GUI_MAIN","ventana_creacion_caja", self.ventana_creacion_caja)
        self.CONEXIONES_DBA()
        self.VARIABLES_GLOBALES()

        self.frameMenu()
        self.frameContenido()
        self.seccion_inicio()
        self.seccion_productos()
        self.seccion_publicidad()
        self.selector_seccion()

        self.ctk_loader = CTkLoader(self.ventana_creacion_caja, opacity=0.8, width=40, height=40)
        self.DICT_WIDGETS.register("CTK_Loader_Frame","start", self.ctk_loader.start_loader)
        self.DICT_WIDGETS.register("CTK_Loader_Frame","stop", self.ctk_loader.stop_loader)

        self.crear_icono_bandeja()

        self.ventana_creacion_caja.mainloop()
        self.DICT_WIDGETS.print_dict()

    def ocultar_a_bandeja(self):
        self.ventana_creacion_caja.withdraw()

    def crear_icono_bandeja(self):
        from PIL import Image

        ruta_icono = os.path.join(ICON_ico())
        image = Image.open(ruta_icono).resize((64, 64), Image.Resampling.LANCZOS)

        def mostrar_ventana(icon, item):
            self.ventana_creacion_caja.deiconify()
            self.ventana_creacion_caja.state('zoomed')

        def salir_app(icon, item):
            icon.stop()
            self.ventana_creacion_caja.destroy()

        menu = TrayMenu(
            MenuItem('Mostrar ventana', mostrar_ventana),
            MenuItem('Salir', salir_app)
        )

        self.tray_icon = TrayIcon("VeriPre", image, menu=menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()



    def frameMenu(self):
        # Crear y configurar el marco del menú
        self.frame_menu = ttk.Frame(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"), bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_menu", self.frame_menu)
        self.frame_menu.grid(row=0, column=0, sticky="NSEW")  # Ocupar toda la altura de la ventana
        
        #/////////////////////////////////// LOGO ///////////////////////////////////
        self.frame_logo = ttk.Frame(self.frame_menu, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_logo", self.frame_logo)
        self.frame_logo.pack(fill="x")

        self.photo_logo = READ_IMG(Logo_info(), 150, 95)
        # Crear el widget de etiqueta
        self.label_image_logo = ttk.Label(self.frame_logo, image=self.photo_logo, bootstyle="inverse-primary")
        self.DICT_WIDGETS.register("GUI_MAIN","label_image_logo", self.label_image_logo)
        self.label_image_logo.pack(pady=30)
        
        #/////////////////////////////////// BOTONES OPCIONES ///////////////////////////////////
        
        
        self.frame_botones_opciones = ttk.Frame(self.frame_menu, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_botones_opciones", self.frame_botones_opciones)
        self.frame_botones_opciones.pack(fill="both")
        
        self.frame_boton_productos = ttk.Frame(self.frame_botones_opciones, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_boton_productos", self.frame_boton_productos)
        self.frame_boton_productos.pack(fill="x")
        ttk.Separator(self.frame_boton_productos, bootstyle="default").pack(fill="x")
        self.photo_productos = READ_IMG(PNG_Productos(), 50, 50)
        self.boton_productos = ttk.Button(self.frame_boton_productos, command=self.command_button_productos, text="Productos", image=self.photo_productos, compound="left", bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN","boton_productos", self.boton_productos)
        self.boton_productos.pack(fill="x")
        
        self.frame_boton_publicidad = ttk.Frame(self.frame_botones_opciones, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_boton_publicidad", self.frame_boton_publicidad)
        self.frame_boton_publicidad.pack(fill="x")
        ttk.Separator(self.frame_boton_publicidad, bootstyle="default").pack(fill="x")
        self.photo_publicidad = READ_IMG(PNG_Publicidad(), 50, 50)
        self.boton_publicidad = ttk.Button(self.frame_botones_opciones, command=self.command_button_publicidad, text="Publicidad", image=self.photo_publicidad, compound="left", bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN","boton_publicidad", self.boton_publicidad)
        self.boton_publicidad.pack(fill="x")
        
        self.frame_botones_config_info = ttk.Frame(self.frame_menu, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_botones_config_info", self.frame_botones_config_info)
        self.frame_botones_config_info.pack(pady=20, side="bottom")
        
        self.photo_setting = READ_IMG(PNG_Settings(), 20, 20)
        self.boton_setting = ttk.Button(self.frame_botones_config_info, image=self.photo_setting, 
                                command=lambda: VentanaManager.abrir_ventana("configuracion", GUI_CONFIG, self.DICT_WIDGETS))
        self.DICT_WIDGETS.register("GUI_MAIN","boton_setting", self.boton_setting)
        self.boton_setting.pack(side="left")
        
        self.photo_info = READ_IMG(PNG_Info(), 20, 20)
        self.boton_info = ttk.Button(self.frame_botones_config_info, image=self.photo_info)
        self.DICT_WIDGETS.register("GUI_MAIN","boton_info", self.boton_info)
        self.boton_info.pack(side="right")
        
    def frameContenido(self):
        # Crear y configurar el marco del contenido
        self.frame_contenido = ttk.Frame(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"), bootstyle="default")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_contenido", self.frame_contenido)
        self.frame_contenido.grid(row=0, column=1, sticky="NSEW")  # Ocupar todo el espacio restantes
        self.frame_barra_superior = ttk.Frame(self.frame_contenido, bootstyle="default")
        self.photo_back = READ_IMG(PNG_Back(), 30, 30)
        self.boton_back = ttk.Button(self.frame_barra_superior, image=self.photo_back, command=self.command_button_volver ,bootstyle="primary-link")
        self.boton_back.pack(side="left")
        
    def command_button_productos(self):
        self.VIGIA_FRAME = "BOTON_PRODUCTOS"
        self.selector_seccion()
        
    def command_button_publicidad(self):
        self.VIGIA_FRAME = "BOTON_PUBLICIDAD"
        self.selector_seccion()
        
    def command_button_volver(self):
        self.VIGIA_VOLVER.pop(-1)
        print(self.VIGIA_VOLVER)
        self.VIGIA_FRAME = self.VIGIA_VOLVER.pop(-1)
        print(self.VIGIA_VOLVER)
        self.selector_seccion()
        
    """def command_button_configuracion(self):
        if not self.DICT_WIDGETS.get_widget("VARIABLES_GLOBALES", "top_level_configuracion_abierta"):
            self.DICT_WIDGETS.register("VARIABLES_GLOBALES","top_level_configuracion_abierta", True)
            self.top_level_configuracion = GUI_CONFIG(self.DICT_WIDGETS)"""
        
    def selector_seccion(self):
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
        print(self.VIGIA_VOLVER)
            
            
    def seccion_inicio(self):
        self.frame_seccion_inicio = ttk.Frame(self.frame_contenido, bootstyle="default")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_seccion_inicio", self.frame_seccion_inicio)
        
        self.label_inicio = ttk.Label(self.frame_seccion_inicio, text="BIENVENIDOS")
        self.label_inicio.pack(pady=20)
        
    def seccion_productos(self):
        self.frame_seccion_productos = ttk.Frame(self.frame_contenido, bootstyle="default")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_seccion_productos", self.frame_seccion_productos)
        
        self.contenido_productos = ContenidoProducto(self.DICT_WIDGETS)
        
    def seccion_publicidad(self):
        self.frame_seccion_publicidad = ttk.Frame(self.frame_contenido, bootstyle="default")
        self.DICT_WIDGETS.register("GUI_MAIN","frame_seccion_publicidad", self.frame_seccion_publicidad)
        
        self.contenido_publicidad = ContenidoPublicidad(self.DICT_WIDGETS)
        

    def CONEXIONES_DBA(self):

        ruta_db = os.path.join(os.path.dirname(__file__), "..", "db", "veripre.db")
        print(ruta_db)  # Imprimirá "db/veripre.db" si está en el mismo directorio del script

        self.DICT_WIDGETS.register("DATABASE", "CONEXIONDBA", SQLiteDB(ruta_db))
        self.CONEXIONDBA = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA")
        self.CONEXIONDBA.crear_tablas()
        try: 
            inserccion_sql = """
            SELECT * FROM VERIPRE_CONEXION
            """
            datos_conexion = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA").ejecutar_consulta(inserccion_sql)
            if not datos_conexion == None:
                datos_conexion = datos_conexion[0]
                conexion = {
                    "user": datos_conexion[1],
                    "password": datos_conexion[2],
                    "dsn": datos_conexion[0]
                }
                self.DICT_WIDGETS.register("DATABASE","CONEXIONDBA_SYBASE", ConexionSybase(**conexion))
                self.DICT_WIDGETS.register("DATABASE","CONEXION_INFORHARD", True)
        except Exception as e:
            print(e)
            print("Sin conexión external")
    
    def VARIABLES_GLOBALES(self):
        self.DICT_WIDGETS.register("VARIABLES_GLOBALES","top_level_configuracion_abierta", False)