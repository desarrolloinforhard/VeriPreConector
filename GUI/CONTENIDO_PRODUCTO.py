#import tkinter as tk
import base64
import os
import threading
import ttkbootstrap as ttk
from io import BytesIO
from tkinter import filedialog
from PIL import Image, ImageTk  # Para manejar imágenes
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
        self.dt.view.bind("<<TreeviewSelect>>", self.mostrar_imagen_producto)
        self.dt.view.bind("<Double-1>", self.abrir_detalle_producto)
        
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
                threading.Thread(target=self.insertar_datos_en_table_view).start()
        except Exception as e:
            print(f"Error: {e}")

    #/////////////////////////////////////////// DATABASE ///////////////////////////////////////////
    def buscar_datos_en_tabla_ARTICULOS(self):
        """Obtiene los artículos con códigos de barras válidos"""
        CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS = """
            SELECT * FROM productos ORDER BY descripcion;
        """
        self.datos_ARTICULOS = self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS)

                
        
    def variables_globales(self):
        self.datos_ARTICULOS = []
        self.datos_PRODUCTOS_COMPLETOS = []
        self.IMG_NO_FOTO = READ_IMG(PNG_No_Foto(), 450, 450)
        
        
    def insertar_datos_en_table_view(self):
        try:
            # Insertar nuevos datos
            self.dt.delete_rows()
            
            for producto in self.datos_ARTICULOS:
                precio_formateado = f"${producto[3]:,.2f}"  # Formatea con dos decimales y separador de miles
                self.dt.insert_row("end", [producto[2], producto[1], precio_formateado])


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
            
    def mostrar_imagen_producto(self, event):
        """Función para obtener y mostrar la imagen almacenada en la base de datos."""
        seleccion = self.dt.view.selection()  # Obtener selección
        if not seleccion:
            return

        item = self.dt.view.item(seleccion)  # Obtener datos de la fila seleccionada
        codigo_producto = item["values"][1]  # Obtener el código del producto

        try:
            # Consultar la base de datos para obtener la imagen en Base64 y su formato
            CONSULTA_SQL_OBTENER_IMG = """
            SELECT img_base64, formato_imagen FROM productos WHERE codigo = ?
            """
            resultado = self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_OBTENER_IMG, (codigo_producto,))

            if resultado and resultado[0]:  # Si hay datos y la imagen no es NULL
                img_base64, tipo_imagen = resultado[0]  # Extrae la primera fila correctamente

                if img_base64:  # Verificar que img_base64 no sea None
                    # Decodificar la imagen en Base64
                    imagen_bytes = base64.b64decode(img_base64)

                    # Convertir los bytes en una imagen PIL
                    imagen_pil = Image.open(BytesIO(imagen_bytes))
                    imagen_pil = imagen_pil.resize((450, 450))  # Redimensionar si es necesario

                    # Convertir la imagen PIL a un formato compatible con Tkinter
                    imagen_tk = ImageTk.PhotoImage(imagen_pil)

                    # Guardar la imagen en la instancia para evitar problemas de referencia
                    self.label_img_producto.image = imagen_tk

                    # Actualizar el widget con la imagen cargada
                    self.label_img_producto.config(image=imagen_tk)
                else:
                    # Si img_base64 es None, mostrar la imagen por defecto
                    self.label_img_producto.config(image=self.IMG_NO_FOTO)

            else:
                # Si no hay imagen en la BD, mostrar la imagen por defecto
                self.label_img_producto.config(image=self.IMG_NO_FOTO)

        except Exception as e:
            print(f"Error al recuperar la imagen desde la base de datos: {e}")
            self.label_img_producto.config(image=self.IMG_NO_FOTO)  # Mostrar imagen por defecto en caso de error


            
    def abrir_detalle_producto(self, event):
        """Abre un top-level con los detalles del producto seleccionado o actualiza el existente."""
        
        # Verificar si ya existe un Toplevel abierto
        if hasattr(self, 'top_level_abierto') and self.top_level_abierto.winfo_exists():
            self.top_level_abierto.destroy()

        seleccion = self.dt.view.selection()  # Obtener selección
        if not seleccion:
            return

        item = self.dt.view.item(seleccion)  # Obtener datos de la fila seleccionada
        codigo_producto = item["values"][1]  # Código del producto
        descripcion_producto = item["values"][0]  # Descripción del producto
        precio_producto = item["values"][2]  # Precio del producto

        # Crear una ventana Toplevel
        top = ttk.Toplevel(self)
        top.transient(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        self.top_level_abierto = top  # Guardar referencia al Toplevel
        top.title(f"Detalle del producto {codigo_producto}")
        top.geometry("650x280")
        top.place_window_center()

        # Frame para organizar elementos
        frame_info = ttk.Frame(top)
        frame_info.pack(fill="both", padx=10, pady=10, expand=True)

        # Función para crear un Entry en modo readonly con un Label
        def crear_entry(frame, texto, valor, fila):
            ttk.Label(frame, text=texto).grid(row=fila, column=0, sticky="w", padx=5, pady=5)
            entry = ttk.Entry(frame, state="normal", width=50)  # Más ancho para mayor visibilidad
            entry.grid(row=fila, column=1, padx=5, pady=5, sticky="ew")
            entry.insert(0, valor)
            entry.config(state="readonly")  # Bloquear edición
            return entry

        # Crear los campos con sus valores
        entry_codigo = crear_entry(frame_info, "Código:", codigo_producto, 0)
        entry_descripcion = crear_entry(frame_info, "Descripción:", descripcion_producto, 1)
        entry_precio = crear_entry(frame_info, "Precio:", precio_producto, 2)

        # Frame para la imagen
        frame_img = ttk.Frame(frame_info)
        frame_img.grid(row=0, column=2, rowspan=3, padx=10, pady=5, sticky="n")

        label_img = ttk.Label(frame_img)
        label_img.pack()

        # Función para obtener la imagen desde la base de datos
        def cargar_imagen_desde_db():
            """Obtiene la imagen en Base64 desde la base de datos y la muestra en el label_img."""
            CONSULTA_SQL_OBTENER_IMG = """
            SELECT img_base64, formato_imagen FROM productos WHERE codigo = ?
            """
            resultado = self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_OBTENER_IMG, (codigo_producto,))

            if resultado and resultado[0]:  # Si hay datos y la imagen no es NULL
                img_base64, tipo_imagen = resultado[0]  # Extrae la primera fila correctamente

                if img_base64:  # Verificar que img_base64 no sea None
                    try:
                        # Decodificar la imagen en Base64
                        imagen_bytes = base64.b64decode(img_base64)

                        # Convertir los bytes en una imagen PIL
                        imagen_pil = Image.open(BytesIO(imagen_bytes))
                        imagen_pil = imagen_pil.resize((200, 200))  # Redimensionar a 200x200 píxeles

                        # Convertir la imagen PIL a un formato compatible con Tkinter
                        imagen_tk = ImageTk.PhotoImage(imagen_pil)

                        # Actualizar el widget con la imagen cargada
                        label_img.config(image=imagen_tk, text="")
                        label_img.image = imagen_tk  # Guardar referencia para evitar que la imagen sea eliminada por el recolector de basura
                    except Exception as e:
                        print(f"Error al cargar la imagen desde la base de datos: {e}")
                        mostrar_imagen_por_defecto()
                else:
                    mostrar_imagen_por_defecto()
            else:
                mostrar_imagen_por_defecto()

        def mostrar_imagen_por_defecto():
            """Carga una imagen por defecto si no hay imagen en la base de datos."""
            try:
                img = Image.open(PNG_No_Foto())  # Función que retorna la ruta de la imagen por defecto
                img = img.resize((200, 200))
                img_tk = ImageTk.PhotoImage(img)
                label_img.config(image=img_tk, text="")
                label_img.image = img_tk
            except Exception as e:
                print(f"Error al cargar la imagen por defecto: {e}")

        # Cargar imagen desde la base de datos
        cargar_imagen_desde_db()

        # Función para seleccionar y guardar nueva imagen en la BD
        def seleccionar_imagen():
            archivo = filedialog.askopenfilename(
                title="Seleccionar imagen",
                filetypes=[("Archivos de imagen", "*.png;*.jpg;*.jpeg;*.gif")]
            )
            if archivo:
                try:
                    # Convertir imagen a Base64
                    with open(archivo, "rb") as img_file:
                        img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

                    # Obtener el formato de la imagen
                    formato_imagen = archivo.split(".")[-1]  # Extraer la extensión

                    # Guardar imagen en la base de datos
                    CONSULTA_SQL_GUARDAR_IMG = """
                    UPDATE productos SET img_base64 = ?, formato_imagen = ? WHERE codigo = ?
                    """
                    self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_GUARDAR_IMG, (img_base64, formato_imagen, codigo_producto))

                    # Cargar la nueva imagen en la interfaz
                    cargar_imagen_desde_db()
                    print("Imagen guardada correctamente en la base de datos.")

                except Exception as e:
                    print(f"Error al guardar la imagen en la base de datos: {e}")

        # Botón para cargar nueva imagen
        btn_cargar_img = ttk.Button(frame_info, text="Cargar Imagen", command=seleccionar_imagen)
        btn_cargar_img.grid(row=3, column=2, padx=5, pady=5)


    def guardar_imagen_en_db(self, codigo_producto, ruta_imagen):
        """Convierte la imagen a Base64 y la guarda en la base de datos."""
        if not os.path.exists(ruta_imagen):
            print("Error: La imagen no existe.")
            return

        # Leer la imagen y convertirla en Base64
        with open(ruta_imagen, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        # Obtener la extensión del archivo
        tipo_imagen = os.path.splitext(ruta_imagen)[1].lower().replace(".", "")

        # Guardar en la base de datos (ajusta esto según tu esquema)
        try:
            CONSULTA_SQL_ACTUALIZAR_IMG = """
            UPDATE productos 
            SET img_base64 = ?, formato_imagen = ? 
            WHERE codigo = ?
            """
            self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_ACTUALIZAR_IMG, (img_base64, tipo_imagen, codigo_producto))
            print("Imagen guardada correctamente en la base de datos.")

        except Exception as e:
            print(f"Error al guardar en la base de datos: {e}")
