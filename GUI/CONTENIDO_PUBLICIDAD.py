import os
import cv2
import tkinter as tk
import ttkbootstrap as ttk
import vlc
import time
from tkinter import filedialog
from tkinter import filedialog, messagebox
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
from PIL import Image, ImageTk, ImageDraw

from ASSETS.path_img import READ_IMG, PNG_Check
from core.network.dispositivo_sender import DispositivoSender
from GUI.OFERTAS_GENERADOR import GeneradorOfertasToplevel
from core.logging.logger import get_logger

# from core.network.selector_envio_dispositivos import EnvioDispositivos

logger = get_logger(__name__)

CELL_HEIGHT = 170  # Hacemos más rectangular
PADDING = 0        # margen interno del canvas
ITEM_MARGIN = 5    # margen entre ítems

CELL_HEIGHT = 170
PADDING = 0
ITEM_MARGIN = 5


class ContenidoPublicidad:
    def __init__(self, widgets):
        logger.info("Inicializando ContenidoPublicidad.")

        self.widgets = widgets
        self.items_dict = {}
        self.items = []
        self.drag_item = None
        self.item_seleccionado = None
        self._clic_pos = None

        self.cols = 4
        self.rows = 2
        self.cell_width = 240

        self.setup_gui()

    def setup_gui(self):
        logger.debug("Construyendo interfaz de ContenidoPublicidad.")

        frame_principal = self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad")
        self.contenedor_general = ttk.Frame(frame_principal)
        self.contenedor_general.pack(fill="both", expand=True)

        self.frame_botones = ttk.Frame(self.contenedor_general)
        self.frame_botones.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Button(self.frame_botones, text="Agregar Multimedia", command=self.agregar_multimedia).pack(side="left")
        ttk.Button(self.frame_botones, text="Enviar", command=self.enviar_multimedia).pack(side="left", padx=(5, 0))
        ttk.Button(self.frame_botones, text="Vista Completa", command=self.mostrar_preview_general).pack(side="left", padx=(5, 0))
        ttk.Button(self.frame_botones, text="Panel de control", command=self.abrir_panel_de_control).pack(side="left", padx=(5, 0))
        ttk.Button(self.frame_botones, text="Ofertas", command=self.abrir_generador_ofertas).pack(side="left", padx=(5, 0))

        self.contenedor = ttk.Frame(self.contenedor_general)
        self.contenedor.pack(fill="both", expand=True, padx=10, pady=10)

        frame_canvas = ScrolledFrame(self.contenedor, autohide=True)
        frame_canvas.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(frame_canvas, bg="white")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.redimensionar_celdas)
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())

        frame_principal.after(100, self.recalcular_y_cargar_ubicaciones)

        logger.debug("Interfaz de ContenidoPublicidad creada correctamente.")

    def redimensionar_celdas(self, event=None):
        try:
            nuevo_ancho = event.width if event else self.canvas.winfo_width()
            self.cell_width = int(((nuevo_ancho - 2 * PADDING) // self.cols) * 0.97)
            logger.debug("Redimensionando celdas | nuevo_ancho=%s | cell_width=%s", nuevo_ancho, self.cell_width)
            self.recolocar_items()
        except Exception:
            logger.exception("Error al redimensionar celdas.")

    def recolocar_items(self):
        try:
            logger.debug("Recolocando items | cantidad=%s", len(self.items))
            for idx, item in enumerate(self.items):
                fila, col = divmod(idx, self.cols)
                x, y = self.calcular_x(col), self.calcular_y(fila)
                self.canvas.coords(item["window_id"], x, y)
                item["frame"].configure(width=self.cell_width, height=CELL_HEIGHT)
                item["label_pos"].config(text=str(idx + 1))
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
                self.agregar_item_multimedia(os.path.basename(ruta), ruta)

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
                highlightthickness=3,
                highlightbackground="#063970"
            )
            frame_item.pack_propagate(False)

            tipo = "video" if filepath.lower().endswith((".mp4", ".avi", ".mov")) else "imagen"
            logger.debug("Tipo multimedia detectado | ruta=%s | tipo=%s", filepath, tipo)

            self.insertar_contenido_multimedia(frame_item, filepath, tipo)

            label_pos = tk.Label(frame_item, text="", font=("Arial", 10, "bold"), bg="white")
            label_pos.place(x=5, y=5)

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
                "label_pos": label_pos
            })
            self.items_dict[filepath] = {
                "fila": fila,
                "columna": col,
                "posicion": fila * self.cols + col + 1
            }

            self.rows = (len(self.items) + self.cols - 1) // self.cols
            self.canvas.config(height=self.rows * (CELL_HEIGHT + ITEM_MARGIN))
            self.guardar_ubicaciones()

            logger.debug("Item multimedia agregado correctamente | total_items=%s", len(self.items))

        except Exception:
            logger.exception("Error al agregar item multimedia | nombre=%s | ruta=%s", nombre, filepath)

    def insertar_contenido_multimedia(self, frame, ruta, tipo):
        try:
            logger.debug("Insertando contenido multimedia | ruta=%s | tipo=%s", ruta, tipo)

            if tipo == "imagen":
                img = Image.open(ruta).resize((self.cell_width, CELL_HEIGHT), Image.Resampling.LANCZOS)
            else:
                cap = cv2.VideoCapture(ruta)
                success, frame_img = cap.read()
                cap.release()

                if success:
                    frame_img = cv2.cvtColor(frame_img, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_img).resize((self.cell_width, CELL_HEIGHT), Image.Resampling.LANCZOS)
                    draw = ImageDraw.Draw(img)
                    triangle = [
                        (self.cell_width // 2 - 20, CELL_HEIGHT // 2 - 20),
                        (self.cell_width // 2 - 20, CELL_HEIGHT // 2 + 20),
                        (self.cell_width // 2 + 20, CELL_HEIGHT // 2)
                    ]
                    draw.polygon(triangle, fill="white")
                else:
                    logger.warning("No se pudo obtener frame de video. Se usará imagen gris | ruta=%s", ruta)
                    img = Image.new("RGB", (self.cell_width, CELL_HEIGHT), color="gray")

            img_tk = ImageTk.PhotoImage(img)
            label = tk.Label(frame, image=img_tk)
            label.image = img_tk
            label.pack(expand=True, fill="both")

            label.bind("<ButtonPress-1>", lambda e, f=frame: f.event_generate("<ButtonPress-1>", x=e.x, y=e.y))
            label.bind("<B1-Motion>", lambda e, f=frame: f.event_generate("<B1-Motion>", x=e.x, y=e.y))
            label.bind("<ButtonRelease-1>", lambda e, f=frame: f.event_generate("<ButtonRelease-1>", x=e.x, y=e.y))
            label.bind("<Double-Button-1>", lambda e, f=frame, ruta=ruta: self.abrir_contenido(ruta))
            label.bind("<Button-3>", lambda e, f=frame, ruta=ruta: self.mostrar_menu_contextual(e, ruta))

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
                self.item_seleccionado["frame"].config(highlightbackground="#063970")

            if self.drag_item:
                logger.debug("Inicio drag | ruta=%s", self.drag_item.get("filepath"))
                self.canvas.tag_raise(self.drag_item["window_id"])
                self.drag_item["frame"].lift()
                self.drag_item["frame"].config(
                    highlightbackground="#00cc66",
                    highlightthickness=5,
                    bg="#f0f0f0"
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
                    highlightbackground="#063970",
                    highlightthickness=3,
                    bg="white"
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
            logger.debug("Guardando ubicaciones de multimedia | cantidad=%s", len(self.items_dict))
            config = self.widgets.get_widget("CONFIG", "config_json")
            config["ubicaciones"] = self.items_dict

            from GUI.GUI_MAIN import guardar_config
            guardar_config(config)

        except Exception:
            logger.exception("Error al guardar ubicaciones.")

    def cargar_ubicaciones(self):
        try:
            config = self.widgets.get_widget("CONFIG", "config_json")
            data = config.get("ubicaciones", {})

            logger.info("Cargando ubicaciones guardadas | cantidad=%s", len(data))

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

        except Exception:
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
            if not self.items:
                logger.warning("Se intentó enviar multimedia sin contenido.")
                messagebox.showinfo("Sin contenido", "No hay contenido para enviar.")
                return

            logger.info("Iniciando envío de multimedia | cantidad_items=%s", len(self.items))

            sender = DispositivoSender(
                self.widgets.get_widget("DATABASE", "CONEXIONDBA"),
                self.widgets.get_widget("GUI_MAIN", "ventana_creacion_caja")
            )
            urls = sender.seleccionar_dispositivos()

            logger.debug("Dispositivos seleccionados para envío | urls=%s", urls)

            if urls:
                sender.enviar_publicidades(urls, self.items)
                logger.info("Envío de publicidades lanzado correctamente.")
            else:
                logger.warning("No se seleccionaron dispositivos para enviar multimedia.")

        except Exception:
            logger.exception("Error al enviar multimedia.")

    def mostrar_preview_general(self):
        try:
            if not self.items:
                logger.warning("Se intentó abrir preview general sin items.")
                messagebox.showinfo("Sin contenido", "No hay ítems para mostrar.")
                return

            logger.info("Abriendo preview general | cantidad_items=%s", len(self.items))

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
                command=lambda: self.iniciar_slideshow(self.items)
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
                        canvas_width, cols, len(self.items)
                    )

                    for idx, item in enumerate(self.items):
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
                    for i, item in enumerate(self.items):
                        if i not in seleccionados:
                            nuevos_items.append(item)
                            nuevos_dict[item["filepath"]] = self.items_dict[item["filepath"]]
                        else:
                            self.canvas.delete(item["window_id"])

                    self.items = nuevos_items
                    self.items_dict = nuevos_dict
                    self.recolocar_items()
                    self.guardar_ubicaciones()
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
                    for item in self.items:
                        tipo = "video" if item["filepath"].lower().endswith((".mp4", ".avi", ".mov", ".mkv")) else "imagen"
                        if tipo != tipo_objetivo:
                            nuevos_items.append(item)
                            nuevos_dict[item["filepath"]] = self.items_dict[item["filepath"]]
                        else:
                            self.canvas.delete(item["window_id"])

                    self.items = nuevos_items
                    self.items_dict = nuevos_dict
                    self.recolocar_items()
                    self.guardar_ubicaciones()
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

    def centrar_ventana(self, ventana, ancho, alto):
        try:
            pantalla_ancho = ventana.winfo_screenwidth()
            pantalla_alto = ventana.winfo_screenheight()
            x = (pantalla_ancho - ancho) // 2
            y = (pantalla_alto - alto) // 2
            ventana.geometry(f"{ancho}x{alto}+{x}+{y}")
            logger.debug("Ventana centrada | ancho=%s | alto=%s | x=%s | y=%s", ancho, alto, x, y)
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