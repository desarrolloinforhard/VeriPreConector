import os
import threading
import json
import locale
import socket
import sys
import getpass
import hashlib
import atexit

import ttkbootstrap as ttk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

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


def _obtener_scope_instancia():
    username = (
        os.environ.get("USERNAME")
        or os.environ.get("USER")
        or getpass.getuser()
        or "default"
    )
    return username.strip().lower() or "default"


def _obtener_puerto_instancia(base=55665):
    scope = _obtener_scope_instancia()
    digest = hashlib.blake2b(scope.encode("utf-8"), digest_size=2).digest()
    offset = int.from_bytes(digest, "big") % 3000
    return base + offset, scope


def comprobar_instancia_unica(puerto_base=55665):
    puerto, scope = _obtener_puerto_instancia(puerto_base)
    logger.debug(
        "Verificando instancia única de la aplicación | puerto=%s | scope_usuario=%s",
        puerto,
        scope,
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", puerto))
        logger.info(
            "Instancia única confirmada. Socket de bloqueo adquirido | puerto=%s | scope_usuario=%s",
            puerto,
            scope,
        )
        return sock  # mantiene el socket abierto
    except OSError:
        logger.warning(
            "Se detectó otra instancia en ejecución para el mismo usuario | puerto=%s | scope_usuario=%s",
            puerto,
            scope,
        )
        messagebox.showinfo(
            "Aplicación ya en ejecución",
            "La aplicación ya está abierta para este usuario.\nRevisá la bandeja del sistema (icono cerca del reloj)."
        )
        sys.exit(0)


class GUI_MAIN:
    def __init__(self, version):
        logger.info("Iniciando GUI_MAIN | version=%s", version)
        self.version = version

        self.socket_lock = comprobar_instancia_unica()
        self.DICT_WIDGETS = WidgetRegistry()
        self.VIGIA_FRAME = "INICIO"
        self.VIGIA_VOLVER = [self.VIGIA_FRAME]
        self.tray_icon = None
        self.tray_thread = None
        self._tray_cleanup_done = False
        self.contenido_productos = None
        self.contenido_publicidad = None
        self._seccion_productos_creada = False
        self._seccion_publicidad_creada = False
        self._bootstrap_finalizado = False
        self._modulo_inicializando = None

        logger.debug("Cargando configuraciÃ³n JSON.")
        self.config_data = cargar_config()
        self.usuario_windows = _obtener_scope_instancia()
        self._asegurar_perfiles_usuario_config()
        self.permisos_usuario = self._resolver_permisos_usuario()
        self.DICT_WIDGETS.register("CONFIG", "config_json", self.config_data)
        self.DICT_WIDGETS.register("CONFIG", "usuario_windows", self.usuario_windows)
        self.DICT_WIDGETS.register("CONFIG", "permisos_usuario", self.permisos_usuario)

        try:
            locale.setlocale(locale.LC_TIME, "Spanish_Spain")  # o 'es_AR.UTF-8'
            logger.debug("Locale configurado correctamente | locale=Spanish_Spain")
        except Exception:
            logger.exception("No se pudo configurar locale 'Spanish_Spain'.")

        logger.debug("Creando ventana principal ttkbootstrap.")
        self.ventana_creacion_caja = ttk.Window(themename="flatly", iconphoto=ICON())
        self.ventana_creacion_caja.title(f"VeriPre_Connector, V.{version}")
        self.ventana_creacion_caja.state("zoomed")
        self.style = self.ventana_creacion_caja.style
        self._configurar_estilos_gui()

        self.ventana_creacion_caja.grid_columnconfigure(0, minsize=176, weight=0)
        self.ventana_creacion_caja.grid_columnconfigure(1, weight=1)
        self.ventana_creacion_caja.rowconfigure(0, weight=1)

        self.ventana_creacion_caja.protocol("WM_DELETE_WINDOW", self.ocultar_a_bandeja)

        self.DICT_WIDGETS.register("GUI_MAIN", "ventana_creacion_caja", self.ventana_creacion_caja)

        logger.debug("Construyendo frame del menÃº.")
        self.frameMenu()

        logger.debug("Construyendo frame de contenido.")
        self.frameContenido()

        logger.debug("Creando secciÃ³n inicio.")
        self.seccion_inicio()

        logger.debug("Inicializando loader CTk.")
        self.ctk_loader = CTkLoader(self.ventana_creacion_caja, opacity=0.8, width=40, height=40)
        self.DICT_WIDGETS.register("CTK_Loader_Frame", "start", self.ctk_loader.start_loader)
        self.DICT_WIDGETS.register("CTK_Loader_Frame", "stop", self.ctk_loader.stop_loader)
        self.DICT_WIDGETS.register("CTK_Loader_Frame", "message", self.ctk_loader.set_message)
        self.mostrar_loader_global("Iniciando SmartPrice...")
        self.ventana_creacion_caja.after(80, self._iniciar_bootstrap)

        atexit.register(self._cleanup_tray_icon)

        logger.info("AplicaciÃ³n iniciada correctamente. Entrando en mainloop.")
        self.ventana_creacion_caja.mainloop()

        self._cleanup_tray_icon()

        logger.debug("Mainloop finalizado. Imprimiendo WidgetRegistry.")
        self.DICT_WIDGETS.print_dict()

    def _configurar_estilos_gui(self):
        self.style.configure(
            "TButton",
            padding=(11, 7),
            font=("Segoe UI", 10, "bold"),
        )
        self.sidebar_bg = "#f3f6fa"
        self.sidebar_card = "#f3fbf6"
        self.sidebar_card_hover = "#ddf4e7"
        self.sidebar_card_active = "#149455"
        self.sidebar_text = "#173227"
        self.sidebar_text_active = "#ffffff"
        self.sidebar_muted = "#4f6478"
        self.sidebar_border = "#e6edf4"
        self.sidebar_brand = "#149455"
        self.sidebar_item_width = 158

    def mostrar_loader_global(self, mensaje="Cargando..."):
        try:
            self.ctk_loader.start_loader(mensaje)
            self.ventana_creacion_caja.update_idletasks()
        except Exception:
            logger.exception("No se pudo mostrar el loader global.")

    def actualizar_loader_global(self, mensaje):
        try:
            self.ctk_loader.set_message(mensaje)
            self.ventana_creacion_caja.update_idletasks()
        except Exception:
            logger.exception("No se pudo actualizar el texto del loader global.")

    def ocultar_loader_global(self):
        try:
            self.ctk_loader.stop_loader()
        except Exception:
            logger.exception("No se pudo ocultar el loader global.")

    def _iniciar_bootstrap(self):
        pasos = [
            ("Preparando base local...", self.CONEXIONES_DBA),
            ("Registrando variables globales...", self.VARIABLES_GLOBALES),
            ("Preparando módulo inicial...", self._preparar_modulo_inicial),
            ("Aplicando pantalla inicial...", self._bootstrap_seccion_inicial),
            ("Inicializando bandeja del sistema...", self.crear_icono_bandeja),
        ]
        self._ejecutar_pasos_bootstrap(pasos, 0)

    def _ejecutar_pasos_bootstrap(self, pasos, index):
        if index >= len(pasos):
            self._bootstrap_finalizado = True
            self.ocultar_loader_global()
            logger.info("Bootstrap inicial completado correctamente.")
            return

        mensaje, accion = pasos[index]
        logger.debug("Bootstrap paso %s/%s | %s", index + 1, len(pasos), mensaje)
        self.actualizar_loader_global(mensaje)

        def correr_paso():
            try:
                accion()
            except Exception:
                logger.exception("Error en bootstrap inicial | paso=%s", mensaje)
                self.actualizar_loader_global("Ocurrió un error al iniciar la aplicación.")
                messagebox.showerror(
                    "Error de inicio",
                    f"No se pudo completar el inicio de SmartPrice.\n\nPaso: {mensaje}",
                )
                self.ocultar_loader_global()
                return
            self.ventana_creacion_caja.after(50, lambda: self._ejecutar_pasos_bootstrap(pasos, index + 1))

        self.ventana_creacion_caja.after(20, correr_paso)

    def _bootstrap_seccion_inicial(self):
        self._ajustar_seccion_inicial_por_permisos()
        logger.debug("Seleccionando sección inicial.")
        self.selector_seccion()

    def _preparar_modulo_inicial(self):
        self._ajustar_seccion_inicial_por_permisos()
        if self.VIGIA_FRAME == "BOTON_PRODUCTOS":
            self._asegurar_modulo("productos")
        elif self.VIGIA_FRAME == "BOTON_PUBLICIDAD":
            self._asegurar_modulo("publicidad")

    def _asegurar_modulo(self, modulo):
        if modulo == "productos":
            if not self._seccion_productos_creada:
                self.seccion_productos()
            return self.contenido_productos
        if modulo == "publicidad":
            if not self._seccion_publicidad_creada:
                self.seccion_publicidad()
            return self.contenido_publicidad
        return None

    def _abrir_modulo_con_loader(self, modulo, mensaje, callback_despues=None):
        if self._modulo_inicializando == modulo:
            return

        self._modulo_inicializando = modulo
        self.mostrar_loader_global(mensaje)

        def tarea():
            try:
                self._asegurar_modulo(modulo)
                if modulo == "productos":
                    self.VIGIA_FRAME = "BOTON_PRODUCTOS"
                elif modulo == "publicidad":
                    self.VIGIA_FRAME = "BOTON_PUBLICIDAD"
                self.selector_seccion()
                if callback_despues:
                    self._modulo_inicializando = None
                    self.ocultar_loader_global()
                    self.ventana_creacion_caja.after(20, callback_despues)
                    return
            except Exception:
                logger.exception("No se pudo abrir el módulo %s.", modulo)
                messagebox.showerror("Error", f"No se pudo abrir el módulo {modulo}.")
            finally:
                if self._modulo_inicializando == modulo:
                    self._modulo_inicializando = None
                    self.ocultar_loader_global()

        self.ventana_creacion_caja.after(40, tarea)

    def _asegurar_perfiles_usuario_config(self):
        perfiles = self.config_data.setdefault("perfiles_usuario", {})
        changed = False

        defaults = {
            "default": {
                "modulos": {
                    "productos": True,
                    "publicidad": True,
                    "configuracion": True,
                }
            },
            "administrador": {
                "modulos": {
                    "productos": True,
                    "publicidad": True,
                    "configuracion": True,
                }
            },
            "pantalla": {
                "modulos": {
                    "productos": False,
                    "publicidad": True,
                    "configuracion": False,
                }
            },
        }

        for perfil, perfil_default in defaults.items():
            if perfil not in perfiles:
                perfiles[perfil] = perfil_default
                changed = True
                continue

            modulos = perfiles[perfil].setdefault("modulos", {})
            for modulo, valor in perfil_default["modulos"].items():
                if modulo not in modulos:
                    modulos[modulo] = valor
                    changed = True

        if self.usuario_windows not in perfiles:
            perfiles[self.usuario_windows] = {
                "modulos": {
                    "productos": False,
                    "publicidad": False,
                    "configuracion": False,
                },
                "estado": "pendiente",
            }
            changed = True
            logger.info(
                "Usuario Windows nuevo detectado. Se crea perfil pendiente sin accesos | usuario=%s",
                self.usuario_windows,
            )

        if changed:
            guardar_config(self.config_data)
            logger.info("Perfiles de usuario iniciales asegurados en config.json")

    def _resolver_permisos_usuario(self):
        perfiles = self.config_data.get("perfiles_usuario", {})
        perfil = perfiles.get(self.usuario_windows) or perfiles.get("default", {})
        modulos = perfil.get("modulos", {})
        permisos = {
            "productos": bool(modulos.get("productos", True)),
            "publicidad": bool(modulos.get("publicidad", True)),
            "configuracion": bool(modulos.get("configuracion", True)),
        }
        logger.info(
            "Permisos resueltos para usuario Windows | usuario=%s | permisos=%s",
            self.usuario_windows,
            permisos,
        )
        return permisos

    def _tiene_permiso(self, modulo):
        return bool(self.permisos_usuario.get(modulo, False))

    def _ajustar_seccion_inicial_por_permisos(self):
        if self._tiene_permiso("productos"):
            self.VIGIA_FRAME = "BOTON_PRODUCTOS"
            self.VIGIA_VOLVER = [self.VIGIA_FRAME]
        elif self._tiene_permiso("publicidad"):
            self.VIGIA_FRAME = "BOTON_PUBLICIDAD"
            self.VIGIA_VOLVER = [self.VIGIA_FRAME]
        else:
            self.VIGIA_FRAME = "INICIO"
            self.VIGIA_VOLVER = [self.VIGIA_FRAME]

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
            if self.tray_icon is not None:
                logger.debug("El icono de bandeja ya estaba creado. Se omite recrearlo.")
                return

            ruta_icono = os.path.join(ICON_ico())
            logger.debug("Cargando icono de bandeja | ruta=%s", ruta_icono)

            image = Image.open(ruta_icono).resize((64, 64), Image.Resampling.LANCZOS)

            def mostrar_ventana(icon, item):
                self.ventana_creacion_caja.after(0, self.mostrar_desde_bandeja)

            def salir_app(icon, item):
                logger.info("Acción bandeja: salir de la aplicación.")
                self.ventana_creacion_caja.after(0, self.cerrar_aplicacion)

            menu = TrayMenu(
                MenuItem("Mostrar ventana", mostrar_ventana, default=True),
                MenuItem("Salir", salir_app)
            )

            self.tray_icon = TrayIcon("VeriPre", image, menu=menu)
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()

            logger.info("Icono de bandeja creado correctamente.")

        except Exception:
            logger.exception("Error al crear icono de bandeja.")

    def _cleanup_tray_icon(self):
        if self._tray_cleanup_done:
            return

        self._tray_cleanup_done = True
        icon = self.tray_icon
        self.tray_icon = None

        if icon is None:
            return

        try:
            icon.visible = False
        except Exception:
            logger.debug("No se pudo ocultar el icono antes de detenerlo.", exc_info=True)

        try:
            icon.stop()
            logger.info("Icono de bandeja detenido correctamente.")
        except Exception:
            logger.exception("Error al detener el icono de bandeja.")

    def cerrar_aplicacion(self):
        logger.info("Cerrando aplicación de forma controlada.")
        self._cleanup_tray_icon()
        try:
            self.ventana_creacion_caja.destroy()
        except Exception:
            logger.exception("Error al destruir la ventana principal durante el cierre.")

    def frameMenu(self):
        logger.debug("Construyendo frameMenu.")

        self.frame_menu = ttk.Frame(
            self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"),
            bootstyle="light",
            width=176,
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_menu", self.frame_menu)
        self.frame_menu.grid(row=0, column=0, sticky="NSEW")
        self.frame_menu.grid_propagate(False)

        self.frame_menu_inner = tk.Frame(
            self.frame_menu,
            bg=self.sidebar_bg,
            padx=6,
            pady=14,
        )
        self.frame_menu_inner.pack(fill="both", expand=True)

        # LOGO
        self.frame_logo = tk.Frame(self.frame_menu_inner, bg=self.sidebar_bg)
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_logo", self.frame_logo)
        self.frame_logo.pack(fill="x")

        self.photo_logo = self._cargar_logo_sidebar(PNG_LOGO_SECUNDARIO(), max_width=158, max_height=28)

        self.label_image_logo = tk.Label(
            self.frame_logo,
            image=self.photo_logo,
            bg=self.sidebar_bg,
            bd=0,
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "label_image_logo", self.label_image_logo)
        self.label_image_logo.pack(pady=(2, 12), anchor="center")

        # BOTONES OPCIONES
        self.frame_botones_opciones = tk.Frame(self.frame_menu_inner, bg=self.sidebar_bg)
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_botones_opciones", self.frame_botones_opciones)
        self.frame_botones_opciones.pack(fill="both", expand=True)

        self.nav_card = tk.Frame(
            self.frame_botones_opciones,
            bg=self.sidebar_bg,
            bd=0,
            highlightthickness=0,
            width=self.sidebar_item_width,
            padx=2,
            pady=0,
        )
        self.nav_card.pack(anchor="n", pady=(2, 0))

        self.photo_publicidad = READ_IMG(PNG_Publicidad(), 28, 28)
        self.photo_productos = READ_IMG(PNG_Productos(), 28, 28)
        self.menu_cards = {}
        self.frame_boton_productos = None
        self.frame_boton_publicidad = None

        if self._tiene_permiso("productos"):
            self.frame_boton_productos = self._crear_tarjeta_menu(
                "productos",
                self.photo_productos,
                "Productos",
                self.command_button_productos,
            )
            self.DICT_WIDGETS.register("GUI_MAIN", "frame_boton_productos", self.frame_boton_productos)

        if self._tiene_permiso("publicidad"):
            self.frame_boton_publicidad = self._crear_tarjeta_menu(
                "publicidad",
                self.photo_publicidad,
                "Publicidad",
                self.command_button_publicidad,
            )
            self.DICT_WIDGETS.register("GUI_MAIN", "frame_boton_publicidad", self.frame_boton_publicidad)

        self.frame_botones_config_info = tk.Frame(self.frame_menu_inner, bg=self.sidebar_bg)
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_botones_config_info", self.frame_botones_config_info)
        self.frame_botones_config_info.pack(pady=(14, 0), side="bottom", fill="x")

        self.footer_card = tk.Frame(
            self.frame_botones_config_info,
            bg=self.sidebar_bg,
            bd=0,
            highlightthickness=0,
            width=self.sidebar_item_width,
            padx=2,
            pady=2,
        )
        self.footer_card.pack(anchor="s")

        self.photo_setting = READ_IMG(PNG_Settings(), 20, 20)
        self.boton_setting = None
        self.boton_setting_icon = None
        self.boton_setting_texto = None
        if self._tiene_permiso("configuracion"):
            self.boton_setting = tk.Frame(
                self.footer_card,
                bg=self.sidebar_card,
                cursor="hand2",
            )
            self.DICT_WIDGETS.register("GUI_MAIN", "boton_setting", self.boton_setting)
            self.boton_setting.pack(fill="x", pady=(0, 10))

            self.boton_setting_icon = tk.Label(self.boton_setting, image=self.photo_setting, bg=self.sidebar_card, bd=0)
            self.boton_setting_icon.pack(side="left")
            self.boton_setting_texto = tk.Label(
                self.boton_setting,
                text="Configuración",
                bg=self.sidebar_card,
                fg=self.sidebar_muted,
                font=("Segoe UI", 10, "bold"),
            )
            self.boton_setting_texto.pack(side="left", padx=(10, 0))

            for widget in (self.boton_setting, self.boton_setting_icon, self.boton_setting_texto):
                widget.bind("<Button-1>", lambda _e: self.command_button_configuracion())
                widget.bind("<Enter>", lambda _e: self._hover_footer_action(self.boton_setting, self.boton_setting_icon, self.boton_setting_texto, True))
                widget.bind("<Leave>", lambda _e: self._hover_footer_action(self.boton_setting, self.boton_setting_icon, self.boton_setting_texto, False))

        self.photo_info = READ_IMG(PNG_Info(), 20, 20)
        self.boton_info = tk.Frame(
            self.footer_card,
            bg=self.sidebar_card,
            cursor="hand2",
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "boton_info", self.boton_info)
        self.boton_info.pack(fill="x")

        self.boton_info_icon = tk.Label(self.boton_info, image=self.photo_info, bg=self.sidebar_card, bd=0)
        self.boton_info_icon.pack(side="left")
        self.boton_info_texto = tk.Label(
            self.boton_info,
            text="Acerca de",
            bg=self.sidebar_card,
            fg=self.sidebar_muted,
            font=("Segoe UI", 10, "bold"),
        )
        self.boton_info_texto.pack(side="left", padx=(10, 0))

        for widget in (self.boton_info, self.boton_info_icon, self.boton_info_texto):
            widget.bind("<Enter>", lambda _e: self._hover_footer_action(self.boton_info, self.boton_info_icon, self.boton_info_texto, True))
            widget.bind("<Leave>", lambda _e: self._hover_footer_action(self.boton_info, self.boton_info_icon, self.boton_info_texto, False))

        logger.debug("frameMenu construido correctamente.")

    def _cargar_logo_sidebar(self, path, max_width, max_height):
        image_logo = Image.open(path)
        image_logo.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image_logo)

    def _crear_tarjeta_menu(self, key, image, text, command):
        frame = tk.Frame(
            self.nav_card,
            bg=self.sidebar_bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        frame.pack(fill="x", pady=(0, 4))

        canvas = tk.Canvas(
            frame,
            width=self.sidebar_item_width,
            height=46,
            bg=self.sidebar_bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        canvas.pack(anchor="center")

        def on_enter(_event):
            if not self.menu_cards.get(key, {}).get("active"):
                self._aplicar_estado_tarjeta_menu(key, hover=True)

        def on_leave(_event):
            if not self.menu_cards.get(key, {}).get("active"):
                self._aplicar_estado_tarjeta_menu(key, hover=False)

        for widget in (frame, canvas):
            widget.bind("<Button-1>", lambda _e: command())
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        bg_shape = self._draw_rounded_rect(canvas, 2, 2, 10, 44, 14, fill=self.sidebar_card, outline="")
        icon_id = canvas.create_image(16, 23, image=image, anchor="w")
        text_id = canvas.create_text(
            50,
            23,
            text=text,
            fill=self.sidebar_text,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )

        def redraw(_event):
            width = max(canvas.winfo_width() - 2, 10)
            height = max(canvas.winfo_height() - 2, 10)
            canvas.coords(bg_shape, self._rounded_rect_points(2, 2, width, height, 14))
            canvas.coords(icon_id, 16, height / 2)
            canvas.coords(text_id, 50, height / 2)

        canvas.bind("<Configure>", redraw)

        self.menu_cards[key] = {
            "frame": frame,
            "canvas": canvas,
            "shape": bg_shape,
            "icon_id": icon_id,
            "text_id": text_id,
            "active": False,
        }
        self._aplicar_estado_tarjeta_menu(key, active=False, hover=False)
        return frame

    def _aplicar_estado_tarjeta_menu(self, key, active=None, hover=False):
        data = self.menu_cards.get(key)
        if not data:
            return

        if active is not None:
            data["active"] = active

        if data["active"]:
            bg = self.sidebar_card_active
        elif hover:
            bg = self.sidebar_card_hover
        else:
            bg = self.sidebar_card

        data["frame"].configure(bg=self.sidebar_bg)
        data["canvas"].itemconfigure(data["shape"], fill=bg)
        data["canvas"].itemconfigure(
            data["text_id"],
            fill=self.sidebar_text_active if data["active"] else self.sidebar_text,
        )

    def _hover_footer_action(self, frame, icon, label, hover):
        bg = self.sidebar_card_hover if hover else self.sidebar_card
        fg = self.sidebar_brand if hover else self.sidebar_muted
        frame.configure(bg=bg)
        icon.configure(bg=bg)
        label.configure(bg=bg, fg=fg)

    def _rounded_rect_points(self, x1, y1, x2, y2, radius):
        return [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        return canvas.create_polygon(
            self._rounded_rect_points(x1, y1, x2, y2, radius),
            smooth=True,
            splinesteps=24,
            **kwargs,
        )

    def frameContenido(self):
        logger.debug("Construyendo frameContenido.")

        self.frame_contenido = ttk.Frame(
            self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"),
            padding=(20, 18),
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_contenido", self.frame_contenido)
        self.frame_contenido.grid(row=0, column=1, sticky="NSEW")

        self.frame_barra_superior = ttk.Frame(self.frame_contenido)
        self.photo_back = READ_IMG(PNG_Back(), 30, 30)
        self.boton_back = ttk.Button(
            self.frame_barra_superior,
            image=self.photo_back,
            command=self.command_button_volver,
            bootstyle="primary-link",
        )
        self.boton_back.pack(side="left")

        logger.debug("frameContenido construido correctamente.")

    def command_button_productos(self):
        if not self._tiene_permiso("productos"):
            messagebox.showwarning("Acceso restringido", "Este usuario no tiene acceso al módulo Productos.")
            return
        logger.info("NavegaciÃ³n solicitada a secciÃ³n PRODUCTOS.")
        self._abrir_modulo_con_loader(
            "productos",
            "Cargando módulo Productos...",
            callback_despues=lambda: self.contenido_productos.cargar_productos_locales_con_loader(
                force=True,
                mostrar_sin_datos=True,
            ),
        )

    def command_button_publicidad(self):
        if not self._tiene_permiso("publicidad"):
            messagebox.showwarning("Acceso restringido", "Este usuario no tiene acceso al módulo Publicidad.")
            return
        logger.info("NavegaciÃ³n solicitada a secciÃ³n PUBLICIDAD.")
        self._abrir_modulo_con_loader("publicidad", "Cargando módulo Publicidad...")

    def command_button_configuracion(self):
        if not self._tiene_permiso("configuracion"):
            messagebox.showwarning("Acceso restringido", "Este usuario no tiene acceso al módulo Configuración.")
            return
        VentanaManager.abrir_ventana("configuracion", GUI_CONFIG, self.DICT_WIDGETS)

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
        frame_productos = getattr(self, "frame_seccion_productos", None)
        frame_publicidad = getattr(self, "frame_seccion_publicidad", None)

        if self.VIGIA_FRAME == "BOTON_PRODUCTOS" and not self._tiene_permiso("productos"):
            self._ajustar_seccion_inicial_por_permisos()
        elif self.VIGIA_FRAME == "BOTON_PUBLICIDAD" and not self._tiene_permiso("publicidad"):
            self._ajustar_seccion_inicial_por_permisos()

        if self.VIGIA_FRAME == "INICIO":
            self.VIGIA_VOLVER = ["INICIO"]
            self.frame_seccion_inicio.pack(fill="both", expand=True)
            if frame_productos:
                frame_productos.pack_forget()
            if frame_publicidad:
                frame_publicidad.pack_forget()
            self.frame_barra_superior.pack_forget()

        elif self.VIGIA_FRAME == "BOTON_PRODUCTOS":
            if frame_publicidad:
                frame_publicidad.pack_forget()
            self.frame_seccion_inicio.pack_forget()
            self.frame_barra_superior.pack(fill="x")
            if frame_productos:
                frame_productos.pack(fill="both", expand=True)

        elif self.VIGIA_FRAME == "BOTON_PUBLICIDAD":
            if frame_productos:
                frame_productos.pack_forget()
            self.frame_seccion_inicio.pack_forget()
            self.frame_barra_superior.pack(fill="x")
            if frame_publicidad:
                frame_publicidad.pack(fill="both", expand=True)

        if self.VIGIA_VOLVER[-1] != self.VIGIA_FRAME and self.VIGIA_FRAME not in self.VIGIA_VOLVER:
            self.VIGIA_VOLVER.append(self.VIGIA_FRAME)

        self._actualizar_estilo_menu_activo()

        logger.debug("SecciÃ³n aplicada | historial_resultante=%s", self.VIGIA_VOLVER)

    def _actualizar_estilo_menu_activo(self):
        activo_productos = self.VIGIA_FRAME == "BOTON_PRODUCTOS"
        activo_publicidad = self.VIGIA_FRAME == "BOTON_PUBLICIDAD"
        try:
            self._aplicar_estado_tarjeta_menu("productos", active=activo_productos)
            self._aplicar_estado_tarjeta_menu("publicidad", active=activo_publicidad)
        except Exception:
            logger.exception("No se pudo actualizar estilo del menu activo.")

    def seccion_inicio(self):
        logger.debug("Creando widgets de secciÃ³n INICIO.")

        self.frame_seccion_inicio = ttk.Frame(self.frame_contenido)
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_inicio", self.frame_seccion_inicio)

        self.label_inicio = ttk.Label(self.frame_seccion_inicio, text="Bienvenidos", font=("Segoe UI", 22, "bold"))
        self.label_inicio.pack(pady=(30, 8), anchor="w")
        ttk.Label(
            self.frame_seccion_inicio,
            text="Seleccioná una sección del panel lateral para comenzar.",
            bootstyle="secondary",
            font=("Segoe UI", 11),
        ).pack(anchor="w")
        ttk.Label(
            self.frame_seccion_inicio,
            text=f"Usuario actual: {self.usuario_windows}",
            bootstyle="secondary",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(6, 0))
        if not any(self.permisos_usuario.values()):
            ttk.Label(
                self.frame_seccion_inicio,
                text="Acceso pendiente de autorización. Un administrador debe habilitar tus módulos.",
                bootstyle="warning",
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w", pady=(10, 0))

    def seccion_productos(self):
        logger.debug("Creando widgets de secciÃ³n PRODUCTOS.")

        if not self._seccion_productos_creada:
            self.frame_seccion_productos = ttk.Frame(self.frame_contenido)
            self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_productos", self.frame_seccion_productos)
            self.contenido_productos = ContenidoProducto(self.DICT_WIDGETS)
            self._seccion_productos_creada = True
            logger.debug("ContenidoProducto inicializado correctamente.")

    def seccion_publicidad(self):
        logger.debug("Creando widgets de secciÃ³n PUBLICIDAD.")

        if not self._seccion_publicidad_creada:
            self.frame_seccion_publicidad = ttk.Frame(self.frame_contenido)
            self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_publicidad", self.frame_seccion_publicidad)
            self.contenido_publicidad = ContenidoPublicidad(self.DICT_WIDGETS)
            self._seccion_publicidad_creada = True
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
