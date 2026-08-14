import threading

import requests
import ttkbootstrap as ttk

from core.dao.dispositivos_dao import DispositivosDAO
from core.network.urls_dispositivos import ENDPOINT_STATUS, VeriPreDispositivosURLBuilder
from core.services.device_discovery_service import DeviceDiscoveryService
from core.services.dispositivos_envio_service import DispositivosEnvioService
from core.ui.responsive import fit_toplevel_to_workarea


class DispositivoSender:
    def __init__(self, conexion_dba, parent_tk, batch_size=1000, tipos_descubrir=("verificador", "infotv")):
        self.conexion_dba = conexion_dba
        self.parent_tk = parent_tk
        self.batch_size = batch_size
        self.tipos_descubrir = tuple(tipos_descubrir or ("verificador", "infotv"))
        self.dispositivos_dao = DispositivosDAO(conexion_dba)
        self.envio_service = DispositivosEnvioService(conexion_dba, batch_size=batch_size)
        self.url_a_nombre = {}

    def _descripcion_tipos(self):
        tipos = set(self.tipos_descubrir)
        if tipos == {"verificador"}:
            return "verificadores"
        if tipos == {"infotv"}:
            return "InforTV"
        return "dispositivos"

    def seleccionar_dispositivos(self, endpoint="/api/veri/batch_productos"):
        builder = VeriPreDispositivosURLBuilder(self.conexion_dba)
        dispositivos = builder.obtener_urls_api(endpoint)

        resultado = []
        top = ttk.Toplevel(self.parent_tk)
        top.title("Seleccionar Dispositivos")
        fit_toplevel_to_workarea(top, 560, 560, min_width=500, min_height=460)
        top.place_window_center()
        top.grab_set()

        ttk.Label(
            top,
            text=f"Selecciona los {self._descripcion_tipos()} para enviar:",
            font=("Segoe UI", 11),
        ).pack(pady=(10, 5))
        estado_var = ttk.StringVar(value="Cargando dispositivos registrados...")
        ttk.Label(top, textvariable=estado_var, bootstyle="secondary").pack(pady=(0, 6))

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
        dispositivos_indexados = {}
        detectados_nuevos = {}
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

        def set_estado(msg):
            try:
                if top.winfo_exists():
                    estado_var.set(msg)
            except Exception:
                pass

        def aplicar_estado_dispositivo(chk, estado, texto):
            try:
                if top.winfo_exists() and chk.winfo_exists():
                    chk.config(state=estado, text=texto)
            except Exception:
                pass

        def verificar_dispositivo(dispositivo, chk):
            origen = dispositivo.get("origen", "registrado")
            tipo = dispositivo.get("tipo", "-")
            prefijo = "[Detectado]" if origen == "detectado" else "[Registrado]"
            try:
                base_url = dispositivo["url"].split("/api")[0]
                respuesta = requests.get(f"{base_url}{ENDPOINT_STATUS}", timeout=2)
                if respuesta.status_code == 200:
                    self.parent_tk.after(
                        0,
                        aplicar_estado_dispositivo,
                        chk,
                        "normal",
                        f"{prefijo} {dispositivo['nombre']} ({tipo}) - Online",
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
                        f"{prefijo} {dispositivo['nombre']} ({tipo}) - Online",
                    )
                    return
            except Exception:
                pass

            self.parent_tk.after(
                0,
                aplicar_estado_dispositivo,
                chk,
                "disabled",
                f"{prefijo} {dispositivo['nombre']} ({tipo}) - Offline",
            )

        def agregar_dispositivo_ui(dispositivo, detectado=False):
            key = dispositivo["url"]
            if key in dispositivos_indexados:
                return

            dispositivo = dict(dispositivo)
            dispositivo["origen"] = "detectado" if detectado else "registrado"
            dispositivos_indexados[key] = dispositivo
            var = ttk.BooleanVar(value=False)
            sufijo = " [detectado]" if detectado else ""
            chk = ttk.Checkbutton(scroll_frame, text=f"Comprobando...{sufijo}", variable=var, state="disabled")
            chk.pack(anchor="w", padx=20, pady=2)
            check_widgets.append((dispositivo, var, chk))
            vars_check.append((var, chk))
            self.url_a_nombre[dispositivo["url"]] = dispositivo["nombre"]
            if detectado:
                detectados_nuevos[key] = dispositivo
            threading.Thread(target=verificar_dispositivo, args=(dispositivo, chk), daemon=True).start()

        for disp in dispositivos:
            agregar_dispositivo_ui(
                {
                    "nombre": disp["nombre"],
                    "url": disp["url"],
                    "tipo": self._inferir_tipo_por_endpoint_y_puerto(disp["url"], endpoint),
                },
                detectado=False,
            )

        def descubrir_en_red():
            set_estado(f"Buscando {self._descripcion_tipos()} automaticamente en la red...")
            try:
                service = DeviceDiscoveryService()
                encontrados = service.discover(
                    progress_callback=set_estado,
                    tipos=self.tipos_descubrir,
                    use_cache=True,
                )
            except Exception as e:
                self.parent_tk.after(0, lambda: set_estado(f"Error buscando en red: {e}"))
                return

            def aplicar_descubiertos():
                nuevos = 0
                for disp in encontrados:
                    url = f"http://{disp['ip']}:{disp['puerto']}{endpoint}"
                    dispositivo = {
                        "nombre": disp["nombre"],
                        "url": url,
                        "tipo": disp.get("tipo", "-"),
                        "ip": disp.get("ip"),
                        "puerto": disp.get("puerto"),
                        "comentario": disp.get("comentario") or "Detectado automaticamente en red",
                    }
                    if url not in dispositivos_indexados:
                        agregar_dispositivo_ui(dispositivo, detectado=True)
                        nuevos += 1

                total = len(dispositivos_indexados)
                if nuevos:
                    set_estado(f"Busqueda completa. Nuevos detectados: {nuevos}. Total listados: {total}")
                else:
                    set_estado(f"Busqueda completa. No se detectaron nuevos dispositivos. Total listados: {total}")

            self.parent_tk.after(0, aplicar_descubiertos)

        threading.Thread(target=descubrir_en_red, daemon=True).start()

        def confirmar():
            for disp, var, chk in check_widgets:
                try:
                    if chk.winfo_exists() and var.get() and str(chk.cget("state")) == "normal":
                        resultado.append(disp["url"])
                except Exception:
                    pass
            top.destroy()

        def guardar_detectados():
            guardados = 0
            omitidos = 0
            existentes = {
                (str(data.get("direccion_ip", "")).strip(), int(data.get("puerto", 0) or 0)): nombre
                for nombre, data in self.dispositivos_dao.listar_dict().items()
            }
            for dispositivo in list(detectados_nuevos.values()):
                ip = str(dispositivo.get("ip") or "").strip()
                puerto = int(dispositivo.get("puerto", 0) or 0)
                if not ip or not puerto:
                    omitidos += 1
                    continue
                if (ip, puerto) in existentes:
                    omitidos += 1
                    continue
                nombre = self._generar_nombre_dispositivo_unico(dispositivo, set(self.dispositivos_dao.listar_dict().keys()))
                comentario = dispositivo.get("comentario") or "Detectado automaticamente en red"
                tipo = dispositivo.get("tipo")
                if tipo:
                    comentario = f"{comentario} | Tipo: {tipo}"
                self.dispositivos_dao.crear(nombre, ip, str(puerto), comentario)
                existentes[(ip, puerto)] = nombre
                guardados += 1

            if guardados or omitidos:
                set_estado(f"Detectados guardados: {guardados} | omitidos: {omitidos}")
            else:
                set_estado("No habia detectados nuevos para guardar.")
            if guardados:
                try:
                    self.parent_tk.event_generate("<<DispositivosActualizados>>", when="tail")
                except Exception:
                    pass

        acciones = ttk.Frame(top)
        acciones.pack(fill="x", padx=12, pady=10)
        ttk.Button(acciones, text="Guardar detectados", command=guardar_detectados, bootstyle="success-outline").pack(side="left")
        ttk.Button(acciones, text="Enviar", command=confirmar, bootstyle="primary").pack(side="right")
        self.parent_tk.wait_window(top)
        self.url_a_nombre = {disp["url"]: disp["nombre"] for disp, _var, _chk in check_widgets}
        return resultado

    def _inferir_tipo_por_endpoint_y_puerto(self, url, endpoint):
        try:
            base = url.split("/api")[0]
            puerto = int(base.rsplit(":", 1)[1])
        except Exception:
            puerto = 0
        if puerto == 2727:
            return "infotv"
        if puerto == 8080:
            return "verificador"
        if endpoint == "/api/veri/ad_medias_images":
            return "infotv"
        return "verificador"

    def _generar_nombre_dispositivo_unico(self, dispositivo, existentes=None):
        existentes = set(existentes or ())
        base = (dispositivo.get("nombre") or "Dispositivo detectado").strip()
        nombre = base
        sufijo = 2
        while nombre in existentes:
            nombre = f"{base} ({sufijo})"
            sufijo += 1
        return nombre

    def _ventana_estado_envio(self, urls, url_a_nombre):
        top = ttk.Toplevel(self.parent_tk)
        top.title("Estado de Envio a Dispositivos")
        fit_toplevel_to_workarea(top, 600, 500, min_width=520, min_height=420)
        top.place_window_center()
        top.grab_set()

        ttk.Label(top, text="Estado de transmision por dispositivo", font=("Segoe UI", 12)).pack(pady=10)
        scrolled = ttk.ScrolledFrame(top, autohide=True)
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

    def enviar_config_imagenes(self, base_url, estado_callback=None):
        return self.envio_service.enviar_config_imagenes(base_url, estado_callback=estado_callback)
