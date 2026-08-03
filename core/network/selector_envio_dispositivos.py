import threading
import os
import json
import requests
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledFrame
from core.network.api_client import DispositivoAPIClient
from core.network.urls_dispositivos import VeriPreDispositivosURLBuilder
from core.ui.responsive import fit_toplevel_to_workarea

class EnvioDispositivos:
    def __init__(self, conexion_dba, batch_size=1000):
        self.CONEXIONDBA = conexion_dba
        self.BATCH_SIZE = batch_size

    def seleccionar_y_enviar(self, root, datos_a_enviar, modo="completo"):
        builder = VeriPreDispositivosURLBuilder(self.CONEXIONDBA)
        dispositivos = builder.obtener_urls_api("/api/veri/batch_productos")

        toplevel = ttk.Toplevel(root)
        toplevel.title("Seleccionar Dispositivos")
        fit_toplevel_to_workarea(toplevel, 500, 500, min_width=460, min_height=420)
        toplevel.place_window_center()
        toplevel.grab_set()

        ttk.Label(toplevel, text="Selecciona los dispositivos para enviar:", font=("Segoe UI", 11)).pack(pady=(10, 5))

        # Scroll canvas
        frame_scroll = ttk.Frame(toplevel)
        frame_scroll.pack(fill="both", expand=True)

        canvas = ttk.Canvas(frame_scroll)
        scrollbar = ttk.Scrollbar(frame_scroll, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        vars_check = []
        check_widgets = []
        var_todos = ttk.BooleanVar(value=False)

        def toggle_all():
            for var, widget in vars_check:
                if str(widget['state']) == "normal":
                    var.set(var_todos.get())
                    widget.update()  # ← Forzar actualización visual


        ttk.Checkbutton(scroll_frame, text="Seleccionar todos", variable=var_todos, command=toggle_all).pack(anchor="w", padx=10, pady=(5, 10))

        def verificar_dispositivo(dispositivo, var, chk):
            try:
                base_url = dispositivo["url"].split("/api")[0]
                r = requests.get(f"{base_url}/", timeout=2)
                if r.status_code == 200:
                    chk.config(state="normal", text=f"🟢 {dispositivo['nombre']}")
                else:
                    chk.config(state="disabled", text=f"🔴 {dispositivo['nombre']} (Offline)")
            except:
                chk.config(state="disabled", text=f"🔴 {dispositivo['nombre']} (Offline)")

        for disp in dispositivos:
            var = ttk.BooleanVar(value=False)
            chk = ttk.Checkbutton(scroll_frame, text=f"{disp['nombre']} (Verificando...)", variable=var, state="disabled")
            chk.pack(anchor="w", padx=20, pady=2)
            check_widgets.append((disp, var, chk))
            vars_check.append((var, chk))
            threading.Thread(target=verificar_dispositivo, args=(disp, var, chk), daemon=True).start()

        def ventana_estado_envio(urls, nombres):
            top_estado = ttk.Toplevel()
            top_estado.title("Estado de Envío a Dispositivos")
            fit_toplevel_to_workarea(top_estado, 600, 500, min_width=520, min_height=420)
            top_estado.place_window_center()
            top_estado.grab_set()
            estado_finalizados = {"count": 0}
            total_dispositivos = len(urls)

            ttk.Label(top_estado, text="Estado de transmisión por dispositivo", font=("Segoe UI", 12)).pack(pady=10)

            scrolled = ScrolledFrame(top_estado, autohide=True)
            scrolled.pack(fill="both", expand=True, padx=10, pady=10)
            inner_frame = scrolled

            barras_estado = {}

            for url in urls:
                frame = ttk.Frame(inner_frame, padding=10, relief="ridge")
                frame.pack(fill="x", pady=5)

                nombre = nombres.get(url, url.split("//")[-1].split("/")[0])
                ttk.Label(frame, text=nombre, font=("Segoe UI", 13, "bold")).pack(fill="x")

                barra = ttk.Progressbar(frame, mode="indeterminate", length=300)
                barra.pack(pady=(5, 5))
                barra.start()

                label = ttk.Label(frame, text="Esperando...", font=("Segoe UI", 10))
                label.pack()

                barras_estado[url] = (label, barra)

            return top_estado, barras_estado, estado_finalizados, total_dispositivos

        def confirmar():
            seleccionados = []
            for disp, var, chk in check_widgets:
                if var.get() and str(chk.cget("state")) == "normal":
                    seleccionados.append(disp["url"])


            if not seleccionados:
                messagebox.showwarning("Sin selección", "Debes seleccionar al menos un dispositivo en línea.")
                return
            

            toplevel.destroy()
            url_nombre = {disp["url"]: disp["nombre"] for disp, var, chk in check_widgets}
            top_estado, barras_estado, estado_finalizados, total_dispositivos = ventana_estado_envio(seleccionados, url_nombre)

            def enviar_por_dispositivo(url, datos_a_enviar, modo):
                label, barra = barras_estado[url]

                def actualizar_estado(msg):
                    label.config(text=msg)
                    if msg.startswith("✅") or msg.startswith("❌"):
                        barra.stop()
                        estado_finalizados["count"] += 1
                        if estado_finalizados["count"] == total_dispositivos:
                            ttk.Button(top_estado, text="Cerrar", command=top_estado.destroy).pack(pady=10)

                try:
                    client = DispositivoAPIClient(url, estado_callback=actualizar_estado)
                    actualizar_estado(f"🟡 Enviando ({modo})...")

                    if modo == "completo" or modo == "novedades":
                        client.enviar_delete()
                        total = len(datos_a_enviar)
                        for i in range(0, total, self.BATCH_SIZE):
                            batch = datos_a_enviar[i:i + self.BATCH_SIZE]
                            json_batch = [{
                                "codigo": art[1],
                                "descripcion": art[2],
                                "precio": art[3],
                                "img_base64": art[4],
                                "formato_imagen": art[5]
                            } for art in batch]
                            client.enviar_post_json(json_batch)
                        actualizar_estado("✅ Enviado correctamente")

                    elif modo == "publicidad":
                        for item in datos_a_enviar:
                            filepath = item["filepath"]
                            posicion = item["grid"][0] * 4 + item["grid"][1] + 1
                            nombre_media = os.path.splitext(os.path.basename(filepath))[0]
                            formato = os.path.splitext(filepath)[1][1:].lower()

                            if formato in ["jpg", "jpeg", "png", "gif", "webp"]:
                                path_api = "/api/veri/ad_medias_images"
                            elif formato in ["mp4", "avi", "mov", "mkv", "webm"]:
                                path_api = "/api/veri/ad_medias_videos"
                            else:
                                actualizar_estado(f"❌ Formato no soportado: {formato}")
                                continue

                            url_post = url.split("/api")[0] + path_api
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
                                    actualizar_estado(f"▶ Enviando {nombre_media}...")
                                    response = requests.post(url_post, files=files)
                                    actualizar_estado(f"✅ {nombre_media}: {response.status_code}")
                            except Exception as e:
                                actualizar_estado(f"❌ Error al enviar {nombre_media}: {e}")

                        # Reiniciar launcher
                        try:
                            requests.post(url.split("/api")[0] + "/api/veri/reiniciar_launcher")
                            actualizar_estado("✅ Launcher reiniciado")
                        except:
                            actualizar_estado("⚠ No se pudo reiniciar launcher")

                except Exception as e:
                    actualizar_estado(f"❌ Error general: {e}")

            for url in seleccionados:
                threading.Thread(
                    target=enviar_por_dispositivo,
                    args=(url,),  # 👈 le estás pasando url
                    daemon=True
                ).start()

        ttk.Button(toplevel, text="Enviar", command=confirmar).pack(pady=10)
            














"""
#CODIGO QUE ESTABA EN CONTENIDO_PRODUCTO
def seleccionar_dispositivos(self, callback_enviar, datos_a_enviar, modo="completo"):
        builder = VeriPreDispositivosURLBuilder(self.CONEXIONDBA)
        dispositivos = builder.obtener_urls_api("/api/veri/batch_productos")  # Devuelve [{"nombre": ..., "url": ...}, ...]

        toplevel = ttk.Toplevel()
        toplevel.title("Seleccionar Dispositivos")
        toplevel.geometry("500x500")
        toplevel.place_window_center()
        toplevel.grab_set()

        ttk.Label(toplevel, text="Selecciona los dispositivos para enviar:", font=("Segoe UI", 11)).pack(pady=(10, 5))

        frame_scroll = ttk.Frame(toplevel)
        frame_scroll.pack(fill="both", expand=True)

        canvas = ttk.Canvas(frame_scroll)
        scrollbar = ttk.Scrollbar(frame_scroll, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        vars_check = []
        check_widgets = []
        var_todos = ttk.BooleanVar(value=False)  # ← antes estaba en True

        def toggle_all():
            for var, widget in vars_check:
                if str(widget['state']) == "normal":
                    var.set(var_todos.get())
                    print(var.get())



        ttk.Checkbutton(scroll_frame, text="Seleccionar todos", variable=var_todos, command=toggle_all).pack(anchor="w", padx=10, pady=(5, 10))

        def verificar_dispositivo(dispositivo, var, check):
            try:
                base_url = dispositivo["url"].split("/api")[0]
                resp = requests.get(f"{base_url}/", timeout=2)
                if resp.status_code == 200:
                    check.config(state="normal", text=f"🟢 {dispositivo['nombre']}")
                    vars_check.append((var, check))  # Solo agregar si está en línea
                else:
                    check.config(state="disabled", text=f"🔴 {dispositivo['nombre']} (Offline)")
            except Exception:
                check.config(state="disabled", text=f"🔴 {dispositivo['nombre']} (Offline)")
                
        def actualizar_estado_seleccionar_todos():
            seleccionables = [var for var, chk in vars_check if str(chk['state']) == "normal"]
            seleccionados = [var for var in seleccionables if var.get()]
            if len(seleccionados) == len(seleccionables):
                var_todos.set(True)
            else:
                var_todos.set(False)



        for disp in dispositivos:
            var = ttk.BooleanVar(value=False)
            chk = ttk.Checkbutton(scroll_frame, text=f"{disp['nombre']} (Verificando...)", variable=var, state="disabled")
            chk.config(command=actualizar_estado_seleccionar_todos)
            chk.pack(anchor="w", padx=20, pady=2)
            check_widgets.append((disp, var, chk))

            # 👇 Agregar de inmediato
            vars_check.append((var, chk))

            threading.Thread(target=verificar_dispositivo, args=(disp, var, chk), daemon=True).start()
            
            

        def ventana_estado_envio(urls, nombres):
            top_estado = ttk.Toplevel()
            top_estado.title("Estado de Envío a Dispositivos")
            top_estado.geometry("600x500")
            top_estado.place_window_center()
            top_estado.grab_set()
            self.estado_finalizados = {"count": 0}
            self.total_dispositivos = len(urls)
            
            ttk.Label(top_estado, text="Estado de transmisión por dispositivo", font=("Segoe UI", 12)).pack(pady=10)

            # Usar ScrolledFrame para scroll vertical automático
            scrolled = ScrolledFrame(top_estado, autohide=True)
            scrolled.pack(fill="both", expand=True, padx=10, pady=10)

            inner_frame = scrolled  # ← este es el frame real donde agregás los widgets

            barras_estado = {}

            for url in urls:
                frame_disp = ttk.Frame(inner_frame, padding=10, relief="ridge")
                frame_disp.pack(fill="x", pady=5)

                nombre = nombres.get(url, url.split("//")[-1].split("/")[0])

                # Título centrado (h1-like)
                ttk.Label(frame_disp, text=nombre, font=("Segoe UI", 13, "bold"), anchor="center", justify="center").pack(fill="x", pady=(0, 5))

                # Progressbar
                barra = ttk.Progressbar(frame_disp, mode="indeterminate", length=300)
                barra.pack(pady=(0, 5))
                barra.start()

                # Estado
                label = ttk.Label(frame_disp, text="Esperando...", font=("Segoe UI", 10), anchor="center", justify="center")
                label.pack(fill="x")

                barras_estado[url] = (label, barra)



            return top_estado, barras_estado



        def confirmar():
            seleccionados = []
            for disp, var, chk in check_widgets:
                estado = str(chk.cget("state"))
                if var.get() and estado == "normal":
                    seleccionados.append(disp["url"])

            if not seleccionados:
                messagebox.showwarning("Sin selección", "Debes seleccionar al menos un dispositivo en línea.")
                return

            toplevel.destroy()
            url_nombre = {disp["url"]: disp["nombre"] for disp, var, chk in check_widgets}

            # 👉 Ventana de estado visual por dispositivo
            top_estado, barras_estado = ventana_estado_envio(seleccionados, url_nombre)


            def enviar_por_dispositivo(url, datos_a_enviar, modo):
                label, barra = barras_estado[url]

                def actualizar_estado(msg):
                    print(msg)
                    label.config(text=msg)
                    if msg.startswith("✅") or msg.startswith("❌"):
                        barra.stop()
                        self.estado_finalizados["count"] += 1
                        if self.estado_finalizados["count"] == self.total_dispositivos:
                            ttk.Button(top_estado, text="Cerrar", command=top_estado.destroy).pack(pady=10)

                try:
                    client = DispositivoAPIClient(url, estado_callback=actualizar_estado)
                    actualizar_estado(f"🟡 Enviando ({modo})...")
                    client.enviar_delete()

                    total = len(datos_a_enviar)
                    for i in range(0, total, self.BATCH_SIZE):
                        batch = datos_a_enviar[i:i + self.BATCH_SIZE]
                        json_batch = [{
                            "codigo": art[1],
                            "descripcion": art[2],
                            "precio": art[3],
                            "img_base64": art[4],
                            "formato_imagen": art[5]
                        } for art in batch]
                        client.enviar_post_json(json_batch)

                    actualizar_estado("✅ Enviado correctamente")
                except Exception as e:
                    actualizar_estado(f"❌ Error: {e}")

            for url in seleccionados:
                threading.Thread(
                    target=enviar_por_dispositivo,
                    args=(url, datos_a_enviar, modo),
                    daemon=True
                ).start()

        ttk.Button(toplevel, text="Enviar", command=confirmar).pack(pady=10)
    
"""
