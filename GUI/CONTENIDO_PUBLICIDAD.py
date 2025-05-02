import json
import requests
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


CELL_HEIGHT = 170  # Hacemos más rectangular
PADDING = 0        # margen interno del canvas
ITEM_MARGIN = 5  # margen entre ítems

CELL_HEIGHT = 170
PADDING = 0
ITEM_MARGIN = 5

class ContenidoPublicidad:
    def __init__(self, widgets):
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
        frame_principal = self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad")
        self.contenedor_general = ttk.Frame(frame_principal)
        self.contenedor_general.pack(fill="both", expand=True)

        self.frame_botones = ttk.Frame(self.contenedor_general)
        self.frame_botones.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Button(self.frame_botones, text="Agregar Multimedia", command=self.agregar_multimedia).pack(side="left")
        ttk.Button(self.frame_botones, text="Enviar", command=self.enviar_multimedia).pack(side="left", padx=(5, 0))
        ttk.Button(self.frame_botones, text="Vista Completa", command=self.mostrar_preview_general).pack(side="left", padx=(5, 0))
        ttk.Button(self.frame_botones, text="Panel de control", command=self.abrir_panel_de_control).pack(side="left", padx=(5, 0))



        self.contenedor = ttk.Frame(self.contenedor_general)
        self.contenedor.pack(fill="both", expand=True, padx=10, pady=10)

        frame_canvas = ScrolledFrame(self.contenedor, autohide=True)
        frame_canvas.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(frame_canvas, bg="white")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.redimensionar_celdas)
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())


        frame_principal.after(100, self.recalcular_y_cargar_ubicaciones)

    def redimensionar_celdas(self, event=None):
        nuevo_ancho = event.width if event else self.canvas.winfo_width()
        self.cell_width = int(((nuevo_ancho - 2 * PADDING) // self.cols) * 0.97)
        self.recolocar_items()

    def recolocar_items(self):
        for idx, item in enumerate(self.items):
            fila, col = divmod(idx, self.cols)
            x, y = self.calcular_x(col), self.calcular_y(fila)
            self.canvas.coords(item["window_id"], x, y)
            item["frame"].configure(width=self.cell_width, height=CELL_HEIGHT)
            item["label_pos"].config(text=str(idx + 1))

    def agregar_multimedia(self):
        filepaths = filedialog.askopenfilenames(title="Seleccionar archivos multimedia",
            filetypes=[("Archivos multimedia", "*.jpg *.jpeg *.png *.mp4 *.avi *.mov"), ("Todos los archivos", "*.*")])
        for ruta in filepaths:
            self.agregar_item_multimedia(os.path.basename(ruta), ruta)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.recolocar_items()

    def agregar_item_multimedia(self, nombre, filepath, fila=None, col=None):
        if fila is None or col is None:
            fila, col = self.obtener_proxima_posicion_libre()

        frame_item = tk.Frame(self.canvas, width=self.cell_width, height=CELL_HEIGHT, highlightthickness=3, highlightbackground="#063970")
        frame_item.pack_propagate(False)

        tipo = "video" if filepath.lower().endswith((".mp4", ".avi", ".mov")) else "imagen"
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

        self.items.append({"frame": frame_item, "grid": (fila, col), "filepath": filepath, "window_id": window_id, "label_pos": label_pos})
        self.items_dict[filepath] = {"fila": fila, "columna": col, "posicion": fila * self.cols + col + 1}

        self.rows = (len(self.items) + self.cols - 1) // self.cols
        self.canvas.config(height=self.rows * (CELL_HEIGHT + ITEM_MARGIN))
        self.guardar_ubicaciones()

    def insertar_contenido_multimedia(self, frame, ruta, tipo):
        try:
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
                        (self.cell_width//2 - 20, CELL_HEIGHT//2 - 20),
                        (self.cell_width//2 - 20, CELL_HEIGHT//2 + 20),
                        (self.cell_width//2 + 20, CELL_HEIGHT//2)
                    ]
                    draw.polygon(triangle, fill="white")
                else:
                    img = Image.new("RGB", (self.cell_width, CELL_HEIGHT), color="gray")

            img_tk = ImageTk.PhotoImage(img)
            label = tk.Label(frame, image=img_tk)
            label.image = img_tk
            label.pack(expand=True, fill="both")

            # Transferencia precisa de eventos al frame
            label.bind("<ButtonPress-1>", lambda e, f=frame: f.event_generate("<ButtonPress-1>", x=e.x, y=e.y))
            label.bind("<B1-Motion>", lambda e, f=frame: f.event_generate("<B1-Motion>", x=e.x, y=e.y))
            label.bind("<ButtonRelease-1>", lambda e, f=frame: f.event_generate("<ButtonRelease-1>", x=e.x, y=e.y))
            label.bind("<Double-Button-1>", lambda e, f=frame, ruta=ruta: self.abrir_contenido(ruta))
            label.bind("<Button-3>", lambda e, f=frame, ruta=ruta: self.mostrar_menu_contextual(e, ruta))

        except Exception as e:
            print(f"Error cargando multimedia: {e}")


    def obtener_proxima_posicion_libre(self):
        ocupadas = {item["grid"] for item in self.items}
        fila = 0
        while True:
            for col in range(self.cols):
                if (fila, col) not in ocupadas:
                    return fila, col
            fila += 1

    def calcular_x(self, col):
        return col * (self.cell_width + ITEM_MARGIN) + self.cell_width // 2

    def calcular_y(self, fila):
        return fila * (CELL_HEIGHT + ITEM_MARGIN) + CELL_HEIGHT // 2

    def start_drag(self, event, frame):
        self._clic_pos = (event.x_root, event.y_root)
        for item in self.items:
            if item["frame"] == frame:
                self.drag_item = item
                break
        if self.item_seleccionado and self.item_seleccionado != self.drag_item:
            self.item_seleccionado["frame"].config(highlightbackground="#063970")
        if self.drag_item:
            self.canvas.tag_raise(self.drag_item["window_id"])
            self.drag_item["frame"].lift()
            self.drag_item["frame"].config(
                highlightbackground="#00cc66",
                highlightthickness=5,
                bg="#f0f0f0"  # leve sombra clara alrededor
            )
            self.item_seleccionado = self.drag_item


    def do_drag(self, event):
        if self.drag_item:
            dx = event.x_root - self._clic_pos[0]
            dy = event.y_root - self._clic_pos[1]
            self._clic_pos = (event.x_root, event.y_root)
            x, y = self.canvas.coords(self.drag_item["window_id"])
            self.canvas.coords(self.drag_item["window_id"], x + dx, y + dy)
            self.canvas.tag_raise(self.drag_item["window_id"])  # mantener al frente todo el tiempo
            self.drag_item["frame"].lift()  # 🔥 fuerza levantar el Frame en su propio contexto


    def end_drag(self, event):
        if not self.drag_item:
            return

        # Coordenadas relativas al canvas
        x, y = self.canvas.coords(self.drag_item["window_id"])
        col = int(x // (self.cell_width + ITEM_MARGIN))
        row = int(y // (CELL_HEIGHT + ITEM_MARGIN))
        col = max(0, min(col, self.cols - 1))
        row = max(0, row)

        nuevo_index = row * self.cols + col
        nuevo_index = min(nuevo_index, len(self.items) - 1)

        # Reubicar en la nueva posición
        self.items.remove(self.drag_item)
        self.items.insert(nuevo_index, self.drag_item)

        # Recolocar todos los ítems
        self.recolocar_items()

        # Actualizar dict
        self.items_dict = {
            item["filepath"]: {"fila": idx // self.cols, "columna": idx % self.cols, "posicion": idx + 1}
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


    def mostrar_menu_contextual(self, event, filepath):
        menu = tk.Menu(self.canvas, tearoff=0)
        menu.add_command(label="Eliminar", command=lambda: self.eliminar_item(filepath))
        menu.tk_popup(event.x_root, event.y_root)

    def eliminar_item(self, filepath):
        for item in self.items:
            if item["filepath"] == filepath:
                self.canvas.delete(item["window_id"])
                self.items.remove(item)
                break
        if filepath in self.items_dict:
            del self.items_dict[filepath]
        self.recolocar_items()
        self.guardar_ubicaciones()

    def abrir_contenido(self, ruta):
        if ruta.lower().endswith((".jpg", ".jpeg", ".png")):
            self.abrir_imagen(ruta)
        else:
            self.reproducir_video(ruta)

    def abrir_imagen(self, path):
        top = ttk.Toplevel()
        top.title("Imagen")
        img = Image.open(path)
        img_tk = ImageTk.PhotoImage(img)
        label = tk.Label(top, image=img_tk)
        label.image = img_tk
        label.pack()
        top.focus_force()

    def reproducir_video(self, path):
        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo: {e}")

    def guardar_ubicaciones(self, archivo="ubicaciones.json"):
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(self.items_dict, f, indent=4, ensure_ascii=False)

    def cargar_ubicaciones(self, archivo="ubicaciones.json"):
        if not os.path.exists(archivo):
            return
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
        for ruta, info in data.items():
            if os.path.exists(ruta):
                self.agregar_item_multimedia("Multimedia", ruta, fila=info.get("fila"), col=info.get("columna"))

    def recalcular_y_cargar_ubicaciones(self):
        self.canvas.update_idletasks()
        self.cargar_ubicaciones()
        self.redimensionar_celdas()

    def enviar_multimedia(self):
        for filepath, info in self.items_dict.items():
            if not os.path.exists(filepath):
                print(f"Archivo no encontrado: {filepath}")
                continue

            posicion = info["posicion"]
            nombre_media = os.path.splitext(os.path.basename(filepath))[0]
            formato = os.path.splitext(filepath)[1][1:].lower()

            # Determinar si es imagen o video
            if formato in ["jpg", "jpeg", "png", "gif", "webp"]:
                url = "http://192.168.1.161:8080/api/veri/ad_medias_images"
            elif formato in ["mp4", "avi", "mov", "mkv", "webm"]:
                url = "http://192.168.1.161:8080/api/veri/ad_medias_videos"
            else:
                print(f"Formato no compatible: {formato}")
                continue

            json_data = {
                "nro_posicion": posicion,
                "nombre_media": nombre_media,
                "formato_media": formato
            }

            try:
                with open(filepath, "rb") as f:
                    files = {
                        "json": (None, json.dumps(json_data), "application/json"),
                        "file": (os.path.basename(filepath), f, "application/octet-stream")
                    }

                    print(f"▶ Enviando a {url} → {filepath}")
                    response = requests.post(url, files=files)
                    print(f"✅ Respuesta {response.status_code}: {response.text}")
            except Exception as e:
                print(f"❌ Error al enviar {filepath}: {e}")
        url = "http://192.168.1.161:8080/api/veri/reiniciar_launcher"
        response = requests.post(url)
        print(response)
        
    def mostrar_preview_general(self):
        if not self.items:
            messagebox.showinfo("Sin contenido", "No hay ítems para mostrar.")
            return

        ventana = tk.Toplevel()
        ventana.title("Vista completa de publicidades")
        ventana.state("zoomed")
        ventana.resizable(False, False)
        ventana.grab_set()
        ventana.focus_force()

        canvas = tk.Canvas(ventana, bg="black")
        canvas.pack(fill="both", expand=True)

        ttk.Button(ventana, text="Iniciar presentación", command=lambda: self.iniciar_slideshow(self.items)).pack(pady=10)

        def render_items():
            cell_w = 200
            cell_h = 140
            canvas_width = canvas.winfo_width()

            cols = max(1, canvas_width // (cell_w + 20))
            total_width = cols * cell_w
            remaining_space = canvas_width - total_width
            padding_x = remaining_space // (cols + 1)

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
                                (cell_w//2 - 15, cell_h//2 - 15),
                                (cell_w//2 - 15, cell_h//2 + 15),
                                (cell_w//2 + 15, cell_h//2)
                            ]
                            draw.polygon(triangle, fill="white")
                        else:
                            img = Image.new("RGB", (cell_w, cell_h), color="gray")

                    img_tk = ImageTk.PhotoImage(img)
                    label = tk.Label(canvas, image=img_tk)
                    label.image = img_tk
                    canvas.create_window(x, y, anchor="nw", window=label)
                except Exception as e:
                    print(f"Error en vista completa: {e}")

        ventana.after(100, render_items)


    def iniciar_slideshow(self, items):
        if not items:
            return

        slideshow = tk.Toplevel()
        slideshow.attributes("-fullscreen", True)
        slideshow.configure(background="black")
        slideshow.focus_set()
        slideshow.lift()
        slideshow.attributes("-topmost", True)
        def cerrar_slideshow(event=None):
            try:
                player.stop()
            except:
                pass
            if slideshow.winfo_exists():
                slideshow.destroy()

        slideshow.bind_all("<Escape>", cerrar_slideshow)
        slideshow.focus_force()



        label = tk.Label(slideshow, bg="black")
        label.pack(expand=True, fill="both")

        # Overlay: cartel ESC
        cartel_esc = tk.Label(
            slideshow,
            text="Presione ESC para salir",
            font=("Segoe UI", 12, "bold"),
            fg="white",
            bg="black",
            anchor="se"
        )
        cartel_esc.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)


        instance = vlc.Instance()
        player = instance.media_player_new()

        index = [0]

        def mostrar_siguiente():
            if index[0] >= len(items):
                player.stop()
                slideshow.destroy()
                return

            filepath = items[index[0]]["filepath"]
            tipo = "video" if filepath.lower().endswith((".mp4", ".avi", ".mov", ".mkv")) else "imagen"

            if tipo == "imagen":
                player.stop()
                img = Image.open(filepath)
                original_width, original_height = img.size

                # Escalar imagen proporcionalmente para que entre completa en pantalla
                screen_w = slideshow.winfo_screenwidth()
                screen_h = slideshow.winfo_screenheight()

                ratio = min(screen_w / original_width, screen_h / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Calcular fondo
                if filepath.lower().endswith(".png") and img.mode in ("RGBA", "LA"):
                    # Usar color contrastante si hay transparencia
                    rgba_data = img.convert("RGBA").getdata()
                    opaque_pixels = [pixel[:3] for pixel in rgba_data if pixel[3] > 128]
                    if opaque_pixels:
                        avg = tuple(sum(c) // len(c) for c in zip(*opaque_pixels))
                        contrast_color = tuple(255 - c for c in avg)
                    else:
                        contrast_color = (0, 0, 0)
                else:
                    # Color predominante
                    small = img.convert("RGB").resize((50, 50))
                    pixels = list(small.getdata())
                    freq = {}
                    for px in pixels:
                        freq[px] = freq.get(px, 0) + 1
                    contrast_color = max(freq, key=freq.get)

                # Crear fondo con color adecuado
                fondo = Image.new("RGB", (screen_w, screen_h), color=contrast_color)
                pos_x = (screen_w - new_width) // 2
                pos_y = (screen_h - new_height) // 2
                if img_resized.mode == "RGBA":
                    fondo = fondo.convert("RGBA")
                    fondo.paste(img_resized, (pos_x, pos_y), mask=img_resized)
                else:
                    fondo.paste(img_resized, (pos_x, pos_y))

                # Convertir y mostrar
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
                player.set_hwnd(video_widget_id)  # Windows específico
                media = instance.media_new(filepath)
                player.set_media(media)

                def revisar_estado():
                    state = player.get_state()
                    if state in (vlc.State.Ended, vlc.State.Error):
                        index[0] += 1
                        mostrar_siguiente()
                    else:
                        slideshow.after(500, revisar_estado)

                player.play()
                revisar_estado()

        mostrar_siguiente()
        
    def abrir_panel_de_control(self):
        if not self.items:
            messagebox.showinfo("Sin contenido", "No hay ítems para mostrar.")
            return

        top = tk.Toplevel()

        cuadro_w = 110
        cuadro_h = 80
        espacio_x = 10
        espacio_y = 10

        try:
            check_tk = READ_IMG(PNG_Check(), 32, 32)
        except:
            check_tk = None  # por si no se encuentra la imagen
        print(check_tk)

        # Crear overlay semitransparente con PIL (negro alpha)
        try:
            overlay_img = Image.new("RGBA", (cuadro_w, cuadro_h), (0, 0, 0, 100))  # alpha 100 de 255
            overlay_tk = ImageTk.PhotoImage(overlay_img)
        except Exception as e:
            print(f"Error creando overlay: {e}")
            overlay_tk = None

        top.title("Panel de control de multimedia")

        max_ancho = top.winfo_screenwidth() - 100  # dejá margen de pantalla
        total_items = len(self.items)

        # Calcular columnas dinámicas según ancho máximo
        columnas = max(1, min(total_items, max_ancho // (cuadro_w + espacio_x)))
        filas = (total_items + columnas - 1) // columnas

        # Calcular tamaño exacto de ventana
        ancho_ventana = columnas * (cuadro_w + espacio_x) + 40
        alto_ventana = min(filas * (cuadro_h + espacio_y) + 120, top.winfo_screenheight() - 100)

        # Centrar la ventana
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
        imagenes_originales = {}  # Guardar las PIL.Image originales
        imagenes_tk = {}          # Guardar las PhotoImage actuales
        tilde_labels = {}         # Guardar referencias de tildes por idx

        for idx, item in enumerate(self.items):
            fila = idx // columnas
            col = idx % columnas

            tipo = "video" if item["filepath"].lower().endswith((".mp4", ".avi", ".mov", ".mkv")) else "imagen"

            frame = tk.Frame(frame_scroll, width=cuadro_w, height=cuadro_h, relief="ridge", borderwidth=2, bg="#f0f0f0")
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
                        img = Image.new("RGB", (cuadro_w, cuadro_h), color="gray")

                img = img.resize((cuadro_w, cuadro_h), Image.Resampling.LANCZOS)

                # Si es video, dibujamos el icono ▶️ encima
                if tipo == "video":
                    draw = ImageDraw.Draw(img)
                    triangle = [
                        (cuadro_w//2 - 8, cuadro_h//2 - 10),
                        (cuadro_w//2 - 8, cuadro_h//2 + 10),
                        (cuadro_w//2 + 10, cuadro_h//2)
                    ]
                    draw.polygon(triangle, fill="white")

                imagenes_originales[idx] = img  # Guardar imagen original PIL

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



            except Exception as e:
                print(f"Error cargando preview: {e}")
                label = tk.Label(frame, text=f"{idx+1}\n{tipo}", justify="center", bg="#f0f0f0")
                label.pack(expand=True, fill="both")


            def toggle_select(event, i=idx, lbl=label):
                if i in seleccionados:
                    seleccionados.remove(i)
                    lbl.config(image=imagenes_tk[i])  # Volver a imagen original
                    lbl.image = imagenes_tk[i]
                    if tilde_labels[i]:
                        tilde_labels[i].place_forget()
                else:
                    seleccionados.add(i)

                    # Crear overlay y aplicar
                    base_img = imagenes_originales[i].convert("RGBA")
                    overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 100))  # negro translúcido
                    img_modificada = Image.alpha_composite(base_img, overlay).convert("RGB")

                    img_tk_modificada = ImageTk.PhotoImage(img_modificada)
                    lbl.config(image=img_tk_modificada)
                    lbl.image = img_tk_modificada  # Guardar ref para evitar garbage collection

                    if tilde_labels[i]:
                        tilde_labels[i].place(relx=1.0, rely=0.0, anchor="ne", x=-6, y=6)



            frame.bind("<Button-1>", toggle_select)
            label.bind("<Button-1>", toggle_select)

        # Acciones
        def eliminar_seleccionados():
            if not seleccionados:
                messagebox.showinfo("Nada seleccionado", "No seleccionaste ningún ítem.")
                return
            if not messagebox.askyesno("Confirmación", f"¿Eliminar {len(seleccionados)} ítems seleccionados?"):
                return

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

        def eliminar_por_tipo(tipo_objetivo):
            if not messagebox.askyesno("Confirmación", f"¿Eliminar todos los archivos tipo {tipo_objetivo}?"):
                return

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

        # Botones inferiores
        marco_botones = ttk.Frame(top)
        marco_botones.pack(pady=10)

        ttk.Button(marco_botones, text="🗑 Eliminar seleccionados", command=eliminar_seleccionados).pack(side="left", padx=5)
        ttk.Button(marco_botones, text="🟦 Eliminar videos", command=lambda: eliminar_por_tipo("video")).pack(side="left", padx=5)
        ttk.Button(marco_botones, text="🖼 Eliminar imágenes", command=lambda: eliminar_por_tipo("imagen")).pack(side="left", padx=5)

    def centrar_ventana(self, ventana, ancho, alto):
        pantalla_ancho = ventana.winfo_screenwidth()
        pantalla_alto = ventana.winfo_screenheight()
        x = (pantalla_ancho - ancho) // 2
        y = (pantalla_alto - alto) // 2
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")
