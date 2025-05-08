import os
import json
import threading
import requests
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledFrame
from core.network.api_client import DispositivoAPIClient
from core.network.urls_dispositivos import VeriPreDispositivosURLBuilder


class DispositivoSender:
    def __init__(self, conexion_dba, parent_tk, batch_size=1000):
        self.conexion_dba = conexion_dba
        self.parent_tk = parent_tk
        self.batch_size = batch_size

    def seleccionar_dispositivos(self):
        builder = VeriPreDispositivosURLBuilder(self.conexion_dba)
        dispositivos = builder.obtener_urls_api("/api/veri/batch_productos")

        resultado = []
        top = ttk.Toplevel(self.parent_tk)
        top.title("Seleccionar Dispositivos")
        top.geometry("500x500")
        top.place_window_center()
        top.grab_set()

        ttk.Label(top, text="Selecciona los dispositivos para enviar:", font=("Segoe UI", 11)).pack(pady=(10, 5))

        frame_scroll = ttk.Frame(top)
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
            for var, chk in vars_check:
                if str(chk.cget("state")) == "normal":
                    var.set(var_todos.get())

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
            chk = ttk.Checkbutton(scroll_frame, text="⏳", variable=var, state="disabled")
            chk.pack(anchor="w", padx=20, pady=2)
            check_widgets.append((disp, var, chk))
            vars_check.append((var, chk))
            threading.Thread(target=verificar_dispositivo, args=(disp, var, chk), daemon=True).start()

        def confirmar():
            for disp, var, chk in check_widgets:
                if var.get() and str(chk.cget("state")) == "normal":
                    resultado.append(disp["url"])
            top.destroy()

        ttk.Button(top, text="Enviar", command=confirmar).pack(pady=10)
        self.parent_tk.wait_window(top)
        self.url_a_nombre = {disp["url"]: disp["nombre"] for disp, var, chk in check_widgets}
        return resultado

    def _ventana_estado_envio(self, urls, url_a_nombre):
        top = ttk.Toplevel(self.parent_tk)
        top.title("Estado de Envío a Dispositivos")
        top.geometry("600x500")
        top.place_window_center()
        top.grab_set()

        ttk.Label(top, text="Estado de transmisión por dispositivo", font=("Segoe UI", 12)).pack(pady=10)
        scrolled = ScrolledFrame(top, autohide=True)
        scrolled.pack(fill="both", expand=True, padx=10, pady=10)

        barras_estado = {}
        for url in urls:
            frame = ttk.Frame(scrolled, padding=10, relief="ridge")
            frame.pack(fill="x", pady=5)
            nombre = url_a_nombre.get(url, url)
            ttk.Label(
                frame,
                text=nombre,
                font=("Segoe UI", 13, "bold"),
                anchor="center",
                justify="center"
            ).pack(fill="x", pady=(0, 5))

            barra = ttk.Progressbar(frame, mode="indeterminate", length=300)
            barra.pack(pady=(5, 5))
            barra.start()
            label = ttk.Label(frame, text="Esperando...", font=("Segoe UI", 10))
            label.pack()
            barras_estado[url] = (label, barra)

        return top, barras_estado

    def enviar_datos(self, urls, datos, modo="completo"):
        top_estado, barras_estado = self._ventana_estado_envio(urls, self.url_a_nombre)
        finalizados = {"count": 0}

        def enviar(url):
            label, barra = barras_estado[url]

            def actualizar(msg):
                label.config(text=msg)
                if msg.startswith("✅") or msg.startswith("❌"):
                    barra.stop()
                    finalizados["count"] += 1
                    if finalizados["count"] == len(urls):
                        ttk.Button(top_estado, text="Cerrar", command=top_estado.destroy).pack(pady=10)

            try:
                client = DispositivoAPIClient(url, estado_callback=actualizar)
                actualizar(f"🟡 Enviando ({modo})...")

                if modo == "novedades":
                    for art in datos:
                        try:
                            actualizar(f"📦 Enviando: {art[2]}...")
                            client.enviar_post_json([{
                                "codigo": art[0],
                                "descripcion": art[1],
                                "precio": art[2],
                                "img_base64": art[3],
                                "formato_imagen": art[4]
                            }])
                        except Exception as e:
                            actualizar(f"❌ Error con {art[2]}: {e}")
                elif modo == "rango_fecha":
                    for i in range(0, len(datos), self.batch_size):
                        batch = datos[i:i + self.batch_size]
                        json_batch = [{
                            "codigo": art[0],
                            "descripcion": art[1],
                            "precio": art[2],
                            "img_base64": art[3],
                            "formato_imagen": art[4]
                        } for art in batch]

                        if batch:
                            actualizar(f"📦 Enviando producto de fecha: {batch[0][1]} ...")
                        client.enviar_post_json(json_batch)
                    actualizar("✅ Rango de fecha enviado correctamente")
                else:
                    client.enviar_delete()
                    for i in range(0, len(datos), self.batch_size):
                        batch = datos[i:i + self.batch_size]
                        json_batch = [{
                            "codigo": art[0],
                            "descripcion": art[1],
                            "precio": art[2],
                            "img_base64": art[3],
                            "formato_imagen": art[4]
                        } for art in batch]

                        if batch:
                            actualizar(f"📦 Enviando lote: {batch[0][2]} ...")
                        client.enviar_post_json(json_batch)

                actualizar("✅ Enviado correctamente")
            except Exception as e:
                actualizar(f"❌ Error: {e}")

        for url in urls:
            threading.Thread(target=enviar, args=(url,), daemon=True).start()


    def enviar_publicidades(self, urls, items):
        top_estado, barras_estado = self._ventana_estado_envio(urls, self.url_a_nombre)
        finalizados = {"count": 0}

        def enviar(url):
            label, barra = barras_estado[url]

            def actualizar(msg):
                label.config(text=msg)
                if msg.startswith("✅") or msg.startswith("❌"):
                    barra.stop()
                    finalizados["count"] += 1
                    if finalizados["count"] == len(urls):
                        ttk.Button(top_estado, text="Cerrar", command=top_estado.destroy).pack(pady=10)

            try:
                # Limpiar carpeta y tabla antes de enviar
                vaciar_ad_medias(url, actualizar)
                for item in items:
                    filepath = item["filepath"]
                    posicion = item["grid"][0] * 4 + item["grid"][1] + 1
                    nombre = os.path.splitext(os.path.basename(filepath))[0]
                    formato = os.path.splitext(filepath)[1][1:].lower()

                    if formato in ["jpg", "jpeg", "png", "gif", "webp"]:
                        path_api = "/api/veri/ad_medias_images"
                    elif formato in ["mp4", "avi", "mov", "mkv", "webm"]:
                        path_api = "/api/veri/ad_medias_videos"
                    else:
                        actualizar(f"❌ Formato no soportado: {formato}")
                        continue

                    url_post = url.split("/api")[0] + path_api
                    json_data = {
                        "nro_posicion": posicion,
                        "nombre_media": nombre,
                        "formato_media": formato
                    }

                    with open(filepath, "rb") as f:
                        files = {
                            "json": (None, json.dumps(json_data), "application/json"),
                            "file": (os.path.basename(filepath), f, "application/octet-stream")
                        }
                        actualizar(f"▶ Enviando {nombre}...")
                        requests.post(url_post, files=files)

                # Reiniciar launcher
                try:
                    requests.post(url.split("/api")[0] + "/api/veri/reiniciar_launcher")
                    actualizar("✅ Launcher reiniciado")
                except:
                    actualizar("⚠ No se pudo reiniciar launcher")

            except Exception as e:
                actualizar(f"❌ Error general: {e}")
                
        def vaciar_ad_medias(url, actualizar):
            try:
                url_delete = url.split("/api")[0] + "/api/veri/vaciar_ad_medias"
                respuesta = requests.delete(url_delete)
                if respuesta.status_code == 200:
                    actualizar("🗑 Carpeta y base de datos ad_medias vaciadas")
                else:
                    actualizar(f"⚠ No se pudo vaciar ad_medias: {respuesta.status_code}")
            except Exception as e:
                actualizar(f"❌ Error al vaciar ad_medias: {e}")

        for url in urls:
            threading.Thread(target=enviar, args=(url,), daemon=True).start()
    
    def enviar_logo_principal(self, urls, ruta_imagen_logo):
        top_estado, barras_estado = self._ventana_estado_envio(urls, self.url_a_nombre)
        finalizados = {"count": 0}

        def enviar(url):
            label, barra = barras_estado[url]

            def actualizar(msg):
                label.config(text=msg)
                if msg.startswith("✅") or msg.startswith("❌"):
                    barra.stop()
                    finalizados["count"] += 1
                    if finalizados["count"] == len(urls):
                        ttk.Button(top_estado, text="Cerrar", command=top_estado.destroy).pack(pady=10)

            try:
                nombre = "!!!LOGO_PRINCIPAL!!!"
                formato = os.path.splitext(ruta_imagen_logo)[1][1:].lower()

                if formato not in ["jpg", "jpeg", "png", "webp"]:
                    actualizar(f"❌ Formato no soportado: {formato}")
                    return

                path_api = "/api/veri/ad_medias_images"
                url_post = url.split("/api")[0] + path_api
                json_data = {
                    "nro_posicion": 0,
                    "nombre_media": nombre,
                    "formato_media": formato
                }

                with open(ruta_imagen_logo, "rb") as f:
                    files = {
                        "json": (None, json.dumps(json_data), "application/json"),
                        "file": (os.path.basename(ruta_imagen_logo), f, "application/octet-stream")
                    }
                    actualizar(f"▶ Enviando logo...")
                    r = requests.post(url_post, files=files)
                    if r.status_code == 200:
                        actualizar("✅ Logo enviado correctamente")
                    else:
                        actualizar(f"❌ Error HTTP: {r.status_code}")

                try:
                    requests.post(url.split("/api")[0] + "/api/veri/reiniciar_launcher")
                    actualizar("✅ Launcher reiniciado")
                except:
                    actualizar("⚠ No se pudo reiniciar launcher")

            except Exception as e:
                actualizar(f"❌ Error al enviar logo: {e}")

        for url in urls:
            threading.Thread(target=enviar, args=(url,), daemon=True).start()

