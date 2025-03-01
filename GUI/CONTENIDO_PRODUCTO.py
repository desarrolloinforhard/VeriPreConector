#import tkinter as tk
import ttkbootstrap as ttk
import threading
from ASSETS.path_img import *
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import *
from pprint import pprint


class ContenidoProducto:
    def __init__(self, DICT_WIDGETS):
        self.DICT_WIDGETS = DICT_WIDGETS
        self.CONEXIONDBA = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA")
        self.CONEXION_INFORHARD = self.DICT_WIDGETS.get_widget("DATABASE","CONEXION_INFORHARD")
        if self.CONEXION_INFORHARD:
            self.CONEXIONDBA_SYBASE = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA_SYBASE")
        self.variables_globales()
        self.frame_producto = self.DICT_WIDGETS.get_widget("GUI_MAIN", "frame_seccion_productos")
        
        self.label_producto = ttk.Label(self.frame_producto, text="SECCION PRODUCTOS")
        self.label_producto.pack(pady=10)
        
        self.crear_interfaz_table_view()
        
        self.button_crear_datos = ttk.Button(self.frame_producto, text="Crear Datos", command=self.command_crear_datos)
        self.button_crear_datos.pack(padx=50, pady=10)
        
        self.ctk_loader =  self.DICT_WIDGETS.get_widget("VARIABLES_GLOBALES", "ctk_loader")
        
        
    def crear_interfaz_table_view(self):
        self.frame_table_view = ttk.Frame(self.frame_producto)
        self.frame_table_view.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        colors = self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja").style.colors
        coldata = [
            {"text": "Producto", "stretch": False},
            {"text": "Codígo de Barras", "stretch": False},
            {"text": "Precio", "stretch": False},
        ]
        
        
        self.dt = Tableview(
            master=self.frame_table_view,
            coldata=coldata,
            #rowdata=rowdata,
            paginated=True,
            pagesize=100,
            searchable=True,
            autoalign=True,
            height=3,
            bootstyle=PRIMARY,
            stripecolor=(colors.light, None),
        )
        self.dt.align_heading_center(cid=0)
        self.dt.align_heading_center(cid=1)
        self.dt.align_heading_center(cid=2)
        self.dt.align_column_center(cid=0)
        self.dt.align_column_center(cid=1)
        self.dt.align_column_center(cid=2)
        self.dt.pack(side="left", fill=BOTH, padx=10, pady=10)
        
        self.frame_img_producto = ttk.Frame(self.frame_table_view)
        self.frame_img_producto.pack(side="right", fill=BOTH, expand=True, padx=10, pady=10)
        self.label_img_producto = ttk.Label(
            self.frame_img_producto, 
            text="", 
            image=self.IMG_NO_FOTO,
            anchor="center",  # Asegura que el contenido se centre
            #bootstyle="inverse-success"
        )

        self.label_img_producto.place(relx=0.5, rely=0.5, relwidth=1, relheight=1, anchor="center")


        
#/////////////////////////////////////////// COMMAND_BUTTONS ///////////////////////////////////////////
    def command_crear_datos(self):
        try:
            threading.Thread(target=self.DICT_WIDGETS.get_widget("CTK_Loader_Frame","start")).start()
            if self.CONEXION_INFORHARD:
                self.buscar_datos_en_tabla_ARTICULOS()
                self.buscar_datos_tabla_CODBARP()
                threading.Thread(target=self.insertar_datos_en_table_view).start()
        except Exception as e:
            print(f"Error: {e}")

    #/////////////////////////////////////////// DATABASE ///////////////////////////////////////////
    def buscar_datos_en_tabla_ARTICULOS(self):
        """Obtiene los artículos con códigos de barras válidos"""
        CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS = """
            SELECT CREF, CDETALLE, CCODEBAR, NPVP1 
            FROM ARTICULO 
            WHERE CCODEBAR IS NOT NULL AND CCODEBAR <> ''
            ORDER BY CREF;
        """
        self.datos_ARTICULOS = self.CONEXIONDBA_SYBASE.ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS)

    def buscar_datos_tabla_CODBARP(self):
        """Obtiene los códigos de barra adicionales y los une con la lista de productos"""
        
        self.datos_PRODUCTOS_COMPLETOS = []

        if not self.datos_ARTICULOS:
            print("No hay datos en ARTICULO")
            return

        # Obtener lista de referencias (CREF) de los productos
        crefs = tuple(producto[0] for producto in self.datos_ARTICULOS)

        # Consulta optimizada: buscar todos los códigos adicionales en una sola consulta
        CONSULTA_SQL_BUSCAR_DATOS_CODBARP = f"""
            SELECT CREF, CDETALLE, CCODEBAR 
            FROM CODBARP 
            WHERE CREF IN {crefs} AND CCODEBAR IS NOT NULL AND CCODEBAR <> '';
        """

        # Ejecutar la consulta de una sola vez
        datos_codbarp = self.CONEXIONDBA_SYBASE.ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_CODBARP)
        
        # Convertir los resultados en un diccionario {CREF: [(CDETALLE, CCODEBAR), ...]}
        codbarp_dict = {}
        if datos_codbarp:
            for cref, cdetalle, ccodebar in datos_codbarp:
                if cref not in codbarp_dict:
                    codbarp_dict[cref] = []
                codbarp_dict[cref].append((cdetalle, ccodebar))

        # Unir los datos de ARTICULO con CODBARP
        for producto in self.datos_ARTICULOS:
            cref, cdetalle, ccodebar, npvp1 = producto
            self.datos_PRODUCTOS_COMPLETOS.append(producto)

            # Si hay más códigos de barra, agregarlos
            if cref in codbarp_dict:
                for cdetalle_extra, ccodebar_extra in codbarp_dict[cref]:
                    self.datos_PRODUCTOS_COMPLETOS.append((cref, cdetalle_extra, ccodebar_extra, npvp1))

                
        
    def variables_globales(self):
        self.datos_ARTICULOS = []
        self.datos_PRODUCTOS_COMPLETOS = []
        self.IMG_NO_FOTO = READ_IMG(PNG_No_Foto(), 450, 450)
        
        
    def insertar_datos_en_table_view(self):
        try:
            # Insertar nuevos datos
            for producto in self.datos_PRODUCTOS_COMPLETOS:
                self.dt.insert_row("end", [producto[1], producto[2], producto[3]])

            # Recargar datos en la tabla
            self.dt.load_table_data()
            self.dt.autofit_columns()

            # 🔹 Ajustar la altura dinámicamente según la cantidad de filas
            nueva_altura = min(20, len(self.datos_PRODUCTOS_COMPLETOS))  # Máximo 20 filas visibles
            self.dt.configure(height=nueva_altura)  # Cambia la altura del widget

            # 🔹 Volver a empaquetar para reflejar cambios
            self.dt.pack_forget()  # Elimina el widget temporalmente
            self.dt.pack(side="left", fill=BOTH, padx=10, pady=10)  # Vuelve a empaquetar

            self.dt.update_idletasks()  # 🔹 Fuerza la actualización de la interfaz
            self.DICT_WIDGETS.get_widget("CTK_Loader_Frame","stop")()

        except Exception as e:
            print(e)
            self.DICT_WIDGETS.get_widget("CTK_Loader_Frame","stop")()
        