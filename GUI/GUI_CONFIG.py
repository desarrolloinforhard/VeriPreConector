import os
import sys
import subprocess
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
from core.ui.responsive import clamp, fit_toplevel_to_workarea, get_size_class, get_workarea_size
from core.ui.theme_tokens import (
    BUTTON_PAD_X,
    BUTTON_PAD_Y,
    FONT_BODY_BOLD,
    FONT_LABEL_BOLD,
    FONT_SUBTITLE,
    FONT_TITLE_LG,
    PANEL_PAD_X,
    PANEL_PAD_Y,
)
from core.services.device_discovery_service import DeviceDiscoveryService
from core.services.productos_sync_service import ProductosSyncService


class GUI_CONFIG:
    def __init__(self, DICT_WIDGETS):
        self.DICT_WIDGETS = DICT_WIDGETS
        self.DICT_WIDGETS.register("GUI_CONFIG", "instance", self)
        self.permisos_usuario = self.DICT_WIDGETS.get_widget("CONFIG", "permisos_usuario") or {}
        if not bool(self.permisos_usuario.get("configuracion", False)):
            messagebox.showwarning("Acceso restringido", "Este usuario no tiene acceso al módulo Configuración.")
            raise PermissionError("Usuario sin permiso de configuración")
        self.datos_dispositivos = {}
        self._responsive_after_id = None
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
        fit_toplevel_to_workarea(self.top_level_configuracion, 1320, 860, min_width=1080, min_height=680)
        self.top_level_configuracion.minsize(1040, 660)
        self.top_level_configuracion.place_window_center()
        self.top_level_configuracion.bind("<Configure>", self._programar_layout_responsivo, add="+")
        self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja").bind(
            "<<DispositivosActualizados>>",
            self._refrescar_dispositivos_desde_evento,
            add="+",
        )
        
        self.notebook_widget_configuracion = ttk.Notebook(self.top_level_configuracion, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_CONFIG","notebook_widget_configuracion", self.notebook_widget_configuracion)
        self.creacion_frame_notebook_dispositivos()
        self.creacion_frame_notebook_fuente_datos()
        self.creacion_frame_notebook_config_datos()
        self.creacion_frame_notebook_usuarios_permisos()
        self.creacion_frame_notebook_go_upc()
        
        self.notebook_widget_configuracion.add(self.frame_notebook_dispositivos, text="Dispositivos", padding=10)
        self.notebook_widget_configuracion.add(self.frame_notebook_fuente_datos, text="Fuente de Datos", padding=10)
        self.notebook_widget_configuracion.add(self.frame_notebook_config_datos, text="Configuración de Datos", padding=10)
        self.notebook_widget_configuracion.add(self.frame_notebook_usuarios_permisos, text="Usuarios y Permisos", padding=10)
        self.notebook_widget_configuracion.add(self.frame_notebook_go_upc, text="Conexión GO-UPC", padding=10)

        self.notebook_widget_configuracion.pack(side="top", expand=True, fill="both", padx=8, pady=8)
        self._aplicar_layout_responsivo()

    def _programar_layout_responsivo(self, _event=None):
        if self._responsive_after_id:
            try:
                self.top_level_configuracion.after_cancel(self._responsive_after_id)
            except Exception:
                pass
        self._responsive_after_id = self.top_level_configuracion.after(80, self._aplicar_layout_responsivo)

    def _aplicar_layout_responsivo(self):
        self._responsive_after_id = None
        try:
            width = max(self.top_level_configuracion.winfo_width(), get_workarea_size(self.top_level_configuracion)[0])
            height = max(self.top_level_configuracion.winfo_height(), get_workarea_size(self.top_level_configuracion)[1])
            size_class = get_size_class(width, height)
            ancho_util = min(width, 1540)
            padding_lateral = max(int((width - ancho_util) / 2), PANEL_PAD_X - 8)

            if size_class == "compact":
                combo_width = 34
                combo_perfiles_width = 24
                combo_fuente_width = 28
                mostrar_texto_botones = False
            elif size_class == "standard":
                combo_width = 40
                combo_perfiles_width = 28
                combo_fuente_width = 34
                mostrar_texto_botones = True
            else:
                combo_width = 46
                combo_perfiles_width = 32
                combo_fuente_width = 40
                mostrar_texto_botones = True

            if hasattr(self, "combobox_dispositivos"):
                self.combobox_dispositivos.configure(width=combo_width)
            if hasattr(self, "combobox_perfiles_permiso"):
                self.combobox_perfiles_permiso.configure(width=combo_perfiles_width)
            if hasattr(self, "combobox_lista_fuente_datos"):
                self.combobox_lista_fuente_datos.configure(width=combo_fuente_width)
            if hasattr(self, "combobox_odbc"):
                self.combobox_odbc.configure(width=combo_fuente_width + 4)
            if hasattr(self, "labelframe_opciones"):
                self.labelframe_opciones.pack_configure(padx=padding_lateral)
            if hasattr(self, "labelframe_datos_dispositivos"):
                self.labelframe_datos_dispositivos.pack_configure(padx=padding_lateral)
            if hasattr(self, "labelframe_conexion_fuente_datos"):
                self.labelframe_conexion_fuente_datos.pack_configure(padx=padding_lateral)
            if hasattr(self, "labelframe_datos_de_conexion_fuente_datos"):
                self.labelframe_datos_de_conexion_fuente_datos.pack_configure(padx=padding_lateral)
            if hasattr(self, "frame_logo_config_datos"):
                self.frame_logo_config_datos.pack_configure(padx=padding_lateral)
            if hasattr(self, "frame_guia_imagenes"):
                self.frame_guia_imagenes.pack_configure(padx=padding_lateral)
            if hasattr(self, "frame_automatizacion_config_datos"):
                self.frame_automatizacion_config_datos.pack_configure(padx=padding_lateral)
            if hasattr(self, "frame_superior_usuarios"):
                self.frame_superior_usuarios.pack_configure(padx=padding_lateral)
            if hasattr(self, "frame_perfiles_usuarios"):
                self.frame_perfiles_usuarios.pack_configure(padx=padding_lateral)
            if hasattr(self, "frame_editor_usuarios"):
                self.frame_editor_usuarios.pack_configure(padx=padding_lateral)
            if hasattr(self, "frame_acciones_usuarios"):
                self.frame_acciones_usuarios.pack_configure(padx=padding_lateral)
            if hasattr(self, "labelframe_go_upc"):
                self.labelframe_go_upc.pack_configure(padx=padding_lateral)
            if hasattr(self, "label_info_notebook_config_datos"):
                self.label_info_notebook_config_datos.configure(wraplength=max(ancho_util - 180, 320))
            if hasattr(self, "label_usuario_windows_actual"):
                self.label_usuario_windows_actual.configure(wraplength=max(ancho_util - 220, 320))
            if hasattr(self, "label_rol_windows_actual"):
                self.label_rol_windows_actual.configure(wraplength=max(ancho_util - 220, 320))
            if hasattr(self, "label_permisos_efectivos"):
                self.label_permisos_efectivos.configure(wraplength=max(ancho_util - 220, 320))
            if hasattr(self, "label_info_permisos"):
                self.label_info_permisos.configure(wraplength=max(int(ancho_util * 0.34), 260), justify="right")
            if hasattr(self, "lbl_estado_go_upc"):
                self.lbl_estado_go_upc.configure(wraplength=max(ancho_util - 180, 320))
            if hasattr(self, "lbl_estado_api_imagenes"):
                self.lbl_estado_api_imagenes.configure(wraplength=max(ancho_util - 180, 320))
            if hasattr(self, "tree_perfiles_usuario"):
                self.tree_perfiles_usuario.column("usuario", width=clamp(int(ancho_util * 0.20), 180, 280), anchor="w")
                self.tree_perfiles_usuario.column("admin_windows", width=clamp(int(ancho_util * 0.09), 100, 130), anchor="center")
                self.tree_perfiles_usuario.column("estado", width=clamp(int(ancho_util * 0.13), 120, 170), anchor="center")
                self.tree_perfiles_usuario.column("productos", width=clamp(int(ancho_util * 0.09), 95, 120), anchor="center")
                self.tree_perfiles_usuario.column("publicidad", width=clamp(int(ancho_util * 0.09), 95, 120), anchor="center")
                self.tree_perfiles_usuario.column("configuracion", width=clamp(int(ancho_util * 0.11), 110, 145), anchor="center")
            self._reordenar_toolbar_dispositivos(mostrar_texto_botones)
        except Exception:
            pass

    def _reordenar_toolbar_dispositivos(self, mostrar_texto_botones):
        if not hasattr(self, "frame_contenedor_botones"):
            return

        botones = [
            self.button_agregar,
            self.button_editar,
            self.button_eliminar,
            self.button_guardar,
            self.button_estado,
            self.button_player,
            self.button_buscar_red,
        ]

        for i in range(7):
            self.frame_contenedor_botones.columnconfigure(i, weight=0)

        for button in botones:
            button.grid_forget()

        width_actual = max(self.top_level_configuracion.winfo_width(), 1040)
        compacto = width_actual < 1220

        if mostrar_texto_botones:
            self.button_estado.configure(text="Estado")
            self.button_player.configure(text="Player")
            self.button_buscar_red.configure(text="Buscar red")
        else:
            self.button_estado.configure(text="Estado")
            self.button_player.configure(text="Player")
            self.button_buscar_red.configure(text="Red")

        if compacto:
            for col in range(4):
                self.frame_contenedor_botones.columnconfigure(col, weight=1)
            layout = [
                (self.button_agregar, 0, 0),
                (self.button_editar, 0, 1),
                (self.button_eliminar, 0, 2),
                (self.button_guardar, 0, 3),
                (self.button_estado, 1, 0),
                (self.button_player, 1, 1),
                (self.button_buscar_red, 1, 2),
            ]
            for button, row, col in layout:
                    colspan = 2 if button is self.button_buscar_red else 1
                    button.grid(
                        row=row,
                        column=col,
                        columnspan=colspan,
                        padx=BUTTON_PAD_X,
                        pady=BUTTON_PAD_Y,
                        sticky="ew",
                    )
        else:
            for col in range(7):
                self.frame_contenedor_botones.columnconfigure(col, weight=1)
            self.button_agregar.grid(row=0, column=0, padx=BUTTON_PAD_X, sticky="ew")
            self.button_editar.grid(row=0, column=1, padx=BUTTON_PAD_X, sticky="ew")
            self.button_eliminar.grid(row=0, column=2, padx=BUTTON_PAD_X, sticky="ew")
            self.button_guardar.grid(row=0, column=3, padx=BUTTON_PAD_X, sticky="ew")
            self.button_estado.grid(row=0, column=4, padx=(BUTTON_PAD_X + 4, BUTTON_PAD_X), sticky="ew")
            self.button_player.grid(row=0, column=5, padx=(BUTTON_PAD_X, max(1, BUTTON_PAD_X - 3)), sticky="ew")
            self.button_buscar_red.grid(row=0, column=6, padx=(BUTTON_PAD_X + 2, 0), sticky="ew")

    def _crear_textarea_base(self, parent, height=4, width=None):
        kwargs = {"height": height, "wrap": "word"}
        if width is not None:
            kwargs["width"] = width
        text_widget = ttk.Text(parent, **kwargs)
        text_widget.configure(relief="solid", borderwidth=1)
        return text_widget

    def _set_textarea_value(self, widget, value, readonly=True):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        if readonly:
            widget.config(state="disabled")

    def _refrescar_dispositivos_desde_evento(self, _event=None):
        try:
            nombre_actual = self.combobox_dispositivos.get() if hasattr(self, "combobox_dispositivos") else ""
            self.datos_dispositivos = self.dispositivos_dao.listar_dict()
            nombres = list(self.datos_dispositivos.keys())
            if hasattr(self, "combobox_dispositivos"):
                self.combobox_dispositivos.config(values=nombres)
                if nombre_actual in self.datos_dispositivos:
                    self.combobox_dispositivos.set(nombre_actual)
                elif not nombres:
                    self.combobox_dispositivos.set("")
            self.top_level_configuracion.update_idletasks()
        except Exception:
            pass
        
        
#///////////////////////////////////////////////////// NOTEBOOK DISPOSITIVOS /////////////////////////////////////////////////////
        
    def creacion_frame_notebook_dispositivos(self):
        self.frame_notebook_dispositivos = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_dispositivos.pack(fill="both", expand=True)
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_notebook_dispositivos", self.frame_notebook_dispositivos)
        
        
        self.labelframe_opciones = ttk.Labelframe(
            self.frame_notebook_dispositivos,
            text="Opciones",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 4, PANEL_PAD_Y - 4),
        )
        self.labelframe_opciones.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(PANEL_PAD_Y - 4, 8))
        self.DICT_WIDGETS.register("GUI_CONFIG","labelframe_opciones", self.labelframe_opciones)
        self.creacion_contenido_labelframe_opciones()
        
        
        self.labelframe_datos_dispositivos = ttk.Labelframe(
            self.frame_notebook_dispositivos,
            text="Datos de Dispositivo",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 4, PANEL_PAD_Y - 4),
        )
        self.labelframe_datos_dispositivos.pack(fill="both", expand=True, padx=PANEL_PAD_X - 8, pady=(0, PANEL_PAD_Y - 4))
        self.DICT_WIDGETS.register("GUI_CONFIG","labelframe_datos_dispositivos", self.labelframe_datos_dispositivos)
        self.creacion_labelframe_datos_dispositivos()       
        
        
    def creacion_contenido_labelframe_opciones(self):
        self.frame_contenedor_combobox_dispositivos = ttk.Frame(self.labelframe_opciones)
        self.frame_contenedor_combobox_dispositivos.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, PANEL_PAD_X - 8),
            pady=0,
        )
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_contenedor_combobox_dispositivos", self.frame_contenedor_combobox_dispositivos)
        self.creacion_contenido_frame_contenedor_combobox_dispositivos()
        
        self.frame_contenedor_botones = ttk.Frame(self.labelframe_opciones)
        self.frame_contenedor_botones.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(PANEL_PAD_X - 8, 0),
            pady=0,
        )
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
        self.button_agregar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_agregar, command=self.command_button_agregar, compound="center" ,bootstyle="success-outline", width=4, padding=(8, 8))
        ToolTip(self.button_agregar, text="Agregar Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_agregar", self.button_agregar)
        self.button_editar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_editar, command=self.command_button_editar_dispositivo, compound="center" ,bootstyle="info-outline", width=4, state="disable", padding=(8, 8))
        ToolTip(self.button_editar, text="Editar datos de Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_editar", self.button_editar)
        self.button_eliminar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_eliminar, command=self.command_button_eliminar, compound="center" ,bootstyle="danger-outline", width=4, state="disable", padding=(8, 8))
        ToolTip(self.button_eliminar, text="Eliminar Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_eliminar", self.button_eliminar)
        self.button_guardar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_guardar, compound="center" ,bootstyle="primary", width=4, padding=(8, 8))
        ToolTip(self.button_guardar, text="Guardar configuración de Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_guardar", self.button_guardar)
        self.button_estado = ttk.Button(
            self.frame_contenedor_botones,
            text="Estado",
            command=self.command_button_estado_dispositivo,
            bootstyle="outline",
            width=10,
            state="disable",
            padding=(12, 8),
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
            padding=(12, 8),
        )
        ToolTip(self.button_player, text="Configurar pantalla y parametros del player")
        self.DICT_WIDGETS.register("GUI_CONFIG", "button_player", self.button_player)
        self.button_buscar_red = ttk.Button(
            self.frame_contenedor_botones,
            text="Buscar red",
            command=self.command_button_buscar_dispositivos_red,
            bootstyle="info-outline",
            width=12,
            padding=(12, 8),
        )
        ToolTip(self.button_buscar_red, text="Detectar verificadores e InforTV en la red local")
        self.DICT_WIDGETS.register("GUI_CONFIG", "button_buscar_red", self.button_buscar_red)

        # Posicionamiento con grid (alineados al centro)
        self.frame_contenedor_botones.columnconfigure(0, weight=1)
        self.frame_contenedor_botones.columnconfigure(1, weight=1)
        self.frame_contenedor_botones.columnconfigure(2, weight=1)
        self.frame_contenedor_botones.columnconfigure(3, weight=1)
        self.frame_contenedor_botones.columnconfigure(4, weight=1)
        self.frame_contenedor_botones.columnconfigure(5, weight=1)
        self.frame_contenedor_botones.columnconfigure(6, weight=1)

        self.button_agregar.grid(row=0, column=0, padx=BUTTON_PAD_X)
        self.button_editar.grid(row=0, column=1, padx=BUTTON_PAD_X)
        self.button_eliminar.grid(row=0, column=2, padx=BUTTON_PAD_X)
        self.button_guardar.grid(row=0, column=3, padx=BUTTON_PAD_X)
        self.button_estado.grid(row=0, column=4, padx=(BUTTON_PAD_X + 4, BUTTON_PAD_X))
        self.button_player.grid(row=0, column=5, padx=(BUTTON_PAD_X, max(1, BUTTON_PAD_X - 3)))
        self.button_buscar_red.grid(row=0, column=6, padx=(BUTTON_PAD_X + 2, 0))
        
    def creacion_contenido_frame_contenedor_combobox_dispositivos(self):
        self.frame_label_combobox_dispositivos = ttk.Label(
            self.frame_contenedor_combobox_dispositivos,
            text="Seleccione su dispositivo:",
            font=FONT_BODY_BOLD,
        )
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_label_combobox_dispositivos", self.frame_label_combobox_dispositivos)
        self.frame_label_combobox_dispositivos.pack(side="left", padx=(0, PANEL_PAD_X - 6))
        
        self.combobox_dispositivos = ttk.Combobox(self.frame_contenedor_combobox_dispositivos, values=self.actualizar_datos_combobox(), state="readonly", width=42)
        self.combobox_dispositivos.bind("<<ComboboxSelected>>", self.seleccion_dispositivo)
        self.DICT_WIDGETS.register("GUI_CONFIG","combobox_dispositivos", self.combobox_dispositivos)
        self.combobox_dispositivos.pack(side="right", fill="x", expand=True, ipady=4)
        
    def creacion_contenido_toplevel_button_agregar(self):
        self.creacion_labelframe_nuevo_dispositivo_button_agregar()
        self.creacion_labelframe_datos_button_agregar()
        self.button_agregar_dispositivo = ttk.Button(self.toplevel_button_agregar, text="Agregar", command=self.command_button_agregar_dispositivo)
        self.button_agregar_dispositivo.pack(pady=(0, PANEL_PAD_Y - 6))
        
    def creacion_labelframe_nuevo_dispositivo_button_agregar(self):
        self.labelframe_nuevo_dispositivo_button_agregar = ttk.Labelframe(
            self.toplevel_button_agregar,
            text="Nuevo dispositivo",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 6, PANEL_PAD_Y - 6),
        )
        self.labelframe_nuevo_dispositivo_button_agregar.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(PANEL_PAD_Y - 4, 6))

        self.label_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos = ttk.Label(
            self.labelframe_nuevo_dispositivo_button_agregar,
            text="Nombre del equipo:",
            font=FONT_BODY_BOLD,
        )
        self.label_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.pack(
            side="left",
            pady=BUTTON_PAD_Y + 4,
            padx=(0, PANEL_PAD_X - 8),
        )

        self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos = ttk.Entry(self.labelframe_nuevo_dispositivo_button_agregar)
        self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.pack(
            side="right",
            pady=BUTTON_PAD_Y + 4,
            fill="x",
            expand=True,
        )
        
    def creacion_labelframe_datos_button_agregar(self):
        self.labelframe_datos_button_agregar = ttk.Labelframe(
            self.toplevel_button_agregar,
            text="Datos de conexión",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 6, PANEL_PAD_Y - 6),
        )
        self.labelframe_datos_button_agregar.pack(fill="both", expand=True, padx=PANEL_PAD_X - 8, pady=(0, PANEL_PAD_Y - 6))
        
        # Dirección IP/RED
        self.label_direccion_ip = ttk.Label(self.labelframe_datos_button_agregar, text="Dirección IP/RED:", font=FONT_BODY_BOLD)
        self.entry_direccion_ip = ttk.Entry(self.labelframe_datos_button_agregar)

        # Puerto
        self.label_puerto = ttk.Label(self.labelframe_datos_button_agregar, text="PUERTO:", font=FONT_BODY_BOLD)
        self.entry_puerto = ttk.Entry(self.labelframe_datos_button_agregar)

        # Comentario (más grande)
        self.label_comentario = ttk.Label(self.labelframe_datos_button_agregar, text="COMENTARIO:", font=FONT_BODY_BOLD)
        self.text_comentario = self._crear_textarea_base(self.labelframe_datos_button_agregar, height=4, width=30)

        # Posicionar con grid
        self.label_direccion_ip.grid(row=0, column=0, sticky="w", padx=(0, BUTTON_PAD_X), pady=BUTTON_PAD_Y)
        self.entry_direccion_ip.grid(row=0, column=1, sticky="ew", padx=(BUTTON_PAD_X, 0), pady=BUTTON_PAD_Y)

        self.label_puerto.grid(row=1, column=0, sticky="w", padx=(0, BUTTON_PAD_X), pady=BUTTON_PAD_Y)
        self.entry_puerto.grid(row=1, column=1, sticky="ew", padx=(BUTTON_PAD_X, 0), pady=BUTTON_PAD_Y)

        self.label_comentario.grid(row=2, column=0, sticky="w", padx=(0, BUTTON_PAD_X), pady=BUTTON_PAD_Y)
        self.text_comentario.grid(row=2, column=1, sticky="ew", padx=(BUTTON_PAD_X, 0), pady=BUTTON_PAD_Y)

        # Expandir entradas en el contenedor
        self.labelframe_datos_button_agregar.columnconfigure(1, weight=1)
        
    def creacion_labelframe_datos_dispositivos(self):
        self.frame_contenedor_labelframe_datos_dispositivo = ttk.Frame(
            self.labelframe_datos_dispositivos,
            padding=(PANEL_PAD_X + 2, PANEL_PAD_Y + 2),
        )

        self.label_nombre_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="Seleccione un dispositivo",
            font=FONT_TITLE_LG,
        )
        self.label_nombre_contenido_labelframe_opciones.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, PANEL_PAD_Y + 6),
        )

        self.label_direccion_ip_izq_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="Dirección IP / Red",
            font=FONT_LABEL_BOLD,
        )
        self.label_direccion_ip_izq_contenido_labelframe_opciones.grid(row=1, column=0, sticky="w", pady=(0, 8), padx=(0, 14))
        self.label_direccion_ip_der_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="-",
            font=FONT_SUBTITLE,
            bootstyle="secondary",
        )
        self.label_direccion_ip_der_contenido_labelframe_opciones.grid(row=1, column=1, sticky="ew", pady=(0, 8))

        self.label_puerto_izq_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="Puerto",
            font=FONT_LABEL_BOLD,
        )
        self.label_puerto_izq_contenido_labelframe_opciones.grid(row=2, column=0, sticky="w", pady=(0, 8), padx=(0, 14))
        self.label_puerto_der_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="-",
            font=FONT_SUBTITLE,
            bootstyle="secondary",
        )
        self.label_puerto_der_contenido_labelframe_opciones.grid(row=2, column=1, sticky="ew", pady=(0, 8))

        self.label_comentario_contenido_labelframe_opciones = ttk.Label(
            self.frame_contenedor_labelframe_datos_dispositivo,
            text="Comentario",
            font=FONT_LABEL_BOLD,
        )
        self.label_comentario_contenido_labelframe_opciones.grid(row=3, column=0, sticky="nw", pady=(10, 6), padx=(0, 14))

        self.text_comentario_contenido_labelframe_opciones = self._crear_textarea_base(
            self.frame_contenedor_labelframe_datos_dispositivo,
            height=10,
        )
        self._set_textarea_value(self.text_comentario_contenido_labelframe_opciones, "Sin comentario")
        self.text_comentario_contenido_labelframe_opciones.grid(row=3, column=1, sticky="nsew", pady=(10, 6))

        self.frame_contenedor_labelframe_datos_dispositivo.columnconfigure(1, weight=1)
        self.frame_contenedor_labelframe_datos_dispositivo.rowconfigure(3, weight=1)

#///////////////////////////////////////////////////// NOTEBOOK FUENTE DE DATOS /////////////////////////////////////////////////////

    def creacion_frame_notebook_fuente_datos(self):
        self.frame_notebook_fuente_datos = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_fuente_datos.pack(fill="both", expand=True)  # Corrección aquí
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_notebook_fuente_datos", self.frame_notebook_fuente_datos)

        self.labelframe_conexion_fuente_datos = ttk.Labelframe(
            self.frame_notebook_fuente_datos,
            text="Conexiones disponibles",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 2, PANEL_PAD_Y - 2),
        )
        self.labelframe_conexion_fuente_datos.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(PANEL_PAD_Y - 4, 8))

        self.frame_selector_fuente_datos = ttk.Frame(self.labelframe_conexion_fuente_datos)
        self.frame_selector_fuente_datos.pack(fill="x")
        self.frame_selector_fuente_datos.columnconfigure(1, weight=1)

        lista_conexiones_disponibles = ["Conexión ODBC"]
        self.label_tipo_conexion = ttk.Label(
            self.frame_selector_fuente_datos,
            text="Tipos de conexiones:",
            font=FONT_BODY_BOLD,
        )
        self.label_tipo_conexion.grid(row=0, column=0, sticky="w", padx=(0, PANEL_PAD_X - 8))
        self.combobox_lista_fuente_datos = ttk.Combobox(
            self.frame_selector_fuente_datos,
            values=lista_conexiones_disponibles,
            state="readonly",
        )
        self.combobox_lista_fuente_datos.grid(row=0, column=1, sticky="ew")
        self.combobox_lista_fuente_datos.configure(width=36)
        self.combobox_lista_fuente_datos.bind("<<ComboboxSelected>>", self.bind_combobox_lista_fuente_datos)
        
        
        self.labelframe_datos_de_conexion_fuente_datos = ttk.Labelframe(
            self.frame_notebook_fuente_datos,
            text="Datos de conexión",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 2, PANEL_PAD_Y - 2),
        )
        self.labelframe_datos_de_conexion_fuente_datos.pack(fill="both", expand=True, padx=PANEL_PAD_X - 8, pady=(0, PANEL_PAD_Y - 4))

        
        
        
        
    def bind_combobox_lista_fuente_datos(self, event):
        if self.combobox_lista_fuente_datos.get() == "Conexión ODBC":
            self.mostrar_widgets_ODBC()
            self.obtener_datos_conexion_odbc()
        
        
        
        
    def mostrar_widgets_ODBC(self):
        if hasattr(self, "frame_contenido_opcion_odbc") and self.frame_contenido_opcion_odbc.winfo_exists():
            self.frame_contenido_opcion_odbc.destroy()
        if hasattr(self, "frame_acciones_fuente_datos") and self.frame_acciones_fuente_datos.winfo_exists():
            self.frame_acciones_fuente_datos.destroy()

        self.frame_contenido_opcion_odbc = ttk.Frame(self.labelframe_datos_de_conexion_fuente_datos)
        self.frame_contenido_opcion_odbc.pack(fill="both", expand=True, padx=(PANEL_PAD_X + 8, PANEL_PAD_X + 8), pady=(PANEL_PAD_Y + 6, PANEL_PAD_Y))
        self.frame_contenido_opcion_odbc.columnconfigure(1, weight=1)

        self.frame_odbc = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_odbc.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, BUTTON_PAD_Y + 8))
        self.frame_odbc.columnconfigure(1, weight=1)

        self.label_odbc = ttk.Label(self.frame_odbc, text="Conexión ODBC:", font=FONT_BODY_BOLD)
        self.label_odbc.grid(row=0, column=0, sticky="w", padx=(0, BUTTON_PAD_X + 4))

        self.combobox_odbc = ttk.Combobox(self.frame_odbc, values=self.obtener_listaDSN(), state="readonly")
        self.combobox_odbc.grid(row=0, column=1, sticky="ew", ipady=4)

        self.frame_user = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_user.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, BUTTON_PAD_Y + 8))
        self.frame_user.columnconfigure(1, weight=1)

        self.label_user = ttk.Label(self.frame_user, text="User ID:", font=FONT_BODY_BOLD)
        self.label_user.grid(row=0, column=0, sticky="w", padx=(0, BUTTON_PAD_X + 4))

        self.entry_user = ttk.Entry(self.frame_user)
        self.entry_user.grid(row=0, column=1, sticky="ew", ipady=4)

        self.frame_password = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_password.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, BUTTON_PAD_Y + 8))
        self.frame_password.columnconfigure(1, weight=1)

        self.label_password = ttk.Label(self.frame_password, text="Password:", font=FONT_BODY_BOLD)
        self.label_password.grid(row=0, column=0, sticky="w", padx=(0, BUTTON_PAD_X + 4))

        self.entry_password = ttk.Entry(self.frame_password, show="*")
        self.entry_password.grid(row=0, column=1, sticky="ew", ipady=4)
        
        
        self.frame_checkbox = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_checkbox.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(BUTTON_PAD_Y + 4, 0))

        self.checkbox_var = ttk.BooleanVar()
        self.checkbox = ttk.Checkbutton(self.frame_checkbox, text="Conexión a DBA de Inforhard Sistemas", variable=self.checkbox_var)
        self.checkbox.pack(side="left")

        self.frame_acciones_fuente_datos = ttk.Frame(self.labelframe_datos_de_conexion_fuente_datos)
        self.frame_acciones_fuente_datos.pack(fill="x", padx=(PANEL_PAD_X + 8, PANEL_PAD_X + 8), pady=(0, PANEL_PAD_Y - 2), side="bottom")
        self.button_agregar_datos_de_conexion = ttk.Button(
            self.frame_acciones_fuente_datos,
            text="Guardar conexión",
            command=self.command_button_agregar_datos_de_conexion,
            bootstyle="success",
            padding=(14, 8),
        )
        self.button_agregar_datos_de_conexion.pack(side="left")
    
    def validar_campos(self):
        """Verifica que los campos no estén vacíos."""
        campos = {
            "Nuevo dispositivo": self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.get().strip(),
            "Dirección IP/RED": self.entry_direccion_ip.get().strip(),
            "PUERTO": self.entry_puerto.get().strip(),
            "COMENTARIO": self.text_comentario.get("1.0", "end").strip()  # Obtener texto desde Text
        }

        for campo, valor in campos.items():
            if not valor:  # Si el campo está vacío
                messagebox.showwarning("Campo vacío", f"El campo '{campo}' no puede estar vacío.")
                return False

        return True  # Si todos los campos tienen datos       
    
    
    def obtener_listaDSN(self):
        datos = dsn_configurados()
        dsnLIST = []
        for dsnNAME, dsnDRIVER in datos.items():
            cadena = dsnNAME.decode('utf-8')
            dsnLIST.append(cadena)
        return dsnLIST
    
#///////////////////////////////////////////////////// NOTEBOOK CONFIGURACIÓN DE DATOS /////////////////////////////////////////////////////

    def creacion_frame_notebook_config_datos(self):
        self.frame_notebook_config_datos = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_config_datos.pack(fill="both", expand=True)
        
        self.frame_logo_config_datos = ttk.Labelframe(
            self.frame_notebook_config_datos,
            text="Logo Principal",
            padding=(PANEL_PAD_X - 2, PANEL_PAD_Y - 2),
        )
        self.frame_logo_config_datos.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(PANEL_PAD_Y - 4, 10))

        self.label_logo_preview = ttk.Label(self.frame_logo_config_datos, width=200)
        self.label_logo_preview.pack(fill="both", expand=True, padx=10, pady=10)
        self.label_logo_preview.config(anchor="center")
        self.label_logo_preview.config(style="preview.TLabel")



        self._mostrar_logo_actual()
        # Contenedor para los botones en línea
        frame_botones_logo = ttk.Frame(self.frame_logo_config_datos)
        frame_botones_logo.pack(fill="x", pady=(8, 4))

        # Botón izquierda
        ttk.Button(frame_botones_logo, text="Seleccionar Imagen", command=self._seleccionar_logo, bootstyle="primary", padding=(12, 8)).pack(side="left", padx=(0, 6))
        ttk.Button(frame_botones_logo, text="Normalizar Logo", command=self._normalizar_logo_seleccionado, bootstyle="secondary", padding=(12, 8)).pack(side="left", padx=(0, 6))

        # Botón derecha
        ttk.Button(frame_botones_logo, text="Enviar Logo a Dispositivos", command=self._enviar_logo_a_dispositivos, bootstyle="success", padding=(12, 8)).pack(side="right", padx=(6, 0))

        self.label_validacion_logo = ttk.Label(
            self.frame_logo_config_datos,
            text="Sin imagen seleccionada.",
            bootstyle="secondary",
            justify="left",
            font=FONT_SUBTITLE,
        )
        self.label_validacion_logo.pack(fill="x", padx=10, pady=(6, 2))

        self._crear_panel_guia_imagenes()


        
        
        self.label_info_notebook_config_datos = ttk.Label(
            self.frame_notebook_config_datos,
            bootstyle="secondary",
            font=FONT_SUBTITLE,
        )
        self.label_info_notebook_config_datos.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(0, 8))
        
        
        
        datos_conexion = self.conexion_dao.obtener_todas()
        self.creacion_frame_config_datos_INFORHARD()
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        valor_configurado = config.get("sincronizacion_automatica", True)
        self.frame_automatizacion_config_datos = ttk.Labelframe(
            self.frame_notebook_config_datos,
            text="Automatización y envío",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 2, PANEL_PAD_Y - 2),
        )
        self.frame_automatizacion_config_datos.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(0, 10))

        self.auto_sync_var = BooleanVar(value=valor_configurado)
        # Crear checkbox de sincronización automática
        self.checkbox_auto_sync = ttk.Checkbutton(
            self.frame_automatizacion_config_datos,
            text="Sincronización automática de productos",
            variable=self.auto_sync_var,
            command=self.actualizar_config_sincronizacion_automatica
        )
        self.checkbox_auto_sync.pack(anchor="w", pady=(0, 12))

        valor_envio_auto = bool(config.get("envio_automatico_novedades", False)) and bool(valor_configurado)
        self.auto_send_news_var = BooleanVar(value=valor_envio_auto)
        self.checkbox_auto_send_news = ttk.Checkbutton(
            self.frame_automatizacion_config_datos,
            text="Envio automatico de novedades al detectar cambios",
            variable=self.auto_send_news_var,
            command=self.actualizar_config_envio_automatico_novedades,
        )
        self.checkbox_auto_send_news.pack(anchor="w", pady=(0, 12))
        self._actualizar_estado_checkbox_envio_auto()

        self.keep_video_audio_var = BooleanVar(
            value=bool(config.get("mantener_audio_publicidades", False))
        )
        self.checkbox_keep_video_audio = ttk.Checkbutton(
            self.frame_automatizacion_config_datos,
            text="Mantener audio en videos de publicidades (modo prueba)",
            variable=self.keep_video_audio_var,
            command=self.actualizar_config_audio_publicidades,
        )
        self.checkbox_keep_video_audio.pack(anchor="w")

        # Registrar en el diccionario global
        self.DICT_WIDGETS.register("VARIABLES_GLOBALES", "sincronizacion_automatica", self.auto_sync_var)
        self.DICT_WIDGETS.register("VARIABLES_GLOBALES", "envio_automatico_novedades", self.auto_send_news_var)
        self.DICT_WIDGETS.register("VARIABLES_GLOBALES", "mantener_audio_publicidades", self.keep_video_audio_var)
        
        if datos_conexion:  # Verifica si la lista NO está vacía
            datos_conexion = datos_conexion[0]
            if len(datos_conexion) > 3 and datos_conexion[3]:  # Verifica que haya al menos 4 elementos
                self.label_info_notebook_config_datos.config(
                    text="Se encontró conexión a la fuente de datos de Inforhard Sistema S.R.L"
                )
                self.frame_config_datos_INFORHARD.pack(fill="both", expand=True)
            else:
                self.label_info_notebook_config_datos.config(
                    text="No se encontró conexión a una fuente de datos"
                )
        else:
            self.label_info_notebook_config_datos.config(
                text="No se encontró ninguna conexión a una fuente de datos"
            )

    def creacion_frame_notebook_usuarios_permisos(self):
        self.frame_notebook_usuarios_permisos = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_usuarios_permisos.pack(fill="both", expand=True)
        self.DICT_WIDGETS.register("GUI_CONFIG", "frame_notebook_usuarios_permisos", self.frame_notebook_usuarios_permisos)

        self.frame_superior_usuarios = ttk.Labelframe(
            self.frame_notebook_usuarios_permisos,
            text="Usuario actual",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 2, PANEL_PAD_Y - 2),
        )
        self.frame_superior_usuarios.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(PANEL_PAD_Y - 4, 6))
        self.frame_superior_usuarios.columnconfigure(0, weight=1)

        self.frame_resumen_usuarios = ttk.Frame(self.frame_superior_usuarios)
        self.frame_resumen_usuarios.pack(fill="x")
        self.frame_resumen_usuarios.columnconfigure(0, weight=1)

        self.label_usuario_windows_actual = ttk.Label(
            self.frame_resumen_usuarios,
            text="Usuario Windows: -",
            font=FONT_LABEL_BOLD,
        )
        self.label_usuario_windows_actual.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.label_rol_windows_actual = ttk.Label(
            self.frame_resumen_usuarios,
            text="Rol Windows: -",
            bootstyle="info",
            font=FONT_SUBTITLE,
        )
        self.label_rol_windows_actual.grid(row=1, column=0, sticky="w", pady=(0, 6))

        self.label_permisos_efectivos = ttk.Label(
            self.frame_resumen_usuarios,
            text="Permisos efectivos: -",
            bootstyle="secondary",
            font=FONT_SUBTITLE,
            justify="left",
        )
        self.label_permisos_efectivos.grid(row=2, column=0, sticky="w")

        self.frame_perfiles_usuarios = ttk.Labelframe(
            self.frame_notebook_usuarios_permisos,
            text="Perfiles configurados",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 2, PANEL_PAD_Y - 2),
        )
        self.frame_perfiles_usuarios.pack(fill="both", expand=True, padx=PANEL_PAD_X - 8, pady=(0, 10))

        self.frame_tree_perfiles = ttk.Frame(self.frame_perfiles_usuarios)
        self.frame_tree_perfiles.pack(fill="both", expand=True)

        columnas = ("usuario", "admin_windows", "estado", "productos", "publicidad", "configuracion")
        self.tree_perfiles_usuario = ttk.Treeview(
            self.frame_tree_perfiles,
            columns=columnas,
            show="headings",
            height=8,
            bootstyle="primary",
        )
        self.tree_perfiles_usuario.heading("usuario", text="Usuario / Perfil")
        self.tree_perfiles_usuario.heading("admin_windows", text="Admin Windows")
        self.tree_perfiles_usuario.heading("estado", text="Estado")
        self.tree_perfiles_usuario.heading("productos", text="Productos")
        self.tree_perfiles_usuario.heading("publicidad", text="Publicidad")
        self.tree_perfiles_usuario.heading("configuracion", text="Configuración")
        self.tree_perfiles_usuario.column("usuario", width=190, anchor="w")
        self.tree_perfiles_usuario.column("admin_windows", width=110, anchor="center")
        self.tree_perfiles_usuario.column("estado", width=140, anchor="center")
        self.tree_perfiles_usuario.column("productos", width=110, anchor="center")
        self.tree_perfiles_usuario.column("publicidad", width=110, anchor="center")
        self.tree_perfiles_usuario.column("configuracion", width=130, anchor="center")
        self.tree_perfiles_usuario.pack(fill="both", expand=True, side="left")

        scroll_y = ttk.Scrollbar(self.frame_tree_perfiles, orient="vertical", command=self.tree_perfiles_usuario.yview)
        scroll_y.pack(side="right", fill="y")
        self.tree_perfiles_usuario.configure(yscrollcommand=scroll_y.set)
        self.tree_perfiles_usuario.bind("<<TreeviewSelect>>", self._seleccionar_perfil_desde_tabla)

        self.frame_editor_usuarios = ttk.Labelframe(
            self.frame_notebook_usuarios_permisos,
            text="Editar perfil",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 2, PANEL_PAD_Y - 2),
        )
        self.frame_editor_usuarios.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(0, 10))
        self.frame_editor_usuarios.columnconfigure(1, weight=1)
        self.frame_editor_usuarios.columnconfigure(2, weight=1)

        ttk.Label(self.frame_editor_usuarios, text="Perfil / usuario Windows:", font=FONT_BODY_BOLD).grid(row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 10))
        self.perfil_permiso_var = StringVar()
        self.combobox_perfiles_permiso = ttk.Combobox(
            self.frame_editor_usuarios,
            textvariable=self.perfil_permiso_var,
            state="readonly",
            width=30,
        )
        self.combobox_perfiles_permiso.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 10))
        self.combobox_perfiles_permiso.bind("<<ComboboxSelected>>", self._seleccionar_perfil_permiso)

        self.perm_productos_var = BooleanVar(value=False)
        self.perm_publicidad_var = BooleanVar(value=False)
        self.perm_configuracion_var = BooleanVar(value=False)

        self.frame_checks_usuarios = ttk.Frame(self.frame_editor_usuarios)
        self.frame_checks_usuarios.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.frame_checks_usuarios.columnconfigure(0, weight=1)
        self.frame_checks_usuarios.columnconfigure(1, weight=1)
        self.frame_checks_usuarios.columnconfigure(2, weight=1)

        ttk.Checkbutton(self.frame_checks_usuarios, text="Productos", variable=self.perm_productos_var).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Checkbutton(self.frame_checks_usuarios, text="Publicidad", variable=self.perm_publicidad_var).grid(row=0, column=1, sticky="w", pady=2)
        ttk.Checkbutton(self.frame_checks_usuarios, text="Configuración", variable=self.perm_configuracion_var).grid(row=0, column=2, sticky="w", pady=2)

        self.frame_acciones_usuarios = ttk.Frame(self.frame_notebook_usuarios_permisos)
        self.frame_acciones_usuarios.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(0, 10))

        self.button_refrescar_perfiles = ttk.Button(
            self.frame_acciones_usuarios,
            text="Refrescar",
            bootstyle="secondary-outline",
            command=self.refrescar_tab_usuarios_permisos,
            padding=(12, 8),
        )
        self.button_refrescar_perfiles.pack(side="left")

        self.button_nuevo_perfil = ttk.Button(
            self.frame_acciones_usuarios,
            text="Nuevo perfil",
            bootstyle="info-outline",
            command=self._crear_nuevo_perfil_permiso,
            padding=(12, 8),
        )
        self.button_nuevo_perfil.pack(side="left", padx=(8, 0))

        self.button_guardar_perfil = ttk.Button(
            self.frame_acciones_usuarios,
            text="Guardar permisos",
            bootstyle="success",
            command=self._guardar_perfil_permiso,
            padding=(14, 8),
        )
        self.button_guardar_perfil.pack(side="left", padx=(8, 0))

        self.label_info_permisos = ttk.Label(
            self.frame_acciones_usuarios,
            text="Los cambios aplican al próximo ingreso del usuario afectado.",
            bootstyle="secondary",
            font=FONT_SUBTITLE,
            justify="right",
        )
        self.label_info_permisos.pack(side="right")

        self.refrescar_tab_usuarios_permisos()

    def refrescar_tab_usuarios_permisos(self):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json") or {}
        usuario_actual = self.DICT_WIDGETS.get_widget("CONFIG", "usuario_windows") or "-"
        usuario_actual_es_admin = bool(self.DICT_WIDGETS.get_widget("CONFIG", "usuario_windows_es_admin"))
        permisos_actuales = self.DICT_WIDGETS.get_widget("CONFIG", "permisos_usuario") or {}
        perfiles = config.get("perfiles_usuario", {})
        usuarios_windows = self._obtener_usuarios_windows_locales()
        usuarios_admin_windows = self._obtener_usuarios_admin_windows_locales()
        nombres_unificados = sorted(set(perfiles.keys()) | set(usuarios_windows))

        self.label_usuario_windows_actual.config(text=f"Usuario Windows: {usuario_actual}")
        self.label_rol_windows_actual.config(
            text=f"Rol Windows: {'Administrador local' if usuario_actual_es_admin else 'Usuario estándar'}"
        )
        self.label_permisos_efectivos.config(
            text=(
                "Permisos efectivos: "
                f"Productos={'Sí' if permisos_actuales.get('productos') else 'No'} | "
                f"Publicidad={'Sí' if permisos_actuales.get('publicidad') else 'No'} | "
                f"Configuración={'Sí' if permisos_actuales.get('configuracion') else 'No'}"
            )
        )

        for item in self.tree_perfiles_usuario.get_children():
            self.tree_perfiles_usuario.delete(item)

        for nombre_perfil in nombres_unificados:
            perfil_data = perfiles.get(nombre_perfil, {})
            modulos = perfil_data.get("modulos", {})
            perfil_existe = bool(perfil_data)
            if not perfil_existe:
                estado = "Detectado sin perfil"
            else:
                estado_guardado = str(perfil_data.get("estado", "") or "").strip().lower()
                if estado_guardado == "pendiente":
                    estado = "Pendiente"
                elif any(
                    (
                        bool(modulos.get("productos", False)),
                        bool(modulos.get("publicidad", False)),
                        bool(modulos.get("configuracion", False)),
                    )
                ):
                    estado = "Activo"
                else:
                    estado = "Pendiente"
            self.tree_perfiles_usuario.insert(
                "",
                "end",
                values=(
                    nombre_perfil,
                    "Sí" if nombre_perfil in usuarios_admin_windows else "No",
                    estado,
                    "Sí" if modulos.get("productos", False if not perfil_existe else True) else "No",
                    "Sí" if modulos.get("publicidad", False if not perfil_existe else True) else "No",
                    "Sí" if modulos.get("configuracion", False if not perfil_existe else True) else "No",
                ),
            )

        nombres = nombres_unificados
        self.combobox_perfiles_permiso.configure(values=nombres)
        perfil_actual = self.perfil_permiso_var.get().strip()
        if perfil_actual and perfil_actual in nombres:
            self._cargar_editor_perfil(perfil_actual)
        elif nombres:
            self.perfil_permiso_var.set(nombres[0])
            self._cargar_editor_perfil(nombres[0])
        else:
            self.perfil_permiso_var.set("")
            self.perm_productos_var.set(False)
            self.perm_publicidad_var.set(False)
            self.perm_configuracion_var.set(False)

    def _obtener_usuarios_windows_locales(self):
        comando = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_UserAccount -Filter \"LocalAccount=True\" | Select-Object -ExpandProperty Name",
        ]
        try:
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            return []

        if resultado.returncode != 0:
            return []

        ignorar = {
            "defaultaccount",
            "guest",
            "wdagutilityaccount",
            "defaultuser0",
        }

        usuarios = []
        for linea in resultado.stdout.splitlines():
            nombre = linea.strip()
            if not nombre:
                continue
            nombre_lower = nombre.lower()
            if nombre_lower in ignorar:
                continue
            usuarios.append(nombre_lower)

        return sorted(set(usuarios))

    def _obtener_usuarios_admin_windows_locales(self):
        comando = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$group = Get-LocalGroup -SID 'S-1-5-32-544' -ErrorAction SilentlyContinue; "
                "if ($null -eq $group) { exit 0 }; "
                "Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction SilentlyContinue | "
                "ForEach-Object { "
                "  $name = $_.Name; "
                "  if ($name -match '\\\\') { $name = $name.Split('\\\\')[-1] }; "
                "  $name "
                "}"
            ),
        ]
        try:
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            return set()

        if resultado.returncode != 0:
            return set()

        usuarios = set()
        for linea in resultado.stdout.splitlines():
            nombre = linea.strip()
            if not nombre:
                continue
            usuarios.add(nombre.lower())
        return usuarios

    def _cargar_editor_perfil(self, nombre_perfil):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json") or {}
        perfiles = config.get("perfiles_usuario", {})
        perfil_data = perfiles.get(nombre_perfil, {})
        modulos = perfil_data.get("modulos", {})
        perfil_existe = bool(perfil_data)
        self.perfil_permiso_var.set(nombre_perfil)
        self.perm_productos_var.set(bool(modulos.get("productos", False if not perfil_existe else True)))
        self.perm_publicidad_var.set(bool(modulos.get("publicidad", False if not perfil_existe else True)))
        self.perm_configuracion_var.set(bool(modulos.get("configuracion", False if not perfil_existe else True)))

    def _seleccionar_perfil_permiso(self, event=None):
        nombre_perfil = self.perfil_permiso_var.get().strip()
        if nombre_perfil:
            self._cargar_editor_perfil(nombre_perfil)

    def _seleccionar_perfil_desde_tabla(self, event=None):
        seleccion = self.tree_perfiles_usuario.selection()
        if not seleccion:
            return
        valores = self.tree_perfiles_usuario.item(seleccion[0], "values")
        if valores:
            self._cargar_editor_perfil(str(valores[0]))

    def _crear_nuevo_perfil_permiso(self):
        nombre = simpledialog.askstring(
            "Nuevo perfil",
            "Nombre del usuario/perfil Windows:",
            parent=self.top_level_configuracion,
        )
        if nombre is None:
            return
        nombre = nombre.strip().lower()
        if not nombre:
            messagebox.showwarning("Usuarios y Permisos", "Ingresá un nombre válido.")
            return

        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json") or {}
        perfiles = config.setdefault("perfiles_usuario", {})
        if nombre in perfiles:
            messagebox.showinfo("Usuarios y Permisos", f"El perfil '{nombre}' ya existe.")
            self.refrescar_tab_usuarios_permisos()
            self._cargar_editor_perfil(nombre)
            return

        perfiles[nombre] = {
            "modulos": {
                "productos": True,
                "publicidad": True,
                "configuracion": False,
            }
        }
        guardar_config(config)
        self.refrescar_tab_usuarios_permisos()
        self._cargar_editor_perfil(nombre)
        messagebox.showinfo("Usuarios y Permisos", f"Perfil '{nombre}' creado correctamente.")

    def _guardar_perfil_permiso(self):
        nombre = self.perfil_permiso_var.get().strip().lower()
        if not nombre:
            messagebox.showwarning("Usuarios y Permisos", "Seleccioná un perfil para guardar.")
            return

        productos = bool(self.perm_productos_var.get())
        publicidad = bool(self.perm_publicidad_var.get())
        configuracion = bool(self.perm_configuracion_var.get())

        if not any((productos, publicidad, configuracion)):
            messagebox.showwarning("Usuarios y Permisos", "El perfil debe tener al menos un módulo habilitado.")
            return

        usuario_actual = self.DICT_WIDGETS.get_widget("CONFIG", "usuario_windows") or ""
        if nombre == str(usuario_actual).strip().lower() and not configuracion:
            messagebox.showwarning(
                "Usuarios y Permisos",
                "No podés quitarte a vos mismo el acceso a Configuración desde esta pantalla.",
            )
            return

        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json") or {}
        perfiles = config.setdefault("perfiles_usuario", {})
        perfil = perfiles.setdefault(nombre, {})
        perfil["modulos"] = {
            "productos": productos,
            "publicidad": publicidad,
            "configuracion": configuracion,
        }
        perfil["estado"] = "activo" if any((productos, publicidad, configuracion)) else "pendiente"
        guardar_config(config)
        self.refrescar_tab_usuarios_permisos()
        messagebox.showinfo(
            "Usuarios y Permisos",
            f"Permisos guardados para '{nombre}'.\nLos cambios aplican al próximo ingreso de ese usuario.",
        )
            
    def creacion_frame_config_datos_INFORHARD(self):
        self.frame_config_datos_INFORHARD = ttk.Frame(self.frame_notebook_config_datos)
        
        self.button_importar_datos_INFORHARD = ttk.Button(self.frame_config_datos_INFORHARD, text="Sincronizars Datos", command=self.command_importar_datos_INFORHARD)
        self.button_importar_datos_INFORHARD.pack()

    def _crear_panel_guia_imagenes(self):
        self.frame_guia_imagenes = ttk.Labelframe(
            self.frame_notebook_config_datos,
            text="Guia de imagenes para Android",
            bootstyle="info",
            padding=(PANEL_PAD_X - 2, PANEL_PAD_Y - 2),
        )
        self.frame_guia_imagenes.pack(fill="x", padx=PANEL_PAD_X - 8, pady=(0, 10))

        texto_producto = (
            "Imagen de producto\n"
            "- Formatos: jpg, jpeg, png, webp\n"
            "- Recomendado: jpg | png solo si necesita transparencia\n"
            "- Relacion ideal: 1:1\n"
            "- Tamano ideal: 1000 x 1000 px\n"
            "- Maximo recomendado: 1400 x 1400 px\n"
            "- Evitar mas de 1600 x 1600 px\n"
            "- Peso ideal: 150 KB a 400 KB | aceptable hasta 700 KB\n"
            "- Evitar archivos mayores a 1 MB"
        )
        texto_logo = (
            "Logo inferior / logo de empresa\n"
            "- Formatos: png, jpg, jpeg, webp\n"
            "- Recomendado: png\n"
            "- Relacion recomendada: 4:1\n"
            "- Tamano ideal: 840 x 216 px o 1200 x 300 px\n"
            "- Ancho recomendado: 800 a 1400 px\n"
            "- Mantener margen interno para que no quede cortado"
        )
        texto_motivo = (
            "Motivo tecnico\n"
            "- Android decodifica la imagen completa sin resize previo\n"
            "- Base64 aumenta aprox. 33% el tamano enviado\n"
            "- Imagenes grandes consumen mas memoria y tardan mas en mostrar"
        )

        ttk.Label(self.frame_guia_imagenes, text=texto_producto, justify="left", font=FONT_SUBTITLE).grid(row=0, column=0, sticky="nw", padx=(0, 12))
        ttk.Label(self.frame_guia_imagenes, text=texto_logo, justify="left", font=FONT_SUBTITLE).grid(row=0, column=1, sticky="nw", padx=(0, 12))
        ttk.Label(self.frame_guia_imagenes, text=texto_motivo, justify="left", bootstyle="secondary", font=FONT_SUBTITLE).grid(row=0, column=2, sticky="nw")

        self.frame_guia_imagenes.columnconfigure(0, weight=1)
        self.frame_guia_imagenes.columnconfigure(1, weight=1)
        self.frame_guia_imagenes.columnconfigure(2, weight=1)

    def _validar_logo_seleccionado(self, filepath):
        try:
            img = Image.open(filepath)
            width, height = img.size
            formato = (img.format or os.path.splitext(filepath)[1][1:]).upper()
            peso_kb = os.path.getsize(filepath) / 1024
            ratio = round(width / height, 2) if height else 0

            observaciones = []
            estado = "success"

            if width < 800 or width > 1400:
                observaciones.append("ancho fuera del rango recomendado (800-1400 px)")
                estado = "warning"
            if ratio < 3.6 or ratio > 4.4:
                observaciones.append("proporcion fuera del objetivo 4:1")
                estado = "warning"
            if peso_kb > 700:
                observaciones.append("peso alto para envio")
                estado = "warning"

            if not observaciones:
                resumen = "OK. Logo dentro del rango recomendado para Android."
            else:
                resumen = "Revisar: " + "; ".join(observaciones) + "."

            self.label_validacion_logo.config(
                text=(
                    f"Archivo: {os.path.basename(filepath)} | Formato: {formato} | "
                    f"{width}x{height}px | {peso_kb:.0f} KB | Ratio: {ratio}\n{resumen}"
                ),
                bootstyle=estado,
            )
        except Exception as exc:
            self.label_validacion_logo.config(
                text=f"No se pudo validar la imagen seleccionada: {exc}",
                bootstyle="danger",
            )
        
    def creacion_toplevel_carga_datos(self):
        # Crear ventana Toplevel
        self.top_level_carga = ttk.Toplevel()
        self.top_level_carga.title("Cargar Datos")
        
        # Congelar la ventana principal al mostrar esta ventana
        self.top_level_carga.transient(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        self.top_level_carga.grab_set()  # Esto congela la ventana principal
        self.top_level_carga.protocol("WM_DELETE_WINDOW", self.bloquear_cierre)
        
        # Posicionar la ventana en el centro
        fit_toplevel_to_workarea(self.top_level_carga, 400, 250, min_width=360, min_height=220)
        self.top_level_carga.place_window_center()

        # Agregar una barra de progreso
        self.progressbar_carga = ttk.Floodgauge(self.top_level_carga, mode="determinate", bootstyle="primary")
        self.DICT_WIDGETS.register("UI", "BARRA_PROGRESO", self.progressbar_carga)
        self.progressbar_carga.pack(fill="x", expand=True, padx=20, pady=(20,10))
        
        # Label de porcentaje con tamaño mayor
        self.label_porcentaje = ttk.Label(self.top_level_carga, text="0%", anchor="center", font=FONT_LABEL_BOLD)
        self.label_porcentaje.pack(pady=10)

        # Entry para mostrar las acciones, con tamaño mayor y centrado
        self.entry_acciones = ttk.Entry(self.top_level_carga, state="readonly", font=FONT_SUBTITLE)
        self.entry_acciones.pack(fill="x", padx=20, pady=10)
        self.mostrar_accion("Iniciando la carga de datos...")
        
    #///////////////////////////////////////////////////// NOTEBOOK GO-UPC /////////////////////////////////////////////////////

    def creacion_frame_notebook_go_upc(self):
        """Pestaña para configurar la API KEY de GO-UPC (guardada en SQLite)."""
        self.frame_notebook_go_upc = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_go_upc.pack(fill="both", expand=True)
        self.DICT_WIDGETS.register("GUI_CONFIG", "frame_notebook_go_upc", self.frame_notebook_go_upc)

        self.labelframe_go_upc = ttk.Labelframe(
            self.frame_notebook_go_upc,
            text="Conexión GO-UPC",
            bootstyle="primary",
            padding=(PANEL_PAD_X - 2, PANEL_PAD_Y - 2),
        )
        self.labelframe_go_upc.pack(fill="both", expand=True, padx=PANEL_PAD_X - 8, pady=(PANEL_PAD_Y - 4, PANEL_PAD_Y - 4))

        ttk.Label(
            self.labelframe_go_upc,
            text="API KEY (se guarda localmente en la base de datos):",
            font=FONT_LABEL_BOLD,
        ).pack(anchor="w", pady=(0, 6))

        self.entry_go_upc_api_key = ttk.Entry(self.labelframe_go_upc, show="â€¢")
        self.entry_go_upc_api_key.pack(fill="x", pady=(0, 10))
        self.DICT_WIDGETS.register("GUI_CONFIG", "entry_go_upc_api_key", self.entry_go_upc_api_key)

        frame_btn = ttk.Frame(self.labelframe_go_upc)
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

        self.btn_enviar_config_imagenes = ttk.Button(
            frame_btn,
            text="Enviar al dispositivo seleccionado",
            bootstyle="info-outline",
            command=self.command_enviar_config_imagenes_dispositivo,
        )
        self.btn_enviar_config_imagenes.pack(side="right")

        self.lbl_estado_go_upc = ttk.Label(self.labelframe_go_upc, text="", bootstyle="secondary", font=FONT_SUBTITLE)
        self.lbl_estado_go_upc.pack(anchor="w", pady=(10, 0))

        self.lbl_estado_api_imagenes = ttk.Label(self.labelframe_go_upc, text="", bootstyle="secondary", font=FONT_SUBTITLE)
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
            messagebox.showerror("GO-UPC", f"No se pudo asegurar la tabla de API KEY.\n\n{e}")

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
            messagebox.showwarning("GO-UPC", "Ingresá la API KEY.")
            return

        try:
            self.api_key_dao.reemplazar(api_key)
            self.lbl_estado_go_upc.config(text="API KEY guardada correctamente.", bootstyle="success")
        except Exception as e:
            self.lbl_estado_go_upc.config(text=f"Error guardando API KEY: {e}", bootstyle="danger")
            messagebox.showerror("GO-UPC", f"No se pudo guardar la API KEY.\n\n{e}")

    def command_enviar_config_imagenes_dispositivo(self):
        nombre, _dispositivo, base_url = self._obtener_dispositivo_seleccionado()
        if not nombre:
            messagebox.showwarning(
                "Configurar dispositivo",
                "Seleccione un dispositivo en la pestaña Dispositivos antes de enviar la configuración.",
            )
            return

        self.btn_enviar_config_imagenes.config(state="disabled", text="Enviando...")
        self.lbl_estado_go_upc.config(
            text=f"Enviando GO-UPC + API de imágenes a {nombre}...",
            bootstyle="info",
        )

        def tarea():
            ventana_padre = self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja")
            sender = DispositivoSender(self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA"), ventana_padre)
            mensajes = []

            def actualizar(msg):
                mensajes.append(msg)

            sender.enviar_config_imagenes(base_url, estado_callback=actualizar)

            def finalizar():
                self.btn_enviar_config_imagenes.config(state="normal", text="Enviar al dispositivo seleccionado")
                ultimo = mensajes[-1] if mensajes else "Configuración enviada."
                error = any(str(msg).startswith("Advertencia:") or str(msg).startswith("Error:") for msg in mensajes)
                self.lbl_estado_go_upc.config(
                    text=ultimo,
                    bootstyle="warning" if error else "success",
                )
                detalle = "\n".join(mensajes) if mensajes else "Sin detalle devuelto."
                messagebox.showinfo(
                    "Config enviada",
                    f"Se intentó enviar GO-UPC + API de imágenes a {nombre}.\n\n{detalle}",
                )

            self._run_en_ui(finalizar)

        threading.Thread(target=tarea, daemon=True).start()

    def _abrir_config_api_imagenes(self, event=None):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        actual = config.get("api_imagenes_url", "") or "http://inforhardserver.ddns.net:5000"
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
                text="API propia de imagenes usando valor por defecto: http://inforhardserver.ddns.net:5000 | Atajo: Ctrl+Shift+I",
                bootstyle="info",
            )


            
#//////////////////////////////////////////////// COMMAND DE BOTONES ///////////////////////////////////////////////
    def command_button_agregar(self):
        self.toplevel_button_agregar = ttk.Toplevel(self.top_level_configuracion)
        self.DICT_WIDGETS.register("GUI_CONFIG", "toplevel_button_agregar", self.toplevel_button_agregar)
        self.toplevel_button_agregar.title("VeriPre_Connector - Agregar Dispositivo")
        self.toplevel_button_agregar.transient(self.top_level_configuracion)
        fit_toplevel_to_workarea(self.toplevel_button_agregar, 500, 300, min_width=460, min_height=280)
        self.toplevel_button_agregar.place_window_center()

        self.creacion_contenido_toplevel_button_agregar()
        
    def command_button_eliminar(self):
        if messagebox.askyesno("Eliminar Dispositivo", f"¿Desea eliminar el Dispositivo {self.combobox_dispositivos.get()}?"):
            
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
            images_api = client.get_images_api_url()

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
                    f"GO-UPC key: {status.get('go_upc_key', '-')}\n"
                    f"Images API URL: {(images_api or {}).get('url', '-')}"
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
                        "Configuración Player",
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
        fit_toplevel_to_workarea(top, 700, 470, min_width=640, min_height=420)
        top.place_window_center()
        top.transient(self.top_level_configuracion)
        top.grab_set()

        settings = config_player.get("settings", {}) if isinstance(config_player, dict) else {}
        pantallas = config_player.get("pantallas_detectadas", []) if isinstance(config_player, dict) else []
        campos = config_player.get("campos_soportados", []) if isinstance(config_player, dict) else []

        ttk.Label(
            top,
            text=f"Configuración remota del player para {nombre}",
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
        text_info = self._crear_textarea_base(info, height=8)
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
                    estado_lbl.config(text="Configuración guardada correctamente.", bootstyle="success")
                    messagebox.showinfo("Player", "Configuración del player guardada correctamente.")

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
            messagebox.showwarning("Dispositivo", "No se encontró el dispositivo seleccionado en memoria.")
        
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
                messagebox.showinfo("Dispositivo Agregado", "Dispositivo agregado con éxito.")
                self.toplevel_button_agregar.destroy()
        except Exception as e:
            return []
            
    def command_button_actualizar_datos_dispositivo(self):
        try:
            if self.validar_campos():
                # Prepara la consulta segura usando parámetros
                sentencia_actualizacion = """
                UPDATE VERIPRE_EQUIPOS 
                SET nombre = ?, direccion_conexion = ?, puerto = ?, comentarios = ? 
                WHERE nombre = ?;
                """

                valores = (
                    self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.get(),
                    self.entry_direccion_ip.get(),
                    self.entry_puerto.get(),
                    self.text_comentario.get("1.0", "end").strip(),  # Evita el salto de línea final
                    self.combobox_dispositivos.get()
                )

                # Ejecuta la consulta de forma segura
                conexion = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA")
                conexion.ejecutar_consulta(sentencia_actualizacion, valores)

                # Actualiza el Combobox con los nuevos datos
                self.combobox_dispositivos.config(values=self.actualizar_datos_combobox())

                messagebox.showinfo("Dispositivo Actualizado", "Dispositivo actualizado con éxito.")
                self.toplevel_button_agregar.destroy()
                self.limpiar_frame_despues_actualizacion()

        except Exception as e:
            messagebox.showerror("Dispositivo", f"No se pudo actualizar el dispositivo.\n\n{e}")

    def command_button_buscar_dispositivos_red(self):
        tipos_var = ttk.StringVar(value="ambos")

        selector = ttk.Toplevel(self.top_level_configuracion)
        selector.title("Buscar en red")
        fit_toplevel_to_workarea(selector, 520, 230, min_width=480, min_height=220)
        selector.place_window_center()
        selector.transient(self.top_level_configuracion)
        selector.grab_set()
        selector.resizable(False, False)

        frame_selector = ttk.Frame(selector, padding=(PANEL_PAD_X + 2, PANEL_PAD_Y + 2))
        frame_selector.pack(fill="both", expand=True)
        frame_selector.columnconfigure(0, weight=1)

        ttk.Label(
            frame_selector,
            text="Seleccione qué tipo de dispositivos desea detectar:",
            font=FONT_LABEL_BOLD,
        ).pack(anchor="w", pady=(4, 12))

        ttk.Label(
            frame_selector,
            text="Puede buscar verificadores de precio, players InforTV o ambos.",
            bootstyle="secondary",
            font=FONT_SUBTITLE,
            justify="left",
            wraplength=460,
        ).pack(anchor="w", pady=(0, 12))

        combo = ttk.Combobox(
            frame_selector,
            state="readonly",
            values=["Ambos", "Verificadores", "InforTV"],
            width=34,
        )
        combo.pack(anchor="w", fill="x", ipady=4)
        combo.set("Ambos")

        usar_cache = ttk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame_selector,
            text="Usar cache reciente si existe",
            variable=usar_cache,
        ).pack(anchor="w", pady=(14, 0))

        def resolver_tipos():
            valor = combo.get().strip().lower()
            if valor == "verificadores":
                return ("verificador",)
            if valor == "infotv":
                return ("infotv",)
            return ("verificador", "infotv")

        def iniciar_busqueda():
            tipos = resolver_tipos()
            cache_habilitado = bool(usar_cache.get())
            selector.destroy()
            self._ejecutar_busqueda_dispositivos_red(
                tipos=tipos,
                use_cache=cache_habilitado,
            )

        acciones = ttk.Frame(frame_selector)
        acciones.pack(fill="x", pady=(PANEL_PAD_Y + 10, 0))
        ttk.Button(acciones, text="Buscar", command=iniciar_busqueda, bootstyle="info", width=14, padding=(12, 8)).pack(side="left")
        ttk.Button(acciones, text="Cancelar", command=selector.destroy, width=14, padding=(12, 8)).pack(side="right")

    def _ejecutar_busqueda_dispositivos_red(self, tipos=("verificador", "infotv"), use_cache=True):
        top = ttk.Toplevel(self.top_level_configuracion)
        top.title("Buscar dispositivos en red")
        fit_toplevel_to_workarea(top, 580, 220, min_width=520, min_height=210)
        top.place_window_center()
        top.transient(self.top_level_configuracion)
        top.grab_set()
        top.resizable(False, False)

        frame_estado_busqueda = ttk.Frame(top, padding=(PANEL_PAD_X + 6, PANEL_PAD_Y + 6))
        frame_estado_busqueda.pack(fill="both", expand=True)

        ttk.Label(
            frame_estado_busqueda,
            text="Buscando verificadores (8080) e InforTV (2727) en la red local...",
            font=FONT_LABEL_BOLD,
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(2, 12))

        progress = ttk.Progressbar(frame_estado_busqueda, mode="indeterminate", bootstyle="info-striped")
        progress.pack(fill="x", pady=(0, 14))
        progress.start(12)

        estado_var = ttk.StringVar(value="Iniciando descubrimiento...")
        ttk.Label(
            frame_estado_busqueda,
            textvariable=estado_var,
            bootstyle="secondary",
            font=FONT_SUBTITLE,
            wraplength=520,
            justify="left",
        ).pack(anchor="w")

        acciones = ttk.Frame(frame_estado_busqueda)
        acciones.pack(fill="x", pady=(PANEL_PAD_Y + 10, 0))
        btn_cerrar = ttk.Button(acciones, text="Cerrar", command=top.destroy, state="disabled", padding=(12, 8))
        btn_cerrar.pack(side="right")

        def update_estado(msg):
            self.top_level_configuracion.after(0, lambda: estado_var.set(msg))

        def finalizar(resultados=None, error=None):
            progress.stop()
            btn_cerrar.config(state="normal", text="Cerrar")
            if error:
                estado_var.set(f"Error buscando dispositivos: {error}")
                return
            resultados = resultados or []
            estado_var.set(f"Dispositivos detectados: {len(resultados)}")
            if top.winfo_exists():
                top.destroy()
            self._mostrar_resultados_dispositivos_detectados(resultados)

        def worker():
            try:
                service = DeviceDiscoveryService()
                resultados = service.discover(
                    progress_callback=update_estado,
                    tipos=tipos,
                    use_cache=use_cache,
                )
                self.top_level_configuracion.after(0, lambda: finalizar(resultados=resultados))
            except Exception as e:
                self.top_level_configuracion.after(0, lambda: finalizar(error=e))

        threading.Thread(target=worker, daemon=True).start()

    def _mostrar_resultados_dispositivos_detectados(self, dispositivos):
        top = ttk.Toplevel(self.top_level_configuracion)
        top.title("Dispositivos detectados")
        fit_toplevel_to_workarea(top, 1240, 680, min_width=980, min_height=560)
        top.place_window_center()
        top.transient(self.top_level_configuracion)

        frame_principal = ttk.Frame(top, padding=(PANEL_PAD_X - 4, PANEL_PAD_Y - 2))
        frame_principal.pack(fill="both", expand=True)
        frame_principal.columnconfigure(0, weight=1)
        frame_principal.rowconfigure(1, weight=1)

        ttk.Label(
            frame_principal,
            text="Seleccione los dispositivos detectados que desea agregar a la configuración local.",
            font=FONT_LABEL_BOLD,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        frame_contenido = ttk.Frame(frame_principal)
        frame_contenido.grid(row=1, column=0, sticky="nsew", pady=(0, PANEL_PAD_Y - 4))
        frame_contenido.columnconfigure(0, weight=5)
        frame_contenido.columnconfigure(1, weight=3)
        frame_contenido.rowconfigure(0, weight=1)

        frame_tree = ttk.Frame(frame_contenido)
        frame_tree.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        frame_filtros = ttk.Frame(frame_tree)
        frame_filtros.pack(fill="x", pady=(0, 8))
        ttk.Label(frame_filtros, text="Mostrar:", font=FONT_BODY_BOLD).pack(side="left", padx=(0, 8))
        filtro_var = ttk.StringVar(value="nuevos")
        combo_filtro = ttk.Combobox(
            frame_filtros,
            state="readonly",
            values=["Solo nuevos", "Solo registrados", "Todos"],
            width=18,
            textvariable=filtro_var,
        )
        combo_filtro.pack(side="left")
        combo_filtro.set("Solo nuevos")

        columns = ("nombre", "tipo", "ip", "puerto", "estado")
        tree = ttk.Treeview(frame_tree, columns=columns, show="headings", height=18, selectmode="extended")
        headings = {
            "nombre": ("Nombre", 300),
            "tipo": ("Tipo", 130),
            "ip": ("IP", 210),
            "puerto": ("Puerto", 100),
            "estado": ("Estado", 180),
        }
        for key, (text, width) in headings.items():
            tree.heading(key, text=text)
            tree.column(key, width=width, anchor="w")
        tree.tag_configure("nuevo", background="#e9f8ef", foreground="#146c43")
        tree.tag_configure("registrado", background="#f3f6f9", foreground="#52606d")

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll_y.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        frame_editor = ttk.Labelframe(
            frame_contenido,
            text="Edición rápida",
            padding=(PANEL_PAD_X - 4, PANEL_PAD_Y - 2),
            bootstyle="primary",
        )
        frame_editor.grid(row=0, column=1, sticky="nsew")
        frame_editor.columnconfigure(1, weight=1)

        dispositivos_indexados = {}
        nombres_editados = {}
        nuevos_iids = []
        registrados_iids = []
        existentes = {
            (str(data.get("direccion_ip", "")).strip(), int(data.get("puerto", 0) or 0)): nombre
            for nombre, data in self.datos_dispositivos.items()
        }

        for idx, dispositivo in enumerate(dispositivos, start=1):
            ip = str(dispositivo.get("ip", "")).strip()
            puerto = int(dispositivo.get("puerto", 0) or 0)
            ya_existe = (ip, puerto) in existentes
            estado = "Ya registrado" if ya_existe else "Nuevo"
            iid = f"det_{idx}"
            nombre_sugerido = dispositivo.get("nombre") or f"Dispositivo {ip}"
            dispositivos_indexados[iid] = {
                "data": dispositivo,
                "ip": ip,
                "puerto": puerto,
                "ya_existe": ya_existe,
                "estado": estado,
                "tipo": dispositivo.get("tipo", "-"),
            }
            nombres_editados[iid] = nombre_sugerido
            if not ya_existe:
                nuevos_iids.append(iid)
            else:
                registrados_iids.append(iid)

        editor_iid = ttk.StringVar(value="")
        nombre_var = ttk.StringVar(value="")
        tipo_var = ttk.StringVar(value="-")
        ip_var = ttk.StringVar(value="-")
        puerto_var = ttk.StringVar(value="-")
        estado_var_editor = ttk.StringVar(value="-")

        def obtener_iids_filtrados():
            valor = combo_filtro.get().strip().lower()
            if valor == "solo nuevos":
                return list(nuevos_iids)
            if valor == "solo registrados":
                return list(registrados_iids)
            return list(dispositivos_indexados.keys())

        def repoblar_tree(preservar_iid=None):
            visibles = obtener_iids_filtrados()
            tree.delete(*tree.get_children())
            for iid in visibles:
                item = dispositivos_indexados[iid]
                tree.insert(
                    "",
                    "end",
                    iid=iid,
                    values=(
                        nombres_editados.get(iid, ""),
                        item.get("tipo", "-"),
                        item.get("ip", ""),
                        item.get("puerto", ""),
                        item.get("estado", "-"),
                    ),
                    tags=("registrado" if item.get("ya_existe") else "nuevo",),
                )

            if not visibles:
                editor_iid.set("")
                nombre_var.set("")
                tipo_var.set("-")
                ip_var.set("-")
                puerto_var.set("-")
                estado_var_editor.set("-")
                ayuda_var.set("No hay dispositivos para el filtro seleccionado.")
                return

            destino = preservar_iid if preservar_iid in visibles else visibles[0]
            tree.selection_set((destino,))
            tree.see(destino)
            cargar_editor(destino)

        ttk.Label(frame_editor, text="Nombre:", font=FONT_BODY_BOLD).grid(row=0, column=0, sticky="w", pady=(0, 8))
        entry_nombre = ttk.Entry(frame_editor, textvariable=nombre_var, width=28)
        entry_nombre.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(frame_editor, text="Tipo:", font=FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Label(frame_editor, textvariable=tipo_var, font=FONT_SUBTITLE).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(frame_editor, text="IP:", font=FONT_BODY_BOLD).grid(row=2, column=0, sticky="w", pady=4)
        ttk.Label(frame_editor, textvariable=ip_var, font=FONT_SUBTITLE).grid(row=2, column=1, sticky="w", pady=4)
        ttk.Label(frame_editor, text="Puerto:", font=FONT_BODY_BOLD).grid(row=3, column=0, sticky="w", pady=4)
        ttk.Label(frame_editor, textvariable=puerto_var, font=FONT_SUBTITLE).grid(row=3, column=1, sticky="w", pady=4)
        ttk.Label(frame_editor, text="Estado:", font=FONT_BODY_BOLD).grid(row=4, column=0, sticky="w", pady=4)
        ttk.Label(frame_editor, textvariable=estado_var_editor, font=FONT_SUBTITLE).grid(row=4, column=1, sticky="w", pady=4)

        ayuda_var = ttk.StringVar(value="Seleccione un dispositivo para editar su nombre antes de guardar.")
        ttk.Label(frame_editor, textvariable=ayuda_var, bootstyle="secondary", font=FONT_SUBTITLE, wraplength=320, justify="left").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(14, 10)
        )

        def cargar_editor(iid):
            item = dispositivos_indexados.get(iid)
            if not item:
                return
            dispositivo = item.get("data") or {}
            valores = tree.item(iid, "values")
            editor_iid.set(iid)
            nombre_var.set(nombres_editados.get(iid, valores[0] if valores else ""))
            tipo_var.set(item.get("tipo", "-"))
            ip_var.set(str(item.get("ip", "")).strip() or "-")
            puerto_var.set(str(item.get("puerto", "")).strip() or "-")
            estado_var_editor.set(valores[4] if len(valores) >= 5 else "-")
            ayuda_var.set("Puede cambiar el nombre y luego aplicar el cambio a la fila seleccionada.")

        def aplicar_nombre_editado(_event=None):
            iid = editor_iid.get()
            if not iid or iid not in dispositivos_indexados:
                return

            dispositivo = dispositivos_indexados[iid]["data"]
            nombre_base = (nombre_var.get() or "").strip()
            if not nombre_base:
                nombre_base = self._generar_nombre_dispositivo_unico(dispositivo)

            nombre_final = self._resolver_nombre_unico_editado(nombre_base, nombres_editados, excluir_iid=iid)

            nombres_editados[iid] = nombre_final
            nombre_var.set(nombre_final)
            valores = list(tree.item(iid, "values"))
            if valores:
                valores[0] = nombre_final
                tree.item(iid, values=valores)

        def aplicar_nombre_a_seleccion():
            seleccion = tree.selection()
            if not seleccion:
                messagebox.showwarning("Buscar en red", "Seleccione uno o más dispositivos para aplicar el nombre.")
                return

            nombre_base = (nombre_var.get() or "").strip()
            if not nombre_base:
                messagebox.showwarning("Buscar en red", "Ingrese un nombre base para aplicar a la selección.")
                entry_nombre.focus_set()
                return

            multiples = len(seleccion) > 1
            for indice, iid in enumerate(seleccion, start=1):
                base_actual = f"{nombre_base} {indice}" if multiples else nombre_base
                nombre_final = self._resolver_nombre_unico_editado(base_actual, nombres_editados, excluir_iid=iid)
                nombres_editados[iid] = nombre_final
                valores = list(tree.item(iid, "values"))
                if valores:
                    valores[0] = nombre_final
                    tree.item(iid, values=valores)

            cargar_editor(seleccion[0])
            ayuda_var.set("Nombre aplicado a la selección actual.")

        def seleccionar_item(_event=None):
            seleccion = tree.selection()
            if not seleccion:
                return
            cargar_editor(seleccion[0])

        def aplicar_filtro(_event=None):
            repoblar_tree(editor_iid.get() or None)

        def seleccionar_solo_nuevos():
            if not nuevos_iids:
                messagebox.showinfo("Buscar en red", "No hay dispositivos nuevos en esta búsqueda.")
                return
            combo_filtro.set("Solo nuevos")
            repoblar_tree(nuevos_iids[0])
            tree.selection_set(tuple(iid for iid in nuevos_iids if iid in tree.get_children()))
            ayuda_var.set("Se seleccionaron solo los dispositivos nuevos.")

        ttk.Button(frame_editor, text="Aplicar nombre", command=aplicar_nombre_editado, bootstyle="info-outline").grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )
        ttk.Button(
            frame_editor,
            text="Aplicar a selección",
            command=aplicar_nombre_a_seleccion,
            bootstyle="secondary-outline",
        ).grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Button(
            frame_editor,
            text="Seleccionar solo nuevos",
            command=seleccionar_solo_nuevos,
            bootstyle="success-outline",
        ).grid(row=8, column=0, columnspan=2, sticky="ew")
        entry_nombre.bind("<Return>", aplicar_nombre_editado)
        tree.bind("<<TreeviewSelect>>", seleccionar_item)
        combo_filtro.bind("<<ComboboxSelected>>", aplicar_filtro)

        if dispositivos:
            seleccion_inicial = nuevos_iids or list(dispositivos_indexados.keys())
            if seleccion_inicial:
                repoblar_tree(seleccion_inicial[0])
                visibles = [iid for iid in seleccion_inicial if iid in tree.get_children()]
                if visibles:
                    tree.selection_set(tuple(visibles))

        info_var = ttk.StringVar(
            value="No se encontraron dispositivos." if not dispositivos else f"Dispositivos encontrados: {len(dispositivos)}"
        )
        ttk.Label(
            frame_principal,
            textvariable=info_var,
            bootstyle="secondary",
            font=FONT_SUBTITLE,
        ).grid(row=2, column=0, sticky="w", pady=(0, 8))

        acciones = ttk.Frame(frame_principal)
        acciones.grid(row=3, column=0, sticky="ew")

        def agregar_seleccionados():
            seleccion = tree.selection()
            if not seleccion:
                messagebox.showwarning("Buscar en red", "Seleccione al menos un dispositivo detectado.")
                return

            agregados = 0
            omitidos = 0
            for iid in seleccion:
                item = dispositivos_indexados.get(iid)
                dispositivo = item.get("data") if item else None
                if not dispositivo:
                    continue

                ip = str(item.get("ip", "")).strip()
                puerto = int(item.get("puerto", 0) or 0)
                if (ip, puerto) in existentes:
                    omitidos += 1
                    continue

                nombre = (nombres_editados.get(iid) or "").strip() or self._generar_nombre_dispositivo_unico(dispositivo)

                existentes_nombres = set(self.datos_dispositivos.keys()) | set(existentes.values())
                if nombre in existentes_nombres:
                    nombre = self._generar_nombre_dispositivo_unico({"nombre": nombre})

                comentario = dispositivo.get("comentario") or "Detectado automaticamente en red"
                tipo = dispositivo.get("tipo")
                if tipo:
                    comentario = f"{comentario} | Tipo: {tipo}"

                self.dispositivos_dao.crear(nombre, ip, str(puerto), comentario)
                existentes[(ip, puerto)] = nombre
                self.datos_dispositivos[nombre] = {
                    "direccion_ip": ip,
                    "puerto": str(puerto),
                    "comentario": comentario,
                }
                agregados += 1

            self.combobox_dispositivos.config(values=self.actualizar_datos_combobox())
            messagebox.showinfo(
                "Buscar en red",
                f"Dispositivos agregados: {agregados}\nOmitidos por ya existir: {omitidos}"
            )
            top.destroy()

        ttk.Button(acciones, text="Agregar seleccionados", command=agregar_seleccionados, bootstyle="success", padding=(12, 8)).pack(side="left")
        ttk.Button(acciones, text="Cerrar", command=top.destroy, padding=(12, 8)).pack(side="right")

    def _generar_nombre_dispositivo_unico(self, dispositivo):
        base = (dispositivo.get("nombre") or f"Dispositivo {dispositivo.get('ip', '')}").strip()
        if not base:
            base = "Dispositivo detectado"

        nombre = base
        sufijo = 2
        existentes = set(self.datos_dispositivos.keys())
        while nombre in existentes:
            nombre = f"{base} ({sufijo})"
            sufijo += 1
        return nombre

    def _resolver_nombre_unico_editado(self, nombre_base, nombres_editados, excluir_iid=None):
        nombres_reservados = set(self.datos_dispositivos.keys())
        for otro_iid, otro_nombre in nombres_editados.items():
            if otro_iid != excluir_iid:
                nombre = (otro_nombre or "").strip()
                if nombre:
                    nombres_reservados.add(nombre)

        nombre_final = nombre_base
        sufijo = 2
        while nombre_final in nombres_reservados:
            nombre_final = f"{nombre_base} ({sufijo})"
            sufijo += 1
        return nombre_final
            
    def command_button_agregar_datos_de_conexion(self):
        try:
            if self.combobox_lista_fuente_datos.get() == "Conexión ODBC":
                self.conexion_dao.crear(
                    self.combobox_odbc.get(),
                    self.entry_user.get(),
                    self.entry_password.get(),
                    self.checkbox_var.get(),
                )
                if self.checkbox_var.get():
                    conexion = {
                        "user": self.entry_user.get(),
                        "password": self.entry_password.get(),
                        "dsn": self.combobox_odbc.get()
                    }
                    self.DICT_WIDGETS.register("DATABASE","CONEXIONDBA_SYBASE", ConexionSybase(**conexion))
                    self.DICT_WIDGETS.register("DATABASE","CONEXION_INFORHARD", True)
                messagebox.showinfo("Conexión Agregada", "Conexión agregada con éxito.")
            self.cambiar_estados_widgets_frame_odbc("disabled")
            self.button_agregar_datos_de_conexion.config(text="Actualizar datos", state="normal", command=self.command_modificado_button_actualizar_datos_de_conexion)
        except Exception as e:
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
            if self.checkbox_var.get():
                conexion = {
                    "user": self.entry_user.get(),
                    "password": self.entry_password.get(),
                    "dsn": self.combobox_odbc.get()
                }
                self.DICT_WIDGETS.register("DATABASE","CONEXIONDBA_SYBASE", ConexionSybase(**conexion))
                self.DICT_WIDGETS.register("DATABASE","CONEXION_INFORHARD", True)
            messagebox.showinfo("Estado Conexión", "Se ha actualizado el método de conexión")
            self.cambiar_estados_widgets_frame_odbc("disabled")
            self.button_agregar_datos_de_conexion.config(text="Actualizar datos", state="normal", command=self.command_modificado_button_actualizar_datos_de_conexion)
        except Exception as e:
            messagebox.showerror("ERROR", e)
            
    def command_importar_datos_INFORHARD(self):
        try:
            self.creacion_toplevel_carga_datos()
            threading.Thread(target=self.procesar_productos_completos).start()
        except Exception as e:
            messagebox.showerror("Carga de datos", f"No se pudo iniciar la carga.\n\n{e}")
            

    def actualizar_config_sincronizacion_automatica(self):
        config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        nuevo_valor = self.auto_sync_var.get()
        valor_anterior = config.get("sincronizacion_automatica", False)

        # Solo preguntar si se está activando (no al desactivar)
        if not valor_anterior and nuevo_valor:
            respuesta = messagebox.askyesno(
                "Reiniciar aplicación",
                "Se activó la sincronización automática.\n¿Deseás reiniciar la aplicación para aplicar los cambios?"
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
        """Actualiza el Entry con el texto de la acción que se está realizando."""
        self.entry_acciones.config(state="normal")
        self.entry_acciones.delete(0, "end")
        self.entry_acciones.insert(0, texto)
        self.entry_acciones.config(state="readonly")
        
    def actualizar_barra(self, progreso, total):            
        """Actualiza la barra de progreso con el porcentaje calculado."""
        porcentaje = (progreso / total) * 100
        
        barra_progreso = self.DICT_WIDGETS.get_widget("UI", "BARRA_PROGRESO")
        if barra_progreso is not None:
            barra_progreso['value'] = porcentaje  # Asegúrate de usar 'value' para actualizar la barra
            self.label_porcentaje.configure(text=f"{int(porcentaje)}%")
        else:
            self.mostrar_accion("Error: No se encontró el widget BARRA_PROGRESO.")




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
        """Obtiene los artículos con códigos de barras válidos y muestra información de lo que está haciendo."""
        CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS = """
            SELECT CREF, CDETALLE, CCODEBAR, CTIPOIVA, NPVP1, dFechaU
            FROM ARTICULO 
            WHERE CCODEBAR IS NOT NULL AND CCODEBAR <> ''
            ORDER BY dFechaU ASC;
        """
        self.datos_ARTICULOS = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS)

        self.mostrar_accion("Iniciando la carga de artículos...")
        time.sleep(0.75)

        # Primera actualización al 50%
        self.actualizar_barra(50, 100)

        self.mostrar_accion(f"{len(self.datos_ARTICULOS)} artículos encontrados.")
        time.sleep(0.75)

        # Última actualización al 100%
        self.actualizar_barra(100, 100)





    def buscar_datos_tabla_CODBARP(self):
        """Obtiene los códigos de barra adicionales y los une con la lista de productos."""
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
        
        total_productos = len(self.datos_PRODUCTOS_COMPLETOS)  # Número total de productos
        if total_productos == 0:
            self.mostrar_accion("No hay productos para insertar o actualizar.")
            return

        # Iniciar la barra de progreso en 0%
        self.actualizar_barra(0, total_productos)
        
        # Preparar todos los parámetros para la inserción o actualización
        parametros = [(producto[0], producto[2], producto[1], producto[3], producto[4]) for producto in self.datos_PRODUCTOS_COMPLETOS]

        # Ejecutar la consulta para todos los productos a la vez
        self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA").ejecutar_consultamany(consulta, parametros)
        
        # Actualizar la barra de progreso al 100% una vez que se han insertado/actualizado todos los productos
        self.actualizar_barra(total_productos, total_productos)

        self.mostrar_accion("Productos insertados o actualizados correctamente.")





            
    def cierre_top_level_configuracion(self):
        """Cierra la ventana y la elimina del gestor de ventanas"""
        VentanaManager.cerrar_ventana("configuracion")  # Llamamos al método de cierre
        try:
            self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja").unbind("<<DispositivosActualizados>>")
        except Exception:
            pass
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
        # Actualizar los Labels con la información del dispositivo seleccionado
        self.label_nombre_contenido_labelframe_opciones.config(text=dispositivo)
        self.label_direccion_ip_der_contenido_labelframe_opciones.config(
            text=self.datos_dispositivos[dispositivo]["direccion_ip"]
        )
        self.label_puerto_der_contenido_labelframe_opciones.config(
            text=self.datos_dispositivos[dispositivo]["puerto"]
        )

        # Actualizar el contenido del Text para el comentario
        self._set_textarea_value(
            self.text_comentario_contenido_labelframe_opciones,
            self.datos_dispositivos[dispositivo]["comentario"],
        )

        # Forzar la actualización de la interfaz
        self.top_level_configuracion.update_idletasks()

    def actualizar_datos_combobox(self):
        try:
            self.traer_todos_los_datos_de_VERIPRE_EQUIPOS()
            list_nombre_dispositivo = []
            for nombre_dispositivo in self.datos_dispositivos:
                list_nombre_dispositivo.append(nombre_dispositivo)
            return list_nombre_dispositivo
        except Exception as e:
            return []
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

    def _ruta_logo_dispositivo_actual(self):
        ruta_nueva = PNG_LOGO_DISPOSITIVO()
        if os.path.exists(ruta_nueva):
            return ruta_nueva

        ruta_legacy = PNG_LOGO_PRINCIPAL()
        if os.path.exists(ruta_legacy):
            return ruta_legacy

        return None

    def _mostrar_logo_actual(self):
        ruta_logo = self._ruta_logo_dispositivo_actual()
        if not ruta_logo:
            ruta_logo = PNG_LOGO_SECUNDARIO()

        if os.path.exists(ruta_logo):
            self.label_logo_preview.update_idletasks()
            ancho_disp = self.label_logo_preview.winfo_width()
            alto_disp = self.label_logo_preview.winfo_height()

            if ancho_disp <= 1 or alto_disp <= 1:
                ancho_disp, alto_disp = 300, 300  # mayor área visible

            img = Image.open(ruta_logo)
            img.thumbnail((ancho_disp, alto_disp), Image.Resampling.LANCZOS)

            self.logo_img_tk = ImageTk.PhotoImage(img)
            self.label_logo_preview.config(image=self.logo_img_tk, text="")
        else:
            self.label_logo_preview.config(image="", text="Sin logo")

            
    def _seleccionar_logo(self):
        filetypes = [("Imágenes", "*.png *.jpg *.jpeg *.webp")]
        filepath = filedialog.askopenfilename(title="Seleccionar Logo", filetypes=filetypes)
        if not filepath:
            return

        try:
            ruta_normalizada = self._guardar_logo_normalizado(filepath)
            self.ruta_logo_seleccionado = ruta_normalizada
            self._mostrar_logo_actual_desde_ruta(ruta_normalizada)
            self._validar_logo_seleccionado(ruta_normalizada)
        except Exception as e:
            messagebox.showerror("Logo", f"No se pudo guardar el logo normalizado.\n{e}")

    def _guardar_logo_normalizado(self, filepath):
        from pathlib import Path

        destino = Path("ASSETS") / "!!!LOGO_DISPOSITIVO!!!.png"
        destino.parent.mkdir(parents=True, exist_ok=True)

        ancho_objetivo = 1200
        alto_objetivo = 300
        margen = 24

        img_original = Image.open(filepath).convert("RGBA")
        area_ancho = ancho_objetivo - (margen * 2)
        area_alto = alto_objetivo - (margen * 2)

        img_ajustada = img_original.copy()
        img_ajustada.thumbnail((area_ancho, area_alto), Image.Resampling.LANCZOS)

        lienzo = Image.new("RGBA", (ancho_objetivo, alto_objetivo), (255, 255, 255, 0))
        offset_x = (ancho_objetivo - img_ajustada.width) // 2
        offset_y = (alto_objetivo - img_ajustada.height) // 2
        lienzo.paste(img_ajustada, (offset_x, offset_y), img_ajustada)
        lienzo.save(destino, format="PNG")
        return str(destino)

    def _normalizar_logo_seleccionado(self):
        ruta_logo = getattr(self, "ruta_logo_seleccionado", None)
        if not ruta_logo:
            ruta_logo = self._ruta_logo_dispositivo_actual()
            if not ruta_logo or not os.path.exists(ruta_logo):
                messagebox.showwarning("Logo", "Primero seleccione una imagen para normalizar.")
                return

        try:
            ruta_normalizada = self._guardar_logo_normalizado(ruta_logo)
            self.ruta_logo_seleccionado = ruta_normalizada
            self._mostrar_logo_actual_desde_ruta(ruta_normalizada)
            self._validar_logo_seleccionado(ruta_normalizada)
            messagebox.showinfo(
                "Logo normalizado",
                "Se genero el logo normalizado en formato PNG 4:1 dentro de assets.",
            )
        except Exception as exc:
            messagebox.showerror("Logo", f"No se pudo normalizar el logo.\n{exc}")

    def _mostrar_logo_actual_desde_ruta(self, ruta_logo):
        if not os.path.exists(ruta_logo):
            self.label_logo_preview.config(image="", text="Sin logo")
            return

        self.label_logo_preview.update_idletasks()
        ancho_disp = self.label_logo_preview.winfo_width()
        alto_disp = self.label_logo_preview.winfo_height()

        if ancho_disp <= 1 or alto_disp <= 1:
            ancho_disp, alto_disp = 300, 300

        img = Image.open(ruta_logo)
        img.thumbnail((ancho_disp, alto_disp), Image.Resampling.LANCZOS)

        self.logo_img_tk = ImageTk.PhotoImage(img)
        self.label_logo_preview.config(image=self.logo_img_tk, text="")


    def _enviar_logo_a_dispositivos(self):
        # Ruta del logo seleccionado (por el usuario)
        ruta_logo = getattr(self, "ruta_logo_seleccionado", None)

        # Si no hay logo seleccionado, buscar el logo principal o uno secundario
        if not ruta_logo:
            ruta_logo = self._ruta_logo_dispositivo_actual()
            if not ruta_logo or not os.path.exists(ruta_logo):
                messagebox.showwarning("Logo no disponible", "No se encontró ningún logo de dispositivo para enviar.")
                return
        ventana_padre = self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja")
        sender = DispositivoSender(self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA"), ventana_padre)
        urls = sender.seleccionar_dispositivos()
        if not urls:
            return

        sender.enviar_logo_principal(urls, ruta_logo)
        messagebox.showinfo("Logo Enviado", "El logo fue enviado exitosamente.")

