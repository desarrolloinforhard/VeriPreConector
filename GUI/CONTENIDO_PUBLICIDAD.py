import tkinter as tk
import ttkbootstrap as ttk
from FUNC.back_button import Back_Button


class ContenidoPublicidad:
    def __init__(self, widgets):
        self.widgets = widgets
        
        self.label_publicidad = ttk.Label(self.widgets.get_widget("GUI_MAIN", "frame_seccion_publicidad"), text="SECCION PUBLICIDAD")
        self.label_publicidad.pack(pady=10)
        
        
    def command_back(self):
        self.donde_sale.pack_forget()
        self.donde_va.pack()
        