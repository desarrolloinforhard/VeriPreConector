from ASSETS.path_img import *
import ttkbootstrap as ttk

class Back_Button(ttk.Button):
    def __init__(self, parent, donde_sale, donde_va, **kwargs):
        self.donde_sale = donde_sale
        self.donde_va = donde_va
        # Llamar al constructor de la clase base (ttk.Button)
        self.photo_back = READ_IMG(PNG_Back(), 30, 30)
        super().__init__(parent, image=self.photo_back, command=self.command_back, bootstyle="primary-link",**kwargs)
        
    def mostrar(self):
        self.pack()
        
    def ocultar(self):
        self.pack_forget()
        
    def command_back(self):
        self.donde_sale.pack_forget()
        self.donde_va.pack()