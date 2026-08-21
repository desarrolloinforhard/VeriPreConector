import os
import threading
import json
import locale
import socket
import sys
import getpass
import hashlib
import atexit
import ctypes
import subprocess

import ttkbootstrap as ttk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

from ASSETS.path_img import *
from pystray import Icon as TrayIcon, Menu as TrayMenu, MenuItem
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
from core.ui.loading_overlay import LoadingOverlay
from core.ui.ttk_theme import (
    SMARTPRICE_DARK_THEME,
    SMARTPRICE_LIGHT_THEME,
    registrar_tema_smartprice,
)
from core.ui.responsive import clamp, get_size_class, get_workarea_size
from core.ui.theme_tokens import (
    BUTTON_PAD_X,
    BUTTON_PAD_Y,
    FONT_BODY_BOLD,
    FONT_LABEL_BOLD,
    FONT_SUBTITLE,
    FONT_TITLE_XL,
)

logger = get_logger(__name__)
ERROR_ALREADY_EXISTS = 183


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


def _obtener_nombre_mutex_instancia():
    scope = _obtener_scope_instancia()
    digest = hashlib.blake2b(scope.encode("utf-8"), digest_size=8).hexdigest()
    return f"Local\\SmartPrice_{digest}"


def _adquirir_mutex_instancia():
    if os.name != "nt":
        return None, False

    nombre_mutex = _obtener_nombre_mutex_instancia()
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, nombre_mutex)
    if not handle:
        logger.warning("No se pudo crear/abrir mutex de instancia | nombre=%s", nombre_mutex)
        return None, False

    already_exists = kernel32.GetLastError() == ERROR_ALREADY_EXISTS
    logger.debug(
        "Mutex de instancia resuelto | nombre=%s | already_exists=%s",
        nombre_mutex,
        already_exists,
    )
    return handle, already_exists


def _liberar_mutex_instancia(handle):
    if os.name != "nt" or not handle:
        return

    try:
        ctypes.windll.kernel32.CloseHandle(handle)
        logger.info("Mutex de instancia liberado correctamente.")
    except Exception:
        logger.exception("Error al liberar el mutex de instancia.")


def _notificar_instancia_existente(puerto, scope):
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=1.5) as cliente:
            cliente.sendall(b"SHOW\n")
        logger.info(
            "Se notificó a la instancia existente para mostrar la ventana | puerto=%s | scope_usuario=%s",
            puerto,
            scope,
        )
        return True
    except OSError:
        logger.warning(
            "No se pudo notificar a la instancia existente | puerto=%s | scope_usuario=%s",
            puerto,
            scope,
        )
        return False


def comprobar_instancia_unica(puerto_base=55665):
    puerto, scope = _obtener_puerto_instancia(puerto_base)
    mutex_handle, already_exists = _adquirir_mutex_instancia()
    logger.debug(
        "Verificando instancia única de la aplicación | puerto=%s | scope_usuario=%s",
        puerto,
        scope,
    )

    if already_exists:
        logger.warning(
            "Se detectó otra instancia en ejecución para el mismo usuario por mutex | puerto=%s | scope_usuario=%s",
            puerto,
            scope,
        )
        _notificar_instancia_existente(puerto, scope)
        messagebox.showinfo(
            "Aplicación ya en ejecución",
            "La aplicación ya está abierta para este usuario.\n"
            "Si estaba minimizada, se intentó mostrarla automáticamente."
        )
        sys.exit(0)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", puerto))
        sock.listen(5)
        logger.info(
            "Instancia única confirmada. Socket de bloqueo adquirido | puerto=%s | scope_usuario=%s",
            puerto,
            scope,
        )
        return {
            "socket": sock,
            "puerto": puerto,
            "scope": scope,
            "mutex": mutex_handle,
        }
    except OSError:
        logger.warning(
            "No se pudo abrir el socket de control de instancia | puerto=%s | scope_usuario=%s",
            puerto,
            scope,
        )
        return {
            "socket": None,
            "puerto": puerto,
            "scope": scope,
            "mutex": mutex_handle,
        }


class GUI_MAIN:
    def __init__(self, version):
        logger.info("Iniciando GUI_MAIN | version=%s", version)
        self.version = version

        self.socket_lock = comprobar_instancia_unica()
        self.socket_lock_server = self.socket_lock["socket"]
        self.socket_lock_port = self.socket_lock["puerto"]
        self.socket_lock_scope = self.socket_lock["scope"]
        self.instance_mutex = self.socket_lock.get("mutex")
        self.socket_listener_thread = None
        self._socket_listener_running = False
        self.DICT_WIDGETS = WidgetRegistry()
        self.DICT_WIDGETS.register("GUI_MAIN", "instance", self)
        self.VIGIA_FRAME = "INICIO"
        self.VIGIA_VOLVER = [self.VIGIA_FRAME]
        self.tray_icon = None
        self.tray_thread = None
        self._tray_cleanup_done = False
        self.contenido_productos = None
        self.contenido_publicidad = None
        self._seccion_productos_creada = False
        self._seccion_publicidad_creada = False
        self._seccion_acerca_creada = False
        self._bootstrap_finalizado = False
        self._modulo_inicializando = None
        self._responsive_after_id = None
        self._sidebar_render_state = None
        self._main_layout_state = None
        self._sidebar_asset_state = None
        self._sidebar_logo_state = None
        self.sidebar_collapsed = False

        logger.debug("Cargando configuración JSON.")
        self.config_data = cargar_config()
        self.usuario_windows = _obtener_scope_instancia()
        self.usuario_windows_es_admin = self._es_usuario_windows_admin()
        self._asegurar_perfiles_usuario_config()
        self.permisos_usuario = self._resolver_permisos_usuario()
        self.DICT_WIDGETS.register("CONFIG", "config_json", self.config_data)
        self.DICT_WIDGETS.register("CONFIG", "usuario_windows", self.usuario_windows)
        self.DICT_WIDGETS.register("CONFIG", "usuario_windows_es_admin", self.usuario_windows_es_admin)
        self.DICT_WIDGETS.register("CONFIG", "permisos_usuario", self.permisos_usuario)

        try:
            locale.setlocale(locale.LC_TIME, "Spanish_Spain")  # o 'es_AR.UTF-8'
            logger.debug("Locale configurado correctamente | locale=Spanish_Spain")
        except Exception:
            logger.exception("No se pudo configurar locale 'Spanish_Spain'.")

        logger.debug("Creando ventana principal ttkbootstrap.")
        registrar_tema_smartprice()
        self.ventana_creacion_caja = ttk.Window(
            theme=SMARTPRICE_LIGHT_THEME,
            light_theme=SMARTPRICE_LIGHT_THEME,
            dark_theme=SMARTPRICE_DARK_THEME,
            iconphoto=ICON(),
        )
        self.ventana_creacion_caja.title(f"VeriPre_Connector, V.{version}")
        self.ventana_creacion_caja.state("zoomed")
        self.style = self.ventana_creacion_caja.style
        self._configurar_estilos_gui()

        self.ventana_creacion_caja.grid_columnconfigure(0, minsize=176, weight=0)
        self.ventana_creacion_caja.grid_columnconfigure(1, weight=1)
        self.ventana_creacion_caja.rowconfigure(0, weight=1)

        self.ventana_creacion_caja.protocol("WM_DELETE_WINDOW", self.ocultar_a_bandeja)
        self.ventana_creacion_caja.bind("<Configure>", self._programar_layout_responsivo, add="+")

        self.DICT_WIDGETS.register("GUI_MAIN", "ventana_creacion_caja", self.ventana_creacion_caja)

        logger.debug("Construyendo frame del menú.")
        self.frameMenu()

        logger.debug("Construyendo frame de contenido.")
        self.frameContenido()

        logger.debug("Creando sección inicio.")
        self.seccion_inicio()

        logger.debug("Inicializando overlay de carga ttk.")
        self.ctk_loader = LoadingOverlay(self.ventana_creacion_caja, opacity=0.8, width=40, height=40)
        self.DICT_WIDGETS.register("CTK_Loader_Frame", "start", self.ctk_loader.start_loader)
        self.DICT_WIDGETS.register("CTK_Loader_Frame", "stop", self.ctk_loader.stop_loader)
        self.DICT_WIDGETS.register("CTK_Loader_Frame", "message", self.ctk_loader.set_message)
        self.mostrar_loader_global("Iniciando SmartPrice...")
        self._iniciar_listener_instancia()
        self.ventana_creacion_caja.after(80, self._iniciar_bootstrap)

        atexit.register(self._cleanup_tray_icon)

        logger.info("Aplicación iniciada correctamente. Entrando en mainloop.")
        self.ventana_creacion_caja.mainloop()

        self._cleanup_tray_icon()

        logger.debug("Mainloop finalizado. Imprimiendo WidgetRegistry.")
        self.DICT_WIDGETS.print_dict()

    def _configurar_estilos_gui(self):
        self.style.configure(
            "TButton",
            padding=(BUTTON_PAD_X + 5, BUTTON_PAD_Y + 3),
            font=FONT_BODY_BOLD,
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
        self.sidebar_expanded_width = 176
        self.sidebar_item_width = 158
        self.sidebar_collapsed_width = 68
        self.sidebar_collapsed_item_width = 52
        self.content_padding_x = 20
        self.content_padding_y = 18

    def _iniciar_listener_instancia(self):
        if self._socket_listener_running or self.socket_lock_server is None:
            return

        self._socket_listener_running = True

        def escuchar():
            logger.debug(
                "Listener de instancia única iniciado | puerto=%s | scope_usuario=%s",
                self.socket_lock_port,
                self.socket_lock_scope,
            )
            while self._socket_listener_running:
                try:
                    cliente, _addr = self.socket_lock_server.accept()
                except OSError:
                    break

                with cliente:
                    try:
                        mensaje = cliente.recv(64).decode("utf-8", errors="ignore").strip().upper()
                    except OSError:
                        continue

                if mensaje == "SHOW":
                    logger.info("Se recibió solicitud SHOW desde otra instancia.")
                    try:
                        self.ventana_creacion_caja.after(0, self.mostrar_desde_bandeja)
                    except Exception:
                        logger.exception("No se pudo mostrar la ventana desde el listener de instancia.")

            logger.debug("Listener de instancia única detenido.")

        self.socket_listener_thread = threading.Thread(target=escuchar, daemon=True)
        self.socket_listener_thread.start()

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

    def _programar_layout_responsivo(self, _event=None):
        if self._responsive_after_id:
            try:
                self.ventana_creacion_caja.after_cancel(self._responsive_after_id)
            except Exception:
                pass
        self._responsive_after_id = self.ventana_creacion_caja.after(80, self._aplicar_layout_responsivo)

    def _aplicar_layout_responsivo(self):
        self._responsive_after_id = None
        try:
            work_width, work_height = get_workarea_size(self.ventana_creacion_caja)
            current_width = self.ventana_creacion_caja.winfo_width()
            current_height = self.ventana_creacion_caja.winfo_height()
            window_width = current_width if current_width > 1 else work_width
            window_height = current_height if current_height > 1 else work_height
            size_class = get_size_class(window_width, window_height)

            if size_class == "compact":
                sidebar_width = clamp(int(window_width * 0.122), 148, 160)
                content_padding_x = 12
                content_padding_y = 12
                logo_max_width = sidebar_width - 26
                logo_max_height = 22
                menu_item_height = 42
                menu_font = ("Segoe UI", 9, "bold")
                icon_size = 24
                footer_icon_size = 18
                footer_font = ("Segoe UI", 9, "bold")
                top_logo_pad = (2, 10)
                footer_pad_top = 10
                inicio_pad_top = 20
            elif size_class == "standard":
                sidebar_width = clamp(int(window_width * 0.132), 156, 172)
                content_padding_x = 16
                content_padding_y = 16
                logo_max_width = sidebar_width - 22
                logo_max_height = 26
                menu_item_height = 44
                menu_font = ("Segoe UI", 10, "bold")
                icon_size = 26
                footer_icon_size = 19
                footer_font = ("Segoe UI", 10, "bold")
                top_logo_pad = (2, 12)
                footer_pad_top = 12
                inicio_pad_top = 26
            else:
                sidebar_width = clamp(int(window_width * 0.136), 164, 182)
                content_padding_x = 18
                content_padding_y = 18
                logo_max_width = sidebar_width - 22
                logo_max_height = 28
                menu_item_height = 46
                menu_font = ("Segoe UI", 10, "bold")
                icon_size = 28
                footer_icon_size = 20
                footer_font = ("Segoe UI", 10, "bold")
                top_logo_pad = (2, 14)
                footer_pad_top = 14
                inicio_pad_top = 30

            item_width = clamp(sidebar_width - 18, 132, 172)
            self.sidebar_expanded_width = sidebar_width
            self.sidebar_item_width = item_width
            self.content_padding_x = content_padding_x
            self.content_padding_y = content_padding_y
            self.sidebar_menu_item_height = menu_item_height
            self.sidebar_menu_font = menu_font
            self.sidebar_icon_size = icon_size
            self.sidebar_footer_icon_size = footer_icon_size
            self.sidebar_footer_font = footer_font
            self.sidebar_logo_pad = top_logo_pad
            self.sidebar_footer_pad_top = footer_pad_top
            self.inicio_pad_top = inicio_pad_top
            sidebar_render = self._resolver_render_sidebar(
                sidebar_width,
                item_width,
                self.sidebar_collapsed,
            )
            effective_sidebar_width = sidebar_render["sidebar_width"]
            effective_item_width = sidebar_render["item_width"]
            wraplength_inicio = max(window_width - effective_sidebar_width - 120, 320)

            sidebar_render_state = (
                effective_sidebar_width,
                effective_item_width,
                logo_max_width,
                logo_max_height,
                menu_item_height,
                icon_size,
                footer_icon_size,
                menu_font,
                footer_font,
                top_logo_pad,
                footer_pad_top,
                inicio_pad_top,
            )
            main_layout_state = (
                effective_sidebar_width,
                content_padding_x,
                content_padding_y,
                wraplength_inicio,
            )
            should_refresh_sidebar = sidebar_render_state != self._sidebar_render_state
            should_refresh_main_layout = main_layout_state != self._main_layout_state

            if should_refresh_sidebar:
                if not sidebar_render["show_logo"]:
                    self.label_image_logo.pack_forget()
                else:
                    logo_state = (logo_max_width, logo_max_height)
                    if logo_state != self._sidebar_logo_state:
                        self.photo_logo = self._cargar_logo_sidebar(
                            PNG_LOGO_SECUNDARIO(),
                            max_width=logo_max_width,
                            max_height=logo_max_height,
                        )
                        self.label_image_logo.configure(image=self.photo_logo)
                        self.label_image_logo.image = self.photo_logo
                        self._sidebar_logo_state = logo_state
                    self.label_image_logo.pack_configure(pady=top_logo_pad, anchor="center")

                asset_state = (icon_size, footer_icon_size)
                if asset_state != self._sidebar_asset_state:
                    self.photo_publicidad = READ_IMG(PNG_Publicidad(), icon_size, icon_size)
                    self.photo_productos = READ_IMG(PNG_Productos(), icon_size, icon_size)
                    self.photo_setting = READ_IMG(PNG_Settings(), footer_icon_size, footer_icon_size)
                    self.photo_info = READ_IMG(PNG_Info(), footer_icon_size, footer_icon_size)
                    self._sidebar_asset_state = asset_state

                if "productos" in self.menu_cards:
                    self.menu_cards["productos"]["canvas"].itemconfigure(
                        self.menu_cards["productos"]["icon_id"],
                        image=self.photo_productos,
                    )
                if "publicidad" in self.menu_cards:
                    self.menu_cards["publicidad"]["canvas"].itemconfigure(
                        self.menu_cards["publicidad"]["icon_id"],
                        image=self.photo_publicidad,
                    )
                if hasattr(self, "boton_setting_icon") and self.boton_setting_icon:
                    self.boton_setting_icon.configure(image=self.photo_setting)
                    self.boton_setting_icon.image = self.photo_setting
                if hasattr(self, "boton_info_icon"):
                    self.boton_info_icon.configure(image=self.photo_info)
                    self.boton_info_icon.image = self.photo_info

                for canvas_data in self.menu_cards.values():
                    canvas_data["canvas"].configure(width=effective_item_width, height=menu_item_height)
                    canvas_data["canvas"].itemconfigure(
                        canvas_data["text_id"],
                        font=menu_font,
                        state="normal" if sidebar_render["show_text"] else "hidden",
                    )
                if hasattr(self, "boton_setting_texto") and self.boton_setting_texto:
                    self.boton_setting_texto.configure(font=footer_font)
                if hasattr(self, "boton_info_texto") and self.boton_info_texto:
                    self.boton_info_texto.configure(font=footer_font)
                if hasattr(self, "frame_botones_config_info"):
                    self.frame_botones_config_info.pack_configure(pady=(footer_pad_top, 0))
                if self.boton_setting:
                    self._render_footer_action(
                        self.boton_setting,
                        self.boton_setting_icon,
                        self.boton_setting_texto,
                        self.sidebar_collapsed,
                    )
                self._render_footer_action(
                    self.boton_info,
                    self.boton_info_icon,
                    self.boton_info_texto,
                    self.sidebar_collapsed,
                )
                if hasattr(self, "label_inicio"):
                    self.label_inicio.pack_configure(pady=(inicio_pad_top, 8))
                self._sidebar_render_state = sidebar_render_state

            if should_refresh_main_layout:
                # Preparar primero los controles internos y cambiar el ancho
                # exterior al final evita mostrar un frame intermedio con el
                # contenido compacto dentro del menú ya expandido.
                if hasattr(self, "label_inicio_subtitulo") and self.label_inicio_subtitulo:
                    self.label_inicio_subtitulo.configure(wraplength=wraplength_inicio)
                if hasattr(self, "label_inicio_usuario") and self.label_inicio_usuario:
                    self.label_inicio_usuario.configure(wraplength=wraplength_inicio)
                if hasattr(self, "label_inicio_bloqueo") and self.label_inicio_bloqueo:
                    self.label_inicio_bloqueo.configure(wraplength=wraplength_inicio)
                self.nav_card.configure(width=effective_item_width)
                self.footer_card.configure(width=effective_item_width)
                if hasattr(self, "frame_contenido"):
                    self.frame_contenido.configure(padding=(content_padding_x, content_padding_y))
                self.ventana_creacion_caja.grid_columnconfigure(
                    0,
                    minsize=effective_sidebar_width,
                    weight=0,
                )
                self.frame_menu.configure(width=effective_sidebar_width)
                self._main_layout_state = main_layout_state
        except Exception:
            logger.exception("No se pudo aplicar layout responsivo en GUI_MAIN.")

    def _resolver_render_sidebar(self, sidebar_width, item_width, collapsed):
        return {
            "sidebar_width": self.sidebar_collapsed_width if collapsed else sidebar_width,
            "item_width": self.sidebar_collapsed_item_width if collapsed else item_width,
            "show_logo": not collapsed,
            "show_text": not collapsed,
            "toggle_text": "☰" if collapsed else "‹",
        }

    def alternar_menu_lateral(self):
        redraw_handle = self._suspender_redibujado_ventana()
        try:
            self.sidebar_collapsed = not self.sidebar_collapsed
            render = self._resolver_render_sidebar(
                self.sidebar_expanded_width,
                self.sidebar_item_width,
                self.sidebar_collapsed,
            )
            self.boton_toggle_menu.configure(text=render["toggle_text"])
            self._sidebar_render_state = None
            self._main_layout_state = None
            self._aplicar_layout_responsivo()
        finally:
            self._reanudar_redibujado_ventana(redraw_handle)

    def _suspender_redibujado_ventana(self):
        """Congela el repintado de Win32 durante un cambio de layout."""
        if os.name != "nt" or not hasattr(self, "ventana_creacion_caja"):
            return None
        try:
            hwnd = int(self.ventana_creacion_caja.winfo_id())
            ctypes.windll.user32.SendMessageW(hwnd, 0x000B, False, 0)  # WM_SETREDRAW
            return hwnd
        except Exception:
            logger.debug("No se pudo suspender el redibujado del sidebar.", exc_info=True)
            return None

    def _reanudar_redibujado_ventana(self, hwnd):
        if not hwnd:
            return
        try:
            # Resolver toda la geometría mientras Win32 todavía no pinta.
            self.ventana_creacion_caja.update_idletasks()
        except Exception:
            logger.debug("No se pudo resolver la geometría del sidebar.", exc_info=True)
        finally:
            # Nunca dejar una ventana congelada aunque falle update_idletasks.
            ctypes.windll.user32.SendMessageW(hwnd, 0x000B, True, 0)  # WM_SETREDRAW
        try:
            ctypes.windll.user32.RedrawWindow(
                hwnd,
                None,
                None,
                0x0001 | 0x0080 | 0x0100,  # INVALIDATE | ALLCHILDREN | UPDATENOW
            )
        except Exception:
            logger.debug("No se pudo reanudar el redibujado del sidebar.", exc_info=True)

    def _iniciar_bootstrap(self):
        pasos = [
            ("Preparando base local...", self.CONEXIONES_DBA, True),
            ("Registrando variables globales...", self.VARIABLES_GLOBALES, False),
            ("Preparando módulo inicial...", self._preparar_modulo_inicial, False),
            ("Aplicando pantalla inicial...", self._bootstrap_seccion_inicial, False),
            ("Inicializando bandeja del sistema...", lambda: None, False),
        ]
        self._ejecutar_pasos_bootstrap(pasos, 0)

    def _ejecutar_pasos_bootstrap(self, pasos, index):
        if index >= len(pasos):
            self._bootstrap_finalizado = True
            self.ocultar_loader_global()
            logger.info("Bootstrap inicial completado correctamente.")
            return

        mensaje, accion, ejecutar_en_segundo_plano = pasos[index]
        logger.debug("Bootstrap paso %s/%s | %s", index + 1, len(pasos), mensaje)
        self.actualizar_loader_global(mensaje)

        def continuar():
            self.ventana_creacion_caja.after(
                50,
                lambda: self._ejecutar_pasos_bootstrap(pasos, index + 1),
            )

        def manejar_error(error):
            logger.error(
                "Error en bootstrap inicial | paso=%s",
                mensaje,
                exc_info=(type(error), error, error.__traceback__),
            )
            self.actualizar_loader_global("Ocurrió un error al iniciar la aplicación.")
            messagebox.showerror(
                "Error de inicio",
                f"No se pudo completar el inicio de SmartPrice.\n\nPaso: {mensaje}",
            )
            self.ocultar_loader_global()

        if ejecutar_en_segundo_plano:
            finalizado = threading.Event()
            resultado = {"error": None}

            def correr_en_segundo_plano():
                try:
                    accion()
                except Exception as error:
                    resultado["error"] = error
                finally:
                    finalizado.set()

            def comprobar_resultado():
                if not finalizado.is_set():
                    self.ventana_creacion_caja.after(50, comprobar_resultado)
                    return
                if resultado["error"] is not None:
                    manejar_error(resultado["error"])
                    return
                continuar()

            threading.Thread(target=correr_en_segundo_plano, daemon=True).start()
            self.ventana_creacion_caja.after(50, comprobar_resultado)
            return

        def correr_en_ui():
            try:
                accion()
            except Exception as error:
                manejar_error(error)
                return
            continuar()

        self.ventana_creacion_caja.after(20, correr_en_ui)

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

    def _es_usuario_windows_admin(self):
        if os.name != "nt":
            return False

        try:
            resultado = subprocess.run(
                ["whoami", "/groups"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except Exception:
            logger.exception(
                "No se pudo consultar el rol Windows del usuario actual | usuario=%s",
                self.usuario_windows,
            )
            return False

        if resultado.returncode != 0:
            logger.warning(
                "whoami /groups devolvió error al consultar rol administrador | usuario=%s | returncode=%s",
                self.usuario_windows,
                resultado.returncode,
            )
            return False

        es_admin = "S-1-5-32-544" in (resultado.stdout or "")
        logger.info(
            "Rol Windows resuelto para usuario actual | usuario=%s | es_admin=%s",
            self.usuario_windows,
            es_admin,
        )
        return es_admin

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
                perfiles[perfil] = dict(perfil_default)
                changed = True
                continue

            modulos = perfiles[perfil].setdefault("modulos", {})
            for modulo, valor in perfil_default["modulos"].items():
                if modulo not in modulos:
                    modulos[modulo] = valor
                    changed = True

        perfil_usuario = perfiles.get(self.usuario_windows)

        if perfil_usuario is None:
            if self.usuario_windows_es_admin:
                perfiles[self.usuario_windows] = {
                    "modulos": dict(defaults["administrador"]["modulos"]),
                    "estado": "activo",
                }
                logger.info(
                    "Usuario Windows nuevo detectado con rol administrador. Se crea perfil con acceso completo | usuario=%s",
                    self.usuario_windows,
                )
            else:
                perfiles[self.usuario_windows] = {
                    "modulos": {
                        "productos": False,
                        "publicidad": False,
                        "configuracion": False,
                    },
                    "estado": "pendiente",
                }
                logger.info(
                    "Usuario Windows nuevo detectado. Se crea perfil pendiente sin accesos | usuario=%s",
                    self.usuario_windows,
                )
            changed = True
        else:
            modulos_usuario = perfil_usuario.setdefault("modulos", {})
            estado_usuario = str(perfil_usuario.get("estado", "") or "").strip().lower()
            tiene_algun_modulo = any(
                bool(modulos_usuario.get(modulo, False))
                for modulo in ("productos", "publicidad", "configuracion")
            )
            if self.usuario_windows_es_admin and (estado_usuario == "pendiente" or not tiene_algun_modulo):
                perfil_usuario["modulos"] = dict(defaults["administrador"]["modulos"])
                perfil_usuario["estado"] = "activo"
                changed = True
                logger.info(
                    "Usuario Windows con rol administrador promovido automáticamente a acceso completo | usuario=%s",
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
        self.crear_icono_bandeja()
        self.ventana_creacion_caja.withdraw()

    def mostrar_desde_bandeja(self):
        logger.info("Accion bandeja: mostrar ventana principal.")
        self.ventana_creacion_caja.deiconify()
        self.ventana_creacion_caja.lift()
        self.ventana_creacion_caja.focus_force()
        self.ventana_creacion_caja.state("zoomed")
        self._detener_icono_bandeja()

    def crear_icono_bandeja(self):
        from PIL import Image

        try:
            if self.tray_icon is not None:
                logger.debug("El icono de bandeja ya estaba creado. Se omite recrearlo.")
                return
            if self.tray_thread is not None and self.tray_thread.is_alive():
                logger.debug("El hilo del icono de bandeja sigue activo. Se omite recrearlo.")
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
            self._tray_cleanup_done = False

            logger.info("Icono de bandeja creado correctamente.")

        except Exception:
            logger.exception("Error al crear icono de bandeja.")

    def _detener_icono_bandeja(self):
        icon = self.tray_icon
        thread = self.tray_thread
        self.tray_icon = None
        self.tray_thread = None

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

        if thread and thread.is_alive():
            try:
                thread.join(timeout=2.0)
            except Exception:
                logger.debug("No se pudo esperar el cierre del hilo de bandeja.", exc_info=True)

    def _cleanup_tray_icon(self):
        if self._tray_cleanup_done:
            return

        self._tray_cleanup_done = True
        self._detener_icono_bandeja()
        self._cleanup_socket_lock()

    def _cleanup_socket_lock(self):
        self._socket_listener_running = False

        try:
            if self.socket_lock_server:
                self.socket_lock_server.close()
                logger.info(
                    "Socket de bloqueo liberado | puerto=%s | scope_usuario=%s",
                    self.socket_lock_port,
                    self.socket_lock_scope,
                )
        except Exception:
            logger.exception("Error al cerrar el socket de bloqueo.")
        finally:
            self.socket_lock_server = None
            _liberar_mutex_instancia(self.instance_mutex)
            self.instance_mutex = None

    def cerrar_aplicacion(self):
        logger.info("Cerrando aplicación de forma controlada.")
        self._cleanup_tray_icon()
        try:
            conexion_sybase = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE")
            if conexion_sybase:
                conexion_sybase.desconectar()
        except Exception:
            logger.exception("Error al cerrar la conexion Sybase durante el cierre de la aplicacion.")
        try:
            self.ventana_creacion_caja.destroy()
        except Exception:
            logger.exception("Error al destruir la ventana principal durante el cierre.")

    def frameMenu(self):
        logger.debug("Construyendo frameMenu.")

        self.frame_menu = ttk.Frame(
            self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"),
            bootstyle="light",
            width=self.sidebar_expanded_width,
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_menu", self.frame_menu)
        self.frame_menu.grid(row=0, column=0, sticky="NSEW")
        self.frame_menu.grid_propagate(False)
        self.frame_menu.pack_propagate(False)

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

        self.photo_publicidad = READ_IMG(PNG_Publicidad(), getattr(self, "sidebar_icon_size", 28), getattr(self, "sidebar_icon_size", 28))
        self.photo_productos = READ_IMG(PNG_Productos(), getattr(self, "sidebar_icon_size", 28), getattr(self, "sidebar_icon_size", 28))
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
        self.frame_botones_config_info.pack(pady=(getattr(self, "sidebar_footer_pad_top", 14), 0), side="bottom", fill="x")

        self.footer_card = tk.Frame(
            self.frame_botones_config_info,
            bg=self.sidebar_bg,
            bd=0,
            highlightthickness=0,
            width=self.sidebar_item_width,
            padx=2,
            pady=2,
        )
        self.footer_card.pack(anchor="s", fill="x")

        self.photo_setting = READ_IMG(PNG_Settings(), getattr(self, "sidebar_footer_icon_size", 20), getattr(self, "sidebar_footer_icon_size", 20))
        self.boton_setting = None
        self.boton_setting_icon = None
        self.boton_setting_texto = None
        if self._tiene_permiso("configuracion"):
            self.boton_setting, self.boton_setting_icon, self.boton_setting_texto = self._crear_footer_action(
                "boton_setting",
                self.photo_setting,
                "Configuración",
                self.command_button_configuracion,
                pady=(0, 10),
            )

        self.photo_info = READ_IMG(PNG_Info(), getattr(self, "sidebar_footer_icon_size", 20), getattr(self, "sidebar_footer_icon_size", 20))
        self.boton_info, self.boton_info_icon, self.boton_info_texto = self._crear_footer_action(
            "boton_info",
            self.photo_info,
            "Acerca de",
            self.command_button_acerca,
        )

        self.boton_toggle_menu = tk.Button(
            self.footer_card,
            text="‹",
            command=self.alternar_menu_lateral,
            bg=self.sidebar_card,
            fg=self.sidebar_text,
            activebackground=self.sidebar_card_hover,
            activeforeground=self.sidebar_brand,
            relief="flat",
            bd=0,
            font=("Segoe UI Symbol", 18, "bold"),
            cursor="hand2",
            padx=8,
            pady=2,
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "boton_toggle_menu", self.boton_toggle_menu)
        self.boton_toggle_menu.pack(fill="x", pady=(10, 0))

        self._render_footer_action(self.boton_info, self.boton_info_icon, self.boton_info_texto, False)
        if self.boton_setting:
            self._render_footer_action(self.boton_setting, self.boton_setting_icon, self.boton_setting_texto, False)
        logger.debug("frameMenu construido correctamente.")

    def _cargar_logo_sidebar(self, path, max_width, max_height):
        image_logo = Image.open(path)
        image_logo.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image_logo)

    def _crear_footer_action(self, widget_key, image, text, command, pady=(0, 0)):
        slot = tk.Frame(
            self.footer_card,
            bg=self.sidebar_card,
            height=36,
            bd=0,
            highlightthickness=0,
        )
        slot.pack(fill="x", pady=pady)
        slot.pack_propagate(False)

        button = tk.Button(
            slot,
            image=image,
            text=text,
            compound="left",
            command=command,
            bg=self.sidebar_card,
            fg=self.sidebar_muted,
            activebackground=self.sidebar_card_hover,
            activeforeground=self.sidebar_brand,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=getattr(self, "sidebar_footer_font", ("Segoe UI", 10, "bold")),
            cursor="hand2",
            padx=8,
            pady=5,
            anchor="w",
        )
        button.sidebar_text = text
        button.sidebar_pady = pady
        button.sidebar_slot = slot
        self.DICT_WIDGETS.register("GUI_MAIN", widget_key, button)
        button.pack(fill="both", expand=True)
        button.bind("<Enter>", lambda _e, b=button: self._hover_footer_action(b, b, b, True))
        button.bind("<Leave>", lambda _e, b=button: self._hover_footer_action(b, b, b, False))

        # Se conservan los tres alias para no alterar el contrato interno de
        # GUI_MAIN; todos apuntan al mismo control atómico.
        return button, button, button

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
            height=getattr(self, "sidebar_menu_item_height", 46),
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
            font=getattr(self, "sidebar_menu_font", ("Segoe UI", 10, "bold")),
            anchor="w",
        )

        def redraw(_event):
            width = max(canvas.winfo_width() - 2, 10)
            height = max(canvas.winfo_height() - 2, 10)
            canvas.coords(bg_shape, self._rounded_rect_points(2, 2, width, height, 14))
            icon_x = width / 2 if self.sidebar_collapsed else 16
            icon_anchor = "center" if self.sidebar_collapsed else "w"
            canvas.itemconfigure(icon_id, anchor=icon_anchor)
            canvas.coords(icon_id, icon_x, height / 2)
            canvas.coords(text_id, 50, height / 2)

        canvas.bind("<Configure>", redraw)

        self.menu_cards[key] = {
            "frame": frame,
            "canvas": canvas,
            "shape": bg_shape,
            "icon_id": icon_id,
            "text_id": text_id,
            "label": text,
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
        frame.configure(bg=bg, fg=fg)

    def _render_footer_action(self, frame, icon, label, collapsed):
        if collapsed:
            frame.configure(text="", compound="none", anchor="center", padx=0)
        else:
            frame.configure(
                text=frame.sidebar_text,
                compound="left",
                anchor="w",
                padx=8,
            )

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
            padding=(18, 10),
        )
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_contenido", self.frame_contenido)
        self.frame_contenido.grid(row=0, column=1, sticky="NSEW")
        self.frame_contenido.columnconfigure(0, weight=1)
        self.frame_contenido.rowconfigure(0, weight=0)
        self.frame_contenido.rowconfigure(1, weight=1)

        self.frame_barra_superior = ttk.Frame(self.frame_contenido)
        self.frame_barra_superior.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.photo_back = READ_IMG(PNG_Back(), 26, 26)
        self.boton_back = ttk.Button(
            self.frame_barra_superior,
            image=self.photo_back,
            command=self.command_button_volver,
            bootstyle="primary-link",
        )
        self.boton_back.pack(side="left")

        self.frame_cuerpo_secciones = ttk.Frame(self.frame_contenido)
        self.frame_cuerpo_secciones.grid(row=1, column=0, sticky="nsew")
        self.frame_cuerpo_secciones.columnconfigure(0, weight=1)
        self.frame_cuerpo_secciones.rowconfigure(0, weight=1)
        self._aplicar_layout_responsivo()

        logger.debug("frameContenido construido correctamente.")

    def command_button_productos(self):
        if not self._tiene_permiso("productos"):
            messagebox.showwarning("Acceso restringido", "Este usuario no tiene acceso al módulo Productos.")
            return
        logger.info("Navegación solicitada a sección PRODUCTOS.")
        self._abrir_modulo_con_loader(
            "productos",
            "Cargando módulo Productos...",
            callback_despues=lambda: self.contenido_productos.cargar_productos_locales_con_loader(
                force=False,
                mostrar_sin_datos=True,
            ),
        )

    def command_button_publicidad(self):
        if not self._tiene_permiso("publicidad"):
            messagebox.showwarning("Acceso restringido", "Este usuario no tiene acceso al módulo Publicidad.")
            return
        logger.info("Navegación solicitada a sección PUBLICIDAD.")
        self._abrir_modulo_con_loader(
            "publicidad",
            "Cargando módulo Publicidad...",
            callback_despues=lambda: self.contenido_publicidad.sincronizar_publicidades_compartidas(),
        )

    def command_button_configuracion(self):
        if not self._tiene_permiso("configuracion"):
            messagebox.showwarning("Acceso restringido", "Este usuario no tiene acceso al módulo Configuración.")
            return
        VentanaManager.abrir_ventana("configuracion", GUI_CONFIG, self.DICT_WIDGETS)

    def command_button_acerca(self):
        logger.info("Navegación solicitada a sección ACERCA DE.")
        self.VIGIA_FRAME = "BOTON_ACERCA"
        self.seccion_acerca()
        self.selector_seccion()

    def command_button_volver(self):
        logger.info("Navegación: volver a sección anterior.")
        try:
            if len(self.VIGIA_VOLVER) <= 1:
                self.VIGIA_FRAME = "INICIO"
                self.VIGIA_VOLVER = ["INICIO"]
            else:
                self.VIGIA_VOLVER.pop()
                self.VIGIA_FRAME = self.VIGIA_VOLVER[-1]

            logger.debug("Frame recuperado al volver: %s", self.VIGIA_FRAME)
            logger.debug("Historial luego de volver: %s", self.VIGIA_VOLVER)

            self.selector_seccion()

        except Exception:
            logger.exception("Error al volver de sección.")
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
            "Seleccionando sección | VIGIA_FRAME=%s | historial_actual=%s",
            self.VIGIA_FRAME,
            self.VIGIA_VOLVER
        )
        frame_productos = getattr(self, "frame_seccion_productos", None)
        frame_publicidad = getattr(self, "frame_seccion_publicidad", None)
        frame_acerca = getattr(self, "frame_seccion_acerca", None)

        if self.VIGIA_FRAME == "BOTON_PRODUCTOS" and not self._tiene_permiso("productos"):
            self._ajustar_seccion_inicial_por_permisos()
        elif self.VIGIA_FRAME == "BOTON_PUBLICIDAD" and not self._tiene_permiso("publicidad"):
            self._ajustar_seccion_inicial_por_permisos()

        if self.VIGIA_FRAME == "INICIO":
            self.VIGIA_VOLVER = ["INICIO"]
            self.frame_seccion_inicio.grid()
            if frame_productos:
                frame_productos.grid_remove()
            if frame_publicidad:
                frame_publicidad.grid_remove()
            if frame_acerca:
                frame_acerca.grid_remove()
            self.frame_barra_superior.grid_remove()

        elif self.VIGIA_FRAME == "BOTON_PRODUCTOS":
            if frame_publicidad:
                frame_publicidad.grid_remove()
            if frame_acerca:
                frame_acerca.grid_remove()
            self.frame_seccion_inicio.grid_remove()
            self.frame_barra_superior.grid_remove()
            if frame_productos:
                frame_productos.grid()

        elif self.VIGIA_FRAME == "BOTON_PUBLICIDAD":
            if frame_productos:
                frame_productos.grid_remove()
            if frame_acerca:
                frame_acerca.grid_remove()
            self.frame_seccion_inicio.grid_remove()
            self.frame_barra_superior.grid()
            if frame_publicidad:
                frame_publicidad.grid()

        elif self.VIGIA_FRAME == "BOTON_ACERCA":
            if frame_productos:
                frame_productos.grid_remove()
            if frame_publicidad:
                frame_publicidad.grid_remove()
            self.frame_seccion_inicio.grid_remove()
            self.frame_barra_superior.grid()
            if frame_acerca:
                frame_acerca.grid()

        if not self.VIGIA_VOLVER:
            self.VIGIA_VOLVER = [self.VIGIA_FRAME]
        elif self.VIGIA_VOLVER[-1] != self.VIGIA_FRAME and self.VIGIA_FRAME not in self.VIGIA_VOLVER:
            self.VIGIA_VOLVER.append(self.VIGIA_FRAME)

        self._actualizar_estilo_menu_activo()

        logger.debug("Sección aplicada | historial_resultante=%s", self.VIGIA_VOLVER)

    def _actualizar_estilo_menu_activo(self):
        activo_productos = self.VIGIA_FRAME == "BOTON_PRODUCTOS"
        activo_publicidad = self.VIGIA_FRAME == "BOTON_PUBLICIDAD"
        try:
            self._aplicar_estado_tarjeta_menu("productos", active=activo_productos)
            self._aplicar_estado_tarjeta_menu("publicidad", active=activo_publicidad)
            activo_info = self.VIGIA_FRAME == "BOTON_ACERCA"
            self._hover_footer_action(
                self.boton_info,
                self.boton_info_icon,
                self.boton_info_texto,
                activo_info,
            )
        except Exception:
            logger.exception("No se pudo actualizar estilo del menu activo.")

    def seccion_inicio(self):
        logger.debug("Creando widgets de sección INICIO.")

        self.frame_seccion_inicio = ttk.Frame(self.frame_cuerpo_secciones)
        self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_inicio", self.frame_seccion_inicio)
        self.frame_seccion_inicio.grid(row=0, column=0, sticky="nsew")
        self.frame_seccion_inicio.columnconfigure(0, weight=1)

        self.label_inicio = ttk.Label(self.frame_seccion_inicio, text="Bienvenidos", font=FONT_TITLE_XL)
        self.label_inicio.pack(pady=(30, 8), anchor="w")
        self.label_inicio_subtitulo = ttk.Label(
            self.frame_seccion_inicio,
            text="Seleccioná una sección del panel lateral para comenzar.",
            bootstyle="secondary",
            font=FONT_SUBTITLE,
        )
        self.label_inicio_subtitulo.pack(anchor="w")
        self.label_inicio_usuario = ttk.Label(
            self.frame_seccion_inicio,
            text=f"Usuario actual: {self.usuario_windows}",
            bootstyle="secondary",
            font=FONT_SUBTITLE,
        )
        self.label_inicio_usuario.pack(anchor="w", pady=(6, 0))
        if not any(self.permisos_usuario.values()):
            self.label_inicio_bloqueo = ttk.Label(
                self.frame_seccion_inicio,
                text="Acceso pendiente de autorización. Un administrador debe habilitar tus módulos.",
                bootstyle="warning",
                font=FONT_BODY_BOLD,
            )
            self.label_inicio_bloqueo.pack(anchor="w", pady=(10, 0))
        else:
            self.label_inicio_bloqueo = None

    def seccion_productos(self):
        logger.debug("Creando widgets de sección PRODUCTOS.")

        if not self._seccion_productos_creada:
            self.frame_seccion_productos = ttk.Frame(self.frame_cuerpo_secciones)
            self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_productos", self.frame_seccion_productos)
            self.frame_seccion_productos.grid(row=0, column=0, sticky="nsew")
            self.contenido_productos = ContenidoProducto(self.DICT_WIDGETS)
            self._seccion_productos_creada = True
            logger.debug("ContenidoProducto inicializado correctamente.")

    def seccion_publicidad(self):
        logger.debug("Creando widgets de sección PUBLICIDAD.")

        if not self._seccion_publicidad_creada:
            self.frame_seccion_publicidad = ttk.Frame(self.frame_cuerpo_secciones)
            self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_publicidad", self.frame_seccion_publicidad)
            self.frame_seccion_publicidad.grid(row=0, column=0, sticky="nsew")
            self.contenido_publicidad = ContenidoPublicidad(self.DICT_WIDGETS)
            self._seccion_publicidad_creada = True
            logger.debug("ContenidoPublicidad inicializado correctamente.")

    def seccion_acerca(self):
        logger.debug("Creando widgets de sección ACERCA DE.")

        if not self._seccion_acerca_creada:
            self.frame_seccion_acerca = ttk.Frame(self.frame_cuerpo_secciones)
            self.DICT_WIDGETS.register("GUI_MAIN", "frame_seccion_acerca", self.frame_seccion_acerca)
            self.frame_seccion_acerca.grid(row=0, column=0, sticky="nsew")
            self.frame_seccion_acerca.columnconfigure(0, weight=1)
            self.frame_seccion_acerca.rowconfigure(1, weight=1)

            header = ttk.Frame(self.frame_seccion_acerca)
            header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
            header.columnconfigure(0, weight=1)

            ttk.Label(header, text="Acerca de", font=FONT_TITLE_XL).grid(row=0, column=0, sticky="w")
            ttk.Label(
                header,
                text="Información general, versión y estado de la aplicación.",
                bootstyle="secondary",
                font=FONT_SUBTITLE,
            ).grid(row=1, column=0, sticky="w", pady=(4, 0))

            body = ttk.Frame(self.frame_seccion_acerca)
            body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
            body.columnconfigure(0, weight=3)
            body.columnconfigure(1, weight=2)
            body.rowconfigure(0, weight=1)

            card_info = ttk.Labelframe(
                body,
                text="Aplicación",
                bootstyle="primary",
                padding=(16, 14),
            )
            card_info.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
            card_info.columnconfigure(1, weight=1)

            info_rows = [
                ("Producto", "SmartPrice / VeriPre_Connector"),
                ("Versión", str(self.version)),
                ("Usuario Windows", str(self.usuario_windows or "-")),
                ("Rol Windows", "Administrador local" if self.usuario_windows_es_admin else "Usuario estándar"),
                ("Módulos habilitados", ", ".join([
                    nombre.capitalize()
                    for nombre, activo in self.permisos_usuario.items()
                    if activo
                ]) or "Sin módulos habilitados"),
            ]
            for idx, (label, value) in enumerate(info_rows):
                ttk.Label(card_info, text=f"{label}:", font=FONT_LABEL_BOLD).grid(row=idx, column=0, sticky="nw", padx=(0, 12), pady=(0, 10))
                ttk.Label(card_info, text=value, font=FONT_SUBTITLE, bootstyle="secondary", justify="left", wraplength=420).grid(row=idx, column=1, sticky="nw", pady=(0, 10))

            card_estado = ttk.Labelframe(
                body,
                text="Estado",
                bootstyle="primary",
                padding=(16, 14),
            )
            card_estado.grid(row=0, column=1, sticky="nsew")
            card_estado.columnconfigure(0, weight=1)

            ttk.Label(
                card_estado,
                text="SmartPrice centraliza sincronización local, envío a dispositivos y administración de publicidad.",
                font=FONT_SUBTITLE,
                bootstyle="secondary",
                justify="left",
                wraplength=320,
            ).grid(row=0, column=0, sticky="w", pady=(0, 14))

            ttk.Label(
                card_estado,
                text="Fuente local SQLite, integración Sybase por ODBC y transmisión HTTP a verificadores / players.",
                font=FONT_SUBTITLE,
                bootstyle="secondary",
                justify="left",
                wraplength=320,
            ).grid(row=1, column=0, sticky="w", pady=(0, 14))

            ttk.Label(
                card_estado,
                text="Desarrollado para operación de punto de venta, cartelería y verificación de precios.",
                font=FONT_SUBTITLE,
                bootstyle="secondary",
                justify="left",
                wraplength=320,
            ).grid(row=2, column=0, sticky="w")

            self._seccion_acerca_creada = True

    def CONEXIONES_DBA(self):
        ruta_db = str(obtener_sqlite_path())
        logger.info("Inicializando conexiones de base de datos | sqlite_path=%s", ruta_db)

        self.DICT_WIDGETS.register("DATABASE", "CONEXIONDBA", SQLiteDB(ruta_db))
        self.CONEXIONDBA = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA")
        self.CONEXIONDBA.crear_tablas()

        try:
            inserccion_sql = """
            SELECT * FROM VERIPRE_CONEXION
            """
            logger.debug("Consultando configuración de conexión externa en SQLite.")
            datos_conexion = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA").ejecutar_consulta(inserccion_sql)

            if datos_conexion is not None and len(datos_conexion) > 0:
                datos_conexion = datos_conexion[0]
                conexion = {
                    "user": datos_conexion[1],
                    "password": datos_conexion[2],
                    "dsn": datos_conexion[0]
                }

                logger.info(
                    "Configuración externa encontrada | dsn=%s | user=%s",
                    conexion["dsn"],
                    conexion["user"]
                )

                conexion_sybase_actual = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE")
                if conexion_sybase_actual:
                    try:
                        conexion_sybase_actual.desconectar()
                    except Exception:
                        logger.exception("Error al cerrar la conexion Sybase anterior antes de reconfigurar.")

                self.DICT_WIDGETS.register("DATABASE", "CONEXIONDBA_SYBASE", ConexionSybase(**conexion))
                self.DICT_WIDGETS.register("DATABASE", "CONEXION_INFORHARD", True)

                logger.info("Conexión externa Sybase registrada correctamente.")
            else:
                self.DICT_WIDGETS.register("DATABASE", "CONEXION_INFORHARD", False)
                logger.warning("No se encontraron datos de conexión externa en VERIPRE_CONEXION.")

        except Exception:
            self.DICT_WIDGETS.register("DATABASE", "CONEXION_INFORHARD", False)
            logger.exception("Sin conexión externa o error al configurar ConexionSybase.")

    def VARIABLES_GLOBALES(self):
        logger.debug("Registrando variables globales.")
        self.DICT_WIDGETS.register("VARIABLES_GLOBALES", "top_level_configuracion_abierta", False)
