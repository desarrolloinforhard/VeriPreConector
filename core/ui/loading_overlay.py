"""Overlay de carga reutilizable basado únicamente en tkinter/ttk."""

import tkinter as tk

import ttkbootstrap as ttk


class LoadingOverlay:
    """Muestra un bloqueo visual sobre una ventana durante tareas breves.

    La instancia se conserva durante toda la vida de la ventana para poder
    iniciarla y detenerla varias veces sin recrear widgets ni imágenes.
    """

    def __init__(self, master, opacity=0.8, width=40, height=40):
        self.master = master
        self.opacity = max(0.0, min(float(opacity), 1.0))
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self._visible = False

        self.frame = tk.Frame(master, bg="#FFFFFF", bd=0, highlightthickness=0)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)

        self.card = ttk.Frame(self.frame, padding=(28, 22), bootstyle="light")
        self.card.grid(row=0, column=0)
        self.card.grid_columnconfigure(0, weight=1)

        self.message = ttk.Label(
            self.card,
            text="Cargando...",
            anchor="center",
            font=("Segoe UI", 10, "bold"),
            bootstyle="primary",
        )
        self.message.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        progress_length = max(140, self.width * 4)
        self.progress = ttk.Progressbar(
            self.card,
            mode="indeterminate",
            length=progress_length,
            bootstyle="primary-striped",
        )
        self.progress.grid(row=1, column=0, sticky="ew")

    def start_loader(self, message="Cargando..."):
        self.set_message(message)
        if not self._visible:
            self.frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            self.frame.lift()
            self.progress.start(12)
            self._visible = True
        self.master.update_idletasks()

    def stop_loader(self):
        if not self._visible:
            return
        self.progress.stop()
        self.frame.place_forget()
        self._visible = False

    def set_message(self, message):
        self.message.configure(text=str(message or "Cargando..."))

    @property
    def visible(self):
        return self._visible
