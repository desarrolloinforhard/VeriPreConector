import threading

import requests
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledFrame

from core.network.urls_dispositivos import ENDPOINT_STATUS, VeriPreDispositivosURLBuilder
from core.services.dispositivos_envio_service import DispositivosEnvioService


class DispositivoSender:
    def __init__(self, conexion_dba, parent_tk, batch_size=1000):
        self.conexion_dba = conexion_dba
        self.parent_tk = parent_tk
        self.batch_size = batch_size
        self.envio_service = DispositivosEnvioService(conexion_dba, batch_size=batch_size)
        self.url_a_nombre = {}

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

        ttk.Checkbutton(
            scroll_frame,
            text="Seleccionar todos",
            variable=var_todos,
            command=toggle_all,
        ).pack(anchor="w", padx=10, pady=(5, 10))

        def aplicar_estado_dispositivo(chk, estado, texto):
            try:
                if top.winfo_exists() and chk.winfo_exists():
                    chk.config(state=estado, text=texto)
            except Exception:
                pass

        def verificar_dispositivo(dispositivo, chk):
            try:
                base_url = dispositivo["url"].split("/api")[0]
                respuesta = requests.get(f"{base_url}{ENDPOINT_STATUS}", timeout=2)
                if respuesta.status_code == 200:
                    self.parent_tk.after(
                        0,
                        aplicar_estado_dispositivo,
                        chk,
                        "normal",
                        f"Online - {dispositivo['nombre']}",
                    )
                    return
            except Exception:
                pass

            try:
                base_url = dispositivo["url"].split("/api")[0]
                respuesta = requests.get(f"{base_url}/", timeout=2)
                if respuesta.status_code == 200:
                    self.parent_tk.after(
                        0,
                        aplicar_estado_dispositivo,
                        chk,
                        "normal",
                        f"Online - {dispositivo['nombre']}",
                    )
                    return
            except Exception:
                pass

            self.parent_tk.after(
                0,
                aplicar_estado_dispositivo,
                chk,
                "disabled",
                f"Offline - {dispositivo['nombre']}",
            )

        for disp in dispositivos:
            var = ttk.BooleanVar(value=False)
            chk = ttk.Checkbutton(scroll_frame, text="Comprobando...", variable=var, state="disabled")
            chk.pack(anchor="w", padx=20, pady=2)
            check_widgets.append((disp, var, chk))
            vars_check.append((var, chk))
            threading.Thread(target=verificar_dispositivo, args=(disp, chk), daemon=True).start()

        def confirmar():
            for disp, var, chk in check_widgets:
                try:
                    if chk.winfo_exists() and var.get() and str(chk.cget("state")) == "normal":
                        resultado.append(disp["url"])
                except Exception:
                    pass
            top.destroy()

        ttk.Button(top, text="Enviar", command=confirmar).pack(pady=10)
        self.parent_tk.wait_window(top)
        self.url_a_nombre = {disp["url"]: disp["nombre"] for disp, _var, _chk in check_widgets}
        return resultado

    def _ventana_estado_envio(self, urls, url_a_nombre):
        top = ttk.Toplevel(self.parent_tk)
        top.title("Estado de Envio a Dispositivos")
        top.geometry("600x500")
        top.place_window_center()
        top.grab_set()

        ttk.Label(top, text="Estado de transmision por dispositivo", font=("Segoe UI", 12)).pack(pady=10)
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
                justify="center",
            ).pack(fill="x", pady=(0, 5))

            barra = ttk.Progressbar(frame, mode="indeterminate", length=300)
            barra.pack(pady=(5, 5))
            barra.start()
            label = ttk.Label(frame, text="Esperando...", font=("Segoe UI", 10))
            label.pack()
            barras_estado[url] = (label, barra)

        return top, barras_estado

    def _actualizar_estado_envio(self, top_estado, label, barra, finalizados, total_urls, msg, url=None, on_device_finished=None):
        es_final = msg.startswith("FINAL_OK:") or msg.startswith("FINAL_ERROR:")
        texto = msg.replace("FINAL_OK:", "", 1).replace("FINAL_ERROR:", "", 1).strip()

        def aplicar():
            label.config(text=texto)
            if es_final:
                barra.stop()
                finalizados["count"] += 1
                if on_device_finished and url:
                    try:
                        on_device_finished(url, msg)
                    except Exception:
                        pass
                if finalizados["count"] == total_urls:
                    ttk.Button(top_estado, text="Cerrar", command=top_estado.destroy).pack(pady=10)

        self.parent_tk.after(0, aplicar)

    def _enviar_en_hilos(self, urls, enviar_callback, on_device_finished=None):
        top_estado, barras_estado = self._ventana_estado_envio(urls, self.url_a_nombre)
        finalizados = {"count": 0}

        def enviar(url):
            label, barra = barras_estado[url]

            def actualizar(msg):
                self._actualizar_estado_envio(
                    top_estado,
                    label,
                    barra,
                    finalizados,
                    len(urls),
                    msg,
                    url=url,
                    on_device_finished=on_device_finished,
                )

            try:
                enviar_callback(url, actualizar)
            except Exception as e:
                actualizar(f"FINAL_ERROR: Error: {e}")

        for url in urls:
            threading.Thread(target=enviar, args=(url,), daemon=True).start()

    def enviar_datos(self, urls, datos, modo="completo"):
        self._enviar_en_hilos(
            urls,
            lambda url, actualizar: self.envio_service.enviar_productos(
                url,
                datos,
                modo=modo,
                estado_callback=actualizar,
            ),
        )

    def enviar_publicidades(self, urls, items, on_device_finished=None):
        self._enviar_en_hilos(
            urls,
            lambda url, actualizar: self.envio_service.enviar_publicidades(
                url,
                items(url) if callable(items) else items,
                estado_callback=actualizar,
            ),
            on_device_finished=on_device_finished,
        )

    def enviar_logo_principal(self, urls, ruta_imagen_logo):
        self._enviar_en_hilos(
            urls,
            lambda url, actualizar: self.envio_service.enviar_logo_principal(
                url,
                ruta_imagen_logo,
                estado_callback=actualizar,
            ),
        )

    def obtener_go_upc_key_guardada(self):
        return self.envio_service.obtener_go_upc_key_guardada()

    def enviar_go_upc_key(self, base_url, api_key):
        return self.envio_service.enviar_go_upc_key(base_url, api_key)
