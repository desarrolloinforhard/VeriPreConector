import base64
from datetime import datetime
import os
import threading
import time
import requests
import ttkbootstrap as ttk
from io import BytesIO
from plyer import notification
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from ASSETS.path_img import *
from ttkbootstrap.tableview import Tableview
from ttkbootstrap.constants import *
from pprint import pprint
from core.network.api_client import DispositivoAPIClient
from core.network.urls_dispositivos import VeriPreDispositivosURLBuilder


class ContenidoProducto:
    def __init__(self, DICT_WIDGETS):
        self.DICT_WIDGETS = DICT_WIDGETS
        self.config = self.DICT_WIDGETS.get_widget("CONFIG", "config_json")
        self._vigia_iniciado = False
        self.CONEXIONDBA = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA")
        self.CONEXION_INFORHARD = self.DICT_WIDGETS.get_widget("DATABASE","CONEXION_INFORHARD")
        if self.CONEXION_INFORHARD:
            self.CONEXIONDBA_SYBASE = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA_SYBASE")
        self.variables_globales()
        self.frame_producto = self.DICT_WIDGETS.get_widget("GUI_MAIN", "frame_seccion_productos")
        
        self.label_producto = ttk.Label(self.frame_producto, text="SECCION PRODUCTOS")
        self.label_producto.pack(pady=10)
        
        self.crear_interfaz_table_view()
        
        self.frame_buttons_productos = ttk.Frame(self.frame_producto)
        self.frame_buttons_productos.pack(padx=50, pady=10)
        
        self.button_crear_datos = ttk.Button(self.frame_buttons_productos, text="Buscar Datos", command=self.command_crear_datos)
        self.button_crear_datos.grid(row=0, column=0, padx=10)
        
        self.button_transmitir_novedades = ttk.Button(self.frame_buttons_productos, text="Transmitir Novedades", command=self.command_transmitir_novedades, state=DISABLED)
        self.button_transmitir_novedades.grid(row=0, column=1, padx=10)

        self.button_transmitir_datos = ttk.Button(self.frame_buttons_productos, text="Transmitir Datos Completos", command=self.command_transmitir_datos, state=DISABLED)
        self.button_transmitir_datos.grid(row=0, column=2, padx=10)
        
        # Agregar el nuevo botón en la columna 3
        #self.button_actualizar_datos = ttk.Button(self.frame_buttons_productos, text="Actualizar Datos", command=self.command_actualizar_datos, state=DISABLED)
        #self.button_actualizar_datos.grid(row=0, column=3, padx=10)

        
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
        
        
    def actualizar_barra(self, progreso, total):            
        """Actualiza la barra de progreso con el porcentaje calculado."""
        porcentaje = (progreso / total) * 100
        
        barra_progreso = self.DICT_WIDGETS.get_widget("UI", "BARRA_PROGRESO")
        if barra_progreso is not None:
            barra_progreso['value'] = porcentaje  # Asegúrate de usar 'value' para actualizar la barra
            self.label_porcentaje.configure(text=f"{int(porcentaje)}%")
        else:
            self.mostrar_accion("Error: No se encontró el widget BARRA_PROGRESO.")
            
            
    def creacion_toplevel_carga_datos(self):
        # Crear ventana Toplevel
        self.top_level_carga = ttk.Toplevel()
        self.top_level_carga.title("Cargar Datos")
        
        # Congelar la ventana principal al mostrar esta ventana
        self.top_level_carga.transient(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        self.top_level_carga.grab_set()  # Esto congela la ventana principal
        self.top_level_carga.protocol("WM_DELETE_WINDOW", self.bloquear_cierre)
        
        # Posicionar la ventana en el centro
        self.top_level_carga.geometry("400x250")  # Tamaño ajustado
        self.top_level_carga.place_window_center()

        # Agregar una barra de progreso
        self.progressbar_carga = ttk.Floodgauge(self.top_level_carga, mode="determinate", bootstyle="primary")
        self.DICT_WIDGETS.register("UI", "BARRA_PROGRESO", self.progressbar_carga)
        self.progressbar_carga.pack(fill="x", expand=True, padx=20, pady=(20,10))
        
        # Label de porcentaje con tamaño mayor
        self.label_porcentaje = ttk.Label(self.top_level_carga, text="0%", anchor="center", font=("Arial", 14))
        self.label_porcentaje.pack(pady=10)

        # Entry para mostrar las acciones, con tamaño mayor y centrado
        self.entry_acciones = ttk.Entry(self.top_level_carga, state="readonly", width=40, font=("Arial", 12))
        self.entry_acciones.pack(pady=10)
        self.mostrar_accion("Iniciando la carga de datos...")
        
        
    def bloquear_cierre(self):
        pass  # No hace nada al intentar cerrar
    
    def mostrar_accion(self, texto):
        print(texto)
        """Actualiza el Entry con el texto de la acción que se está realizando."""
        self.entry_acciones.config(state="normal")
        self.entry_acciones.delete(0, "end")
        self.entry_acciones.insert(0, texto)
        self.entry_acciones.config(state="readonly")


        
#/////////////////////////////////////////// COMMAND_BUTTONS ///////////////////////////////////////////
    def command_crear_datos(self):
        if not self.CONEXION_INFORHARD:
            messagebox.showerror("Error de conexión", "No hay conexión con la base de datos.")
            return

        # Iniciar loader (en el hilo principal, así se ve)
        self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "start")()

        def tarea():
            try:
                # Paso 1: buscar artículos
                self.buscar_datos_en_tabla_ARTICULOS()

                if not self.datos_ARTICULOS:
                    messagebox.showwarning("Sin datos", "No se encontraron productos para mostrar.")
                    return

                # Paso 2: preparar datos y mostrar
                self.datos_PRODUCTOS_COMPLETOS = self.datos_ARTICULOS
                self.insertar_datos_en_table_view()

            except Exception as e:
                print(f"Error: {e}")

            finally:
                # Detener loader siempre al final
                self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "stop")()

        # Ejecutar toda la tarea en segundo plano
        threading.Thread(target=tarea, daemon=True).start()

        # Activar el vigía solo si está habilitado
        if self.config.get("sincronizacion_automatica", True) and not self._vigia_iniciado:
            self.iniciar_vigia_actualizacion_productos(intervalo=10)
            self._vigia_iniciado = True

        self.button_crear_datos.config(
            state="disabled", text="Actualizar Datos", command=self.command_actualizar_datos
        )

    def command_transmitir_datos(self):
        self.buscar_datos_en_tabla_ARTICULOS()
        total_registros = len(self.datos_ARTICULOS)

        if total_registros == 0:
            print("No hay datos para enviar.")
            return

        builder = VeriPreDispositivosURLBuilder(self.CONEXIONDBA)
        urls = builder.obtener_urls_api("/api/veri/batch_productos")
        urls_delete = builder.obtener_urls_api("/api/veri/ALL_PRODUCTOS")

        # Primero: eliminar productos de cada dispositivo
        for url in urls_delete:
            print(f"[{url}] → Enviando DELETE para limpiar base de productos...")
            client = DispositivoAPIClient(url, estado_callback=lambda m: print(f"[{url}] {m}"))
            response = client.enviar_delete()
            if response is None:
                print(f"[{url}] ❌ No se pudo limpiar la base, abortando transmisión.")
                return

        # Segundo: enviar datos por lote en hilos (uno por dispositivo)
        batch_size = 1000
        total_batches = (total_registros + batch_size - 1) // batch_size

        for url in urls:
            def enviar_a_dispositivo(url=url):
                client = DispositivoAPIClient(url, estado_callback=lambda m: print(f"[{url}] {m}"))
                for i in range(0, total_registros, batch_size):
                    batch = self.datos_ARTICULOS[i:i + batch_size]
                    batch_json = [
                        {
                            "codigo": item[1],
                            "descripcion": item[2],
                            "precio": item[3],
                            "img_base64": item[4],
                            "formato_imagen": item[5]
                        } for item in batch
                    ]
                    client.enviar_post_json(batch_json)
            threading.Thread(target=enviar_a_dispositivo, daemon=True).start()

                
            
    def command_transmitir_novedades(self):
        """Envía solo los productos modificados a la API."""
        if not self.productos_modificados:
            print("No hay novedades para transmitir.")
            return

        print(f"Transmitiendo {len(self.productos_modificados)} productos modificados...")

        # Buscar solo los productos modificados en la base de datos
        productos_a_enviar = []
        for codigo in self.productos_modificados:
            CONSULTA_SQL = "SELECT * FROM productos WHERE codigo = ?"
            producto = self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL, (codigo,))
            if producto:
                productos_a_enviar.append(producto[0])

        if not productos_a_enviar:
            print("No se encontraron productos en la base de datos.")
            return

        # Formatear datos para enviar a la API
        batch_json = [
            {
                "codigo": item[1],
                "descripcion": item[2],
                "precio": item[3],
                "img_base64": item[4],
                "formato_imagen": item[5]
            } for item in productos_a_enviar
        ]

        builder = VeriPreDispositivosURLBuilder(self.CONEXIONDBA)
        urls = builder.obtener_urls_api("/api/veri/batch_productos")

        for url in urls:
            client = DispositivoAPIClient(url, estado_callback=lambda m: print(f"[{url}] {m}"))
            threading.Thread(target=lambda: client.enviar_post_json(batch_json), daemon=True).start()

        # Mostrar notificación y limpiar cambios
        try:
            notification.notify(
                title="Transmisión de novedades",
                message="Los productos modificados fueron enviados.",
                timeout=5
            )
        except Exception as e:
            print(f"⚠️ No se pudo mostrar notificación: {e}")

        self.productos_modificados.clear()
        self.button_transmitir_novedades.config(state=DISABLED)

            
            
    def command_actualizar_datos(self):
        if not self.CONEXIONDBA_SYBASE:
            messagebox.showerror("Error de conexión", "No hay conexión con la base de datos Sybase.")
            return
        try:
            self.creacion_toplevel_carga_datos()
            threading.Thread(target=self.procesar_productos_a_actualizar).start()
        except Exception as e:
            print(e)
            
            
    def limpiar_base_dispositivo(self):
        builder = VeriPreDispositivosURLBuilder(self.CONEXIONDBA)
        urls = builder.obtener_urls_api("/api/veri/ALL_PRODUCTOS")
        headers = {"Content-Type": "application/json"}

        for url in urls:
            def estado(msg): print(f"DELETE {url}: {msg}")
            client = DispositivoAPIClient(url, estado_callback=estado)
            threading.Thread(target=client.enviar_delete, daemon=True).start()

        
        
    def procesar_productos_a_actualizar(self):
        self.buscar_datos_en_tabla_ARTICULOS_actualizados()
        self.buscar_datos_tabla_CODBARP()
        self.buscar_datos_tabla_IVAS()
        self.actualizar_precios_con_iva()
        self.insertar_o_actualizar_productos()

        self.mostrar_accion("Proceso completo.")

        if self.datos_ARTICULOS:
            pass
            #messagebox.showinfo("Proceso completo", "Se han insertado los nuevos productos y actualizados los pendientes.")
        else:
            messagebox.showwarning("Sin cambios", "No se registraron cambios ha actualizar.")

        self.top_level_carga.destroy()

        # 🔁 🔽 AGREGADO: recargar todos los productos completos
        self.buscar_datos_en_tabla_ARTICULOS()
        threading.Thread(target=self.insertar_datos_en_table_view).start()

        self.button_crear_datos.config(state="disabled", text="Actualizar Datos", command=self.command_actualizar_datos)



    #/////////////////////////////////////////// DATABASE ///////////////////////////////////////////
    def buscar_datos_en_tabla_ARTICULOS(self):
        """Obtiene los artículos con códigos de barras válidos"""
        CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS = """
            SELECT * FROM productos ORDER BY descripcion;
        """
        self.datos_ARTICULOS = self.CONEXIONDBA.ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS)
        print(len(self.datos_ARTICULOS))
        print(self.datos_ARTICULOS)
        self.datos_PRODUCTOS_COMPLETOS = self.datos_ARTICULOS
        
        
    def buscar_datos_en_tabla_ARTICULOS_actualizados(self):
        """Obtiene los artículos con códigos de barras válidos y fecha de actualización de hoy."""
        CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS = """
            SELECT CREF, CDETALLE, CCODEBAR, CTIPOIVA, NPVP1, CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
            FROM ARTICULO 
            WHERE CCODEBAR IS NOT NULL 
            AND CCODEBAR <> '' 
            AND CONVERT(DATE, dFechaU) = CONVERT(DATE, GETDATE())
            ORDER BY dFechaU DESC;
            ;
        """

        try:
            # Ejecutar la consulta en Sybase y almacenar los datos
            self.datos_ARTICULOS = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(
                CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS
            )
            print(f"Total de registros actualizados: {len(self.datos_ARTICULOS)}")


        except Exception as e:
            print(f"Error al actualizar datos: {e}")
            
            
    def buscar_datos_tabla_CODBARP(self):
        """Obtiene los códigos de barra adicionales y los une con la lista de productos."""
        self.datos_PRODUCTOS_COMPLETOS = []
        
        if not self.datos_ARTICULOS:
            self.mostrar_accion("No hay datos en ARTICULO")
            return
        
        crefs = tuple(producto[0] for producto in self.datos_ARTICULOS)
        
        if not crefs:
            return 

        crefs_str = f"('{ "','".join(crefs) }')"  # Convertir a cadena de consulta válida
        CONSULTA_SQL_BUSCAR_DATOS_CODBARP = f"""
            SELECT CREF, CDETALLE, CCODEBAR, CONVERT(VARCHAR, dFechaU, 120) AS DFECHAU
            FROM CODBARP 
            WHERE CREF IN {crefs_str} AND CCODEBAR IS NOT NULL AND CCODEBAR <> ''
            ORDER BY dFechaU ASC;
        """
        
        self.mostrar_accion("Obteniendo códigos de barra adicionales...")
        datos_codbarp = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_CODBARP)
        
        codbarp_dict = {}
        if datos_codbarp:
            for cref, cdetalle, ccodebar, dfechau in datos_codbarp:
                if cref not in codbarp_dict:
                    codbarp_dict[cref] = []
                codbarp_dict[cref].append((cdetalle, ccodebar, dfechau))
        
        total_productos = len(self.datos_ARTICULOS)
        total_codigos_barra = len(datos_codbarp)
        total = total_productos + total_codigos_barra
        progreso = 0

        for idx, producto in enumerate(self.datos_ARTICULOS):
            print(f"Producto {idx}: {producto}")
            cref, cdetalle, ccodebar, ctipoiva, npvp1, dfechau = producto
            self.datos_PRODUCTOS_COMPLETOS.append(producto)
            progreso += 1
            if progreso % 10 == 0:  # Actualiza la barra cada 10 productos
                self.actualizar_barra(progreso, total)
            
            if cref in codbarp_dict:
                for cdetalle_extra, ccodebar_extra, _ in codbarp_dict[cref]:
                    self.datos_PRODUCTOS_COMPLETOS.append((cref, cdetalle_extra, ccodebar_extra, ctipoiva, npvp1, dfechau))
                    progreso += 1
                    if progreso % 10 == 0:  # Actualiza la barra cada 10 productos
                        self.actualizar_barra(progreso, total)

        self.mostrar_accion(f"{len(self.datos_PRODUCTOS_COMPLETOS)} productos completos.")


    def buscar_datos_tabla_IVAS(self):
        """Obtiene los datos de IVAS y muestra la barra de progreso mientras se realiza la consulta."""
        
        self.mostrar_accion("Obteniendo datos de IVAS...")
        
        # Iniciar la barra de progreso en 0%
        self.actualizar_barra(0, 100)

        # Simular el tiempo de espera para la consulta (esto es solo para efectos de la barra)
        # Realmente, la consulta se ejecuta de forma bloqueante, por lo que la barra de progreso puede ir del 0% al 100% al final
        try:
            CONSULTA_SQL_BUSCAR_DATOS_IVAS = f"""
                SELECT * FROM IVAS;
            """
            # Aquí ejecutamos la consulta y almacenamos los resultados
            self.datos_IVAS = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_IVAS)

            # Una vez que la consulta finalice, actualizamos el progreso al 100%
            self.actualizar_barra(100, 100)
            
            self.mostrar_accion(f"{len(self.datos_IVAS)} tipos de IVA encontrados.")
        except Exception as e:
            self.mostrar_accion(f"Error al obtener los datos de IVAS: {str(e)}")

        
    def actualizar_precios_con_iva(self):
        """Actualiza los precios de los productos agregando el IVA correspondiente y muestra el progreso."""
        iva_dict = {str(iva[0]): iva[2] for iva in self.datos_IVAS}
        productos_actualizados = []

        self.mostrar_accion("Actualizando precios con IVA...")

        total_productos = len(self.datos_PRODUCTOS_COMPLETOS)
        if total_productos == 0:
            self.mostrar_accion("No hay productos para actualizar.")
            return

        self.actualizar_barra(0, total_productos)

        for idx, producto in enumerate(self.datos_PRODUCTOS_COMPLETOS):
            codigo_iva = str(producto[3])
            precio_base = producto[4]

            porcentaje_iva = iva_dict.get(codigo_iva, 0.0)
            nuevo_precio = precio_base * (1 + porcentaje_iva / 100)

            producto_actualizado = (
                producto[0],  # cref
                producto[1],  # descripcion
                producto[2],  # codigo
                format(round(nuevo_precio, 2), ".2f"),  # precio actualizado
                producto[5],  # dfechau
            )
            print("actualizar_precios_con_iva", producto_actualizado)
            productos_actualizados.append(producto_actualizado)


            self.actualizar_barra(idx + 1, total_productos)

        self.datos_PRODUCTOS_COMPLETOS = productos_actualizados
        self.mostrar_accion(f"{len(self.datos_PRODUCTOS_COMPLETOS)} productos actualizados con IVA.")

            
        
    def insertar_o_actualizar_productos(self):
        """Inserta o actualiza los productos en la base de datos SQLite en batch con executemany()."""
        
        consulta = """
        INSERT INTO productos (CREF, codigo, descripcion, precio, dfechau) 
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(codigo) DO UPDATE SET 
            CREF = excluded.CREF,
            descripcion = excluded.descripcion,
            precio = excluded.precio,
            dfechau = excluded.dfechau
        """

        self.mostrar_accion("Insertando o actualizando productos...")

        total_productos = len(self.datos_PRODUCTOS_COMPLETOS)
        if total_productos == 0:
            self.mostrar_accion("No hay productos para insertar o actualizar.")
            return

        # Preparar los datos para el execute many
        parametros = [(p[0], p[2], p[1], p[3], p[4]) for p in self.datos_PRODUCTOS_COMPLETOS]
        print(parametros)

        try:
            self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA").ejecutar_consultamany(consulta, parametros)
            print(f"✅ {total_productos} productos insertados/actualizados correctamente.")

            # 🔹 Registrar cambios en self.productos_modificados
            for p in self.datos_PRODUCTOS_COMPLETOS:
                self.registrar_cambio_producto(p[2])  # `p[2]` es el código del producto

            self.mostrar_accion(f"{total_productos} productos procesados.")
        except Exception as e:
            print(f"❌ Error al insertar/actualizar productos: {e}")
            self.mostrar_accion("Error al procesar los productos.")

        self.actualizar_barra(total_productos, total_productos)  # Llenar barra al 100%


        
    def variables_globales(self):
        self.datos_ARTICULOS = []
        self.datos_PRODUCTOS_COMPLETOS = []
        self.IMG_NO_FOTO = READ_IMG(PNG_No_Foto(), 450, 450)
        self.BATCH_SIZE = 1000  # Tamaño del lote
        self.productos_modificados = set()  # Guardará los códigos de productos modificados

        
        
    def insertar_datos_en_table_view(self):
        try:
            self.dt.delete_rows()

            for producto in self.datos_PRODUCTOS_COMPLETOS:
                descripcion = str(producto[2]).strip() if producto[2] else ""
                codigo = producto[1] if producto[1] else ""
                precio = float(producto[3]) if producto[3] else 0.0
                precio_formateado = f"${precio:,.2f}"
                self.dt.insert_row("end", [descripcion, codigo, precio_formateado])
            self.dt.load_table_data()
            self.dt.autofit_columns()

            nueva_altura = min(20, len(self.datos_PRODUCTOS_COMPLETOS))
            self.dt.configure(height=nueva_altura)
            self.dt.pack_forget()
            self.dt.pack(side="left", fill=BOTH, padx=10, pady=10)
            self.dt.update_idletasks()
            time.sleep(2)
            self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "stop")()
            self.button_transmitir_datos.config(state=NORMAL)

        except Exception as e:
            print(f"❌ Error al insertar en la tabla: {e}")
            self.DICT_WIDGETS.get_widget("CTK_Loader_Frame", "stop")()



            
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
                filetypes=[("Archivos de imagen", "*.png;*.jpg;*.jpeg;*.gif;*.webp")]
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
                    self.registrar_cambio_producto(codigo_producto)
                    print("Imagen guardada correctamente en la base de datos.")

                except Exception as e:
                    print(f"Error al guardar la imagen en la base de datos: {e}")

        # Botón para cargar nueva imagen
        btn_cargar_img = ttk.Button(frame_info, text="Cargar Imagen", command=seleccionar_imagen)
        btn_cargar_img.grid(row=3, column=2, padx=5, pady=5)

    def registrar_cambio_producto(self, codigo_producto):
            """Registra que un producto ha sido modificado."""
            self.productos_modificados.add(codigo_producto)
            self.button_transmitir_novedades.config(state=NORMAL)  # Habilitar botón automáticamente
    
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

    def iniciar_vigia_actualizacion_productos(self, intervalo=60):
        def vigia():
            puntos = ["", ".", "..", "..."]
            anim_index = 0

            while True:
                if not self.config.get("sincronizacion_automatica", True):
                    print("⏸️ Vigía pausado por configuración. Esperando activación...", end="\r")
                    time.sleep(5)
                    continue

                try:
                    print(f"🕵️‍♂️ Vigía ejecutando revisión{puntos[anim_index % 4]}   ", end="\r")
                    anim_index += 1

                    sql_local = "SELECT dFechaU FROM productos ORDER BY dFechaU DESC LIMIT 1"
                    res_local = self.CONEXIONDBA.ejecutar_consulta(sql_local)
                    fecha_local = res_local[0][0] if res_local else "2000-01-01 00:00:00"

                    sql_sybase = """
                    SELECT MAX(dFechaU) FROM ARTICULO 
                    WHERE CCODEBAR IS NOT NULL AND CCODEBAR <> ''
                    """
                    res_sybase = self.CONEXIONDBA_SYBASE.ejecutar_consulta(sql_sybase)
                    fecha_remota = res_sybase[0][0] if res_sybase else None

                    if fecha_remota:
                        fmt = "%Y-%m-%d %H:%M:%S"
                        f_local = datetime.strptime(str(fecha_local), fmt)
                        f_remota = datetime.strptime(str(fecha_remota), fmt)

                        if f_remota > f_local:
                            print("🟡 Nueva actualización detectada. Ejecutando actualización...")
                            self.command_actualizar_datos()

                            try:
                                notification.notify(
                                    title="Actualización automática",
                                    message="Se detectaron nuevos productos y se actualizó el catálogo.",
                                    timeout=5
                                )
                            except Exception as e:
                                print(f"⚠️ No se pudo mostrar notificación: {e}")

                except Exception as e:
                    print(f"❌ Vigía error: {e}")

                time.sleep(intervalo)

        threading.Thread(target=vigia, daemon=True).start()