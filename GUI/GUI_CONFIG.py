import os
import sys
import threading
import time
from tkinter import BooleanVar, StringVar, filedialog, messagebox, simpledialog
import ttkbootstrap as ttk
from FUNC.windows_manager import VentanaManager 
from DB.database_sybase import ConexionSybase, dsn_configurados
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from ASSETS.path_img import *
from core.network.api_client import DispositivoAPIClient
from core.network.dispositivo_sender import DispositivoSender
from FUNC.config_json import guardar_config
from core.dao.api_key_dao import ApiKeyDAO
from core.dao.conexion_dao import ConexionDAO
from core.dao.dispositivos_dao import DispositivosDAO
from core.services.productos_sync_service import ProductosSyncService


class GUI_CONFIG:
    def __init__(self, DICT_WIDGETS):
        self.DICT_WIDGETS = DICT_WIDGETS
        self.datos_dispositivos = {}
        self.sqlite_db = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA")
        self.dispositivos_dao = DispositivosDAO(self.sqlite_db)
        self.conexion_dao = ConexionDAO(self.sqlite_db)
        self.api_key_dao = ApiKeyDAO(self.sqlite_db)
        self.top_level_configuracion = ttk.Toplevel(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        self.DICT_WIDGETS.register("GUI_CONFIG","top_level_configuracion", self.top_level_configuracion)
        self.top_level_configuracion.protocol("WM_DELETE_WINDOW", self.cierre_top_level_configuracion)
        self.top_level_configuracion.transient(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        #self.top_level_configuracion.grab_set()
        self.top_level_configuracion.title("VeriPre_Connector - Configuración")
        self.top_level_configuracion.geometry("1120x760")
        self.top_level_configuracion.minsize(1020, 680)
        self.top_level_configuracion.place_window_center()
        
        self.notebook_widget_configuracion = ttk.Notebook(self.top_level_configuracion, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_CONFIG","notebook_widget_configuracion", self.notebook_widget_configuracion)
        self.creacion_frame_notebook_dispositivos()
        self.creacion_frame_notebook_fuente_datos()
        self.creacion_frame_notebook_config_datos()
        self.creacion_frame_notebook_go_upc()
        
        self.notebook_widget_configuracion.add(self.frame_notebook_dispositivos, text="Dispositivos", padding=10)
        self.notebook_widget_configuracion.add(self.frame_notebook_fuente_datos, text="Fuente de Datos", padding=10)
        self.notebook_widget_configuracion.add(self.frame_notebook_config_datos, text="Configuración de Datos", padding=10)
        self.notebook_widget_configuracion.add(self.frame_notebook_go_upc, text="Conexión GO-UPC", padding=10)
        
        self.notebook_widget_configuracion.pack(side="top", expand=True, fill="both")
        
        
#///////////////////////////////////////////////////// NOTEBOOK DISPOSITIVOS /////////////////////////////////////////////////////
        
    def creacion_frame_notebook_dispositivos(self):
        self.frame_notebook_dispositivos = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_dispositivos.pack(fill="both", expand=True)
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_notebook_dispositivos", self.frame_notebook_dispositivos)
        
        
        self.labelframe_opciones = ttk.Labelframe(self.frame_notebook_dispositivos, text="Opciones", bootstyle="primary")
        self.labelframe_opciones.pack(fill="x", padx=10, pady=(10, 6))
        self.DICT_WIDGETS.register("GUI_CONFIG","labelframe_opciones", self.labelframe_opciones)
        self.creacion_contenido_labelframe_opciones()
        
        
        self.labelframe_datos_dispositivos = ttk.Labelframe(self.frame_notebook_dispositivos, text="Datos de Dispositivo", bootstyle="primary")
        self.labelframe_datos_dispositivos.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.DICT_WIDGETS.register("GUI_CONFIG","labelframe_datos_dispositivos", self.labelframe_datos_dispositivos)
        self.creacion_labelframe_datos_dispositivos()       
        
        
    def creacion_contenido_labelframe_opciones(self):
        self.frame_contenedor_combobox_dispositivos = ttk.Frame(self.labelframe_opciones)
        self.frame_contenedor_combobox_dispositivos.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=8)
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_contenedor_combobox_dispositivos", self.frame_contenedor_combobox_dispositivos)
        self.creacion_contenido_frame_contenedor_combobox_dispositivos()
        
        self.frame_contenedor_botones = ttk.Frame(self.labelframe_opciones)
        self.frame_contenedor_botones.grid(row=0, column=1, sticky="e", padx=(8, 12), pady=8)
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_contenedor_botones", self.frame_contenedor_botones)
        self.creacion_contenido_frame_contenedor_botones()
        self.labelframe_opciones.columnconfigure(0, weight=1)
        
        
    def creacion_contenido_frame_contenedor_botones(self):
        # Imágenes de los botones
        self.img_agregar = READ_IMG(PNG_Add(), 25, 25)
        self.img_guardar = READ_IMG(PNG_Save(), 25, 25)
        self.img_editar = READ_IMG(PNG_Edit(), 25, 25)
        self.img_eliminar = READ_IMG(PNG_Delete(), 25, 25)

        # Creación de botones
        self.button_agregar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_agregar, command=self.command_button_agregar, compound="center" ,bootstyle="outline", width=4)
        ToolTip(self.button_agregar, text="Agregar Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_agregar", self.button_agregar)
        self.button_editar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_editar, command=self.command_button_editar_dispositivo, compound="center" ,bootstyle="outline", width=4, state="disable")
        ToolTip(self.button_editar, text="Editar datos de Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_editar", self.button_editar)
        self.button_eliminar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_eliminar, command=self.command_button_eliminar, compound="center" ,bootstyle="outline", width=4, state="disable")
        ToolTip(self.button_eliminar, text="Eliminar Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_eliminar", self.button_eliminar)
        self.button_guardar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_guardar, compound="center" ,bootstyle="outline", width=4)
        ToolTip(self.button_guardar, text="Guardar configuración de Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_guardar", self.button_guardar)
        self.button_estado = ttk.Button(
            self.frame_contenedor_botones,
            text="Estado",
            command=self.command_button_estado_dispositivo,
            bootstyle="outline",
            width=10,
            state="disable",
        )
        ToolTip(self.button_estado, text="Consultar estado del dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_estado", self.button_estado)
        self.button_player = ttk.Button(
            self.frame_contenedor_botones,
            text="Player",
            command=self.command_button_configuracion_player,
            bootstyle="outline",
            width=10,
            state="disable",
        )
        ToolTip(self.button_player, text="Configurar pantalla y parametros del player")
        self.DICT_WIDGETS.register("GUI_CONFIG", "button_player", self.button_player)

        # Posicionamiento con grid (alineados al centro)
        self.frame_contenedor_botones.columnconfigure(0, weight=1)
        self.frame_contenedor_botones.columnconfigure(1, weight=1)
        self.frame_contenedor_botones.columnconfigure(2, weight=1)
        self.frame_contenedor_botones.columnconfigure(3, weight=1)
        self.frame_contenedor_botones.columnconfigure(4, weight=1)
        self.frame_contenedor_botones.columnconfigure(5, weight=1)

        self.button_agregar.grid(row=0, column=0, padx=3)
        self.button_editar.grid(row=0, column=1, padx=3)
        self.button_eliminar.grid(row=0, column=2, padx=3)
        self.button_guardar.grid(row=0, column=3, padx=3)
        self.button_estado.grid(row=0, column=4, padx=(10, 3))
        self.button_player.grid(row=0, column=5, padx=(3, 1))
        
    def creacion_contenido_frame_contenedor_combobox_dispositivos(self):
        self.frame_label_combobox_dispositivos = ttk.Label(
            self.frame_contenedor_combobox_dispositivos,
            text="Seleccione su dispositivo:",
            font=("Segoe UI", 10, "bold"),
        )
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_label_combobox_dispositivos", self.frame_label_combobox_dispositivos)
        self.frame_label_combobox_dispositivos.pack(side="left", padx=(0, 10))
        
        self.combobox_dispositivos = ttk.Combobox(self.frame_contenedor_combobox_dispositivos, values=self.actualizar_datos_combobox(), state="readonly", width=42)
        self.combobox_dispositivos.bind("<<ComboboxSelected>>", self.seleccion_dispositivo)
        self.DICT_WIDGETS.register("GUI_CONFIG","combobox_dispositivos", self.combobox_dispositivos)
        self.combobox_dispositivos.pack(side="right", fill="x", expand=True)
        
    def creacion_contenido_toplevel_button_agregar(self):
        self.creacion_labelframe_nuevo_dispositivo_button_agregar()
        self.creacion_labelframe_datos_button_agregar()
        self.button_agregar_dispositivo = ttk.Button(self.toplevel_button_agregar, text="Agregar", command=self.command_button_agregar_dispositivo)
        self.button_agregar_dispositivo.pack(pady=(0,5))
        
    def creacion_labelframe_nuevo_dispositivo_button_agregar(self):
        self.labelframe_nuevo_dispositivo_button_agregar = ttk.Labelframe(self.toplevel_button_agregar, text="Nuevo dispositivo", bootstyle="primary")
        self.labelframe_nuevo_dispositivo_button_agregar.pack(fill="x", padx=5)

        self.label_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos = ttk.Label(
            self.labelframe_nuevo_dispositivo_button_agregar, text="Nombre del equipo:"
        )
        self.label_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.pack(side="left", pady=10, padx=10)

        self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos = ttk.Entry(self.labelframe_nuevo_dispositivo_button_agregar)
        self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.pack(side="right", pady=10, padx=(0,10), fill="x", expand=True)
        
    def creacion_labelframe_datos_button_agregar(self):
        self.labelframe_datos_button_agregar = ttk.Labelframe(self.toplevel_button_agregar, text="Nuevo dispositivo", bootstyle="primary")
        self.labelframe_datos_button_agregar.pack(fill="both", expand=True, padx=5, pady=5)
        
        # DirecciÃ³n IP/RED
        self.label_direccion_ip = ttk.Label(self.labelframe_datos_button_agregar, text="DirecciÃ³n IP/RED:")
        self.entry_direccion_ip = ttk.Entry(self.labelframe_datos_button_agregar)

        # Puerto
        self.label_puerto = ttk.Label(self.labelframe_datos_button_agregar, text="PUERTO:")
        self.entry_puerto = ttk.Entry(self.labelframe_datos_button_agregar)

        # Comentario (mÃ¡s grande)
        self.label_comentario = ttk.Label(self.labelframe_datos_button_agregar, text="COMENTARIO:")
        self.text_comentario = ttk.Text(self.labelframe_datos_button_agregar, height=4, width=30)  # Ajusta tamaÃ±o

        # Posicionar con grid
        self.label_direccion_ip.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.entry_direccion_ip.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        self.label_puerto.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.entry_puerto.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        self.label_comentario.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.text_comentario.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        # Expandir entradas en el contenedor
        self.labelframe_datos_button_agregar.columnconfigure(1, weight=1)
        
    def creacion_labelframe_datos_dispositivos(self):
        self.frame_contenedor_labelframe_datos_dispositivo = ttk.Frame(self.labelframe_datos_dispositivos, padding=20)

        self.label_nombre_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="Seleccione un dispositivo",
            font=("Segoe UI", 18, "bold"),
        )
        self.label_nombre_contenido_labelframe_opciones.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))

        self.label_direccion_ip_izq_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="Dirección IP / Red",
            font=("Segoe UI", 11, "bold"),
        )
        self.label_direccion_ip_izq_contenido_labelframe_opciones.grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.label_direccion_ip_der_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="-",
            font=("Segoe UI", 11),
            bootstyle="secondary",
        )
        self.label_direccion_ip_der_contenido_labelframe_opciones.grid(row=1, column=1, sticky="ew", pady=(0, 6))

        self.label_puerto_izq_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="Puerto",
            font=("Segoe UI", 11, "bold"),
        )
        self.label_puerto_izq_contenido_labelframe_opciones.grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.label_puerto_der_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="-",
            font=("Segoe UI", 11),
            bootstyle="secondary",
        )
        self.label_puerto_der_contenido_labelframe_opciones.grid(row=2, column=1, sticky="ew", pady=(0, 6))

        self.label_comentario_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="Comentario",
            font=("Segoe UI", 11, "bold"),
        )
        self.label_comentario_contenido_labelframe_opciones.grid(row=3, column=0, sticky="nw", pady=(8, 6))

        self.text_comentario_contenido_labelframe_opciones = ttk.Text(
            self.frame_contenedor_labelframe_datos_dispositivo,
            height=8,
            wrap="word",
        )
        self.text_comentario_contenido_labelframe_opciones.insert("1.0", "Sin comentario")
        self.text_comentario_contenido_labelframe_opciones.config(state="disabled")
        self.text_comentario_contenido_labelframe_opciones.grid(row=3, column=1, sticky="nsew", pady=(8, 6))

        self.frame_contenedor_labelframe_datos_dispositivo.columnconfigure(1, weight=1)
        self.frame_contenedor_labelframe_datos_dispositivo.rowconfigure(3, weight=1)

#///////////////////////////////////////////////////// NOTEBOOK FUENTE DE DATOS /////////////////////////////////////////////////////

    def creacion_frame_notebook_fuente_datos(self):
        self.frame_notebook_fuente_datos = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_fuente_datos.pack(fill="both", expand=True)  # CorrecciÃ³n aquÃ­
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_notebook_fuente_datos", self.frame_notebook_fuente_datos)

        self.labelframe_conexion_fuente_datos = ttk.Labelframe(self.frame_notebook_fuente_datos, text="Conexiones disponibles: ", bootstyle="primary")
        self.labelframe_conexion_fuente_datos.pack(fill="x")
        
        lista_conexiones_disponibles = ["ConexiÃ³n ODBC"]
        self.label_tipo_conexion = ttk.Label(self.labelframe_conexion_fuente_datos, text="Tipos de Conexiones:")
        self.label_tipo_conexion.pack(side="left", padx=(30,15))
        self.combobox_lista_fuente_datos = ttk.Combobox(self.labelframe_conexion_fuente_datos, values=lista_conexiones_disponibles, state="readonly")
        self.combobox_lista_fuente_datos.pack(side="right", fill="x", expand=True, padx=(5,10), pady=(0,5))
        self.combobox_lista_fuente_datos.bind("<<ComboboxSelected>>", self.bind_combobox_lista_fuente_datos)
        
        
        self.labelframe_datos_de_conexion_fuente_datos = ttk.Labelframe(self.frame_notebook_fuente_datos, text="Datos de ConexiÃ³n: ", bootstyle="primary")
        self.labelframe_datos_de_conexion_fuente_datos.pack(fill="both", expand=True, pady=10)

        
        
        
        
    def bind_combobox_lista_fuente_datos(self, event):
        if self.combobox_lista_fuente_datos.get() == "ConexiÃ³n ODBC":
            self.mostrar_widgets_ODBC()
            self.obtener_datos_conexion_odbc()
        
        
        
        
    def mostrar_widgets_ODBC(self):
        self.frame_contenido_opcion_odbc = ttk.Frame(self.labelframe_datos_de_conexion_fuente_datos)
        self.frame_contenido_opcion_odbc.pack(fill="both", expand=True, padx=(50,55), pady=50)
        self.frame_odbc = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_odbc.pack(fill="x", pady=5)

        self.label_odbc = ttk.Label(self.frame_odbc, text="ConexiÃ³n ODBC:")
        self.label_odbc.pack(side="left", padx=5)

        self.combobox_odbc = ttk.Combobox(self.frame_odbc, values=self.obtener_listaDSN(), state="readonly")
        self.combobox_odbc.pack(side="right", fill="x", expand=True)

        # ðŸ”¹ Frame para User ID
        self.frame_user = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_user.pack(fill="x", pady=5)

        self.label_user = ttk.Label(self.frame_user, text="User ID:")
        self.label_user.pack(side="left", padx=5)

        self.entry_user = ttk.Entry(self.frame_user)
        self.entry_user.pack(side="right", fill="x", expand=True)

        # ðŸ”¹ Frame para Password
        self.frame_password = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_password.pack(fill="x", pady=5)

        self.label_password = ttk.Label(self.frame_password, text="Password:")
        self.label_password.pack(side="left", padx=5)

        self.entry_password = ttk.Entry(self.frame_password, show="*")  # Ocultar texto
        self.entry_password.pack(side="right", fill="x", expand=True)
        
        
        self.frame_checkbox = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_checkbox.pack(fill="x", pady=5)

        self.checkbox_var = ttk.BooleanVar()  # Variable para almacenar el estado del checkbox
        self.checkbox = ttk.Checkbutton(self.frame_checkbox, text="ConexiÃ³n a DBA de Inforhard Sistemas", variable=self.checkbox_var)
        self.checkbox.pack(side="left", padx=5)
        
        self.button_agregar_datos_de_conexion = ttk.Button(self.labelframe_datos_de_conexion_fuente_datos, text="Agregar", command=self.command_button_agregar_datos_de_conexion)
        self.button_agregar_datos_de_conexion.pack(pady=(0,5), side="bottom")
    
    def validar_campos(self):
        """Verifica que los campos no estÃ©n vacÃ­os."""
        campos = {
            "Nuevo dispositivo": self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.get().strip(),
            "DirecciÃ³n IP/RED": self.entry_direccion_ip.get().strip(),
            "PUERTO": self.entry_puerto.get().strip(),
            "COMENTARIO": self.text_comentario.get("1.0", "end").strip()  # Obtener texto desde Text
        }

        for campo, valor in campos.items():
            if not valor:  # Si el campo estÃ¡ vacÃ­o
                messagebox.showwarning("Campo vacÃ­o", f"El campo '{campo}' no puede estar vacÃ­o.")
                return False

        return True  # Si todos los campos tienen datos       
    
    
    def obtener_listaDSN(self):
        datos = dsn_configurados()
        dsnLIST = []
        for dsnNAME, dsnDRIVER in datos.items():
            cadena = dsnNAME.decode('utf-8')
            dsnLIST.append(cadena)
        for dsnNAME in dsnLIST:
            print(dsnNAME) 
        return dsnLIST
    
#///////////////////////////////////////////////////// NOTEBOOK CONFIGURACIÃ“N DE DATOS /////////////////////////////////////////////////////

    def creacion_frame_notebook_config_datos(self):
        self.frame_notebook_config_datos = ttk.Labelframe(self.notebook_widget_configuracion, text="Configurar Datos")
        self.frame_notebook_config_datos.pack(fill="both", expand=True)
        
        frame_logo = ttk.LabelFrame(self.frame_notebook_config_datos, text="Logo Principal", padding=10)
        frame_logo.pack(fill="x", padx=10, pady=10)

        self.label_logo_preview = ttk.Label(frame_logo, width=200)
        self.label_logo_preview.pack(fill="both", expand=True, padx=10, pady=10)
        self.label_logo_preview.config(anchor="center")
        self.label_logo_preview.config(style="preview.TLabel")



        self._mostrar_logo_actual()
        # Contenedor para los botones en lÃ­nea
        frame_botones_logo = ttk.Frame(frame_logo)
        frame_botones_logo.pack(fill="x", pady=5)

        # BotÃ³n izquierda
        ttk.Button(frame_botones_logo, text="Seleccionar Imagen", command=self._seleccionar_logo).pack(side="left", padx=(0, 5))

        # BotÃ³n derecha
        ttk.Button(frame_botones_logo, text="Enviar Logo a Dispositivos", command=self._enviar_logo_a_dispositivos).pack(side="right", padx=(5, 0))


        
        
        self.label_info_notebook_config_datos = ttk.Label(self.frame_notebook_config_datos)
        self.label_info_notebook_config_datos.pack(fill="x", padx=5, pady=5)
        
        
        
        datos_conexion = self.conexion_dao.obtener_todas()
        self.creacion_frame_config_datos_INFORHARD()
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        valor_configurado = config.get("sincronizacion_automatica", True)
        self.auto_sync_var = BooleanVar(value=valor_configurado)
        # Crear checkbox de sincronizaciÃ³n automÃ¡tica
        self.checkbox_auto_sync = ttk.Checkbutton(
            self.frame_notebook_config_datos,
            text="SincronizaciÃ³n automÃ¡tica de productos",
            variable=self.auto_sync_var,
            command=self.actualizar_config_sincronizacion_automatica
        )
        self.checkbox_auto_sync.pack(pady=15)

        valor_envio_auto = bool(config.get("envio_automatico_novedades", False)) and bool(valor_configurado)
        self.auto_send_news_var = BooleanVar(value=valor_envio_auto)
        self.checkbox_auto_send_news = ttk.Checkbutton(
            self.frame_notebook_config_datos,
            text="Envio automatico de novedades al detectar cambios",
            variable=self.auto_send_news_var,
            command=self.actualizar_config_envio_automatico_novedades,
        )
        self.checkbox_auto_send_news.pack(pady=(0, 15))
        self._actualizar_estado_checkbox_envio_auto()

        self.keep_video_audio_var = BooleanVar(
            value=bool(config.get("mantener_audio_publicidades", False))
        )
        self.checkbox_keep_video_audio = ttk.Checkbutton(
            self.frame_notebook_config_datos,
            text="Mantener audio en videos de publicidades (modo prueba)",
            variable=self.keep_video_audio_var,
            command=self.actualizar_config_audio_publicidades,
        )
        self.checkbox_keep_video_audio.pack(pady=(0, 15))

        # Registrar en el diccionario global
        self.DICT_WIDGETS.register("VARIABLES_GLOBALES", "sincronizacion_automatica", self.auto_sync_var)
        self.DICT_WIDGETS.register("VARIABLES_GLOBALES", "envio_automatico_novedades", self.auto_send_news_var)
        self.DICT_WIDGETS.register("VARIABLES_GLOBALES", "mantener_audio_publicidades", self.keep_video_audio_var)
        
        print(datos_conexion)

        if datos_conexion:  # Verifica si la lista NO estÃ¡ vacÃ­a
            datos_conexion = datos_conexion[0]
            if len(datos_conexion) > 3 and datos_conexion[3]:  # Verifica que haya al menos 4 elementos
                self.label_info_notebook_config_datos.config(
                    text="Se encontrÃ³ conexiÃ³n a la fuente de datos de Inforhard Sistema S.R.L"
                )
                self.frame_config_datos_INFORHARD.pack(fill="both", expand=True)
            else:
                self.label_info_notebook_config_datos.config(
                    text="No se encontrÃ³ conexiÃ³n a una fuente de datos"
                )
        else:
            self.label_info_notebook_config_datos.config(
                text="No se encontrÃ³ ninguna conexiÃ³n a una fuente de datos"
            )
            
    def creacion_frame_config_datos_INFORHARD(self):
        self.frame_config_datos_INFORHARD = ttk.Frame(self.frame_notebook_config_datos)
        
        self.button_importar_datos_INFORHARD = ttk.Button(self.frame_config_datos_INFORHARD, text="Sincronizars Datos", command=self.command_importar_datos_INFORHARD)
        self.button_importar_datos_INFORHARD.pack()
        
    def creacion_toplevel_carga_datos(self):
        # Crear ventana Toplevel
        self.top_level_carga = ttk.Toplevel()
        self.top_level_carga.title("Cargar Datos")
        
        # Congelar la ventana principal al mostrar esta ventana
        self.top_level_carga.transient(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        self.top_level_carga.grab_set()  # Esto congela la ventana principal
        self.top_level_carga.protocol("WM_DELETE_WINDOW", self.bloquear_cierre)
        
        # Posicionar la ventana en el centro
        self.top_level_carga.geometry("400x250")  # TamaÃ±o ajustado
        self.top_level_carga.place_window_center()

        # Agregar una barra de progreso
        self.progressbar_carga = ttk.Floodgauge(self.top_level_carga, mode="determinate", bootstyle="primary")
        self.DICT_WIDGETS.register("UI", "BARRA_PROGRESO", self.progressbar_carga)
        self.progressbar_carga.pack(fill="x", expand=True, padx=20, pady=(20,10))
        
        # Label de porcentaje con tamaÃ±o mayor
        self.label_porcentaje = ttk.Label(self.top_level_carga, text="0%", anchor="center", font=("Arial", 14))
        self.label_porcentaje.pack(pady=10)

        # Entry para mostrar las acciones, con tamaÃ±o mayor y centrado
        self.entry_acciones = ttk.Entry(self.top_level_carga, state="readonly", width=40, font=("Arial", 12))
        self.entry_acciones.pack(pady=10)
        self.mostrar_accion("Iniciando la carga de datos...")
        
    #///////////////////////////////////////////////////// NOTEBOOK GO-UPC /////////////////////////////////////////////////////

    def creacion_frame_notebook_go_upc(self):
        """PestaÃ±a para configurar la API KEY de GO-UPC (guardada en SQLite)."""
        self.frame_notebook_go_upc = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_go_upc.pack(fill="both", expand=True)
        self.DICT_WIDGETS.register("GUI_CONFIG", "frame_notebook_go_upc", self.frame_notebook_go_upc)

        lab = ttk.Labelframe(self.frame_notebook_go_upc, text="ConexiÃ³n GO-UPC", bootstyle="primary", padding=15)
        lab.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            lab,
            text="API KEY (se guarda localmente en la base de datos):",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        self.entry_go_upc_api_key = ttk.Entry(lab, show="â€¢")
        self.entry_go_upc_api_key.pack(fill="x", pady=(0, 10))
        self.DICT_WIDGETS.register("GUI_CONFIG", "entry_go_upc_api_key", self.entry_go_upc_api_key)

        frame_btn = ttk.Frame(lab)
        frame_btn.pack(fill="x")

        self.btn_guardar_go_upc = ttk.Button(
            frame_btn,
            text="Guardar",
            bootstyle="success",
            command=self.command_guardar_go_upc_api_key,
        )
        self.btn_guardar_go_upc.pack(side="left")

        self.btn_limpiar_go_upc = ttk.Button(
            frame_btn,
            text="Limpiar",
            bootstyle="secondary",
            command=lambda: self.entry_go_upc_api_key.delete(0, "end"),
        )
        self.btn_limpiar_go_upc.pack(side="left", padx=8)

        self.lbl_estado_go_upc = ttk.Label(lab, text="", bootstyle="secondary")
        self.lbl_estado_go_upc.pack(anchor="w", pady=(10, 0))

        self.lbl_estado_api_imagenes = ttk.Label(lab, text="", bootstyle="secondary")
        self.lbl_estado_api_imagenes.pack(anchor="w", pady=(6, 0))
        self.top_level_configuracion.bind("<Control-Shift-I>", self._abrir_config_api_imagenes)
        self.top_level_configuracion.bind("<Control-Shift-i>", self._abrir_config_api_imagenes)

        # Cargar valor guardado (si existe)
        self._asegurar_tabla_go_upc_api_key()
        self._cargar_go_upc_api_key()
        self._actualizar_estado_api_imagenes()

    def _asegurar_tabla_go_upc_api_key(self):
        """Crea la tabla api_key si no existe (por las dudas)."""
        try:
            self.api_key_dao.asegurar_tabla()
        except Exception as e:
            print(f"[GO-UPC] Error creando tabla api_key: {e}")

    def _cargar_go_upc_api_key(self):
        """Carga la API KEY desde la DB y la muestra en el Entry (si existe)."""
        try:
            api_key = self.api_key_dao.obtener_ultima()
            if api_key:
                self.entry_go_upc_api_key.delete(0, "end")
                self.entry_go_upc_api_key.insert(0, api_key)
                self.lbl_estado_go_upc.config(text="API KEY cargada desde la base.", bootstyle="success")
            else:
                self.lbl_estado_go_upc.config(text="No hay API KEY guardada.", bootstyle="warning")
        except Exception as e:
            self.lbl_estado_go_upc.config(text=f"Error leyendo API KEY: {e}", bootstyle="danger")

    def command_guardar_go_upc_api_key(self):
        """Guarda la API KEY en la DB (deja una sola vigente)."""
        api_key = self.entry_go_upc_api_key.get().strip()
        if not api_key:
            messagebox.showwarning("GO-UPC", "IngresÃ¡ la API KEY.")
            return

        try:
            self.api_key_dao.reemplazar(api_key)
            self.lbl_estado_go_upc.config(text="API KEY guardada correctamente.", bootstyle="success")
        except Exception as e:
            self.lbl_estado_go_upc.config(text=f"Error guardando API KEY: {e}", bootstyle="danger")
            messagebox.showerror("GO-UPC", f"No se pudo guardar la API KEY.\n\n{e}")

    def _abrir_config_api_imagenes(self, event=None):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        actual = config.get("api_imagenes_url", "")
        url = simpledialog.askstring(
            "API propia de imagenes",
            "URL base de tu API de imagenes:",
            initialvalue=actual,
            parent=self.top_level_configuracion,
        )
        if url is None:
            return

        url = url.strip()
        if url:
            config["api_imagenes_url"] = url
        else:
            config.pop("api_imagenes_url", None)
        guardar_config(config)
        self._actualizar_estado_api_imagenes()

    def _actualizar_estado_api_imagenes(self):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        url = (config.get("api_imagenes_url") or "").strip()
        if url:
            self.lbl_estado_api_imagenes.config(
                text="API propia de imagenes configurada. Atajo: Ctrl+Shift+I",
                bootstyle="success",
            )
        else:
            self.lbl_estado_api_imagenes.config(
                text="API propia de imagenes sin configurar. Atajo: Ctrl+Shift+I",
                bootstyle="secondary",
            )


            
#//////////////////////////////////////////////// COMMAND DE BOTONES ///////////////////////////////////////////////
    def command_button_agregar(self):
        self.toplevel_button_agregar = ttk.Toplevel(self.top_level_configuracion)
        self.DICT_WIDGETS.register("GUI_CONFIG", "toplevel_button_agregar", self.toplevel_button_agregar)
        self.toplevel_button_agregar.title("VeriPre_Connector - Agregar Dispositivo")
        self.toplevel_button_agregar.transient(self.top_level_configuracion)
        self.toplevel_button_agregar.geometry("500x300")
        self.toplevel_button_agregar.place_window_center()

        self.creacion_contenido_toplevel_button_agregar()
        
    def command_button_eliminar(self):
        if messagebox.askyesno("Eliminar Dispositivo", f"Â¿Desea eliminar el Dispositivo {self.combobox_dispositivos.get()}?"):
            
            self.dispositivos_dao.eliminar_por_nombre(self.combobox_dispositivos.get())
            self.limpiar_frame_despues_actualizacion()

    def _obtener_dispositivo_seleccionado(self):
        nombre = self.combobox_dispositivos.get()
        if not nombre or nombre not in self.datos_dispositivos:
            return None, None, None
        dispositivo = self.datos_dispositivos[nombre]
        base_url = f"http://{dispositivo['direccion_ip']}:{dispositivo['puerto']}/api/veri/batch_productos"
        return nombre, dispositivo, base_url

    def command_button_estado_dispositivo(self):
        nombre, _dispositivo, base_url = self._obtener_dispositivo_seleccionado()
        if not nombre:
            messagebox.showwarning("Estado dispositivo", "Seleccione un dispositivo para consultar.")
            return
        self.button_estado.config(state="disabled", text="...")

        def tarea():
            client = DispositivoAPIClient(base_url)
            status = client.get_status_dispositivo()

            def finalizar():
                self.button_estado.config(state="normal", text="Estado")
                if not status:
                    messagebox.showinfo(
                        "Estado dispositivo",
                        "El endpoint /api/veri/status no esta disponible.\n"
                        "Puede ser un APK anterior o el equipo no respondio.",
                    )
                    return

                mensaje = (
                    f"API: {status.get('api', '-')}\n"
                    f"Version API: {status.get('api_version', '-')}\n"
                    f"Productos: {status.get('productos', '-')}\n"
                    f"Publicidades: {status.get('publicidades', '-')}\n"
                    f"Logo principal: {status.get('logo_principal', '-')}\n"
                    f"GO-UPC key: {status.get('go_upc_key', '-')}"
                )
                grupos_activos = status.get("grupos_activos") or []
                if grupos_activos:
                    detalle_grupos = []
                    for grupo in grupos_activos:
                        try:
                            display_txt = f"Pantalla {int(grupo.get('display_index', 0)) + 1}"
                        except Exception:
                            display_txt = "Pantalla ?"
                        detalle_grupos.append(
                            f"- {display_txt}: {grupo.get('grupo', '-')}"
                            f" ({grupo.get('cantidad', 0)} items)"
                        )
                    mensaje += "\n\nGrupos activos:\n" + "\n".join(detalle_grupos)
                messagebox.showinfo(f"Estado - {nombre}", mensaje)

            self._run_en_ui(finalizar)

        threading.Thread(target=tarea, daemon=True).start()

    def command_button_configuracion_player(self):
        nombre, _dispositivo, base_url = self._obtener_dispositivo_seleccionado()
        if not nombre:
            messagebox.showwarning("Player", "Seleccione un dispositivo para configurar.")
            return

        self.button_player.config(state="disabled", text="...")

        def tarea():
            client = DispositivoAPIClient(base_url)
            config_player = client.get_player_configuration()

            def finalizar():
                self.button_player.config(state="normal", text="Player")
                if not config_player:
                    messagebox.showinfo(
                        "Configuracion Player",
                        "El endpoint /api/veri/configuracion_player no esta disponible.\n"
                        "Puede ser un APK anterior o el dispositivo no respondio.",
                    )
                    return
                self._abrir_dialogo_configuracion_player(nombre, base_url, config_player)

            self._run_en_ui(finalizar)

        threading.Thread(target=tarea, daemon=True).start()

    def _descripcion_pantalla(self, pantalla):
        primary = " | Principal" if pantalla.get("primary") else ""
        return (
            f"Pantalla {pantalla.get('index', 0) + 1} | "
            f"{pantalla.get('width', '?')}x{pantalla.get('height', '?')} | "
            f"x={pantalla.get('x', 0)} y={pantalla.get('y', 0)}{primary}"
        )

    def _abrir_dialogo_configuracion_player(self, nombre, base_url, config_player):
        top = ttk.Toplevel(self.top_level_configuracion)
        top.title(f"Player - {nombre}")
        top.geometry("700x470")
        top.place_window_center()
        top.transient(self.top_level_configuracion)
        top.grab_set()

        settings = config_player.get("settings", {}) if isinstance(config_player, dict) else {}
        pantallas = config_player.get("pantallas_detectadas", []) if isinstance(config_player, dict) else []
        campos = config_player.get("campos_soportados", []) if isinstance(config_player, dict) else []

        ttk.Label(
            top,
            text=f"Configuracion remota del player para {nombre}",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 6))

        ttk.Label(
            top,
            text=f"Campos soportados: {', '.join(campos) if campos else 'No informado'}",
            bootstyle="secondary",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        form = ttk.Frame(top, padding=(12, 6))
        form.pack(fill="x")

        ttk.Label(form, text="Pantalla / HDMI:").grid(row=0, column=0, sticky="w", pady=4)
        pantalla_var = StringVar()
        pantalla_combo = ttk.Combobox(form, textvariable=pantalla_var, state="readonly", width=55)
        pantalla_combo.grid(row=0, column=1, sticky="ew", pady=4)

        mapa_pantallas = {}
        valores_pantalla = []
        for pantalla in pantallas:
            descripcion = self._descripcion_pantalla(pantalla)
            valores_pantalla.append(descripcion)
            mapa_pantallas[descripcion] = int(pantalla.get("index", 0))
        if valores_pantalla:
            pantalla_combo.configure(values=valores_pantalla)
            display_index = int(settings.get("display_index", 0) or 0)
            seleccion = next(
                (desc for desc, idx in mapa_pantallas.items() if idx == display_index),
                valores_pantalla[0],
            )
            pantalla_var.set(seleccion)
        else:
            fallback = f"Pantalla {int(settings.get('display_index', 0) or 0) + 1}"
            pantalla_combo.configure(values=[fallback])
            pantalla_var.set(fallback)

        ttk.Label(form, text="Segundos por imagen:").grid(row=1, column=0, sticky="w", pady=4)
        duracion_var = StringVar(value=str(settings.get("image_duration_seconds", 3) or 3))
        ttk.Entry(form, textvariable=duracion_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="API key del player:").grid(row=2, column=0, sticky="w", pady=4)
        api_key_var = StringVar(value=str(settings.get("api_key", "") or ""))
        ttk.Entry(form, textvariable=api_key_var).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Clave de salida:").grid(row=3, column=0, sticky="w", pady=4)
        exit_password_var = StringVar(value=str(settings.get("exit_password", "") or ""))
        ttk.Entry(form, textvariable=exit_password_var).grid(row=3, column=1, sticky="ew", pady=4)

        reload_var = BooleanVar(value=True)
        ttk.Checkbutton(form, text="Recargar player al guardar", variable=reload_var).grid(
            row=4, column=1, sticky="w", pady=(6, 4)
        )

        form.columnconfigure(1, weight=1)

        info = ttk.Labelframe(top, text="Pantallas detectadas", padding=12, bootstyle="primary")
        info.pack(fill="both", expand=True, padx=12, pady=(8, 10))
        text_info = ttk.Text(info, height=8, wrap="word")
        text_info.pack(fill="both", expand=True)
        if pantallas:
            text_info.insert("1.0", "\n".join(self._descripcion_pantalla(p) for p in pantallas))
        else:
            text_info.insert("1.0", "El dispositivo no informo pantallas detectadas.")
        text_info.config(state="disabled")

        estado_lbl = ttk.Label(top, text="", bootstyle="secondary")
        estado_lbl.pack(anchor="w", padx=12, pady=(0, 8))

        def guardar():
            try:
                duracion = int(duracion_var.get().strip())
            except ValueError:
                messagebox.showwarning("Player", "La duracion de imagen debe ser un numero entero.")
                return

            if duracion < 1 or duracion > 60:
                messagebox.showwarning("Player", "La duracion debe estar entre 1 y 60 segundos.")
                return

            display_index = mapa_pantallas.get(pantalla_var.get(), int(settings.get("display_index", 0) or 0))
            payload = {
                "display_index": int(display_index),
                "image_duration_seconds": duracion,
                "api_key": api_key_var.get().strip(),
                "exit_password": exit_password_var.get().strip(),
                "reload": bool(reload_var.get()),
            }

            btn_guardar.config(state="disabled", text="Guardando...")
            estado_lbl.config(text="Enviando configuracion al player...", bootstyle="info")

            def tarea():
                client = DispositivoAPIClient(base_url)
                respuesta = client.set_player_configuration(payload)

                def finalizar():
                    btn_guardar.config(state="normal", text="Guardar en player")
                    if not respuesta:
                        estado_lbl.config(text="No se pudo guardar la configuracion.", bootstyle="danger")
                        return
                    estado_lbl.config(text="Configuracion guardada correctamente.", bootstyle="success")
                    messagebox.showinfo("Player", "Configuracion del player guardada correctamente.")

                self._run_en_ui(finalizar)

            threading.Thread(target=tarea, daemon=True).start()

        acciones = ttk.Frame(top, padding=(12, 0, 12, 12))
        acciones.pack(fill="x")
        btn_guardar = ttk.Button(acciones, text="Guardar en player", command=guardar, bootstyle="success")
        btn_guardar.pack(side="left")
        ttk.Button(acciones, text="Cerrar", command=top.destroy).pack(side="right")
            
    def command_button_editar_dispositivo(self):
        self.command_button_agregar()
        
        dispositivo = self.combobox_dispositivos.get()

        if dispositivo in self.datos_dispositivos:
            self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.insert(0, dispositivo)
            self.entry_direccion_ip.insert(0, self.datos_dispositivos[dispositivo]["direccion_ip"])
            self.entry_puerto.insert(0, self.datos_dispositivos[dispositivo]["puerto"])
            self.text_comentario.insert("1.0", self.datos_dispositivos[self.combobox_dispositivos.get()]["comentario"])
        else:
            print(f"Error: {dispositivo} no encontrado en datos_dispositivos")
        
        self.button_agregar_dispositivo.config(text="Actualizar", command=self.command_button_actualizar_datos_dispositivo)
        
    def command_button_agregar_dispositivo(self):
        try:
            if self.validar_campos():
                self.dispositivos_dao.crear(
                    self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.get().strip(),
                    self.entry_direccion_ip.get().strip(),
                    self.entry_puerto.get().strip(),
                    self.text_comentario.get("1.0", "end").strip(),
                )
                self.combobox_dispositivos.config(values=self.actualizar_datos_combobox())
                messagebox.showinfo("Dispositivo Agregado", "Â¡Dispositivo Agregado con exito!")
                self.toplevel_button_agregar.destroy()
        except Exception as e:
            print(e)    
            
    def command_button_actualizar_datos_dispositivo(self):
        try:
            if self.validar_campos():
                # Prepara la consulta segura usando parÃ¡metros
                sentencia_actualizacion = """
                UPDATE VERIPRE_EQUIPOS 
                SET nombre = ?, direccion_conexion = ?, puerto = ?, comentarios = ? 
                WHERE nombre = ?;
                """

                valores = (
                    self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.get(),
                    self.entry_direccion_ip.get(),
                    self.entry_puerto.get(),
                    self.text_comentario.get("1.0", "end").strip(),  # Evita el salto de lÃ­nea final
                    self.combobox_dispositivos.get()
                )

                # Ejecuta la consulta de forma segura
                conexion = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA")
                conexion.ejecutar_consulta(sentencia_actualizacion, valores)

                # Actualiza el Combobox con los nuevos datos
                self.combobox_dispositivos.config(values=self.actualizar_datos_combobox())

                messagebox.showinfo("Dispositivo Actualizado", "Â¡Dispositivo actualizado con Ã©xito!")
                self.toplevel_button_agregar.destroy()
                self.limpiar_frame_despues_actualizacion()

        except Exception as e:
            print(f"Error al actualizar el dispositivo: {e}")
            
    def command_button_agregar_datos_de_conexion(self):
        try:
            if self.combobox_lista_fuente_datos.get() == "ConexiÃ³n ODBC":
                self.conexion_dao.crear(
                    self.combobox_odbc.get(),
                    self.entry_user.get(),
                    self.entry_password.get(),
                    self.checkbox_var.get(),
                )
                print(self.checkbox_var.get())
                if self.checkbox_var.get():
                    conexion = {
                        "user": self.entry_user.get(),
                        "password": self.entry_password.get(),
                        "dsn": self.combobox_odbc.get()
                    }
                    self.DICT_WIDGETS.register("DATABASE","CONEXIONDBA_SYBASE", ConexionSybase(**conexion))
                    self.DICT_WIDGETS.register("DATABASE","CONEXION_INFORHARD", True)
                else:
                    print("NO CONEXION INFORHARD")
                messagebox.showinfo("ConexiÃ³n Agregada", "Â¡ConexiÃ³n agregada con exito!")
            self.cambiar_estados_widgets_frame_odbc("disabled")
            self.button_agregar_datos_de_conexion.config(text="Actualizar datos", state="normal", command=self.command_modificado_button_actualizar_datos_de_conexion)
        except Exception as e:
            print(e)
            messagebox.showerror("ERROR", e)
            
    def command_modificado_button_actualizar_datos_de_conexion(self):            
            self.cambiar_estados_widgets_frame_odbc("normal")
            self.top_level_configuracion.update_idletasks()
            self.dsn_actual = self.combobox_odbc.get()
            self.button_agregar_datos_de_conexion.config(text="Agregar", command=self.command_modificado_actulizar_datos_odbc)
            
    def command_modificado_actulizar_datos_odbc(self):
        try:
            self.conexion_dao.actualizar_por_dsn(
                self.dsn_actual,
                self.combobox_odbc.get(),
                self.entry_user.get(),
                self.entry_password.get(),
                self.checkbox_var.get(),
            )
            print(self.checkbox_var.get())
            if self.checkbox_var.get():
                conexion = {
                    "user": self.entry_user.get(),
                    "password": self.entry_password.get(),
                    "dsn": self.combobox_odbc.get()
                }
                self.DICT_WIDGETS.register("DATABASE","CONEXIONDBA_SYBASE", ConexionSybase(**conexion))
                self.DICT_WIDGETS.register("DATABASE","CONEXION_INFORHARD", True)
            else:
                print("NO CONEXION INFORHARD")
            messagebox.showinfo("Estado ConexiÃ³n", "Se ha actualizado el metodo de conexiÃ³n")
            self.cambiar_estados_widgets_frame_odbc("disabled")
            self.button_agregar_datos_de_conexion.config(text="Actualizar datos", state="normal", command=self.command_modificado_button_actualizar_datos_de_conexion)
        except Exception as e:
            print(e)
            
    def command_importar_datos_INFORHARD(self):
        try:
            self.creacion_toplevel_carga_datos()
            threading.Thread(target=self.procesar_productos_completos).start()
        except Exception as e:
            print(e)
            

    def actualizar_config_sincronizacion_automatica(self):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        nuevo_valor = self.auto_sync_var.get()
        valor_anterior = config.get("sincronizacion_automatica", False)

        # Solo preguntar si se estÃ¡ activando (no al desactivar)
        if not valor_anterior and nuevo_valor:
            respuesta = messagebox.askyesno(
                "Reiniciar aplicaciÃ³n",
                "Se activÃ³ la sincronizaciÃ³n automÃ¡tica.\nÂ¿DeseÃ¡s reiniciar la aplicaciÃ³n para aplicar los cambios?"
            )
            if respuesta:
                config["sincronizacion_automatica"] = True
                config["envio_automatico_novedades"] = self.auto_send_news_var.get()
                guardar_config(config)
                self._reiniciar_aplicacion()
            else:
                self.auto_sync_var.set(valor_anterior)
        else:
            # Si se desactiva o no cambia, solo guardar
            config["sincronizacion_automatica"] = nuevo_valor
            if not nuevo_valor:
                config["envio_automatico_novedades"] = False
                self.auto_send_news_var.set(False)
            guardar_config(config)
        self._actualizar_estado_checkbox_envio_auto()

    def actualizar_config_envio_automatico_novedades(self):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        if not self.auto_sync_var.get():
            self.auto_send_news_var.set(False)

        config["envio_automatico_novedades"] = self.auto_send_news_var.get()
        guardar_config(config)
        self._actualizar_estado_checkbox_envio_auto()

    def actualizar_config_audio_publicidades(self):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        config["mantener_audio_publicidades"] = self.keep_video_audio_var.get()
        guardar_config(config)

    def _actualizar_estado_checkbox_envio_auto(self):
        estado = NORMAL if self.auto_sync_var.get() else DISABLED
        self.checkbox_auto_send_news.config(state=estado)

    def _reiniciar_aplicacion(self):
        ejecutable = sys.executable
        if getattr(sys, "frozen", False):
            os.execl(ejecutable, ejecutable, *sys.argv[1:])
        else:
            os.execl(ejecutable, ejecutable, *sys.argv)
    def procesar_productos_completos(self):
        """Llama a todas las funciones para procesar los productos en conjunto."""
        try:
            resultado = self._crear_productos_sync_service().sincronizar_completo(
                progress_callback=self._sync_progress
            )
            self.datos_ARTICULOS = resultado["articulos"]
            self.datos_PRODUCTOS_COMPLETOS = resultado["productos"]
            self._run_en_ui(self.mostrar_accion, "Proceso completo.")
            self._run_en_ui(
                messagebox.showinfo,
                "Proceso completo",
                "Se han insertado los nuevos productos y actualizados los pendientes.",
            )
        finally:
            self._run_en_ui(self.top_level_carga.destroy)
        return



    def mostrar_accion(self, texto):
        print(texto)
        """Actualiza el Entry con el texto de la acciÃ³n que se estÃ¡ realizando."""
        self.entry_acciones.config(state="normal")
        self.entry_acciones.delete(0, "end")
        self.entry_acciones.insert(0, texto)
        self.entry_acciones.config(state="readonly")
        
    def actualizar_barra(self, progreso, total):            
        """Actualiza la barra de progreso con el porcentaje calculado."""
        porcentaje = (progreso / total) * 100
        
        barra_progreso = self.DICT_WIDGETS.get_widget("UI", "BARRA_PROGRESO")
        if barra_progreso is not None:
            barra_progreso['value'] = porcentaje  # AsegÃºrate de usar 'value' para actualizar la barra
            self.label_porcentaje.configure(text=f"{int(porcentaje)}%")
        else:
            self.mostrar_accion("Error: No se encontrÃ³ el widget BARRA_PROGRESO.")




    def _run_en_ui(self, callback, *args, **kwargs):
        root = self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja")
        root.after(0, lambda: callback(*args, **kwargs))

    def _sync_progress(self, mensaje=None, progreso=None, total=None):
        if mensaje:
            self._run_en_ui(self.mostrar_accion, mensaje)
        if progreso is not None and total:
            self._run_en_ui(self.actualizar_barra, progreso, total)

    def _crear_productos_sync_service(self):
        return ProductosSyncService(
            self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA"),
            self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE"),
        )

    #/////////////////////////////////////////// DATABASE ///////////////////////////////////////////
    def buscar_datos_en_tabla_ARTICULOS(self):
        """Obtiene los artÃ­culos con cÃ³digos de barras vÃ¡lidos y muestra informaciÃ³n de lo que estÃ¡ haciendo."""
        CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS = """
            SELECT CREF, CDETALLE, CCODEBAR, CTIPOIVA, NPVP1, dFechaU
            FROM ARTICULO 
            WHERE CCODEBAR IS NOT NULL AND CCODEBAR <> ''
            ORDER BY dFechaU ASC;
        """
        self.datos_ARTICULOS = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS)

        self.mostrar_accion("Iniciando la carga de artÃ­culos...")
        time.sleep(0.75)

        # Primera actualizaciÃ³n al 50%
        self.actualizar_barra(50, 100)

        self.mostrar_accion(f"{len(self.datos_ARTICULOS)} artÃ­culos encontrados.")
        time.sleep(0.75)

        # Ãšltima actualizaciÃ³n al 100%
        self.actualizar_barra(100, 100)





    def buscar_datos_tabla_CODBARP(self):
        """Obtiene los cÃ³digos de barra adicionales y los une con la lista de productos."""
        self.datos_PRODUCTOS_COMPLETOS = []
        
        if not self.datos_ARTICULOS:
            self.mostrar_accion("No hay datos en ARTICULO")
            return
        
        crefs = tuple(producto[0] for producto in self.datos_ARTICULOS)
        
        CONSULTA_SQL_BUSCAR_DATOS_CODBARP = f"""
            SELECT CREF, CDETALLE, CCODEBAR, dFechaU
            FROM CODBARP 
            WHERE CREF IN {crefs} AND CCODEBAR IS NOT NULL AND CCODEBAR <> ''
            ORDER BY dFechaU ASC;
        """
        
        self.mostrar_accion("Obteniendo cÃ³digos de barra adicionales...")
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
            cref, cdetalle, ccodebar, ctipoiva, npvp1, dfechau = producto
            self.datos_PRODUCTOS_COMPLETOS.append(producto)
            progreso += 1
            if progreso % 10 == 0:  # Actualiza la barra cada 10 productos
                self.actualizar_barra(progreso, total)
            
            if cref in codbarp_dict:
                for cdetalle_extra, ccodebar_extra, dfechau in codbarp_dict[cref]:
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
            # AquÃ­ ejecutamos la consulta y almacenamos los resultados
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

            producto_actualizado = list(producto)
            del producto_actualizado[3]
            producto_actualizado[3] = format(round(nuevo_precio, 2), ".2f")
            productos_actualizados.append(tuple(producto_actualizado))

            self.actualizar_barra(idx + 1, total_productos)

        self.datos_PRODUCTOS_COMPLETOS = productos_actualizados
        self.mostrar_accion(f"{len(self.datos_PRODUCTOS_COMPLETOS)} productos actualizados con IVA.")

            
        
    def insertar_o_actualizar_productos(self):
        """Elimina los datos y los reemplazo con los nuevos"""
        consulta_limpieza = """
        DELETE FROM productos
        """
        """Inserta o actualiza los productos en la base de datos SQLite y muestra el progreso."""
        self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA").ejecutar_consulta(consulta_limpieza)
        consulta = """
        INSERT OR REPLACE INTO productos (CREF, codigo, descripcion, precio, dfechau) 
        VALUES (?, ?, ?, ?, ?)
        """

        self.mostrar_accion("Insertando o actualizando productos...")
        
        total_productos = len(self.datos_PRODUCTOS_COMPLETOS)  # NÃºmero total de productos
        if total_productos == 0:
            self.mostrar_accion("No hay productos para insertar o actualizar.")
            return

        # Iniciar la barra de progreso en 0%
        self.actualizar_barra(0, total_productos)
        
        # Preparar todos los parÃ¡metros para la inserciÃ³n o actualizaciÃ³n
        parametros = [(producto[0], producto[2], producto[1], producto[3], producto[4]) for producto in self.datos_PRODUCTOS_COMPLETOS]

        # Ejecutar la consulta para todos los productos a la vez
        self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA").ejecutar_consultamany(consulta, parametros)
        
        # Actualizar la barra de progreso al 100% una vez que se han insertado/actualizado todos los productos
        self.actualizar_barra(total_productos, total_productos)

        self.mostrar_accion("Productos insertados o actualizados correctamente.")





            
    def cierre_top_level_configuracion(self):
        """Cierra la ventana y la elimina del gestor de ventanas"""
        VentanaManager.cerrar_ventana("configuracion")  # Llamamos al mÃ©todo de cierre
        self.top_level_configuracion.destroy()
        
    def obtener_datos_conexion_odbc(self):
        datos_conexion = self.conexion_dao.obtener_todas()
        if datos_conexion is not None:
            for datos in datos_conexion:
                self.combobox_odbc.set(value=datos[0])                
                self.entry_user.insert("0", datos[1])                
                self.entry_password.insert("0", datos[2])                
                self.checkbox_var.set(datos[3])
                self.checkbox.config(variable=self.checkbox_var)
                self.cambiar_estados_widgets_frame_odbc("disabled")
                self.button_agregar_datos_de_conexion.config(text="Actualizar datos", state="normal", command=self.command_modificado_button_actualizar_datos_de_conexion)
        
    def cambiar_estados_widgets_frame_odbc(self, estado):
        if estado == "normal":
            self.combobox_odbc.config(state="readonly")
            self.entry_user.config(state=estado)
            self.entry_password.config(state=estado)
            self.checkbox.config(state=estado)
        elif estado == "disabled":
            self.combobox_odbc.config(state=estado)
            self.entry_user.config(state=estado)
            self.entry_password.config(state=estado)
            self.checkbox.config(state=estado)
    
    def seleccion_dispositivo(self, event):
        self.button_editar.config(state="normal")
        self.button_eliminar.config(state="normal")
        self.button_estado.config(state="normal")
        self.button_player.config(state="normal")
        self.frame_contenedor_labelframe_datos_dispositivo.pack(fill="both", expand=True)
        dispositivo = self.combobox_dispositivos.get()
        print(f"Seleccionaste: {dispositivo}")

        # Actualizar los Labels con la informaciÃ³n del dispositivo seleccionado
        self.label_nombre_contenido_labelframe_opciones.config(text=dispositivo)
        self.label_direccion_ip_der_contenido_labelframe_opciones.config(
            text=self.datos_dispositivos[dispositivo]["direccion_ip"]
        )
        self.label_puerto_der_contenido_labelframe_opciones.config(
            text=self.datos_dispositivos[dispositivo]["puerto"]
        )

        # Actualizar el contenido del Text para el comentario
        self.text_comentario_contenido_labelframe_opciones.config(state="normal")  # Habilitar ediciÃ³n
        self.text_comentario_contenido_labelframe_opciones.delete("1.0", "end")  # Eliminar texto anterior
        self.text_comentario_contenido_labelframe_opciones.insert("1.0", self.datos_dispositivos[dispositivo]["comentario"])  # Insertar nuevo comentario
        self.text_comentario_contenido_labelframe_opciones.config(state="disabled")  # Deshabilitar ediciÃ³n

        # Forzar la actualizaciÃ³n de la interfaz
        self.top_level_configuracion.update_idletasks()

    def actualizar_datos_combobox(self):
        try:
            self.traer_todos_los_datos_de_VERIPRE_EQUIPOS()
            list_nombre_dispositivo = []
            for nombre_dispositivo in self.datos_dispositivos:
                list_nombre_dispositivo.append(nombre_dispositivo)
            return list_nombre_dispositivo
        except Exception as e:
            print(e)
            return []
    
    def traer_todos_los_datos_de_VERIPRE_EQUIPOS(self):
        try:
            self.datos_dispositivos = self.dispositivos_dao.listar_dict()
        except Exception as e:
            return []
        
    def limpiar_frame_despues_actualizacion(self):
        self.button_editar.config(state="disable")
        self.button_eliminar.config(state="disable")
        self.button_estado.config(state="disable")
        self.button_player.config(state="disable")
        self.combobox_dispositivos.config(values=self.actualizar_datos_combobox())
        self.combobox_dispositivos.set(value="")
        self.frame_contenedor_labelframe_datos_dispositivo.pack_forget()
        
    def bloquear_cierre(self):
        pass  # No hace nada al intentar cerrar

    from PIL import Image, ImageTk

    def _mostrar_logo_actual(self):
        ruta_logo = PNG_LOGO_PRINCIPAL()
        if not os.path.exists(ruta_logo):
            ruta_logo = PNG_LOGO_SECUNDARIO()

        if os.path.exists(ruta_logo):
            self.label_logo_preview.update_idletasks()
            ancho_disp = self.label_logo_preview.winfo_width()
            alto_disp = self.label_logo_preview.winfo_height()

            if ancho_disp <= 1 or alto_disp <= 1:
                ancho_disp, alto_disp = 300, 300  # mayor Ã¡rea visible

            img = Image.open(ruta_logo)
            img.thumbnail((ancho_disp, alto_disp), Image.Resampling.LANCZOS)

            self.logo_img_tk = ImageTk.PhotoImage(img)
            self.label_logo_preview.config(image=self.logo_img_tk, text="")
        else:
            self.label_logo_preview.config(image="", text="Sin logo")

            
    def _seleccionar_logo(self):
        filetypes = [("ImÃ¡genes", "*.png *.jpg *.jpeg *.webp")]
        filepath = filedialog.askopenfilename(title="Seleccionar Logo", filetypes=filetypes)
        if not filepath:
            return

        # Mostrar preview adaptado
        self.label_logo_preview.update_idletasks()
        ancho_disp = self.label_logo_preview.winfo_width()
        alto_disp = self.label_logo_preview.winfo_height()

        if ancho_disp <= 1 or alto_disp <= 1:
            ancho_disp, alto_disp = 300, 300

        img = Image.open(filepath)
        img.thumbnail((ancho_disp, alto_disp), Image.Resampling.LANCZOS)

        self.logo_img_tk = ImageTk.PhotoImage(img)
        self.label_logo_preview.config(image=self.logo_img_tk, text="")

        # Guardar para enviar
        self.ruta_logo_seleccionado = filepath

        # Guardar copia en carpeta /assets/ con nombre !!!LOGO_PRINCIPAL!!!.png
        try:
            from pathlib import Path
            destino = Path("assets") / "!!!LOGO_PRINCIPAL!!!.png"
            destino.parent.mkdir(parents=True, exist_ok=True)  # crear carpeta si no existe

            img_original = Image.open(filepath).convert("RGBA")  # asegura transparencia
            img_original.save(destino, format="PNG")

            print(f"âœ… Logo guardado como {destino}")
        except Exception as e:
            print(f"âŒ No se pudo guardar el logo en assets/: {e}")



    def _enviar_logo_a_dispositivos(self):
        # Ruta del logo seleccionado (por el usuario)
        ruta_logo = getattr(self, "ruta_logo_seleccionado", None)

        # Si no hay logo seleccionado, buscar el logo principal o uno secundario
        if not ruta_logo:
            ruta_logo = PNG_LOGO_PRINCIPAL()
            if not os.path.exists(ruta_logo):
                ruta_logo = PNG_LOGO_SECUNDARIO()  # â† definilo como ruta alternativa
                if not os.path.exists(ruta_logo):
                    messagebox.showwarning("Logo no disponible", "No se encontrÃ³ ningÃºn logo para enviar.")
                    return
        ventana_padre = self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja")
        sender = DispositivoSender(self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA"), ventana_padre)
        urls = sender.seleccionar_dispositivos()
        if not urls:
            return

        sender.enviar_logo_principal(urls, ruta_logo)
        messagebox.showinfo("Logo Enviado", "El logo fue enviado exitosamente.")

