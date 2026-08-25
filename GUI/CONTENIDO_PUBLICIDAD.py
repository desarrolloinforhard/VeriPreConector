import os
import shutil
import cv2
import tkinter as tk
import ttkbootstrap as ttk
import vlc
import time
import threading
import hashlib
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog
from ttkbootstrap.constants import *
from PIL import Image, ImageTk, ImageDraw

from ASSETS.path_img import READ_IMG, PNG_Back, PNG_Check
from core.network.api_client import DispositivoAPIClient
from core.network.dispositivo_sender import DispositivoSender
from GUI.OFERTAS_GENERADOR import GeneradorOfertasToplevel
from core.logging.logger import get_logger
from core.ui.responsive import center_toplevel_in_workarea, fit_toplevel_to_workarea, clamp
from core.ui.theme_tokens import FONT_LABEL_BOLD, FONT_SUBTITLE, FONT_TITLE_LG, PANEL_PAD_X, PANEL_PAD_Y
from core.ui.ttk_theme import (
    SMARTPRICE_DARK_BORDER,
    SMARTPRICE_DARK_CARD,
    SMARTPRICE_DARK_HOVER,
    SMARTPRICE_DARK_SURFACE,
)
from FUNC.config_json import cargar_config, guardar_config, obtener_data_dir

# from core.network.selector_envio_dispositivos import EnvioDispositivos

logger = get_logger(__name__)

CELL_HEIGHT = 210
PREVIEW_HEIGHT = 128
PADDING = 0        # margen interno del canvas
ITEM_MARGIN = 5    # margen entre ítems

class ContenidoPublicidad:
    MAX_IMAGE_MB = 15
    MAX_VIDEO_MB = 250
    MAX_VIDEO_SECONDS = 180
    CARD_BG = "#ffffff"
    CARD_BORDER = "#dce4ee"
    PAGE_BG = "#f4f7fb"
    ACCENT = "#0d6efd"

    @staticmethod
    def _paleta_publicidad(tema):
        if str(tema).strip().lower() in {"oscuro", "dark"}:
            return {
                "card_bg": SMARTPRICE_DARK_CARD,
                "card_border": SMARTPRICE_DARK_BORDER,
                "page_bg": SMARTPRICE_DARK_SURFACE,
                "badge_bg": SMARTPRICE_DARK_HOVER,
                "badge_fg": "#f4fbf7",
                "item_selected": "#149455",
            }
        return {
            "card_bg": "#ffffff",
            "card_border": "#dce4ee",
            "page_bg": "#f4f7fb",
            "badge_bg": "#f0f6ff",
            "badge_fg": "#0d6efd",
            "item_selected": "#149455",
        }

    def __init__(self, widgets):
        logger.info("Inicializando ContenidoPublicidad.")

        self.widgets = widgets
        config = self.widgets.get_widget("CONFIG", "config_json") or {}
        self.tema_interfaz = str(config.get("tema_interfaz", "claro"))
        self._actualizar_tokens_tema(self.tema_interfaz)
        self.items_dict = {}
        self.items = []
        self.drag_item = None
        self.item_seleccionado = None
        self._clic_pos = None
        self._cargando_grupo = False
        self._opciones_visibles = False
        self._layout_after_id = None
        self._botones_grupo = []
        self._botones_accion = []
        self.grupo_activo_id = "default"
        self.publicidades_storage_dir = obtener_data_dir() / "publicidades"
        self.publicidades_storage_dir.mkdir(parents=True, exist_ok=True)
        self.biblioteca_metadata = {}

        self.cols = 4
        self.rows = 2
        self.cell_width = 240

        self.setup_gui()

    def _actualizar_tokens_tema(self, tema):
        self.tema_interfaz = "oscuro" if str(tema).strip().lower() in {"oscuro", "dark"} else "claro"
        paleta = self._paleta_publicidad(self.tema_interfaz)
        self.CARD_BG = paleta["card_bg"]
        self.CARD_BORDER = paleta["card_border"]
        self.PAGE_BG = paleta["page_bg"]
        self.BADGE_BG = paleta["badge_bg"]
        self.BADGE_FG = paleta["badge_fg"]
        self.ITEM_SELECTED = paleta["item_selected"]

    def aplicar_tema_interfaz(self, tema):
        self._actualizar_tokens_tema(tema)
        if not hasattr(self, "canvas"):
            return

        self.panel_opciones.configure(bg=self.CARD_BG, highlightbackground=self.CARD_BORDER)
        self.grid_card.configure(bg=self.CARD_BG, highlightbackground=self.CARD_BORDER)
        self.canvas.configure(bg=self.PAGE_BG)
        for frame in (self.frame_toolbar_contenido,):
            frame.configure(bg=self.CARD_BG)
        for label in (self.lbl_contenido_grupo, self.lbl_ayuda_orden):
            label.configure(bg=self.CARD_BG, fg=self.BADGE_FG)
        self.frame_estado_vacio.configure(bg=self.PAGE_BG)
        for label in (self.lbl_vacio_icono, self.lbl_vacio_titulo, self.lbl_vacio_texto, self.lbl_vacio_flujo):
            label.configure(bg=self.PAGE_BG, fg=self.BADGE_FG)
        for clave, label in self.pastillas_resumen.items():
            label.configure(
                bg=self.CARD_BG,
                fg="#55d68b" if clave == "pendientes" else self.BADGE_FG,
                highlightbackground=self.CARD_BORDER,
            )
        self._estilizar_boton_eliminar()

        for item in self.items:
            seleccionado = item is self.item_seleccionado
            item["frame"].configure(
                bg=self.CARD_BG,
                highlightbackground=self.ITEM_SELECTED if seleccionado else self.CARD_BORDER,
            )
            item["label_pos"].configure(bg=self.BADGE_BG, fg=self.BADGE_FG)
            item.get("frame_info", item["frame"]).configure(bg=self.CARD_BG)
            if item.get("label_nombre"):
                item["label_nombre"].configure(
                    bg=self.CARD_BG,
                    fg="#DBE7E0" if self.tema_interfaz == "oscuro" else "#2B3A34",
                )
            if item.get("label_detalle"):
                item["label_detalle"].configure(bg=self.CARD_BG)
            if item.get("separador"):
                item["separador"].configure(bg=self.CARD_BORDER)

        if hasattr(self, "frame_drop_agregar"):
            self.frame_drop_agregar.configure(bg=self.PAGE_BG, highlightbackground=self.CARD_BORDER)
            self.lbl_drop_agregar.configure(bg=self.PAGE_BG, fg=self.BADGE_FG)

        self.canvas.update_idletasks()

    def _estilizar_boton_eliminar(self):
        if not hasattr(self, "btn_eliminar_grupo"):
            return
        self.btn_eliminar_grupo.configure(
            bg=self.CARD_BG,
            fg=self.BADGE_FG,
            activebackground="#b4232d",
            activeforeground="white",
            highlightbackground=self.CARD_BORDER,
        )

    def setup_gui(self):
        logger.debug("Construyendo interfaz de ContenidoPublicidad.")

        frame_principal = self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad")
        self.contenedor_general = ttk.Frame(frame_principal)
        self.contenedor_general.pack(fill="both", expand=True, padx=PANEL_PAD_X - 6, pady=(10, 0))

        self.frame_resumen = ttk.Frame(self.contenedor_general)
        self.frame_resumen.pack(fill="x", padx=PANEL_PAD_X - 6, pady=(0, 12))
        self.frame_resumen.columnconfigure(2, weight=1)

        self.photo_back_local = READ_IMG(PNG_Back(), 24, 24)
        self.button_back_local = ttk.Button(
            self.frame_resumen,
            image=self.photo_back_local,
            command=lambda: self.widgets.get_widget("GUI_MAIN", "instance").command_button_volver(),
            bootstyle="primary-link",
            width=2,
        )
        self.button_back_local.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.lbl_titulo = ttk.Label(
            self.frame_resumen,
            text="Publicidad",
            font=FONT_TITLE_LG,
        )
        self.lbl_titulo.grid(row=0, column=1, sticky="w")

        self.lbl_resumen_grupo = ttk.Label(
            self.frame_resumen,
            text="",
            font=FONT_SUBTITLE,
            bootstyle="secondary",
        )
        self.lbl_resumen_grupo.grid_remove()

        self.frame_pastillas_resumen = ttk.Frame(self.frame_resumen)
        self.frame_pastillas_resumen.grid(row=0, column=3, sticky="e")
        self.pastillas_resumen = {}
        for columna, (clave, titulo) in enumerate((
            ("grupo", "DEL GRUPO"),
            ("globales", "GLOBALES"),
            ("envio", "AL ENVIAR"),
            ("pendientes", "PENDIENTES"),
        )):
            pastilla = tk.Label(
                self.frame_pastillas_resumen,
                text=f"{titulo}  0",
                font=("Segoe UI", 8),
                padx=10,
                pady=6,
                bd=0,
                relief="flat",
                highlightthickness=1,
            )
            pastilla.grid(row=0, column=columna, padx=(0, 6) if columna < 3 else 0)
            self.pastillas_resumen[clave] = pastilla

        self.panel_opciones = tk.Frame(
            self.contenedor_general,
            bg=self.CARD_BG,
            highlightthickness=1,
            highlightbackground=self.CARD_BORDER,
            bd=0,
            padx=PANEL_PAD_X,
            pady=10,
        )
        self.panel_opciones.pack(fill="x", padx=PANEL_PAD_X - 6, pady=(0, 12))

        self.frame_opciones = ttk.Frame(self.panel_opciones, padding=(0, 0))
        self.frame_opciones.pack(fill="x")

        self.frame_grupos = ttk.Frame(self.frame_opciones)
        self.frame_grupos.pack(fill="x")

        ttk.Label(self.frame_grupos, text="GRUPO", font=("Segoe UI", 8), bootstyle="secondary").pack(side="left", padx=(0, 10))
        self.combo_grupos = ttk.Combobox(self.frame_grupos, state="readonly", width=26)
        self.combo_grupos.pack(side="left", padx=(0, 10), ipady=4)
        self.combo_grupos.bind("<<ComboboxSelected>>", self.cambiar_grupo_desde_combo)

        self.frame_grupos_botones = ttk.Frame(self.frame_grupos)
        self.frame_grupos_botones.pack(side="left")
        self.frame_grupos_botones_l1 = ttk.Frame(self.frame_grupos_botones)
        self.frame_grupos_botones_l1.pack(side="left")
        self.frame_grupos_botones_l2 = ttk.Frame(self.frame_grupos_botones)

        self._botones_grupo = [
            ttk.Button(self.frame_grupos_botones, text="Nuevo", command=self.crear_grupo, bootstyle="secondary-outline", padding=(10, 6)),
            ttk.Button(self.frame_grupos_botones, text="Renombrar", command=self.renombrar_grupo, bootstyle="secondary-outline", padding=(10, 6)),
        ]
        for boton in self._botones_grupo:
            boton.pack(side="left", padx=(0, 6))
        self.btn_eliminar_grupo = tk.Button(
            self.frame_grupos_botones,
            text="Eliminar",
            command=self.eliminar_grupo,
            font=("Segoe UI", 9),
            padx=10,
            pady=5,
            bd=0,
            relief="flat",
            highlightthickness=1,
            cursor="hand2",
        )
        self.btn_eliminar_grupo.pack(side="left", padx=(0, 6))
        self.btn_eliminar_grupo.bind("<Enter>", lambda _event: self.btn_eliminar_grupo.configure(bg="#b4232d", fg="white"))
        self.btn_eliminar_grupo.bind("<Leave>", lambda _event: self._estilizar_boton_eliminar())

        self.lbl_multipantalla = ttk.Label(self.frame_grupos, text="Multipantalla: por dispositivo", bootstyle="secondary")
        self.lbl_multipantalla.pack(side="left", padx=(10, 0))

        self.btn_agregar_principal = ttk.Button(
            self.frame_grupos,
            text="＋ Agregar multimedia",
            command=self.agregar_multimedia,
            bootstyle="success",
            padding=(14, 7),
        )
        self.btn_agregar_principal.pack(side="right")

        self.frame_botones = ttk.Frame(self.frame_opciones)
        self.frame_botones_accion_l1 = ttk.Frame(self.frame_botones)
        self.frame_botones_accion_l2 = ttk.Frame(self.frame_botones)
        self._botones_accion = []

        self.grid_card = tk.Frame(
            self.contenedor_general,
            bg=self.CARD_BG,
            highlightthickness=1,
            highlightbackground=self.CARD_BORDER,
            bd=0,
            padx=PANEL_PAD_Y,
            pady=0,
        )
        self.grid_card.pack(fill="both", expand=True, padx=PANEL_PAD_X - 6, pady=(0, 10))

        self.frame_toolbar_contenido = tk.Frame(self.grid_card, bg=self.CARD_BG, bd=0, padx=10, pady=9)
        self.frame_toolbar_contenido.pack(fill="x")
        self.lbl_contenido_grupo = tk.Label(
            self.frame_toolbar_contenido,
            text="CONTENIDO DEL GRUPO",
            bg=self.CARD_BG,
            fg=self.BADGE_FG,
            font=("Segoe UI", 8),
        )
        self.lbl_contenido_grupo.pack(side="left")
        self.lbl_ayuda_orden = tk.Label(
            self.frame_toolbar_contenido,
            text="arrastrá para cambiar el orden · doble clic para abrir",
            bg=self.CARD_BG,
            fg=self.BADGE_FG,
            font=("Segoe UI", 8),
        )
        self.lbl_ayuda_orden.pack(side="left", padx=(12, 0))
        self.frame_herramientas_contenido = ttk.Frame(self.frame_toolbar_contenido)
        self.frame_herramientas_contenido.pack(side="right")
        for texto, comando in (
            ("Biblioteca", self.abrir_biblioteca_publicidades),
            ("Globales", self.abrir_globales),
            ("Historial", self.abrir_historial_publicidades),
            ("Vista completa", self.mostrar_preview_general),
        ):
            ttk.Button(
                self.frame_herramientas_contenido,
                text=texto,
                command=comando,
                bootstyle="secondary-outline",
                padding=(8, 5),
            ).pack(side="left", padx=(0, 6))
        self.btn_mas = ttk.Button(
            self.frame_herramientas_contenido,
            text="Más ▾",
            command=self._mostrar_menu_mas_publicidad,
            bootstyle="secondary-outline",
            padding=(8, 5),
        )
        self.btn_mas.pack(side="left")

        self.contenedor = ttk.Frame(self.grid_card)
        self.contenedor.pack(fill="both", expand=True)

        frame_canvas = ttk.ScrolledFrame(self.contenedor, autohide=True)
        frame_canvas.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(frame_canvas, bg=self.PAGE_BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.redimensionar_celdas)
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())
        frame_principal.bind("<Configure>", self._programar_layout_responsivo, add="+")

        self.frame_estado_vacio = tk.Frame(self.canvas, bg=self.PAGE_BG, bd=0)
        self.lbl_vacio_icono = tk.Label(self.frame_estado_vacio, text="＋", font=("Segoe UI", 22), bg=self.PAGE_BG, fg=self.BADGE_FG)
        self.lbl_vacio_icono.pack(pady=(0, 8))
        self.lbl_vacio_titulo = tk.Label(self.frame_estado_vacio, text="El grupo todavía no tiene contenido", font=("Segoe UI", 12, "bold"), bg=self.PAGE_BG, fg=self.BADGE_FG)
        self.lbl_vacio_titulo.pack()
        self.lbl_vacio_texto = tk.Label(self.frame_estado_vacio, text="Agregá imágenes o videos, ordenalos y envialos a los dispositivos.", font=("Segoe UI", 9), bg=self.PAGE_BG, fg=self.BADGE_FG)
        self.lbl_vacio_texto.pack(pady=(6, 12))
        self.frame_vacio_acciones = ttk.Frame(self.frame_estado_vacio)
        self.frame_vacio_acciones.pack()
        ttk.Button(self.frame_vacio_acciones, text="＋ Agregar multimedia", command=self.agregar_multimedia, bootstyle="success", padding=(10, 6)).pack(side="left", padx=4)
        ttk.Button(self.frame_vacio_acciones, text="Elegir desde Biblioteca", command=self.abrir_biblioteca_publicidades, bootstyle="secondary-outline", padding=(10, 6)).pack(side="left", padx=4)
        ttk.Button(self.frame_vacio_acciones, text="Generar desde Ofertas", command=self.abrir_generador_ofertas, bootstyle="secondary-outline", padding=(10, 6)).pack(side="left", padx=4)
        self.lbl_vacio_flujo = tk.Label(self.frame_estado_vacio, text="1  Agregar   ›   2  Ordenar   ›   3  Validar   ›   4  Enviar", font=("Segoe UI", 8), bg=self.PAGE_BG, fg=self.BADGE_FG)
        self.lbl_vacio_flujo.pack(pady=(14, 0))
        self.empty_window_id = self.canvas.create_window(0, 0, window=self.frame_estado_vacio, anchor="center")
        self.frame_drop_agregar = tk.Frame(
            self.canvas,
            bg=self.PAGE_BG,
            highlightthickness=1,
            highlightbackground=self.CARD_BORDER,
            bd=0,
            cursor="hand2",
        )
        self.lbl_drop_agregar = tk.Label(
            self.frame_drop_agregar,
            text="＋\n\nAgregar multimedia",
            bg=self.PAGE_BG,
            fg=self.BADGE_FG,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self.lbl_drop_agregar.pack(fill="both", expand=True)
        for widget in (self.frame_drop_agregar, self.lbl_drop_agregar):
            widget.bind("<Button-1>", lambda _event: self.agregar_multimedia())
        self.drop_window_id = self.canvas.create_window(0, 0, window=self.frame_drop_agregar, anchor="center", state="hidden")

        self.frame_pie_publicidad = ttk.Frame(self.contenedor_general)
        self.frame_pie_publicidad.pack(fill="x", padx=PANEL_PAD_X - 6, pady=(0, 8))
        self.lbl_estado_pie = ttk.Label(self.frame_pie_publicidad, text="Sin archivos en General · 0 globales", bootstyle="secondary")
        self.lbl_estado_pie.pack(side="left")
        self.btn_enviar_pie = ttk.Button(self.frame_pie_publicidad, text="Enviar a dispositivos", command=self.enviar_multimedia, bootstyle="success", padding=(12, 7))
        self.btn_enviar_pie.pack(side="right", padx=(6, 0))
        self.btn_validar_pie = ttk.Button(self.frame_pie_publicidad, text="Validar", command=self.validar_publicidades, bootstyle="success-outline", padding=(12, 7))
        self.btn_validar_pie.pack(side="right", padx=(6, 0))
        self.btn_panel_pie = ttk.Button(self.frame_pie_publicidad, text="Panel de control", command=self.abrir_panel_de_control, bootstyle="secondary-outline", padding=(12, 7))
        self.btn_panel_pie.pack(side="right", padx=(6, 0))

        self._opciones_visibles = True
        self._estilizar_boton_eliminar()
        self._aplicar_layout_responsivo()
        frame_principal.after(100, self.inicializar_grupos_publicidad)

        logger.debug("Interfaz de ContenidoPublicidad creada correctamente.")

    def redimensionar_celdas(self, event=None):
        try:
            nuevo_ancho = event.width if event else self.canvas.winfo_width()
            self.cell_width = int(((nuevo_ancho - 2 * PADDING) // self.cols) * 0.97)
            if hasattr(self, "empty_window_id"):
                self.canvas.coords(
                    self.empty_window_id,
                    max(nuevo_ancho // 2, 1),
                    max(self.canvas.winfo_height() // 2, 1),
                )
            logger.debug("Redimensionando celdas | nuevo_ancho=%s | cell_width=%s", nuevo_ancho, self.cell_width)
            self.recolocar_items()
        except Exception:
            logger.exception("Error al redimensionar celdas.")

    def _programar_layout_responsivo(self, _event=None):
        root = self.widgets.get_widget("GUI_MAIN", "ventana_creacion_caja")
        if self._layout_after_id:
            try:
                root.after_cancel(self._layout_after_id)
            except Exception:
                pass
        self._layout_after_id = root.after(70, self._aplicar_layout_responsivo)

    def _aplicar_layout_responsivo(self):
        self._layout_after_id = None
        try:
            frame_principal = self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad")
            ancho_real = max(frame_principal.winfo_width(), 1080)
            ancho_util = min(ancho_real, 1540)
            padding_lateral = max(int((ancho_real - ancho_util) / 2), PANEL_PAD_X - 8)
            panel_interno = clamp(int(ancho_util * 0.012), 10, 18)

            self.contenedor_general.pack_configure(padx=padding_lateral)
            self.frame_resumen.pack_configure(padx=padding_lateral)
            if self._opciones_visibles:
                self.panel_opciones.pack_configure(padx=padding_lateral)
            self.grid_card.pack_configure(padx=padding_lateral)
            self.panel_opciones.configure(padx=panel_interno, pady=PANEL_PAD_Y)
            self.grid_card.configure(padx=panel_interno)
            self.combo_grupos.configure(width=22 if ancho_util < 1360 else 26 if ancho_util < 1540 else 30)
            self.redimensionar_celdas()
        except Exception:
            logger.exception("Error aplicando layout responsivo en Publicidad.")

    def _mostrar_menu_mas_publicidad(self):
        menu = tk.Menu(self.btn_mas, tearoff=0)
        menu.add_command(label="Panel de control", command=self.abrir_panel_de_control)
        menu.add_command(label="Generar desde ofertas", command=self.abrir_generador_ofertas)
        menu.add_command(label="Configurar multipantalla", command=self.abrir_config_multipantalla)
        try:
            menu.tk_popup(
                self.btn_mas.winfo_rootx(),
                self.btn_mas.winfo_rooty() + self.btn_mas.winfo_height(),
            )
        finally:
            menu.grab_release()

    def _reorganizar_botoneras(self, ancho_util):
        for widget in self._botones_grupo:
            widget.pack_forget()
            widget.grid_forget()
        for widget in self._botones_accion:
            widget.pack_forget()
            widget.grid_forget()
        self.frame_grupos_botones_l1.pack_forget()
        self.frame_grupos_botones_l2.pack_forget()
        self.frame_botones_accion_l1.pack_forget()
        self.frame_botones_accion_l2.pack_forget()

        self.frame_grupos_botones_l1.pack(fill="x")
        self.frame_botones.pack(fill="x", pady=(10, 0))
        self.frame_botones_accion_l1.pack(fill="x")

        columnas_grupo = 3 if ancho_util < 1460 else 5
        filas_grupo = (len(self._botones_grupo) + columnas_grupo - 1) // columnas_grupo
        frames_grupo = [self.frame_grupos_botones_l1]
        if filas_grupo > 1:
            self.frame_grupos_botones_l2.pack(fill="x", pady=(6, 0))
            frames_grupo.append(self.frame_grupos_botones_l2)
        self._distribuir_botones_uniformes(self._botones_grupo, frames_grupo, columnas_grupo)

        columnas_accion = 4
        self.frame_botones_accion_l2.pack(fill="x", pady=(6, 0))
        self._distribuir_botones_uniformes(
            self._botones_accion,
            [self.frame_botones_accion_l1, self.frame_botones_accion_l2],
            columnas_accion,
        )

    @staticmethod
    def _distribuir_botones_uniformes(botones, frames, columnas):
        for frame in frames:
            for columna in range(columnas):
                frame.columnconfigure(columna, weight=1, uniform="publicidad_botones")

        for indice, boton in enumerate(botones):
            fila = indice // columnas
            columna = indice % columnas
            frame = frames[min(fila, len(frames) - 1)]
            boton.grid(
                in_=frame,
                row=0,
                column=columna,
                sticky="ew",
                padx=(0, 6) if columna < columnas - 1 else 0,
            )

    def toggle_opciones(self):
        if self._opciones_visibles:
            self.panel_opciones.pack_forget()
            self.btn_opciones.configure(text="Mostrar opciones")
            self._opciones_visibles = False
        else:
            self.panel_opciones.pack(fill="x", padx=PANEL_PAD_X - 6, pady=(0, 16), after=self.frame_resumen)
            self.btn_opciones.configure(text="Ocultar opciones")
            self._opciones_visibles = True
            self._aplicar_layout_responsivo()

    def actualizar_resumen_grupo(self):
        try:
            self.refrescar_biblioteca_metadata(persistir=False)
            publicidades = self.asegurar_config_publicidades()
            grupo = publicidades["grupos"].get(self.grupo_activo_id, {})
            nombre = grupo.get("nombre", self.grupo_activo_id)
            total_grupo = len(self.items)
            total_globales = len(publicidades.get("globales", {}))
            total_envio = len(self.obtener_items_para_envio())
            pendientes = sum(1 for meta in self.biblioteca_metadata.values() if meta.get("cambios_pendientes"))

            if grupo.get("usar_display_index"):
                pantalla_txt = f" | Pantalla: {int(grupo.get('display_index', 0)) + 1}"
            else:
                pantalla_txt = " | Pantalla: automática"

            self.lbl_resumen_grupo.configure(
                text=(
                    f"Grupo: {nombre}{pantalla_txt} | {total_grupo} del grupo | "
                    f"{total_globales} globales | {total_envio} al enviar | "
                    f"{pendientes} pendientes"
                )
            )
            valores = {
                "grupo": total_grupo,
                "globales": total_globales,
                "envio": total_envio,
                "pendientes": pendientes,
            }
            titulos = {
                "grupo": "DEL GRUPO",
                "globales": "GLOBALES",
                "envio": "AL ENVIAR",
                "pendientes": "PENDIENTES",
            }
            for clave, valor in valores.items():
                self.pastillas_resumen[clave].configure(text=f"{titulos[clave]}  {valor}")
            estado_grupo = f"{total_grupo} archivo{'s' if total_grupo != 1 else ''} en {nombre} · {total_globales} globales"
            if pendientes:
                estado_grupo += f" · {pendientes} pendientes de envío"
            self.lbl_estado_pie.configure(text=estado_grupo if total_grupo else f"Sin archivos en {nombre} · {total_globales} globales")
            estado_botones = "normal" if total_envio else "disabled"
            self.btn_validar_pie.configure(state=estado_botones)
            self.btn_enviar_pie.configure(state=estado_botones)
            if total_grupo:
                self.canvas.itemconfigure(self.empty_window_id, state="hidden")
                self.canvas.itemconfigure(self.drop_window_id, state="normal")
            else:
                self.lbl_vacio_titulo.configure(text=f"El grupo “{nombre}” todavía no tiene contenido")
                self.canvas.itemconfigure(self.empty_window_id, state="normal")
                self.canvas.itemconfigure(self.drop_window_id, state="hidden")
                self.redimensionar_celdas()
        except Exception:
            logger.exception("Error actualizando resumen de grupo.")

    def _sincronizar_grilla_publicidad(self):
        """Alinea el resumen, el vacío y la celda de carga con la grilla visible."""
        total_visible = len(self.items)
        try:
            if total_visible:
                self.canvas.itemconfigure(self.empty_window_id, state="hidden")
                self.canvas.itemconfigure(self.drop_window_id, state="normal")
            else:
                self.canvas.itemconfigure(self.drop_window_id, state="hidden")
                self.canvas.itemconfigure(self.empty_window_id, state="normal")
            self.recolocar_items()
            self.actualizar_resumen_grupo()
        except Exception:
            logger.exception("Error sincronizando la grilla visual de Publicidad.")

    def inicializar_grupos_publicidad(self):
        try:
            self.refrescar_config_compartida()
            self.asegurar_config_publicidades()
            self.migrar_publicidades_a_storage()
            self.refrescar_biblioteca_metadata(persistir=False)
            self.actualizar_combo_grupos()
            self.canvas.update_idletasks()
            self.cargar_ubicaciones()
            self.redimensionar_celdas()
        except Exception:
            logger.exception("Error al inicializar grupos de publicidad.")

    def _ruta_gestionada(self, ruta):
        try:
            return Path(ruta).resolve().is_relative_to(self.publicidades_storage_dir.resolve())
        except Exception:
            return False

    def _hash_archivo(self, ruta):
        digest = hashlib.sha1()
        with open(ruta, "rb") as archivo:
            for chunk in iter(lambda: archivo.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _copiar_a_storage_publicidades(self, ruta_origen):
        ruta_origen = Path(ruta_origen)
        if not ruta_origen.exists():
            raise FileNotFoundError(f"No existe el archivo: {ruta_origen}")

        if self._ruta_gestionada(ruta_origen):
            return str(ruta_origen.resolve())

        file_hash = self._hash_archivo(ruta_origen)
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in ruta_origen.stem).strip("_")
        safe_name = safe_name or "publicidad"
        destino = self.publicidades_storage_dir / f"{safe_name}_{file_hash[:12]}{ruta_origen.suffix.lower()}"

        if not destino.exists():
            shutil.copy2(ruta_origen, destino)
            logger.info("Publicidad copiada a storage interno | origen=%s | destino=%s", ruta_origen, destino)

        return str(destino.resolve())

    def refrescar_config_compartida(self):
        config = cargar_config()
        if not isinstance(config, dict):
            config = {}
        self.widgets.register("CONFIG", "config_json", config)
        return config

    def _iterar_todas_las_rutas_config(self, publicidades):
        for grupo in publicidades.get("grupos", {}).values():
            for ruta in grupo.get("items", {}):
                yield ruta
        for ruta in publicidades.get("globales", {}):
            yield ruta

    def _eliminar_archivo_gestionado_si_no_se_usa(self, ruta):
        try:
            if not ruta or not self._ruta_gestionada(ruta):
                return

            publicidades = self.asegurar_config_publicidades()
            referencias = set(self._iterar_todas_las_rutas_config(publicidades))
            if ruta in referencias:
                return

            ruta_path = Path(ruta)
            if ruta_path.exists():
                ruta_path.unlink()
                logger.info("Publicidad interna eliminada por quedar sin referencias | ruta=%s", ruta)
        except Exception:
            logger.exception("Error limpiando archivo de publicidad sin uso | ruta=%s", ruta)

    def migrar_publicidades_a_storage(self):
        try:
            publicidades = self.asegurar_config_publicidades()
            cambios = False

            for grupo in publicidades.get("grupos", {}).values():
                items_actuales = grupo.get("items", {})
                items_migrados = {}
                for ruta, info in items_actuales.items():
                    if not os.path.exists(ruta):
                        items_migrados[ruta] = info
                        continue
                    nueva_ruta = self._copiar_a_storage_publicidades(ruta)
                    items_migrados[nueva_ruta] = info
                    if nueva_ruta != ruta:
                        cambios = True
                grupo["items"] = items_migrados

            globales_actuales = publicidades.get("globales", {})
            globales_migrados = {}
            for ruta, info in globales_actuales.items():
                if not os.path.exists(ruta):
                    globales_migrados[ruta] = info
                    continue
                nueva_ruta = self._copiar_a_storage_publicidades(ruta)
                globales_migrados[nueva_ruta] = info
                if nueva_ruta != ruta:
                    cambios = True
            publicidades["globales"] = globales_migrados

            if cambios:
                logger.info("Publicidades migradas a storage interno.")
                self.guardar_config_publicidades()
        except Exception:
            logger.exception("Error migrando publicidades a storage interno.")

    def obtener_config(self):
        config = self.widgets.get_widget("CONFIG", "config_json")
        if isinstance(config, dict):
            return config
        return self.refrescar_config_compartida()

    def asegurar_config_publicidades(self):
        config = self.obtener_config()
        publicidades = config.get("publicidades")

        if isinstance(publicidades, dict) and publicidades.get("grupos"):
            publicidades.setdefault("grupo_activo", next(iter(publicidades["grupos"])))
            publicidades.setdefault("globales", {})
            publicidades.setdefault("biblioteca", {})
            publicidades.setdefault("historial_envios", [])

            for group_id, grupo in publicidades.get("grupos", {}).items():
                grupo.setdefault("nombre", group_id)
                grupo.setdefault("items", {})
                grupo.setdefault("usar_display_index", False)
                grupo.setdefault("display_index", 0)

            self.grupo_activo_id = publicidades["grupo_activo"]
            return publicidades

        ubicaciones_legacy = config.get("ubicaciones", {})
        publicidades = {
            "grupo_activo": "default",
            "grupos": {
                "default": {
                    "nombre": "General",
                    "items": dict(ubicaciones_legacy) if isinstance(ubicaciones_legacy, dict) else {},
                    "usar_display_index": False,
                    "display_index": 0,
                }
            },
            "globales": {},
            "biblioteca": {},
            "historial_envios": [],
        }
        config["publicidades"] = publicidades
        self.grupo_activo_id = "default"
        guardar_config(config)
        return publicidades

    def guardar_config_publicidades(self):
        config_actual = self.obtener_config()
        config_disco = self.refrescar_config_compartida()
        config_disco["publicidades"] = config_actual.get("publicidades", {})
        if "ubicaciones" in config_actual:
            config_disco["ubicaciones"] = config_actual.get("ubicaciones", {})
        guardar_config(config_disco)
        self.widgets.register("CONFIG", "config_json", config_disco)

    def sincronizar_publicidades_compartidas(self):
        self.refrescar_config_compartida()
        self.asegurar_config_publicidades()
        self.limpiar_items_canvas()
        self.actualizar_combo_grupos()
        self.cargar_ubicaciones()
        self.redimensionar_celdas()
        self.actualizar_resumen_grupo()

    def _tipo_archivo_publicidad(self, ruta):
        return "video" if str(ruta).lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm")) else "imagen"

    def _duracion_video(self, ruta):
        cap = cv2.VideoCapture(str(ruta))
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            if fps > 0 and frames > 0:
                return round(frames / fps, 2)
            return 0.0
        finally:
            cap.release()

    def _dimensiones_media(self, ruta, tipo):
        if tipo == "imagen":
            with Image.open(ruta) as img:
                return img.size

        cap = cv2.VideoCapture(str(ruta))
        try:
            return int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        finally:
            cap.release()

    def _formatear_tamanio(self, bytes_size):
        return f"{bytes_size / (1024 * 1024):.2f} MB"

    def _timestamp_actual(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _referencias_por_ruta(self, ruta):
        publicidades = self.asegurar_config_publicidades()
        grupos = []
        es_global = ruta in publicidades.get("globales", {})
        for group_id, grupo in publicidades.get("grupos", {}).items():
            if ruta in grupo.get("items", {}):
                grupos.append(grupo.get("nombre", group_id))
        return grupos, es_global

    def construir_metadata_publicidad(self, ruta):
        ruta_path = Path(ruta)
        grupos, es_global = self._referencias_por_ruta(ruta)
        tipo = self._tipo_archivo_publicidad(ruta)

        if not ruta_path.exists():
            return {
                "ruta": str(ruta_path),
                "nombre": ruta_path.name,
                "tipo": tipo,
                "existe": False,
                "estado": "FALTANTE",
                "grupos": grupos,
                "global": es_global,
                "cambios_pendientes": False,
            }

        size_bytes = ruta_path.stat().st_size
        modified = datetime.fromtimestamp(ruta_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        file_hash = self._hash_archivo(ruta_path)
        width, height = self._dimensiones_media(ruta_path, tipo)
        duracion = self._duracion_video(ruta_path) if tipo == "video" else 0.0

        publicidades = self.asegurar_config_publicidades()
        biblioteca = publicidades.setdefault("biblioteca", {})
        registrado = biblioteca.get(str(ruta_path), {})
        ultimo_hash = registrado.get("ultimo_envio_hash")
        ultimo_resultado = registrado.get("ultimo_envio_resultado")
        cambios_pendientes = bool(ultimo_hash and ultimo_hash != file_hash)

        if not ultimo_hash:
            estado = "NUEVO"
        elif cambios_pendientes:
            estado = "PENDIENTE"
        elif ultimo_resultado == "ok":
            estado = "ENVIADA"
        elif ultimo_resultado == "error":
            estado = "ERROR_ENVIO"
        else:
            estado = "OK"

        return {
            "ruta": str(ruta_path.resolve()),
            "nombre": ruta_path.name,
            "tipo": tipo,
            "existe": True,
            "estado": estado,
            "grupos": grupos,
            "global": es_global,
            "tam_bytes": size_bytes,
            "tam_texto": self._formatear_tamanio(size_bytes),
            "modificado": modified,
            "duracion_seg": duracion,
            "hash": file_hash,
            "width": width,
            "height": height,
            "ultimo_envio": registrado.get("ultimo_envio"),
            "ultimo_envio_resultado": ultimo_resultado,
            "ultimo_error": registrado.get("ultimo_error", ""),
            "cambios_pendientes": cambios_pendientes or not ultimo_hash,
        }

    def refrescar_biblioteca_metadata(self, persistir=False):
        publicidades = self.asegurar_config_publicidades()
        biblioteca = publicidades.setdefault("biblioteca", {})
        rutas = list(dict.fromkeys(self._iterar_todas_las_rutas_config(publicidades)))
        nuevas_rutas = set()

        for ruta in rutas:
            metadata = self.construir_metadata_publicidad(ruta)
            registrado = biblioteca.get(ruta, {})
            registrado.update(metadata)
            biblioteca[ruta] = registrado
            nuevas_rutas.add(ruta)

        for ruta in list(biblioteca.keys()):
            if ruta not in nuevas_rutas:
                del biblioteca[ruta]

        self.biblioteca_metadata = biblioteca
        if persistir:
            self.guardar_config_publicidades()
        return biblioteca

    def _texto_estado_item(self, ruta):
        metadata = self.biblioteca_metadata.get(ruta) or self.construir_metadata_publicidad(ruta)
        if not metadata.get("existe", True):
            return "FALTANTE"
        if metadata.get("width", 0) and metadata.get("height", 0):
            if metadata["width"] < 800 or metadata["height"] < 600:
                return "REVISAR"
        return metadata.get("estado", "OK")

    def _detalle_estado_item(self, ruta):
        metadata = self.biblioteca_metadata.get(ruta) or self.construir_metadata_publicidad(ruta)
        if not metadata.get("existe", True):
            return "El archivo ya no está disponible"
        if metadata.get("width", 0) and metadata.get("height", 0):
            if metadata["width"] < 800 or metadata["height"] < 600:
                return f"{metadata['width']}×{metadata['height']} · menor a 800×600"
        dimensiones = ""
        if metadata.get("width") and metadata.get("height"):
            dimensiones = f"{metadata['width']}×{metadata['height']}"
        duracion = metadata.get("duracion_seg", 0)
        if duracion:
            return f"{dimensiones} · {duracion:.0f} s" if dimensiones else f"{duracion:.0f} s"
        return dimensiones or metadata.get("tipo", "multimedia")

    def validar_items_publicidad(self, items=None):
        items = items or self.obtener_items_para_envio()
        errores = []
        advertencias = []

        for item in items:
            ruta = item["filepath"]
            metadata = self.biblioteca_metadata.get(ruta) or self.construir_metadata_publicidad(ruta)

            if not metadata.get("existe"):
                errores.append(f"Falta archivo: {ruta}")
                continue

            if metadata["tipo"] == "imagen" and metadata.get("tam_bytes", 0) > self.MAX_IMAGE_MB * 1024 * 1024:
                advertencias.append(f"Imagen pesada ({metadata['tam_texto']}): {metadata['nombre']}")

            if metadata.get("width", 0) and metadata.get("height", 0):
                if metadata["width"] < 800 or metadata["height"] < 600:
                    advertencias.append(f"Resolución menor a la pantalla: {metadata['nombre']}")

            if metadata["tipo"] == "video":
                if metadata.get("tam_bytes", 0) > self.MAX_VIDEO_MB * 1024 * 1024:
                    advertencias.append(f"Video pesado ({metadata['tam_texto']}): {metadata['nombre']}")
                if metadata.get("duracion_seg", 0) > self.MAX_VIDEO_SECONDS:
                    advertencias.append(
                        f"Video largo ({metadata['duracion_seg']:.0f}s): {metadata['nombre']}"
                    )

        return errores, advertencias

    def registrar_resultado_envio_publicidades(self, url, msg, items_enviados):
        try:
            publicidades = self.asegurar_config_publicidades()
            historial = publicidades.setdefault("historial_envios", [])
            ok = msg.startswith("FINAL_OK:")
            detalle = msg.replace("FINAL_OK:", "", 1).replace("FINAL_ERROR:", "", 1).strip()

            historial.insert(
                0,
                {
                    "fecha": self._timestamp_actual(),
                    "url": url,
                    "resultado": "ok" if ok else "error",
                    "detalle": detalle,
                    "grupo": self.grupo_activo_id,
                    "cantidad_items": len(items_enviados),
                },
            )
            del historial[50:]

            biblioteca = publicidades.setdefault("biblioteca", {})
            for item in items_enviados:
                ruta = item["filepath"]
                metadata = self.construir_metadata_publicidad(ruta)
                registrado = biblioteca.setdefault(ruta, {})
                registrado.update(metadata)
                registrado["ultimo_envio"] = self._timestamp_actual()
                registrado["ultimo_envio_resultado"] = "ok" if ok else "error"
                registrado["ultimo_error"] = "" if ok else detalle
                if ok and metadata.get("hash"):
                    registrado["ultimo_envio_hash"] = metadata["hash"]

            self.biblioteca_metadata = biblioteca
            self.guardar_config_publicidades()
            self.actualizar_resumen_grupo()
        except Exception:
            logger.exception("Error registrando historial de envio de publicidades.")

    def validar_publicidades(self):
        try:
            self.refrescar_biblioteca_metadata(persistir=False)
            items_envio = self.obtener_items_para_envio()
            if not items_envio:
                messagebox.showinfo("Validacion", "No hay publicidades para validar.")
                return

            errores, advertencias = self.validar_items_publicidad(items_envio)
            resumen = [
                f"Items a enviar: {len(items_envio)}",
                f"Errores: {len(errores)}",
                f"Advertencias: {len(advertencias)}",
            ]
            if errores:
                resumen.append("")
                resumen.append("Errores:")
                resumen.extend(errores[:8])
            if advertencias:
                resumen.append("")
                resumen.append("Advertencias:")
                resumen.extend(advertencias[:8])

            titulo = "Validacion con errores" if errores else "Validacion completada"
            messagebox.showinfo(titulo, "\n".join(resumen))
        except Exception:
            logger.exception("Error validando publicidades.")

    def construir_resumen_envio_publicidades(self, items_envio):
        resumen = {}
        for item in items_envio:
            grupo_id = item.get("grupo_id", "default")
            grupo = item.get("grupo", grupo_id)
            display_index = item.get("display_index")
            key = (grupo_id, display_index)
            if key not in resumen:
                resumen[key] = {
                    "grupo": grupo,
                    "display_index": display_index,
                    "cantidad": 0,
                }
            resumen[key]["cantidad"] += 1

        lineas = []
        for data in resumen.values():
            if data["display_index"] is None:
                destino = "Pantalla automática"
            else:
                destino = f"Pantalla {int(data['display_index']) + 1}"
            lineas.append(f"- {destino} -> {data['grupo']} ({data['cantidad']} items)")
        return "\n".join(lineas)

    def abrir_biblioteca_publicidades(self):
        try:
            self.refrescar_biblioteca_metadata()
            top = ttk.Toplevel(self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad"))
            top.title("Biblioteca de Publicidades")
            fit_toplevel_to_workarea(top, 1080, 420, min_width=920, min_height=360)
            top.place_window_center()
            top.grab_set()

            columns = ("estado", "tipo", "tam", "duracion", "dimensiones", "grupos", "envio", "ruta")
            tree = ttk.Treeview(top, columns=columns, show="headings", height=14)
            headers = {
                "estado": "Estado",
                "tipo": "Tipo",
                "tam": "Tamano",
                "duracion": "Duracion",
                "dimensiones": "Resolucion",
                "grupos": "Grupos",
                "envio": "Ultimo envio",
                "ruta": "Ruta",
            }
            widths = {
                "estado": 120,
                "tipo": 80,
                "tam": 90,
                "duracion": 80,
                "dimensiones": 110,
                "grupos": 170,
                "envio": 150,
                "ruta": 360,
            }
            for col in columns:
                tree.heading(col, text=headers[col])
                tree.column(col, width=widths[col], stretch=col == "ruta")
            tree.pack(fill="both", expand=True, padx=10, pady=10)

            for ruta, meta in sorted(self.biblioteca_metadata.items(), key=lambda item: item[1].get("nombre", "").lower()):
                grupos = ", ".join(meta.get("grupos", []))
                if meta.get("global"):
                    grupos = f"{grupos} | Global" if grupos else "Global"
                tree.insert(
                    "",
                    "end",
                    values=(
                        meta.get("estado", "-"),
                        meta.get("tipo", "-"),
                        meta.get("tam_texto", "-"),
                        f"{meta.get('duracion_seg', 0):.0f}s" if meta.get("tipo") == "video" else "-",
                        f"{meta.get('width', 0)}x{meta.get('height', 0)}" if meta.get("existe") else "-",
                        grupos,
                        meta.get("ultimo_envio") or "-",
                        ruta,
                    ),
                )

            ttk.Button(top, text="Cerrar", command=top.destroy).pack(pady=(0, 10))
        except Exception:
            logger.exception("Error abriendo biblioteca de publicidades.")

    def abrir_historial_publicidades(self):
        try:
            publicidades = self.asegurar_config_publicidades()
            historial = publicidades.get("historial_envios", [])

            top = ttk.Toplevel(self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad"))
            top.title("Historial de Envio de Publicidades")
            fit_toplevel_to_workarea(top, 980, 360, min_width=860, min_height=320)
            top.place_window_center()
            top.grab_set()

            columns = ("fecha", "grupo", "resultado", "cantidad", "url", "detalle")
            tree = ttk.Treeview(top, columns=columns, show="headings", height=12)
            for col, text, width in (
                ("fecha", "Fecha", 150),
                ("grupo", "Grupo", 120),
                ("resultado", "Resultado", 90),
                ("cantidad", "Items", 70),
                ("url", "Dispositivo", 220),
                ("detalle", "Detalle", 300),
            ):
                tree.heading(col, text=text)
                tree.column(col, width=width, stretch=col == "detalle")
            tree.pack(fill="both", expand=True, padx=10, pady=10)

            for row in historial:
                tree.insert(
                    "",
                    "end",
                    values=(
                        row.get("fecha", "-"),
                        row.get("grupo", "-"),
                        row.get("resultado", "-"),
                        row.get("cantidad_items", 0),
                        row.get("url", "-"),
                        row.get("detalle", ""),
                    ),
                )

            ttk.Button(top, text="Cerrar", command=top.destroy).pack(pady=(0, 10))
        except Exception:
            logger.exception("Error abriendo historial de publicidades.")

    def actualizar_combo_grupos(self):
        publicidades = self.asegurar_config_publicidades()
        grupos = publicidades["grupos"]
        valores = [grupos[group_id].get("nombre", group_id) for group_id in grupos]
        self.combo_grupos.configure(values=valores)

        grupo_activo = publicidades.get("grupo_activo") or next(iter(grupos))
        if grupo_activo not in grupos:
            grupo_activo = next(iter(grupos))
            publicidades["grupo_activo"] = grupo_activo

        self.grupo_activo_id = grupo_activo
        self.combo_grupos.set(grupos[grupo_activo].get("nombre", grupo_activo))

    def grupo_id_por_nombre(self, nombre):
        publicidades = self.asegurar_config_publicidades()
        for group_id, grupo in publicidades["grupos"].items():
            if grupo.get("nombre", group_id) == nombre:
                return group_id
        return None

    def normalizar_id_grupo(self, nombre):
        base = "".join(ch.lower() if ch.isalnum() else "_" for ch in nombre.strip())
        base = "_".join(part for part in base.split("_") if part) or "grupo"
        publicidades = self.asegurar_config_publicidades()
        group_id = base
        contador = 2
        while group_id in publicidades["grupos"]:
            group_id = f"{base}_{contador}"
            contador += 1
        return group_id

    def cambiar_grupo_desde_combo(self, event=None):
        group_id = self.grupo_id_por_nombre(self.combo_grupos.get())
        if group_id:
            self.cambiar_grupo(group_id)

    def cambiar_grupo(self, group_id):
        self.refrescar_config_compartida()
        publicidades = self.asegurar_config_publicidades()
        if group_id not in publicidades["grupos"]:
            return

        self.guardar_ubicaciones()
        publicidades["grupo_activo"] = group_id
        self.grupo_activo_id = group_id
        self.guardar_config_publicidades()
        self.limpiar_items_canvas()
        self.actualizar_combo_grupos()
        self.actualizar_resumen_grupo()
        self.refrescar_biblioteca_metadata()
        self.cargar_ubicaciones()
        self.redimensionar_celdas()

    def crear_grupo(self):
        nombre = simpledialog.askstring("Nuevo grupo", "Nombre del grupo de publicidades:")
        if not nombre:
            return
        nombre = nombre.strip()
        if not nombre:
            return

        self.refrescar_config_compartida()
        publicidades = self.asegurar_config_publicidades()
        group_id = self.normalizar_id_grupo(nombre)
        publicidades["grupos"][group_id] = {
            "nombre": nombre,
            "items": {},
            "usar_display_index": False,
            "display_index": 0,
        }
        publicidades["grupo_activo"] = group_id
        self.grupo_activo_id = group_id
        self.guardar_config_publicidades()
        self.limpiar_items_canvas()
        self.actualizar_combo_grupos()
        self.refrescar_biblioteca_metadata()
        self.actualizar_resumen_grupo()

    def renombrar_grupo(self):
        self.refrescar_config_compartida()
        publicidades = self.asegurar_config_publicidades()
        grupo = publicidades["grupos"].get(self.grupo_activo_id)
        if not grupo:
            return

        nombre = simpledialog.askstring(
            "Renombrar grupo",
            "Nuevo nombre del grupo:",
            initialvalue=grupo.get("nombre", self.grupo_activo_id),
        )
        if not nombre:
            return
        grupo["nombre"] = nombre.strip()
        self.guardar_config_publicidades()
        self.actualizar_combo_grupos()
        self.actualizar_resumen_grupo()
        self.refrescar_biblioteca_metadata()

    def eliminar_grupo(self):
        self.refrescar_config_compartida()
        publicidades = self.asegurar_config_publicidades()
        grupos = publicidades["grupos"]
        if len(grupos) <= 1:
            messagebox.showinfo("Grupos", "Debe quedar al menos un grupo de publicidades.")
            return

        nombre = grupos[self.grupo_activo_id].get("nombre", self.grupo_activo_id)
        if not messagebox.askyesno("Eliminar grupo", f"Eliminar el grupo '{nombre}'?"):
            return

        del grupos[self.grupo_activo_id]
        nuevo_activo = next(iter(grupos))
        publicidades["grupo_activo"] = nuevo_activo
        self.grupo_activo_id = nuevo_activo
        self.guardar_config_publicidades()
        self.limpiar_items_canvas()
        self.actualizar_combo_grupos()
        self.cargar_ubicaciones()
        self.actualizar_resumen_grupo()
        self.refrescar_biblioteca_metadata()

    def limpiar_items_canvas(self):
        for item in self.items:
            try:
                self.canvas.delete(item["window_id"])
            except Exception:
                pass
        self.items = []
        self.items_dict = {}
        self.drag_item = None
        self.item_seleccionado = None
        self.actualizar_resumen_grupo()

    def abrir_globales(self):
        try:
            self.refrescar_config_compartida()
            top = ttk.Toplevel(self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad"))
            top.title("Publicidades Globales")
            fit_toplevel_to_workarea(top, 680, 360, min_width=620, min_height=320)
            top.place_window_center()
            top.grab_set()

            ttk.Label(
                top,
                text="Estas publicidades se envian junto con cualquier grupo seleccionado.",
                font=("Segoe UI", 10),
            ).pack(anchor="w", padx=12, pady=(12, 6))

            frame_lista = ttk.Frame(top, padding=(12, 0, 12, 8))
            frame_lista.pack(fill="both", expand=True)

            listbox = tk.Listbox(frame_lista, height=10)
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=listbox.yview)
            scrollbar.pack(side="right", fill="y")
            listbox.configure(yscrollcommand=scrollbar.set)

            def refrescar():
                listbox.delete(0, "end")
                for ruta, _info in self.obtener_globales_ordenadas():
                    listbox.insert("end", ruta)

            def agregar():
                filepaths = filedialog.askopenfilenames(
                    title="Seleccionar publicidades globales",
                    filetypes=[
                        ("Archivos multimedia", "*.jpg *.jpeg *.png *.webp *.mp4 *.avi *.mov *.mkv *.webm"),
                        ("Todos los archivos", "*.*"),
                    ],
                )
                if not filepaths:
                    return
                publicidades = self.asegurar_config_publicidades()
                globales = publicidades.setdefault("globales", {})
                for ruta in filepaths:
                    try:
                        ruta_interna = self._copiar_a_storage_publicidades(ruta)
                    except Exception:
                        logger.exception("Error copiando publicidad global a storage | ruta=%s", ruta)
                        messagebox.showerror("Publicidades", f"No se pudo guardar la publicidad:\n{ruta}")
                        continue

                    if ruta_interna not in globales:
                        posicion = len(globales) + 1
                        fila, col = divmod(posicion - 1, self.cols)
                        globales[ruta_interna] = {"fila": fila, "columna": col, "posicion": posicion}
                self.reordenar_globales(globales)
                self.guardar_config_publicidades()
                self.refrescar_biblioteca_metadata()
                refrescar()
                self.actualizar_resumen_grupo()

            def eliminar():
                seleccion = listbox.curselection()
                if not seleccion:
                    return
                ruta = listbox.get(seleccion[0])
                publicidades = self.asegurar_config_publicidades()
                globales = publicidades.setdefault("globales", {})
                if ruta in globales and messagebox.askyesno("Eliminar global", "Eliminar la publicidad global seleccionada?"):
                    del globales[ruta]
                    self.reordenar_globales(globales)
                    self.guardar_config_publicidades()
                    self._eliminar_archivo_gestionado_si_no_se_usa(ruta)
                    self.refrescar_biblioteca_metadata()
                    refrescar()
                    self.actualizar_resumen_grupo()

            acciones = ttk.Frame(top, padding=12)
            acciones.pack(fill="x")
            ttk.Button(acciones, text="Agregar", command=agregar).pack(side="left")
            ttk.Button(acciones, text="Eliminar", command=eliminar).pack(side="left", padx=(6, 0))
            ttk.Button(acciones, text="Cerrar", command=top.destroy).pack(side="right")

            refrescar()
        except Exception:
            logger.exception("Error al abrir publicidades globales.")

    def abrir_config_pantalla_grupo(self):
        try:
            publicidades = self.asegurar_config_publicidades()
            grupo = publicidades["grupos"].get(self.grupo_activo_id)
            if not grupo:
                messagebox.showwarning("Pantalla Grupo", "No hay grupo activo.")
                return

            top = ttk.Toplevel(self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad"))
            top.title("Pantalla del grupo")
            fit_toplevel_to_workarea(top, 420, 220, min_width=400, min_height=210)
            top.place_window_center()
            top.grab_set()

            nombre = grupo.get("nombre", self.grupo_activo_id)

            ttk.Label(
                top,
                text=f"Grupo: {nombre}",
                font=("Segoe UI", 12, "bold"),
            ).pack(anchor="w", padx=15, pady=(15, 8))

            usar_var = ttk.BooleanVar(value=bool(grupo.get("usar_display_index", False)))
            pantalla_var = ttk.StringVar(value=str(int(grupo.get("display_index", 0)) + 1))

            ttk.Checkbutton(
                top,
                text="Enviar este grupo a una pantalla específica",
                variable=usar_var,
            ).pack(anchor="w", padx=15, pady=(5, 8))

            frame = ttk.Frame(top)
            frame.pack(fill="x", padx=15, pady=5)

            ttk.Label(frame, text="Pantalla / HDMI:").pack(side="left")

            combo = ttk.Combobox(
                frame,
                textvariable=pantalla_var,
                state="readonly",
                values=["1", "2", "3", "4"],
                width=8,
            )
            combo.pack(side="left", padx=(10, 0))

            ttk.Label(
                top,
                text="Si el dispositivo no soporta multi-monitor, se enviará normal.",
                bootstyle="secondary",
            ).pack(anchor="w", padx=15, pady=(8, 0))

            def guardar():
                try:
                    display_index = int(pantalla_var.get()) - 1
                except ValueError:
                    display_index = 0

                if display_index < 0:
                    display_index = 0

                grupo["usar_display_index"] = bool(usar_var.get())
                grupo["display_index"] = display_index

                self.guardar_config_publicidades()
                self.actualizar_resumen_grupo()
                top.destroy()

            acciones = ttk.Frame(top)
            acciones.pack(fill="x", padx=15, pady=15)

            ttk.Button(acciones, text="Guardar", command=guardar, bootstyle="success").pack(side="left")
            ttk.Button(acciones, text="Cancelar", command=top.destroy).pack(side="right")

        except Exception:
            logger.exception("Error abriendo configuracion de pantalla del grupo.")

    def obtener_globales_ordenadas(self):
        publicidades = self.asegurar_config_publicidades()
        globales = publicidades.setdefault("globales", {})
        return sorted(
            globales.items(),
            key=lambda item: (item[1].get("posicion", 999999), item[0]),
        )

    def reordenar_globales(self, globales):
        for idx, ruta in enumerate(
            sorted(globales, key=lambda r: (globales[r].get("posicion", 999999), r)),
            start=1,
        ):
            fila, col = divmod(idx - 1, self.cols)
            globales[ruta] = {"fila": fila, "columna": col, "posicion": idx}

    def obtener_items_para_envio(self):
        self.refrescar_biblioteca_metadata(persistir=False)
        publicidades = self.asegurar_config_publicidades()
        grupos = publicidades.get("grupos", {})
        grupos_con_pantalla = [
            (group_id, grupo)
            for group_id, grupo in grupos.items()
            if grupo.get("usar_display_index")
        ]

        if grupos_con_pantalla:
            grupos_envio = grupos_con_pantalla
        else:
            grupo_activo = grupos.get(self.grupo_activo_id, {})
            grupos_envio = [(self.grupo_activo_id, grupo_activo)]

        items_envio = []
        omitidas = []

        for group_id, grupo in grupos_envio:
            nombre_grupo = grupo.get("nombre", group_id)
            usar_display = bool(grupo.get("usar_display_index", False))
            display_index = int(grupo.get("display_index", 0) or 0)

            rutas = []
            vistos = set()

            for ruta, _info in self.obtener_globales_ordenadas():
                if ruta not in vistos:
                    rutas.append(ruta)
                    vistos.add(ruta)

            items_grupo = grupo.get("items", {})
            rutas_grupo_ordenadas = sorted(
                items_grupo.items(),
                key=lambda item: (item[1].get("posicion", 999999), item[0]),
            )

            for ruta, _info in rutas_grupo_ordenadas:
                if ruta not in vistos:
                    rutas.append(ruta)
                    vistos.add(ruta)

            for ruta in rutas:
                if not os.path.exists(ruta):
                    omitidas.append(ruta)
                    continue

                item_envio = {
                    "filepath": ruta,
                    "grid": divmod(len(items_envio), self.cols),
                    "grupo": nombre_grupo,
                    "grupo_id": group_id,
                    "grupo_activo": group_id == self.grupo_activo_id,
                }

                if usar_display:
                    item_envio["display_index"] = display_index

                items_envio.append(item_envio)

        if omitidas:
            logger.warning("Publicidades omitidas por ruta inexistente | cantidad=%s", len(omitidas))

        return items_envio

    def recolocar_items(self):
        try:
            logger.debug("Recolocando items | cantidad=%s", len(self.items))
            for idx, item in enumerate(self.items):
                fila, col = divmod(idx, self.cols)
                x, y = self.calcular_x(col), self.calcular_y(fila)
                self.canvas.coords(item["window_id"], x, y)
                item["frame"].configure(width=self.cell_width, height=CELL_HEIGHT)
                item["label_pos"].config(text=str(idx + 1))
                if item.get("label_estado"):
                    item["label_estado"].config(text=self._texto_estado_item(item["filepath"]))
                if item.get("label_detalle"):
                    item["label_detalle"].config(text=self._detalle_estado_item(item["filepath"]))
            if hasattr(self, "drop_window_id") and self.items:
                fila_drop, col_drop = divmod(len(self.items), self.cols)
                self.canvas.coords(self.drop_window_id, self.calcular_x(col_drop), self.calcular_y(fila_drop))
                self.canvas.itemconfigure(self.drop_window_id, width=self.cell_width, height=CELL_HEIGHT)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            logger.exception("Error al recolocar items.")

    def agregar_multimedia(self):
        try:
            filepaths = filedialog.askopenfilenames(
                title="Seleccionar archivos multimedia",
                filetypes=[
                    ("Archivos multimedia", "*.jpg *.jpeg *.png *.mp4 *.avi *.mov"),
                    ("Todos los archivos", "*.*")
                ]
            )

            logger.info("Archivos multimedia seleccionados | cantidad=%s", len(filepaths))

            for ruta in filepaths:
                logger.debug("Agregando archivo multimedia | ruta=%s", ruta)
                try:
                    ruta_interna = self._copiar_a_storage_publicidades(ruta)
                except Exception:
                    logger.exception("Error copiando publicidad a storage | ruta=%s", ruta)
                    messagebox.showerror("Publicidades", f"No se pudo guardar la publicidad:\n{ruta}")
                    continue
                self.agregar_item_multimedia(os.path.basename(ruta_interna), ruta_interna)

            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.recolocar_items()

        except Exception:
            logger.exception("Error al agregar multimedia.")

    def agregar_item_multimedia(self, nombre, filepath, fila=None, col=None):
        try:
            if fila is None or col is None:
                fila, col = self.obtener_proxima_posicion_libre()

            logger.info(
                "Agregando item multimedia | nombre=%s | ruta=%s | fila=%s | col=%s",
                nombre, filepath, fila, col
            )

            frame_item = tk.Frame(
                self.canvas,
                width=self.cell_width,
                height=CELL_HEIGHT,
                bg=self.CARD_BG,
                highlightthickness=1,
                highlightbackground=self.CARD_BORDER,
                highlightcolor=self.ACCENT,
                bd=0,
            )
            frame_item.pack_propagate(False)

            self.refrescar_biblioteca_metadata(persistir=False)
            metadata = self.biblioteca_metadata.get(filepath) or self.construir_metadata_publicidad(filepath)
            tipo = self._tipo_archivo_publicidad(filepath)
            logger.debug("Tipo multimedia detectado | ruta=%s | tipo=%s", filepath, tipo)

            frame_preview = tk.Frame(
                frame_item,
                bg="#EDEFEE",
                width=max(self.cell_width - 2, 80),
                height=PREVIEW_HEIGHT,
                bd=0,
            )
            frame_preview.pack(fill="x")
            frame_preview.pack_propagate(False)
            frame_preview.grid_propagate(False)
            self.insertar_contenido_multimedia(frame_preview, filepath, tipo)

            separador = tk.Frame(frame_item, bg=self.CARD_BORDER, height=1, bd=0)
            separador.pack(fill="x")

            frame_info = tk.Frame(frame_item, bg=self.CARD_BG, bd=0, padx=8, pady=6)
            frame_info.pack(fill="both", expand=True)
            label_nombre = tk.Label(
                frame_info,
                text=Path(filepath).name,
                anchor="w",
                bg=self.CARD_BG,
                fg="#DBE7E0" if self.tema_interfaz == "oscuro" else "#2B3A34",
                font=("Segoe UI", 9, "bold"),
            )
            label_nombre.pack(fill="x")
            label_detalle = tk.Label(
                frame_info,
                text=self._detalle_estado_item(filepath),
                anchor="w",
                bg=self.CARD_BG,
                fg="#d5a72b" if self._texto_estado_item(filepath) == "REVISAR" else self.BADGE_FG,
                font=("Segoe UI", 8),
            )
            label_detalle.pack(fill="x", pady=(3, 0))

            label_pos = tk.Label(
                frame_item,
                text="",
                font=("Segoe UI", 11, "bold"),
                bg=self.BADGE_BG,
                fg=self.BADGE_FG,
                padx=8,
                pady=3,
            )
            label_pos.place(x=8, y=8)
            estado_texto = self._texto_estado_item(filepath)
            label_estado = tk.Label(
                frame_preview,
                text=self._texto_estado_item(filepath),
                font=("Segoe UI", 8, "bold"),
                bg="#b77b16" if estado_texto == "REVISAR" else "#1aa053",
                fg="white",
                padx=8,
                pady=3,
            )
            label_estado.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)

            frame_item.bind("<ButtonPress-1>", lambda e, i=frame_item: self.start_drag(e, i))
            frame_item.bind("<B1-Motion>", self.do_drag)
            frame_item.bind("<ButtonRelease-1>", self.end_drag)
            frame_item.bind("<Double-Button-1>", lambda e, ruta=filepath: self.abrir_contenido(ruta))
            frame_item.bind("<Button-3>", lambda e, ruta=filepath: self.mostrar_menu_contextual(e, ruta))

            x, y = self.calcular_x(col), self.calcular_y(fila)
            window_id = self.canvas.create_window(x, y, window=frame_item, anchor="center")

            self.items.append({
                "frame": frame_item,
                "grid": (fila, col),
                "filepath": filepath,
                "window_id": window_id,
                "label_pos": label_pos,
                "label_estado": label_estado,
                "label_nombre": label_nombre,
                "label_detalle": label_detalle,
                "frame_info": frame_info,
                "separador": separador,
            })
            self.items_dict[filepath] = {
                "fila": fila,
                "columna": col,
                "posicion": fila * self.cols + col + 1
            }

            self.rows = (len(self.items) + self.cols - 1) // self.cols
            self.canvas.config(height=self.rows * (CELL_HEIGHT + ITEM_MARGIN))
            self.refrescar_biblioteca_metadata()
            self.guardar_ubicaciones()
            self.actualizar_resumen_grupo()
            self.canvas.after_idle(self._sincronizar_grilla_publicidad)

            logger.debug("Item multimedia agregado correctamente | total_items=%s", len(self.items))

        except Exception:
            logger.exception("Error al agregar item multimedia | nombre=%s | ruta=%s", nombre, filepath)

    def insertar_contenido_multimedia(self, frame, ruta, tipo):
        try:
            logger.debug("Insertando contenido multimedia | ruta=%s | tipo=%s", ruta, tipo)

            if tipo == "imagen":
                img = Image.open(ruta).convert("RGBA")
            else:
                cap = cv2.VideoCapture(ruta)
                success, frame_img = cap.read()
                cap.release()

                if success:
                    frame_img = cv2.cvtColor(frame_img, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_img).convert("RGBA")
                    draw = ImageDraw.Draw(img)
                    centro_x = img.width // 2
                    centro_y = img.height // 2
                    triangle = [
                        (centro_x - 20, centro_y - 20),
                        (centro_x - 20, centro_y + 20),
                        (centro_x + 20, centro_y)
                    ]
                    draw.polygon(triangle, fill="white")
                else:
                    logger.warning("No se pudo obtener frame de video. Se usará imagen gris | ruta=%s", ruta)
                    img = Image.new("RGBA", (max(self.cell_width - 8, 80), PREVIEW_HEIGHT - 8), color="gray")

            ancho_area = max(self.cell_width - 10, 80)
            alto_area = PREVIEW_HEIGHT - 8
            img.thumbnail((ancho_area, alto_area), Image.Resampling.LANCZOS)

            img_tk = ImageTk.PhotoImage(img)
            lienzo = tk.Canvas(
                frame,
                width=ancho_area,
                height=alto_area,
                bg="#EDEFEE",
                bd=0,
                highlightthickness=0,
            )
            lienzo.image = img_tk
            lienzo.create_image(ancho_area // 2, alto_area // 2, image=img_tk, anchor="center")
            lienzo.pack(fill="both", expand=True)

            lienzo.bind("<ButtonPress-1>", lambda e, f=frame: f.event_generate("<ButtonPress-1>", x=e.x, y=e.y))
            lienzo.bind("<B1-Motion>", lambda e, f=frame: f.event_generate("<B1-Motion>", x=e.x, y=e.y))
            lienzo.bind("<ButtonRelease-1>", lambda e, f=frame: f.event_generate("<ButtonRelease-1>", x=e.x, y=e.y))
            lienzo.bind("<Double-Button-1>", lambda e, f=frame, ruta=ruta: self.abrir_contenido(ruta))
            lienzo.bind("<Button-3>", lambda e, f=frame, ruta=ruta: self.mostrar_menu_contextual(e, ruta))

        except Exception:
            logger.exception("Error cargando multimedia | ruta=%s | tipo=%s", ruta, tipo)

    def obtener_proxima_posicion_libre(self):
        try:
            ocupadas = {item["grid"] for item in self.items}
            fila = 0
            while True:
                for col in range(self.cols):
                    if (fila, col) not in ocupadas:
                        logger.debug("Próxima posición libre encontrada | fila=%s | col=%s", fila, col)
                        return fila, col
                fila += 1
        except Exception:
            logger.exception("Error al obtener próxima posición libre.")
            return 0, 0

    def calcular_x(self, col):
        return col * (self.cell_width + ITEM_MARGIN) + self.cell_width // 2

    def calcular_y(self, fila):
        return fila * (CELL_HEIGHT + ITEM_MARGIN) + CELL_HEIGHT // 2

    def start_drag(self, event, frame):
        try:
            self._clic_pos = (event.x_root, event.y_root)

            for item in self.items:
                if item["frame"] == frame:
                    self.drag_item = item
                    break

            if self.item_seleccionado and self.item_seleccionado != self.drag_item:
                self.item_seleccionado["frame"].config(highlightbackground=self.CARD_BORDER)

            if self.drag_item:
                logger.debug("Inicio drag | ruta=%s", self.drag_item.get("filepath"))
                self.canvas.tag_raise(self.drag_item["window_id"])
                self.drag_item["frame"].lift()
                self.drag_item["frame"].config(
                    highlightbackground=self.ITEM_SELECTED,
                    highlightthickness=5,
                    bg=self.CARD_BG,
                )
                self.item_seleccionado = self.drag_item

        except Exception:
            logger.exception("Error al iniciar drag.")

    def do_drag(self, event):
        try:
            if self.drag_item:
                dx = event.x_root - self._clic_pos[0]
                dy = event.y_root - self._clic_pos[1]
                self._clic_pos = (event.x_root, event.y_root)
                x, y = self.canvas.coords(self.drag_item["window_id"])
                self.canvas.coords(self.drag_item["window_id"], x + dx, y + dy)
                self.canvas.tag_raise(self.drag_item["window_id"])
                self.drag_item["frame"].lift()
        except Exception:
            logger.exception("Error durante drag.")

    def end_drag(self, event):
        try:
            if not self.drag_item:
                return

            x, y = self.canvas.coords(self.drag_item["window_id"])
            col = int(x // (self.cell_width + ITEM_MARGIN))
            row = int(y // (CELL_HEIGHT + ITEM_MARGIN))
            col = max(0, min(col, self.cols - 1))
            row = max(0, row)

            nuevo_index = row * self.cols + col
            nuevo_index = min(nuevo_index, len(self.items) - 1)

            logger.info(
                "Fin drag | ruta=%s | nueva_fila=%s | nueva_col=%s | nuevo_index=%s",
                self.drag_item.get("filepath"),
                row,
                col,
                nuevo_index
            )

            self.items.remove(self.drag_item)
            self.items.insert(nuevo_index, self.drag_item)

            self.recolocar_items()

            self.items_dict = {
                item["filepath"]: {
                    "fila": idx // self.cols,
                    "columna": idx % self.cols,
                    "posicion": idx + 1
                }
                for idx, item in enumerate(self.items) if item.get("filepath")
            }

            self.guardar_ubicaciones()

            if self.drag_item:
                self.drag_item["frame"].config(
                    highlightbackground=self.ITEM_SELECTED,
                    highlightthickness=3,
                    bg=self.CARD_BG,
                )

            self.drag_item = None

        except Exception:
            logger.exception("Error al finalizar drag.")

    def mostrar_menu_contextual(self, event, filepath):
        try:
            logger.debug("Mostrando menú contextual | ruta=%s", filepath)
            menu = tk.Menu(self.canvas, tearoff=0)
            menu.add_command(label="Eliminar", command=lambda: self.eliminar_item(filepath))
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            logger.exception("Error al mostrar menú contextual | ruta=%s", filepath)

    def eliminar_item(self, filepath):
        try:
            logger.info("Eliminando item multimedia | ruta=%s", filepath)

            for item in self.items:
                if item["filepath"] == filepath:
                    self.canvas.delete(item["window_id"])
                    self.items.remove(item)
                    break

            if filepath in self.items_dict:
                del self.items_dict[filepath]

            self.recolocar_items()
            self.guardar_ubicaciones()
            self._eliminar_archivo_gestionado_si_no_se_usa(filepath)
            self.refrescar_biblioteca_metadata()
            self.actualizar_resumen_grupo()

            logger.debug("Item eliminado correctamente | total_items=%s", len(self.items))

        except Exception:
            logger.exception("Error al eliminar item | ruta=%s", filepath)

    def abrir_contenido(self, ruta):
        try:
            logger.info("Abriendo contenido multimedia | ruta=%s", ruta)
            if ruta.lower().endswith((".jpg", ".jpeg", ".png")):
                self.abrir_imagen(ruta)
            else:
                self.reproducir_video(ruta)
        except Exception:
            logger.exception("Error al abrir contenido | ruta=%s", ruta)

    def abrir_imagen(self, path):
        try:
            logger.debug("Abriendo imagen en toplevel | ruta=%s", path)
            top = ttk.Toplevel()
            top.title("Imagen")
            img = Image.open(path)
            img_tk = ImageTk.PhotoImage(img)
            label = tk.Label(top, image=img_tk)
            label.image = img_tk
            label.pack()
            top.focus_force()
        except Exception:
            logger.exception("Error al abrir imagen | ruta=%s", path)

    def reproducir_video(self, path):
        try:
            logger.debug("Abriendo video externo | ruta=%s", path)
            if os.name == "nt":
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            logger.exception("No se pudo abrir el video | ruta=%s", path)
            messagebox.showerror("Error", f"No se pudo abrir el archivo: {e}")

    def guardar_ubicaciones(self):
        try:
            if self._cargando_grupo:
                return
            logger.debug("Guardando ubicaciones de multimedia | cantidad=%s", len(self.items_dict))
            config = self.obtener_config()
            publicidades = self.asegurar_config_publicidades()
            grupo = publicidades["grupos"].setdefault(
                self.grupo_activo_id,
                {"nombre": self.grupo_activo_id, "items": {}},
            )
            grupo["items"] = dict(self.items_dict)
            config["ubicaciones"] = dict(self.items_dict)
            self.guardar_config_publicidades()
            self.refrescar_biblioteca_metadata()

        except Exception:
            logger.exception("Error al guardar ubicaciones.")

    def cargar_ubicaciones(self):
        try:
            self.refrescar_config_compartida()
            publicidades = self.asegurar_config_publicidades()
            grupo = publicidades["grupos"].get(self.grupo_activo_id, {})
            data = grupo.get("items", {})

            logger.info("Cargando ubicaciones guardadas | cantidad=%s", len(data))

            self._cargando_grupo = True
            for ruta, info in data.items():
                if os.path.exists(ruta):
                    self.agregar_item_multimedia(
                        "Multimedia",
                        ruta,
                        fila=info.get("fila"),
                        col=info.get("columna")
                    )
                else:
                    logger.warning("Ruta guardada no existe y se omite | ruta=%s", ruta)
            self._cargando_grupo = False
            self.items_dict = {
                item["filepath"]: {
                    "fila": idx // self.cols,
                    "columna": idx % self.cols,
                    "posicion": idx + 1,
                }
                for idx, item in enumerate(self.items) if item.get("filepath")
            }
            self.guardar_ubicaciones()
            self.refrescar_biblioteca_metadata(persistir=False)
            self._sincronizar_grilla_publicidad()

        except Exception:
            self._cargando_grupo = False
            logger.exception("Error al cargar ubicaciones guardadas.")

    def recalcular_y_cargar_ubicaciones(self):
        try:
            logger.debug("Recalculando y cargando ubicaciones.")
            self.canvas.update_idletasks()
            self.cargar_ubicaciones()
            self.redimensionar_celdas()
        except Exception:
            logger.exception("Error en recalcular_y_cargar_ubicaciones.")

    def enviar_multimedia(self):
        try:
            self.refrescar_biblioteca_metadata()
            items_envio = self.obtener_items_para_envio()
            if not items_envio:
                logger.warning("Se intentó enviar multimedia sin contenido.")
                messagebox.showinfo("Sin contenido", "No hay contenido para enviar.")
                return

            errores, advertencias = self.validar_items_publicidad(items_envio)
            if errores:
                messagebox.showerror(
                    "Validacion de publicidades",
                    "No se puede enviar hasta corregir estos errores:\n\n" + "\n".join(errores[:10]),
                )
                return
            if advertencias and not messagebox.askyesno(
                "Validacion de publicidades",
                "Se detectaron advertencias:\n\n"
                + "\n".join(advertencias[:8])
                + "\n\nDesea continuar igual?",
            ):
                return

            resumen_envio = self.construir_resumen_envio_publicidades(items_envio)
            if resumen_envio and not messagebox.askyesno(
                "Confirmar envio de publicidades",
                "Se enviaran los siguientes grupos:\n\n"
                + resumen_envio
                + "\n\nNota: en dispositivos de una sola pantalla se enviara solo el grupo activo."
                + "\n\nDesea continuar?",
            ):
                return

            logger.info("Iniciando envío de multimedia | cantidad_items=%s", len(items_envio))

            sender = DispositivoSender(
                self.widgets.get_widget("DATABASE", "CONEXIONDBA"),
                self.widgets.get_widget("GUI_MAIN", "ventana_creacion_caja"),
                tipos_descubrir=("infotv",),
            )
            urls = sender.seleccionar_dispositivos()

            logger.debug("Dispositivos seleccionados para envío | urls=%s", urls)

            if urls:
                sender.enviar_publicidades(
                    urls,
                    items_envio,
                    on_device_finished=lambda url, msg: self.registrar_resultado_envio_publicidades(
                        url,
                        msg,
                        items_envio,
                    ),
                )
                logger.info("Envío de publicidades lanzado correctamente.")
            else:
                logger.warning("No se seleccionaron dispositivos para enviar multimedia.")

        except Exception:
            logger.exception("Error al enviar multimedia.")

    def mostrar_preview_general(self):
        try:
            items_preview = self.obtener_items_para_envio()
            if not items_preview:
                logger.warning("Se intentó abrir preview general sin items.")
                messagebox.showinfo("Sin contenido", "No hay ítems para mostrar.")
                return

            logger.info("Abriendo preview general | cantidad_items=%s", len(items_preview))

            ventana = tk.Toplevel()
            ventana.title("Vista completa de publicidades")
            ventana.state("zoomed")
            ventana.resizable(False, False)
            ventana.grab_set()
            ventana.focus_force()

            canvas = tk.Canvas(ventana, bg="black")
            canvas.pack(fill="both", expand=True)

            ttk.Button(
                ventana,
                text="Iniciar presentación",
                command=lambda: self.iniciar_slideshow(items_preview)
            ).pack(pady=10)

            def render_items():
                try:
                    cell_w = 200
                    cell_h = 140
                    canvas_width = canvas.winfo_width()

                    cols = max(1, canvas_width // (cell_w + 20))
                    total_width = cols * cell_w
                    remaining_space = canvas_width - total_width
                    padding_x = remaining_space // (cols + 1)

                    logger.debug(
                        "Renderizando preview general | canvas_width=%s | cols=%s | items=%s",
                        canvas_width, cols, len(items_preview)
                    )

                    for idx, item in enumerate(items_preview):
                        fila, col = divmod(idx, cols)
                        x = padding_x + col * (cell_w + padding_x)
                        y = fila * (cell_h + 20) + 20

                        tipo = "video" if item["filepath"].lower().endswith((".mp4", ".avi", ".mov")) else "imagen"

                        try:
                            if tipo == "imagen":
                                img = Image.open(item["filepath"]).resize((cell_w, cell_h), Image.Resampling.LANCZOS)
                            else:
                                cap = cv2.VideoCapture(item["filepath"])
                                success, frame_img = cap.read()
                                cap.release()
                                if success:
                                    frame_img = cv2.cvtColor(frame_img, cv2.COLOR_BGR2RGB)
                                    img = Image.fromarray(frame_img).resize((cell_w, cell_h), Image.Resampling.LANCZOS)
                                    draw = ImageDraw.Draw(img)
                                    triangle = [
                                        (cell_w // 2 - 15, cell_h // 2 - 15),
                                        (cell_w // 2 - 15, cell_h // 2 + 15),
                                        (cell_w // 2 + 15, cell_h // 2)
                                    ]
                                    draw.polygon(triangle, fill="white")
                                else:
                                    logger.warning(
                                        "No se pudo obtener frame para preview general | ruta=%s",
                                        item["filepath"]
                                    )
                                    img = Image.new("RGB", (cell_w, cell_h), color="gray")

                            img_tk = ImageTk.PhotoImage(img)
                            label = tk.Label(canvas, image=img_tk)
                            label.image = img_tk
                            canvas.create_window(x, y, anchor="nw", window=label)

                        except Exception:
                            logger.exception("Error renderizando item en preview general | ruta=%s", item["filepath"])

                except Exception:
                    logger.exception("Error general en render_items del preview general.")

            ventana.after(100, render_items)

        except Exception:
            logger.exception("Error al mostrar preview general.")

    def iniciar_slideshow(self, items):
        try:
            if not items:
                logger.warning("Se intentó iniciar slideshow sin items.")
                return

            logger.info("Iniciando slideshow | cantidad_items=%s", len(items))

            slideshow = tk.Toplevel()
            slideshow.attributes("-fullscreen", True)
            slideshow.configure(background="black")
            slideshow.focus_set()
            slideshow.lift()
            slideshow.attributes("-topmost", True)

            instance = vlc.Instance()
            player = instance.media_player_new()

            def cerrar_slideshow(event=None):
                logger.info("Cerrando slideshow.")
                try:
                    player.stop()
                except Exception:
                    logger.exception("Error al detener player VLC al cerrar slideshow.")
                if slideshow.winfo_exists():
                    slideshow.destroy()

            slideshow.bind_all("<Escape>", cerrar_slideshow)
            slideshow.focus_force()

            label = tk.Label(slideshow, bg="black")
            label.pack(expand=True, fill="both")

            cartel_esc = tk.Label(
                slideshow,
                text="Presione ESC para salir",
                font=("Segoe UI", 12, "bold"),
                fg="white",
                bg="black",
                anchor="se"
            )
            cartel_esc.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

            index = [0]

            def mostrar_siguiente():
                try:
                    if index[0] >= len(items):
                        logger.info("Slideshow finalizado.")
                        player.stop()
                        slideshow.destroy()
                        return

                    filepath = items[index[0]]["filepath"]
                    tipo = "video" if filepath.lower().endswith((".mp4", ".avi", ".mov", ".mkv")) else "imagen"

                    logger.debug(
                        "Mostrando item slideshow | index=%s | ruta=%s | tipo=%s",
                        index[0], filepath, tipo
                    )

                    if tipo == "imagen":
                        player.stop()
                        img = Image.open(filepath)
                        original_width, original_height = img.size

                        screen_w = slideshow.winfo_screenwidth()
                        screen_h = slideshow.winfo_screenheight()

                        ratio = min(screen_w / original_width, screen_h / original_height)
                        new_width = int(original_width * ratio)
                        new_height = int(original_height * ratio)
                        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                        if filepath.lower().endswith(".png") and img.mode in ("RGBA", "LA"):
                            rgba_data = img.convert("RGBA").getdata()
                            opaque_pixels = [pixel[:3] for pixel in rgba_data if pixel[3] > 128]
                            if opaque_pixels:
                                avg = tuple(sum(c) // len(c) for c in zip(*opaque_pixels))
                                contrast_color = tuple(255 - c for c in avg)
                            else:
                                contrast_color = (0, 0, 0)
                        else:
                            small = img.convert("RGB").resize((50, 50))
                            pixels = list(small.getdata())
                            freq = {}
                            for px in pixels:
                                freq[px] = freq.get(px, 0) + 1
                            contrast_color = max(freq, key=freq.get)

                        fondo = Image.new("RGB", (screen_w, screen_h), color=contrast_color)
                        pos_x = (screen_w - new_width) // 2
                        pos_y = (screen_h - new_height) // 2
                        if img_resized.mode == "RGBA":
                            fondo = fondo.convert("RGBA")
                            fondo.paste(img_resized, (pos_x, pos_y), mask=img_resized)
                        else:
                            fondo.paste(img_resized, (pos_x, pos_y))

                        img_tk = ImageTk.PhotoImage(fondo.convert("RGB"))
                        label.config(image=img_tk, bg="#000000")
                        label.image = img_tk

                        index[0] += 1
                        slideshow.after(3000, mostrar_siguiente)

                    else:
                        label.config(image=None)
                        label.image = None
                        slideshow.update_idletasks()

                        video_widget_id = label.winfo_id()
                        player.set_hwnd(video_widget_id)
                        media = instance.media_new(filepath)
                        player.set_media(media)

                        def revisar_estado():
                            try:
                                state = player.get_state()
                                if state in (vlc.State.Ended, vlc.State.Error):
                                    logger.debug(
                                        "Video finalizado o con error en slideshow | ruta=%s | state=%s",
                                        filepath, state
                                    )
                                    index[0] += 1
                                    mostrar_siguiente()
                                else:
                                    slideshow.after(500, revisar_estado)
                            except Exception:
                                logger.exception("Error revisando estado de VLC en slideshow | ruta=%s", filepath)

                        player.play()
                        revisar_estado()

                except Exception:
                    logger.exception("Error en mostrar_siguiente del slideshow.")

            mostrar_siguiente()

        except Exception:
            logger.exception("Error al iniciar slideshow.")

    def abrir_panel_de_control(self):
        try:
            if not self.items:
                logger.warning("Se intentó abrir panel de control sin items.")
                messagebox.showinfo("Sin contenido", "No hay ítems para mostrar.")
                return

            logger.info("Abriendo panel de control | cantidad_items=%s", len(self.items))

            top = tk.Toplevel()

            cuadro_w = 110
            cuadro_h = 80
            espacio_x = 10
            espacio_y = 10

            try:
                check_tk = READ_IMG(PNG_Check(), 32, 32)
                logger.debug("Imagen de check cargada correctamente para panel de control.")
            except Exception:
                logger.exception("No se pudo cargar imagen de check para panel de control.")
                check_tk = None

            try:
                overlay_img = Image.new("RGBA", (cuadro_w, cuadro_h), (0, 0, 0, 100))
                overlay_tk = ImageTk.PhotoImage(overlay_img)
            except Exception:
                logger.exception("Error creando overlay para panel de control.")
                overlay_tk = None

            top.title("Panel de control de multimedia")

            max_ancho = top.winfo_screenwidth() - 100
            total_items = len(self.items)

            columnas = max(1, min(total_items, max_ancho // (cuadro_w + espacio_x)))
            filas = (total_items + columnas - 1) // columnas

            ancho_ventana = columnas * (cuadro_w + espacio_x) + 40
            alto_ventana = min(filas * (cuadro_h + espacio_y) + 500, top.winfo_screenheight() - 100)

            self.centrar_ventana(top, ancho_ventana, alto_ventana)

            top.grab_set()

            seleccionados = set()

            marco = ttk.Frame(top)
            marco.pack(expand=True, fill="both", padx=10, pady=10)

            canvas = tk.Canvas(marco)
            scrollbar = ttk.Scrollbar(marco, orient="vertical", command=canvas.yview)
            frame_scroll = ttk.Frame(canvas)

            frame_scroll.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=frame_scroll, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            frame_scroll.config(width=ancho_ventana, height=alto_ventana - 80)
            imagenes_originales = {}
            imagenes_tk = {}
            tilde_labels = {}

            for idx, item in enumerate(self.items):
                fila = idx // columnas
                col = idx % columnas

                tipo = "video" if item["filepath"].lower().endswith((".mp4", ".avi", ".mov", ".mkv")) else "imagen"

                frame = tk.Frame(
                    frame_scroll,
                    width=cuadro_w,
                    height=cuadro_h,
                    relief="ridge",
                    borderwidth=2,
                    bg="#f0f0f0"
                )
                x_offset = espacio_x + col * (cuadro_w + espacio_x)
                y_offset = fila * (cuadro_h + espacio_y)
                frame.place(x=x_offset, y=y_offset)

                try:
                    if tipo == "imagen":
                        img = Image.open(item["filepath"])
                    else:
                        cap = cv2.VideoCapture(item["filepath"])
                        success, frame_img = cap.read()
                        cap.release()
                        if success:
                            frame_img = cv2.cvtColor(frame_img, cv2.COLOR_BGR2RGB)
                            img = Image.fromarray(frame_img)
                        else:
                            logger.warning("No se pudo obtener frame para panel de control | ruta=%s", item["filepath"])
                            img = Image.new("RGB", (cuadro_w, cuadro_h), color="gray")

                    img = img.resize((cuadro_w, cuadro_h), Image.Resampling.LANCZOS)

                    if tipo == "video":
                        draw = ImageDraw.Draw(img)
                        triangle = [
                            (cuadro_w // 2 - 8, cuadro_h // 2 - 10),
                            (cuadro_w // 2 - 8, cuadro_h // 2 + 10),
                            (cuadro_w // 2 + 10, cuadro_h // 2)
                        ]
                        draw.polygon(triangle, fill="white")

                    imagenes_originales[idx] = img

                    img_tk = ImageTk.PhotoImage(img)
                    imagenes_tk[idx] = img_tk

                    label = tk.Label(frame, image=img_tk, bg="#000000")
                    label.image = img_tk
                    label.pack(expand=True, fill="both")

                    overlay = tk.Label(frame, image=overlay_tk, bd=0)
                    overlay.image = overlay_tk
                    overlay.place(x=0, y=0)
                    overlay.place_forget()

                    tilde = None
                    if check_tk:
                        tilde = tk.Label(frame, image=check_tk, bg="#000000", bd=0)
                        tilde.image = check_tk
                        tilde.place(relx=1.0, rely=0.0, anchor="ne", x=-6, y=6)
                        tilde.place_forget()
                    tilde_labels[idx] = tilde

                except Exception:
                    logger.exception("Error cargando preview del panel de control | ruta=%s", item["filepath"])
                    label = tk.Label(frame, text=f"{idx+1}\n{tipo}", justify="center", bg="#f0f0f0")
                    label.pack(expand=True, fill="both")

                def toggle_select(event, i=idx, lbl=label):
                    try:
                        if i in seleccionados:
                            seleccionados.remove(i)
                            lbl.config(image=imagenes_tk[i])
                            lbl.image = imagenes_tk[i]
                            if tilde_labels[i]:
                                tilde_labels[i].place_forget()
                        else:
                            seleccionados.add(i)

                            base_img = imagenes_originales[i].convert("RGBA")
                            overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 100))
                            img_modificada = Image.alpha_composite(base_img, overlay).convert("RGB")

                            img_tk_modificada = ImageTk.PhotoImage(img_modificada)
                            lbl.config(image=img_tk_modificada)
                            lbl.image = img_tk_modificada

                            if tilde_labels[i]:
                                tilde_labels[i].place(relx=1.0, rely=0.0, anchor="ne", x=-6, y=6)

                        logger.debug("Selección panel de control actualizada | seleccionados=%s", len(seleccionados))

                    except Exception:
                        logger.exception("Error al alternar selección en panel de control | index=%s", i)

                frame.bind("<Button-1>", toggle_select)
                label.bind("<Button-1>", toggle_select)

            def eliminar_seleccionados():
                try:
                    if not seleccionados:
                        logger.warning("Se intentó eliminar seleccionados sin selección.")
                        messagebox.showinfo("Nada seleccionado", "No seleccionaste ningún ítem.")
                        return

                    if not messagebox.askyesno("Confirmación", f"¿Eliminar {len(seleccionados)} ítems seleccionados?"):
                        logger.info("Eliminación de seleccionados cancelada por usuario.")
                        return

                    logger.info("Eliminando items seleccionados | cantidad=%s", len(seleccionados))

                    nuevos_items = []
                    nuevos_dict = {}
                    eliminadas = []
                    for i, item in enumerate(self.items):
                        if i not in seleccionados:
                            nuevos_items.append(item)
                            nuevos_dict[item["filepath"]] = self.items_dict[item["filepath"]]
                        else:
                            self.canvas.delete(item["window_id"])
                            eliminadas.append(item["filepath"])

                    self.items = nuevos_items
                    self.items_dict = nuevos_dict
                    self.recolocar_items()
                    self.guardar_ubicaciones()
                    for ruta in eliminadas:
                        self._eliminar_archivo_gestionado_si_no_se_usa(ruta)
                    self.refrescar_biblioteca_metadata()
                    top.destroy()

                except Exception:
                    logger.exception("Error al eliminar seleccionados en panel de control.")

            def eliminar_por_tipo(tipo_objetivo):
                try:
                    if not messagebox.askyesno("Confirmación", f"¿Eliminar todos los archivos tipo {tipo_objetivo}?"):
                        logger.info("Eliminación por tipo cancelada | tipo=%s", tipo_objetivo)
                        return

                    logger.info("Eliminando items por tipo | tipo=%s", tipo_objetivo)

                    nuevos_items = []
                    nuevos_dict = {}
                    eliminadas = []
                    for item in self.items:
                        tipo = "video" if item["filepath"].lower().endswith((".mp4", ".avi", ".mov", ".mkv")) else "imagen"
                        if tipo != tipo_objetivo:
                            nuevos_items.append(item)
                            nuevos_dict[item["filepath"]] = self.items_dict[item["filepath"]]
                        else:
                            self.canvas.delete(item["window_id"])
                            eliminadas.append(item["filepath"])

                    self.items = nuevos_items
                    self.items_dict = nuevos_dict
                    self.recolocar_items()
                    self.guardar_ubicaciones()
                    for ruta in eliminadas:
                        self._eliminar_archivo_gestionado_si_no_se_usa(ruta)
                    self.refrescar_biblioteca_metadata()
                    top.destroy()

                except Exception:
                    logger.exception("Error al eliminar items por tipo | tipo=%s", tipo_objetivo)

            marco_botones = ttk.Frame(top)
            marco_botones.pack(pady=10)

            ttk.Button(
                marco_botones,
                text="🗑 Eliminar seleccionados",
                command=eliminar_seleccionados
            ).pack(side="left", padx=5)

            ttk.Button(
                marco_botones,
                text="🟦 Eliminar videos",
                command=lambda: eliminar_por_tipo("video")
            ).pack(side="left", padx=5)

            ttk.Button(
                marco_botones,
                text="🖼 Eliminar imágenes",
                command=lambda: eliminar_por_tipo("imagen")
            ).pack(side="left", padx=5)

        except Exception:
            logger.exception("Error al abrir panel de control.")

    def _obtener_dispositivos_registrados(self):
        try:
            conexion = self.widgets.get_widget("DATABASE", "CONEXIONDBA")
            rows = conexion.ejecutar_consulta(
                "SELECT nombre, direccion_conexion, puerto FROM VERIPRE_EQUIPOS ORDER BY nombre"
            )
        except Exception:
            logger.exception("Error obteniendo dispositivos registrados para multipantalla.")
            return []

        dispositivos = []
        for nombre, direccion, puerto in rows or []:
            direccion = str(direccion or "").strip()
            if not direccion:
                continue

            try:
                puerto_int = int(puerto or 2727)
            except Exception:
                puerto_int = 2727

            dispositivos.append(
                {
                    "nombre": str(nombre or direccion).strip() or direccion,
                    "host": direccion,
                    "puerto": puerto_int,
                    "base_url": f"http://{direccion}:{puerto_int}",
                    "device_key": f"{direccion}:{puerto_int}",
                }
            )

        return dispositivos

    def _device_key_desde_url(self, url):
        try:
            base_url = str(url).split("/api")[0].rstrip("/")
            return base_url.split("://", 1)[-1]
        except Exception:
            return str(url)

    def _obtener_config_multipantalla_dispositivo(self, device_key):
        publicidades = self.asegurar_config_publicidades()
        return publicidades.setdefault("multipantalla_dispositivos", {}).get(device_key, {})

    def _normalizar_grupos_multipantalla(self, config_multi):
        grupos_multi = list(config_multi.get("grupos") or [])
        if grupos_multi:
            return grupos_multi

        pantallas = config_multi.get("pantallas") or {}
        grupos_migrados = []
        for pantalla_key in sorted(pantallas, key=lambda value: int(str(value)) if str(value).isdigit() else 999):
            data = pantallas.get(pantalla_key) or {}
            grupo_id = data.get("grupo_id")
            if not grupo_id:
                continue
            try:
                pantalla_idx = int(pantalla_key)
            except Exception:
                pantalla_idx = 0
            destino = "pantalla_1" if pantalla_idx == 0 else "pantalla_2"
            grupos_migrados.append({"grupo_id": grupo_id, "destino": destino})
        return grupos_migrados

    def _construir_items_envio_desde_grupos(self, grupos_asignados):
        self.refrescar_biblioteca_metadata(persistir=False)
        publicidades = self.asegurar_config_publicidades()
        grupos = publicidades.get("grupos", {})
        items_envio = []
        omitidas = []

        for group_id, display_index in grupos_asignados:
            grupo = grupos.get(group_id)
            if not grupo:
                continue

            nombre_grupo = grupo.get("nombre", group_id)
            rutas = []
            vistos = set()

            for ruta, _info in self.obtener_globales_ordenadas():
                if ruta not in vistos:
                    rutas.append(ruta)
                    vistos.add(ruta)

            items_grupo = grupo.get("items", {})
            rutas_grupo_ordenadas = sorted(
                items_grupo.items(),
                key=lambda item: (item[1].get("posicion", 999999), item[0]),
            )

            for ruta, _info in rutas_grupo_ordenadas:
                if ruta not in vistos:
                    rutas.append(ruta)
                    vistos.add(ruta)

            base_index = len(items_envio)
            offset = 0
            for ruta in rutas:
                if not os.path.exists(ruta):
                    omitidas.append(ruta)
                    continue

                item_envio = {
                    "filepath": ruta,
                    "grid": divmod(base_index + offset, self.cols),
                    "grupo": nombre_grupo,
                    "grupo_id": group_id,
                    "grupo_activo": group_id == self.grupo_activo_id,
                }
                if display_index is not None:
                    item_envio["display_index"] = int(display_index)

                items_envio.append(item_envio)
                offset += 1

        if omitidas:
            logger.warning("Publicidades omitidas por ruta inexistente | cantidad=%s", len(omitidas))

        return items_envio

    def asegurar_config_publicidades(self):
        config = self.obtener_config()
        publicidades = config.get("publicidades")

        if isinstance(publicidades, dict) and publicidades.get("grupos"):
            publicidades.setdefault("grupo_activo", next(iter(publicidades["grupos"])))
            publicidades.setdefault("globales", {})
            publicidades.setdefault("biblioteca", {})
            publicidades.setdefault("historial_envios", [])
            publicidades.setdefault("multipantalla_dispositivos", {})

            for group_id, grupo in publicidades.get("grupos", {}).items():
                grupo.setdefault("nombre", group_id)
                grupo.setdefault("items", {})
                grupo.setdefault("usar_display_index", False)
                grupo.setdefault("display_index", 0)

            self.grupo_activo_id = publicidades["grupo_activo"]
            return publicidades

        ubicaciones_legacy = config.get("ubicaciones", {})
        publicidades = {
            "grupo_activo": "default",
            "grupos": {
                "default": {
                    "nombre": "General",
                    "items": dict(ubicaciones_legacy) if isinstance(ubicaciones_legacy, dict) else {},
                    "usar_display_index": False,
                    "display_index": 0,
                }
            },
            "globales": {},
            "biblioteca": {},
            "historial_envios": [],
            "multipantalla_dispositivos": {},
        }
        config["publicidades"] = publicidades
        self.grupo_activo_id = "default"
        guardar_config(config)
        return publicidades

    def actualizar_resumen_grupo(self):
        try:
            self.refrescar_biblioteca_metadata(persistir=False)
            publicidades = self.asegurar_config_publicidades()
            grupo = publicidades["grupos"].get(self.grupo_activo_id, {})
            nombre = grupo.get("nombre", self.grupo_activo_id)
            total_grupo = len(self.items)
            total_globales = len(publicidades.get("globales", {}))
            total_envio = len(self.obtener_items_para_envio())
            pendientes = sum(1 for meta in self.biblioteca_metadata.values() if meta.get("cambios_pendientes"))

            self.lbl_resumen_grupo.configure(
                text=(
                    f"Grupo: {nombre} | Multipantalla por dispositivo | "
                    f"{total_grupo} del grupo | {total_globales} globales | "
                    f"{total_envio} al enviar | {pendientes} pendientes"
                )
            )
        except Exception:
            logger.exception("Error actualizando resumen de grupo.")

    def abrir_config_multipantalla(self):
        try:
            publicidades = self.asegurar_config_publicidades()
            grupos = publicidades.get("grupos", {})
            dispositivos = self._obtener_dispositivos_registrados()

            if not dispositivos:
                messagebox.showwarning("Multipantalla", "No hay dispositivos registrados.")
                return

            top = ttk.Toplevel(self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad"))
            top.title("Configuracion multipantalla")
            fit_toplevel_to_workarea(top, 760, 520, min_width=700, min_height=460)
            top.place_window_center()
            top.grab_set()

            frame_general = ttk.Frame(top, padding=15)
            frame_general.pack(fill="both", expand=True)

            ttk.Label(
                frame_general,
                text="Asignacion de grupos por dispositivo y pantalla",
                font=("Segoe UI", 12, "bold"),
            ).pack(anchor="w", pady=(0, 10))

            frame_selector = ttk.Frame(frame_general)
            frame_selector.pack(fill="x", pady=(0, 10))

            ttk.Label(frame_selector, text="Dispositivo:").pack(side="left")
            dispositivos_map = {disp["nombre"]: disp for disp in dispositivos}
            nombres_dispositivos = list(dispositivos_map.keys())
            dispositivo_var = ttk.StringVar(value=nombres_dispositivos[0])
            combo_dispositivo = ttk.Combobox(
                frame_selector,
                textvariable=dispositivo_var,
                values=nombres_dispositivos,
                state="readonly",
                width=36,
            )
            combo_dispositivo.pack(side="left", padx=(8, 10))

            btn_consultar = ttk.Button(frame_selector, text="Consultar player")
            btn_consultar.pack(side="left")

            estado_var = ttk.StringVar(value="Seleccione un dispositivo y consulte su player.")
            ttk.Label(frame_general, textvariable=estado_var, bootstyle="secondary").pack(anchor="w", pady=(0, 10))

            enabled_var = ttk.BooleanVar(value=False)
            ttk.Checkbutton(
                frame_general,
                text="Activar multipantalla para este dispositivo",
                variable=enabled_var,
            ).pack(anchor="w", pady=(0, 10))

            frame_grupos_multi = ttk.LabelFrame(frame_general, text="Grupos a enviar", padding=10)
            frame_grupos_multi.pack(fill="both", expand=True, pady=(0, 10))

            frame_header = ttk.Frame(frame_grupos_multi)
            frame_header.pack(fill="x", pady=(0, 6))
            ttk.Label(frame_header, text="Grupo", width=34).pack(side="left")
            ttk.Label(frame_header, text="Destino", width=18).pack(side="left", padx=(10, 0))

            frame_rows = ttk.Frame(frame_grupos_multi)
            frame_rows.pack(fill="both", expand=True)

            frame_add = ttk.Frame(frame_general)
            frame_add.pack(fill="x", pady=(0, 10))

            filas_grupos = []
            player_state = {"count": 2}
            grupos_map = {grupo_id: data.get("nombre", grupo_id) for grupo_id, data in grupos.items()}
            valores_grupos = [f"{grupo_id} | {grupos_map[grupo_id]}" for grupo_id in grupos]
            valores_destino = ["ambas | Ambas", "pantalla_1 | Pantalla 1", "pantalla_2 | Pantalla 2"]

            def _renderizar_hint_player():
                cantidad = max(1, int(player_state.get("count", 2) or 2))
                if cantidad <= 1:
                    estado_var.set("El dispositivo informa una sola pantalla. 'Ambas' se tratara como envio normal.")
                else:
                    estado_var.set(
                        f"El dispositivo se trabajara con {cantidad} pantalla(s). "
                        "Por defecto cada grupo nuevo se agrega en Ambas."
                    )

            def _agregar_fila(grupo_id="", destino="ambas"):
                fila = ttk.Frame(frame_rows)
                fila.pack(fill="x", pady=3)

                grupo_var = ttk.StringVar()
                if grupo_id and grupo_id in grupos_map:
                    grupo_var.set(f"{grupo_id} | {grupos_map[grupo_id]}")

                destino_var = ttk.StringVar()
                destino_var.set(
                    "ambas | Ambas"
                    if destino == "ambas"
                    else "pantalla_1 | Pantalla 1"
                    if destino == "pantalla_1"
                    else "pantalla_2 | Pantalla 2"
                )

                combo_grupo = ttk.Combobox(fila, textvariable=grupo_var, state="readonly", values=valores_grupos, width=34)
                combo_grupo.pack(side="left")
                combo_destino = ttk.Combobox(
                    fila,
                    textvariable=destino_var,
                    state="readonly",
                    values=valores_destino,
                    width=18,
                )
                combo_destino.pack(side="left", padx=(10, 0))

                btn_quitar = ttk.Button(fila, text="Quitar", bootstyle="secondary", width=10)
                btn_quitar.pack(side="left", padx=(10, 0))

                row_data = {
                    "frame": fila,
                    "grupo_var": grupo_var,
                    "destino_var": destino_var,
                }

                def quitar():
                    try:
                        fila.destroy()
                    finally:
                        if row_data in filas_grupos:
                            filas_grupos.remove(row_data)
                        if not filas_grupos:
                            _agregar_fila()

                btn_quitar.configure(command=quitar)
                filas_grupos.append(row_data)

            def _aplicar_config_guardada():
                disp = dispositivos_map.get(dispositivo_var.get())
                if not disp:
                    return
                config_actual = self._obtener_config_multipantalla_dispositivo(disp["device_key"])
                enabled_var.set(bool(config_actual.get("enabled", False)))
                for row in list(filas_grupos):
                    try:
                        row["frame"].destroy()
                    except Exception:
                        pass
                filas_grupos.clear()

                grupos_multi = self._normalizar_grupos_multipantalla(config_actual)
                if not grupos_multi:
                    _agregar_fila()
                    return

                for data in grupos_multi:
                    _agregar_fila(data.get("grupo_id", ""), data.get("destino", "ambas"))

            def consultar_player():
                disp = dispositivos_map.get(dispositivo_var.get())
                if not disp:
                    return

                estado_var.set(f"Consultando player de {disp['nombre']}...")
                btn_consultar.config(state="disabled")

                def tarea():
                    client = DispositivoAPIClient(disp["base_url"])
                    config_player = client.get_player_configuration(timeout=5)

                    def aplicar():
                        btn_consultar.config(state="normal")
                        pantallas_detectadas = []
                        if isinstance(config_player, dict):
                            pantallas_detectadas = config_player.get("pantallas_detectadas") or []

                        cantidad = len(pantallas_detectadas) if pantallas_detectadas else 2
                        player_state["count"] = max(1, cantidad)
                        _renderizar_hint_player()

                        if pantallas_detectadas:
                            estado_var.set(
                                f"{disp['nombre']}: player disponible, {len(pantallas_detectadas)} pantalla(s) detectada(s)."
                            )
                        else:
                            estado_var.set(
                                f"{disp['nombre']}: sin detalle de pantallas; se asumiran 2 por defecto."
                            )

                    top.after(0, aplicar)

                threading.Thread(target=tarea, daemon=True).start()

            def al_cambiar_dispositivo(_event=None):
                disp = dispositivos_map.get(dispositivo_var.get())
                if not disp:
                    return
                _aplicar_config_guardada()
                estado_var.set(f"Dispositivo seleccionado: {disp['nombre']}.")
                _renderizar_hint_player()

            def guardar():
                disp = dispositivos_map.get(dispositivo_var.get())
                if not disp:
                    messagebox.showwarning("Multipantalla", "Seleccione un dispositivo.")
                    return

                grupos_multi = []
                for row in filas_grupos:
                    value = row["grupo_var"].get().strip()
                    if not value:
                        continue
                    grupo_id = value.split(" | ", 1)[0].strip()
                    if grupo_id not in grupos:
                        continue

                    destino_value = row["destino_var"].get().strip() or "ambas | Ambas"
                    destino = destino_value.split(" | ", 1)[0].strip()
                    if destino not in {"ambas", "pantalla_1", "pantalla_2"}:
                        destino = "ambas"

                    grupos_multi.append({"grupo_id": grupo_id, "destino": destino})

                publicidades["multipantalla_dispositivos"][disp["device_key"]] = {
                    "enabled": bool(enabled_var.get()),
                    "device_name": disp["nombre"],
                    "grupos": grupos_multi,
                }
                self.guardar_config_publicidades()
                self.actualizar_resumen_grupo()
                top.destroy()

            ttk.Button(
                frame_add,
                text="Agregar grupo",
                command=lambda: _agregar_fila("", "ambas"),
                bootstyle="secondary",
            ).pack(side="left")

            acciones = ttk.Frame(frame_general)
            acciones.pack(fill="x", pady=(10, 0))
            ttk.Button(acciones, text="Guardar", command=guardar, bootstyle="success").pack(side="left")
            ttk.Button(acciones, text="Cancelar", command=top.destroy).pack(side="right")

            combo_dispositivo.bind("<<ComboboxSelected>>", al_cambiar_dispositivo)
            btn_consultar.configure(command=consultar_player)
            _aplicar_config_guardada()
            _renderizar_hint_player()

        except Exception:
            logger.exception("Error abriendo configuracion multipantalla.")

    def obtener_items_para_envio(self):
        return self._construir_items_envio_desde_grupos([(self.grupo_activo_id, None)])

    def obtener_items_para_envio_para_dispositivo(self, url, nombre_dispositivo=None):
        device_key = self._device_key_desde_url(url)
        config_multi = self._obtener_config_multipantalla_dispositivo(device_key)

        if config_multi.get("enabled"):
            grupos_asignados = []
            for data in self._normalizar_grupos_multipantalla(config_multi):
                grupo_id = data.get("grupo_id")
                destino = data.get("destino", "ambas")
                if not grupo_id:
                    continue

                if destino == "pantalla_1":
                    grupos_asignados.append((grupo_id, 0))
                elif destino == "pantalla_2":
                    grupos_asignados.append((grupo_id, 1))
                else:
                    grupos_asignados.append((grupo_id, 0))
                    grupos_asignados.append((grupo_id, 1))

            if grupos_asignados:
                logger.info(
                    "Usando configuracion multipantalla por dispositivo | dispositivo=%s | key=%s | asignaciones=%s",
                    nombre_dispositivo or device_key,
                    device_key,
                    len(grupos_asignados),
                )
                return self._construir_items_envio_desde_grupos(grupos_asignados)

        return self.obtener_items_para_envio()

    def enviar_multimedia(self):
        try:
            self.refrescar_config_compartida()
            self.refrescar_biblioteca_metadata(persistir=False)
            sender = DispositivoSender(
                self.widgets.get_widget("DATABASE", "CONEXIONDBA"),
                self.widgets.get_widget("GUI_MAIN", "ventana_creacion_caja"),
                tipos_descubrir=("infotv",),
            )
            urls = sender.seleccionar_dispositivos()

            logger.debug("Dispositivos seleccionados para envio | urls=%s", urls)

            if not urls:
                logger.warning("No se seleccionaron dispositivos para enviar multimedia.")
                return

            items_por_url = {}
            items_validacion = []
            resumenes_por_dispositivo = []

            for url in urls:
                nombre_dispositivo = sender.url_a_nombre.get(url, url)
                items_dispositivo = self.obtener_items_para_envio_para_dispositivo(url, nombre_dispositivo)
                if not items_dispositivo:
                    continue

                items_por_url[url] = items_dispositivo
                items_validacion.extend(items_dispositivo)
                resumen = self.construir_resumen_envio_publicidades(items_dispositivo)
                if resumen:
                    resumenes_por_dispositivo.append(f"{nombre_dispositivo}:\n{resumen}")

            if not items_por_url:
                logger.warning("Se intento enviar multimedia sin contenido efectivo.")
                messagebox.showinfo("Sin contenido", "No hay contenido para enviar a los dispositivos seleccionados.")
                return

            errores, advertencias = self.validar_items_publicidad(items_validacion)
            if errores:
                messagebox.showerror(
                    "Validacion de publicidades",
                    "No se puede enviar hasta corregir estos errores:\n\n" + "\n".join(errores[:10]),
                )
                return

            if advertencias and not messagebox.askyesno(
                "Validacion de publicidades",
                "Se detectaron advertencias:\n\n"
                + "\n".join(advertencias[:8])
                + "\n\nDesea continuar igual?",
            ):
                return

            resumen_envio = "\n\n".join(resumenes_por_dispositivo)
            if resumen_envio and not messagebox.askyesno(
                "Confirmar envio de publicidades",
                "Se enviara lo siguiente por dispositivo:\n\n"
                + resumen_envio
                + "\n\nSi el player tiene dos pantallas y no esta configurado, repetira el grupo activo en ambas."
                + "\n\nDesea continuar?",
            ):
                return

            total_items = sum(len(items) for items in items_por_url.values())
            logger.info(
                "Iniciando envio de multimedia | dispositivos=%s | total_items=%s",
                len(items_por_url),
                total_items,
            )

            sender.enviar_publicidades(
                list(items_por_url.keys()),
                lambda url: items_por_url.get(url, []),
                on_device_finished=lambda url, msg: self.registrar_resultado_envio_publicidades(
                    url,
                    msg,
                    items_por_url.get(url, []),
                ),
            )
            logger.info("Envio de publicidades lanzado correctamente.")

        except Exception:
            logger.exception("Error al enviar multimedia.")

    def centrar_ventana(self, ventana, ancho, alto):
        try:
            center_toplevel_in_workarea(ventana, ancho, alto)
            logger.debug("Ventana centrada | ancho=%s | alto=%s", ancho, alto)
        except Exception:
            logger.exception("Error al centrar ventana.")

    def abrir_generador_ofertas(self):
        try:
            logger.info("Abriendo generador de ofertas.")
            sybase_conn = self.widgets.get_widget("DATABASE", "CONEXIONDBA_SYBASE")

            if not sybase_conn:
                logger.error("No hay conexión Sybase disponible para abrir generador de ofertas.")
                messagebox.showerror("Error", "No hay conexión Sybase disponible.")
                return

            def on_paths(paths):
                try:
                    logger.info("Imágenes generadas recibidas desde generador de ofertas | cantidad=%s", len(paths))
                    for p in paths:
                        if os.path.exists(p):
                            logger.debug("Agregando imagen generada desde ofertas | ruta=%s", p)
                            self.agregar_item_multimedia(os.path.basename(p), p)
                        else:
                            logger.warning("Ruta generada por ofertas no existe | ruta=%s", p)
                except Exception:
                    logger.exception("Error en callback on_paths de generador de ofertas.")

            GeneradorOfertasToplevel(
                master=self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad").winfo_toplevel(),
                sybase_conn=sybase_conn,
                on_imagenes_generadas=on_paths,
                output_dir="OUTPUT/ofertas"
            )

            logger.debug("GeneradorOfertasToplevel abierto correctamente.")

        except Exception:
            logger.exception("Error al abrir generador de ofertas.")
