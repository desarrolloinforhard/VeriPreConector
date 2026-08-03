import queue
import threading

import ttkbootstrap as ttk
from ttkbootstrap.widgets import Floodgauge

from core.services.headless_envio_service import HeadlessEnvioService
from core.ui.responsive import fit_toplevel_to_workarea


class HeadlessProgressWindow:
    def __init__(self, modo):
        self.modo = modo
        self.exit_code = 0
        self._cola = queue.Queue()
        self._finalizado = False

        self.root = ttk.Window(themename="flatly")
        self.root.title("VeriPre Connector - Envio")
        fit_toplevel_to_workarea(self.root, 560, 190, min_width=520, min_height=180)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._cerrar_si_finalizo)

        self._crear_interfaz()

    def ejecutar(self):
        self.progress.start(10)
        threading.Thread(target=self._ejecutar_envio, daemon=True).start()
        self.root.after(100, self._procesar_cola)
        self.root.mainloop()
        return self.exit_code

    def _crear_interfaz(self):
        contenedor = ttk.Frame(self.root, padding=16)
        contenedor.pack(fill="both", expand=True)
        contenedor.columnconfigure(0, weight=1)

        titulo = "Transmitiendo datos completos" if self.modo == "completo" else "Transmitiendo novedades"
        self.lbl_titulo = ttk.Label(contenedor, text=titulo, font=("Segoe UI", 13, "bold"))
        self.lbl_titulo.grid(row=0, column=0, sticky="w")

        self.lbl_estado = ttk.Label(
            contenedor,
            text="Preparando envio...",
            anchor="w",
            font=("Segoe UI", 10),
        )
        self.lbl_estado.grid(row=1, column=0, sticky="ew", pady=(12, 8))

        self.progress = Floodgauge(
            contenedor,
            mode="indeterminate",
            bootstyle="info",
            text="Enviando...",
            length=500,
        )
        self.progress.grid(row=2, column=0, sticky="ew", pady=(0, 14))

        acciones = ttk.Frame(contenedor)
        acciones.grid(row=3, column=0, sticky="e")

        self.btn_aceptar = ttk.Button(
            acciones,
            text="Aceptar",
            command=self._cerrar,
            state="disabled",
            bootstyle="primary",
        )
        self.btn_aceptar.pack(side="right")

    def _ejecutar_envio(self):
        service = HeadlessEnvioService(progress_callback=self._emitir)
        try:
            if self.modo == "completo":
                exit_code = service.transmitir_completo()
            else:
                exit_code = service.transmitir_novedades()
        except Exception as exc:
            exit_code = 1
            self._emitir(f"ERROR general: {exc}")
        finally:
            service.cerrar()

        self._cola.put(("done", exit_code))

    def _emitir(self, mensaje):
        self._cola.put(("message", mensaje))

    def _procesar_cola(self):
        while True:
            try:
                tipo, valor = self._cola.get_nowait()
            except queue.Empty:
                break

            if tipo == "message":
                self._agregar_mensaje(valor)
            elif tipo == "done":
                self._finalizar(valor)

        if not self._finalizado:
            self.root.after(100, self._procesar_cola)

    def _agregar_mensaje(self, mensaje):
        self.lbl_estado.configure(text=self._mensaje_visible(mensaje))

    def _finalizar(self, exit_code):
        self.exit_code = exit_code
        self._finalizado = True
        self.progress.stop()

        if exit_code == 0:
            mensaje = "Envio finalizado correctamente."
            bootstyle = "success"
            texto_progress = "Finalizado"
        else:
            mensaje = "Envio finalizado con errores. Revise la consola/log."
            bootstyle = "danger"
            texto_progress = "Con errores"

        self._agregar_mensaje(mensaje)
        self.lbl_titulo.configure(text="Envio finalizado")
        self.progress.configure(mode="determinate", value=100, text=texto_progress, bootstyle=bootstyle)
        self.btn_aceptar.configure(state="normal")
        self.btn_aceptar.focus_set()
        self.root.bell()

    def _cerrar_si_finalizo(self):
        if self._finalizado:
            self._cerrar()

    def _cerrar(self):
        self.root.destroy()

    def _mensaje_visible(self, mensaje):
        mensaje = str(mensaje).replace("\n", " ").strip()
        if len(mensaje) <= 86:
            return mensaje
        return f"{mensaje[:83]}..."
