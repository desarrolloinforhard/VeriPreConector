from pprint import pprint
import threading
import time
from tkinter import messagebox
import ttkbootstrap as ttk
from FUNC.windows_manager import VentanaManager 
from DB.database_sybase import ConexionSybase, dsn_configurados
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from ASSETS.path_img import *

class GUI_CONFIG:
    def __init__(self, DICT_WIDGETS):
        self.DICT_WIDGETS = DICT_WIDGETS
        self.datos_dispositivos = {}
        self.top_level_configuracion = ttk.Toplevel(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        self.DICT_WIDGETS.register("GUI_CONFIG","top_level_configuracion", self.top_level_configuracion)
        self.top_level_configuracion.protocol("WM_DELETE_WINDOW", self.cierre_top_level_configuracion)
        self.top_level_configuracion.transient(self.DICT_WIDGETS.get_widget("GUI_MAIN", "ventana_creacion_caja"))
        #self.top_level_configuracion.grab_set()
        self.top_level_configuracion.title("VeriPre_Connector - Configuración")
        self.top_level_configuracion.geometry("630x480")
        self.top_level_configuracion.place_window_center()
        
        self.notebook_widget_configuracion = ttk.Notebook(self.top_level_configuracion, bootstyle="primary")
        self.DICT_WIDGETS.register("GUI_CONFIG","notebook_widget_configuracion", self.notebook_widget_configuracion)
        self.creacion_frame_notebook_dispositivos()
        self.creacion_frame_notebook_fuente_datos()
        self.creacion_frame_notebook_config_datos()
        
        self.notebook_widget_configuracion.add(self.frame_notebook_dispositivos, text="Dispositivos", padding=10)
        self.notebook_widget_configuracion.add(self.frame_notebook_fuente_datos, text="Fuente de Datos", padding=10)
        self.notebook_widget_configuracion.add(self.frame_notebook_config_datos, text="Configuración de Datos", padding=10)
        
        self.notebook_widget_configuracion.pack(side="top", expand=True, fill="both")
        
        
#///////////////////////////////////////////////////// NOTEBOOK DISPOSITIVOS /////////////////////////////////////////////////////
        
    def creacion_frame_notebook_dispositivos(self):
        self.frame_notebook_dispositivos = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_dispositivos.pack(fill="both", expand=True)
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_notebook_dispositivos", self.frame_notebook_dispositivos)
        
        
        self.labelframe_opciones = ttk.Labelframe(self.frame_notebook_dispositivos, text="Opciones", bootstyle="primary")
        self.labelframe_opciones.pack(fill="x")
        self.DICT_WIDGETS.register("GUI_CONFIG","labelframe_opciones", self.labelframe_opciones)
        self.creacion_contenido_labelframe_opciones()
        
        
        self.labelframe_datos_dispositivos = ttk.Labelframe(self.frame_notebook_dispositivos, text="Datos de Dispositivo", bootstyle="primary")
        self.labelframe_datos_dispositivos.pack(fill="both", expand=True, pady=10)
        self.DICT_WIDGETS.register("GUI_CONFIG","labelframe_datos_dispositivos", self.labelframe_datos_dispositivos)
        self.creacion_labelframe_datos_dispositivos()       
        
        
    def creacion_contenido_labelframe_opciones(self):
        self.frame_contenedor_combobox_dispositivos = ttk.Frame(self.labelframe_opciones)
        self.frame_contenedor_combobox_dispositivos.pack(side="left", fill="x", expand=True)
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_contenedor_combobox_dispositivos", self.frame_contenedor_combobox_dispositivos)
        self.creacion_contenido_frame_contenedor_combobox_dispositivos()
        
        self.frame_contenedor_botones = ttk.Frame(self.labelframe_opciones)
        self.frame_contenedor_botones.pack(side="right", padx=(0,10), pady=5)
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_contenedor_botones", self.frame_contenedor_botones)
        self.creacion_contenido_frame_contenedor_botones()
        
        
    def creacion_contenido_frame_contenedor_botones(self):
        # Imágenes de los botones
        self.img_agregar = READ_IMG(PNG_Add(), 25, 25)
        self.img_guardar = READ_IMG(PNG_Save(), 25, 25)
        self.img_editar = READ_IMG(PNG_Edit(), 25, 25)
        self.img_eliminar = READ_IMG(PNG_Delete(), 25, 25)

        # Creación de botones
        self.button_agregar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_agregar, command=self.command_button_agregar, compound="center" ,bootstyle="outline", width=25)
        ToolTip(self.button_agregar, text="Agregar Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_agregar", self.button_agregar)
        self.button_editar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_editar, command=self.command_button_editar_dispositivo, compound="center" ,bootstyle="outline", width=25, state="disable")
        ToolTip(self.button_editar, text="Editar datos de Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_editar", self.button_editar)
        self.button_eliminar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_eliminar, command=self.command_button_eliminar, compound="center" ,bootstyle="outline", width=25, state="disable")
        ToolTip(self.button_eliminar, text="Eliminar Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_eliminar", self.button_eliminar)
        self.button_guardar = ttk.Button(self.frame_contenedor_botones, text="", image=self.img_guardar, compound="center" ,bootstyle="outline", width=25)
        ToolTip(self.button_guardar, text="Guardar configuración de Dispositivo")
        self.DICT_WIDGETS.register("GUI_CONFIG","button_guardar", self.button_guardar)

        # Posicionamiento con grid (alineados al centro)
        self.frame_contenedor_botones.columnconfigure(0, weight=1)
        self.frame_contenedor_botones.columnconfigure(1, weight=1)
        self.frame_contenedor_botones.columnconfigure(2, weight=1)
        self.frame_contenedor_botones.columnconfigure(3, weight=1)

        self.button_agregar.grid(row=0, column=0, padx=1)
        self.button_editar.grid(row=0, column=1, padx=1)
        self.button_eliminar.grid(row=0, column=2, padx=1)
        self.button_guardar.grid(row=0, column=3, padx=1)
        
    def creacion_contenido_frame_contenedor_combobox_dispositivos(self):
        self.frame_label_combobox_dispositivos = ttk.Label(self.frame_contenedor_combobox_dispositivos, text="Seleccione su Dispositivo: ")
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_label_combobox_dispositivos", self.frame_label_combobox_dispositivos)
        self.frame_label_combobox_dispositivos.pack(side="left", padx=(5,0))
        
        self.combobox_dispositivos = ttk.Combobox(self.frame_contenedor_combobox_dispositivos, values=self.actualizar_datos_combobox(), state="readonly", width=30)
        self.combobox_dispositivos.bind("<<ComboboxSelected>>", self.seleccion_dispositivo)
        self.DICT_WIDGETS.register("GUI_CONFIG","combobox_dispositivos", self.combobox_dispositivos)
        self.combobox_dispositivos.pack(side="right", fill="x", expand=True)
        
    def creacion_contenido_toplevel_button_agregar(self):
        self.creacion_labelframe_nuevo_dispositivo_button_agregar()
        self.creacion_labelframe_datos_button_agregar()
        self.button_agregar_dispositivo = ttk.Button(self.toplevel_button_agregar, text="Agregar", command=self.command_button_agregar_dispositivo)
        self.button_agregar_dispositivo.pack(pady=(0,5))
        
    def creacion_labelframe_nuevo_dispositivo_button_agregar(self):
        self.labelframe_nuevo_dispositivo_button_agregar = ttk.Labelframe(self.toplevel_button_agregar, text="Nuevo dispositivo", bootstyle="primary")
        self.labelframe_nuevo_dispositivo_button_agregar.pack(fill="x", padx=5)

        self.label_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos = ttk.Label(
            self.labelframe_nuevo_dispositivo_button_agregar, text="Nombre del equipo:"
        )
        self.label_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.pack(side="left", pady=10, padx=10)

        self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos = ttk.Entry(self.labelframe_nuevo_dispositivo_button_agregar)
        self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.pack(side="right", pady=10, padx=(0,10), fill="x", expand=True)
        
    def creacion_labelframe_datos_button_agregar(self):
        self.labelframe_datos_button_agregar = ttk.Labelframe(self.toplevel_button_agregar, text="Nuevo dispositivo", bootstyle="primary")
        self.labelframe_datos_button_agregar.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Dirección IP/RED
        self.label_direccion_ip = ttk.Label(self.labelframe_datos_button_agregar, text="Dirección IP/RED:")
        self.entry_direccion_ip = ttk.Entry(self.labelframe_datos_button_agregar)

        # Puerto
        self.label_puerto = ttk.Label(self.labelframe_datos_button_agregar, text="PUERTO:")
        self.entry_puerto = ttk.Entry(self.labelframe_datos_button_agregar)

        # Comentario (más grande)
        self.label_comentario = ttk.Label(self.labelframe_datos_button_agregar, text="COMENTARIO:")
        self.text_comentario = ttk.Text(self.labelframe_datos_button_agregar, height=4, width=30)  # Ajusta tamaño

        # Posicionar con grid
        self.label_direccion_ip.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.entry_direccion_ip.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        self.label_puerto.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.entry_puerto.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        self.label_comentario.grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.text_comentario.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        # Expandir entradas en el contenedor
        self.labelframe_datos_button_agregar.columnconfigure(1, weight=1)
        
    def creacion_labelframe_datos_dispositivos(self):
        # Frame principal
        self.frame_contenedor_labelframe_datos_dispositivo = ttk.Frame(self.labelframe_datos_dispositivos, padding=10)

        # Frame para cada fila de datos
        self.frame_direccion_ip_contenido_labelframe_opciones = ttk.Frame(self.frame_contenedor_labelframe_datos_dispositivo)
        self.frame_puerto_contenido_labelframe_opciones = ttk.Frame(self.frame_contenedor_labelframe_datos_dispositivo)
        self.frame_comentario_contenido_labelframe_opciones = ttk.Frame(self.frame_contenedor_labelframe_datos_dispositivo)

        # Fuente personalizada para los labels de la izquierda
        font_izquierda = ("Arial", 14, "bold")

        # Labels de la izquierda con negrita y tamaño más grande
        self.label_nombre_contenido_labelframe_opciones = ttk.Label(self.frame_contenedor_labelframe_datos_dispositivo, text="NOMBRE DEL DISPOSITIVO", font=("Arial", 18, "bold"))
        self.label_direccion_ip_izq_contenido_labelframe_opciones = ttk.Label(self.frame_direccion_ip_contenido_labelframe_opciones, text="DIRECCIÓN IP/RED:", font=font_izquierda)
        self.label_puerto_izq_contenido_labelframe_opciones = ttk.Label(self.frame_puerto_contenido_labelframe_opciones, text="PUERTO:", font=font_izquierda)
        self.label_comentario_contenido_labelframe_opciones = ttk.Label(self.frame_comentario_contenido_labelframe_opciones, text="COMENTARIO:", font=font_izquierda)

        self.label_direccion_ip_der_contenido_labelframe_opciones = ttk.Label(self.frame_direccion_ip_contenido_labelframe_opciones, text="VALOR IP")
        self.label_puerto_der_contenido_labelframe_opciones = ttk.Label(self.frame_puerto_contenido_labelframe_opciones, text="VALOR PUERTO")

        # Cuadro de texto en lugar de Label para el comentario (pero deshabilitado)
        self.text_comentario_contenido_labelframe_opciones = ttk.Text(self.frame_comentario_contenido_labelframe_opciones, height=2, width=30, wrap="word")
        self.text_comentario_contenido_labelframe_opciones.insert("1.0", "Texto de comentario")  # Valor por defecto
        self.text_comentario_contenido_labelframe_opciones.config(state="disabled")  # Hace que no se pueda escribir

        # Posicionamiento de los Labels dentro de cada Frame
        self.label_nombre_contenido_labelframe_opciones.pack(pady=(15, 30))

        self.label_direccion_ip_izq_contenido_labelframe_opciones.pack(side="left", padx=50)
        self.label_direccion_ip_der_contenido_labelframe_opciones.pack(side="right", padx=50)

        self.label_puerto_izq_contenido_labelframe_opciones.pack(side="left", padx=50)
        self.label_puerto_der_contenido_labelframe_opciones.pack(side="right", padx=50)

        self.label_comentario_contenido_labelframe_opciones.pack()
        self.text_comentario_contenido_labelframe_opciones.pack(fill="both", expand=True)

        # Posicionamiento de los Frames en la interfaz
        self.frame_direccion_ip_contenido_labelframe_opciones.pack(fill="x", pady=2)
        self.frame_puerto_contenido_labelframe_opciones.pack(fill="x", pady=2)
        self.frame_comentario_contenido_labelframe_opciones.pack(fill="both", expand=True, pady=(15,2))

#///////////////////////////////////////////////////// NOTEBOOK FUENTE DE DATOS /////////////////////////////////////////////////////

    def creacion_frame_notebook_fuente_datos(self):
        self.frame_notebook_fuente_datos = ttk.Frame(self.notebook_widget_configuracion)
        self.frame_notebook_fuente_datos.pack(fill="both", expand=True)  # Corrección aquí
        self.DICT_WIDGETS.register("GUI_CONFIG","frame_notebook_fuente_datos", self.frame_notebook_fuente_datos)

        self.labelframe_conexion_fuente_datos = ttk.Labelframe(self.frame_notebook_fuente_datos, text="Conexiones disponibles: ", bootstyle="primary")
        self.labelframe_conexion_fuente_datos.pack(fill="x")
        
        lista_conexiones_disponibles = ["Conexión ODBC"]
        self.label_tipo_conexion = ttk.Label(self.labelframe_conexion_fuente_datos, text="Tipos de Conexiones:")
        self.label_tipo_conexion.pack(side="left", padx=(30,15))
        self.combobox_lista_fuente_datos = ttk.Combobox(self.labelframe_conexion_fuente_datos, values=lista_conexiones_disponibles, state="readonly")
        self.combobox_lista_fuente_datos.pack(side="right", fill="x", expand=True, padx=(5,10), pady=(0,5))
        self.combobox_lista_fuente_datos.bind("<<ComboboxSelected>>", self.bind_combobox_lista_fuente_datos)
        
        
        self.labelframe_datos_de_conexion_fuente_datos = ttk.Labelframe(self.frame_notebook_fuente_datos, text="Datos de Conexión: ", bootstyle="primary")
        self.labelframe_datos_de_conexion_fuente_datos.pack(fill="both", expand=True, pady=10)

        
        
        
        
    def bind_combobox_lista_fuente_datos(self, event):
        if self.combobox_lista_fuente_datos.get() == "Conexión ODBC":
            self.mostrar_widgets_ODBC()
            self.obtener_datos_conexion_odbc()
        
        
        
        
    def mostrar_widgets_ODBC(self):
        self.frame_contenido_opcion_odbc = ttk.Frame(self.labelframe_datos_de_conexion_fuente_datos)
        self.frame_contenido_opcion_odbc.pack(fill="both", expand=True, padx=(50,55), pady=50)
        self.frame_odbc = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_odbc.pack(fill="x", pady=5)

        self.label_odbc = ttk.Label(self.frame_odbc, text="Conexión ODBC:")
        self.label_odbc.pack(side="left", padx=5)

        self.combobox_odbc = ttk.Combobox(self.frame_odbc, values=self.obtener_listaDSN(), state="readonly")
        self.combobox_odbc.pack(side="right", fill="x", expand=True)

        # 🔹 Frame para User ID
        self.frame_user = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_user.pack(fill="x", pady=5)

        self.label_user = ttk.Label(self.frame_user, text="User ID:")
        self.label_user.pack(side="left", padx=5)

        self.entry_user = ttk.Entry(self.frame_user)
        self.entry_user.pack(side="right", fill="x", expand=True)

        # 🔹 Frame para Password
        self.frame_password = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_password.pack(fill="x", pady=5)

        self.label_password = ttk.Label(self.frame_password, text="Password:")
        self.label_password.pack(side="left", padx=5)

        self.entry_password = ttk.Entry(self.frame_password, show="*")  # Ocultar texto
        self.entry_password.pack(side="right", fill="x", expand=True)
        
        
        self.frame_checkbox = ttk.Frame(self.frame_contenido_opcion_odbc)
        self.frame_checkbox.pack(fill="x", pady=5)

        self.checkbox_var = ttk.BooleanVar()  # Variable para almacenar el estado del checkbox
        self.checkbox = ttk.Checkbutton(self.frame_checkbox, text="Conexión a DBA de Inforhard Sistemas", variable=self.checkbox_var)
        self.checkbox.pack(side="left", padx=5)
        
        self.button_agregar_datos_de_conexion = ttk.Button(self.labelframe_datos_de_conexion_fuente_datos, text="Agregar", command=self.command_button_agregar_datos_de_conexion)
        self.button_agregar_datos_de_conexion.pack(pady=(0,5), side="bottom")
    
    def validar_campos(self):
        """Verifica que los campos no estén vacíos."""
        campos = {
            "Nuevo dispositivo": self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.get().strip(),
            "Dirección IP/RED": self.entry_direccion_ip.get().strip(),
            "PUERTO": self.entry_puerto.get().strip(),
            "COMENTARIO": self.text_comentario.get("1.0", "end").strip()  # Obtener texto desde Text
        }

        for campo, valor in campos.items():
            if not valor:  # Si el campo está vacío
                messagebox.showwarning("Campo vacío", f"El campo '{campo}' no puede estar vacío.")
                return False

        return True  # Si todos los campos tienen datos       
    
    
    def obtener_listaDSN(self):
        datos = dsn_configurados()
        dsnLIST = []
        for dsnNAME, dsnDRIVER in datos.items():
            cadena = dsnNAME.decode('utf-8')
            dsnLIST.append(cadena)
        for dsnNAME in dsnLIST:
            print(dsnNAME) 
        return dsnLIST
    
#///////////////////////////////////////////////////// NOTEBOOK CONFIGURACIÓN DE DATOS /////////////////////////////////////////////////////

    def creacion_frame_notebook_config_datos(self):
        self.frame_notebook_config_datos = ttk.Labelframe(self.notebook_widget_configuracion, text="Configurar Datos")
        self.frame_notebook_config_datos.pack(fill="both", expand=True)
        
        
        self.label_info_notebook_config_datos = ttk.Label(self.frame_notebook_config_datos)
        self.label_info_notebook_config_datos.pack(fill="x", padx=5, pady=5)
        
        inserccion_sql = """
        SELECT * FROM VERIPRE_CONEXION
        """
        datos_conexion = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA").ejecutar_consulta(inserccion_sql)
        self.creacion_frame_config_datos_INFORHARD()
        
        print(datos_conexion)

        if datos_conexion:  # Verifica si la lista NO está vacía
            datos_conexion = datos_conexion[0]
            if len(datos_conexion) > 3 and datos_conexion[3]:  # Verifica que haya al menos 4 elementos
                self.label_info_notebook_config_datos.config(
                    text="Se encontró conexión a la fuente de datos de Inforhard Sistema S.R.L"
                )
                self.frame_config_datos_INFORHARD.pack(fill="both", expand=True)
            else:
                self.label_info_notebook_config_datos.config(
                    text="No se encontró conexión a una fuente de datos"
                )
        else:
            self.label_info_notebook_config_datos.config(
                text="No se encontró ninguna conexión a una fuente de datos"
            )
            
    def creacion_frame_config_datos_INFORHARD(self):
        self.frame_config_datos_INFORHARD = ttk.Frame(self.frame_notebook_config_datos)
        
        self.button_importar_datos_INFORHARD = ttk.Button(self.frame_config_datos_INFORHARD, text="Sincronizars Datos", command=self.command_importar_datos_INFORHARD)
        self.button_importar_datos_INFORHARD.pack()
        
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

            
#//////////////////////////////////////////////// COMMAND DE BOTONES ///////////////////////////////////////////////
    def command_button_agregar(self):
        self.toplevel_button_agregar = ttk.Toplevel(self.top_level_configuracion)
        self.DICT_WIDGETS.register("GUI_CONFIG", "toplevel_button_agregar", self.toplevel_button_agregar)
        self.toplevel_button_agregar.title("VeriPre_Connector - Agregar Dispositivo")
        self.toplevel_button_agregar.transient(self.top_level_configuracion)
        self.toplevel_button_agregar.geometry("500x300")
        self.toplevel_button_agregar.place_window_center()

        self.creacion_contenido_toplevel_button_agregar()
        
    def command_button_eliminar(self):
        if messagebox.askyesno("Eliminar Dispositivo", f"¿Desea eliminar el Dispositivo {self.combobox_dispositivos.get()}?"):
            
            sentencia_insercion = f"""
            DELETE FROM VERIPRE_EQUIPOS
            WHERE nombre = '{self.combobox_dispositivos.get()}'
            """
            self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA").ejecutar_consulta(sentencia_insercion)
            self.limpiar_frame_despues_actualizacion()
            
    def command_button_editar_dispositivo(self):
        self.command_button_agregar()
        
        dispositivo = self.combobox_dispositivos.get()

        if dispositivo in self.datos_dispositivos:
            self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.insert(0, dispositivo)
            self.entry_direccion_ip.insert(0, self.datos_dispositivos[dispositivo]["direccion_ip"])
            self.entry_puerto.insert(0, self.datos_dispositivos[dispositivo]["puerto"])
            self.text_comentario.insert("1.0", self.datos_dispositivos[self.combobox_dispositivos.get()]["comentario"])
        else:
            print(f"Error: {dispositivo} no encontrado en datos_dispositivos")
        
        self.button_agregar_dispositivo.config(text="Actualizar", command=self.command_button_actualizar_datos_dispositivo)
        
    def command_button_agregar_dispositivo(self):
        try:
            if self.validar_campos():
                sentencia_insercion = f"""
                INSERT INTO VERIPRE_EQUIPOS (nombre, direccion_conexion, puerto, comentarios) 
                VALUES ('{self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.get()}', '{self.entry_direccion_ip.get()}', '{self.entry_puerto.get()}', '{self.text_comentario.get("1.0", "end")}');
                """
                self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA").ejecutar_consulta(sentencia_insercion)
                self.combobox_dispositivos.config(values=self.actualizar_datos_combobox())
                messagebox.showinfo("Dispositivo Agregado", "¡Dispositivo Agregado con exito!")
                self.toplevel_button_agregar.destroy()
        except Exception as e:
            print(e)    
            
    def command_button_actualizar_datos_dispositivo(self):
        try:
            if self.validar_campos():
                # Prepara la consulta segura usando parámetros
                sentencia_actualizacion = """
                UPDATE VERIPRE_EQUIPOS 
                SET nombre = ?, direccion_conexion = ?, puerto = ?, comentarios = ? 
                WHERE nombre = ?;
                """

                valores = (
                    self.entry_labelframe_nuevo_dispositivo_button_agregar_nombre_dispositivos.get(),
                    self.entry_direccion_ip.get(),
                    self.entry_puerto.get(),
                    self.text_comentario.get("1.0", "end").strip(),  # Evita el salto de línea final
                    self.combobox_dispositivos.get()
                )

                # Ejecuta la consulta de forma segura
                conexion = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA")
                conexion.ejecutar_consulta(sentencia_actualizacion, valores)

                # Actualiza el Combobox con los nuevos datos
                self.combobox_dispositivos.config(values=self.actualizar_datos_combobox())

                messagebox.showinfo("Dispositivo Actualizado", "¡Dispositivo actualizado con éxito!")
                self.toplevel_button_agregar.destroy()
                self.limpiar_frame_despues_actualizacion()

        except Exception as e:
            print(f"Error al actualizar el dispositivo: {e}")
            
    def command_button_agregar_datos_de_conexion(self):
        try:
            if self.combobox_lista_fuente_datos.get() == "Conexión ODBC":
                insercion_sql = f"""
                INSERT INTO VERIPRE_CONEXION (dsn, user, password, activo) 
                VALUES ('{self.combobox_odbc.get()}', '{self.entry_user.get()}', '{self.entry_password.get()}', {self.checkbox_var.get()});
                """
                self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA").ejecutar_consulta(insercion_sql)
                print(self.checkbox_var.get())
                if self.checkbox_var.get():
                    conexion = {
                        "user": self.entry_user.get(),
                        "password": self.entry_password.get(),
                        "dsn": self.combobox_odbc.get()
                    }
                    self.DICT_WIDGETS.register("DATABASE","CONEXIONDBA_SYBASE", ConexionSybase(**conexion))
                    self.DICT_WIDGETS.register("DATABASE","CONEXION_INFORHARD", True)
                else:
                    print("NO CONEXION INFORHARD")
                messagebox.showinfo("Conexión Agregada", "¡Conexión agregada con exito!")
            self.cambiar_estados_widgets_frame_odbc("disabled")
            self.button_agregar_datos_de_conexion.config(text="Actualizar datos", state="normal", command=self.command_modificado_button_actualizar_datos_de_conexion)
        except Exception as e:
            print(e)
            messagebox.showerror("ERROR", e)
            
    def command_modificado_button_actualizar_datos_de_conexion(self):            
            self.cambiar_estados_widgets_frame_odbc("normal")
            self.top_level_configuracion.update_idletasks()
            self.dsn_actual = self.combobox_odbc.get()
            self.button_agregar_datos_de_conexion.config(text="Agregar", command=self.command_modificado_actulizar_datos_odbc)
            
    def command_modificado_actulizar_datos_odbc(self):
        try:
            conexion = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA")

            sentencia_actualizacion = """
            UPDATE VERIPRE_CONEXION
            SET dsn = ?, user = ?, password = ?, activo = ? 
            WHERE dsn = ?;
            """
            
            
            valores = (
                self.combobox_odbc.get(),
                self.entry_user.get(),
                self.entry_password.get(),
                self.checkbox_var.get(),
                self.dsn_actual
            )

            # Ejecuta la consulta de forma segura
            conexion.ejecutar_consulta(sentencia_actualizacion, valores)
            print(self.checkbox_var.get())
            if self.checkbox_var.get():
                conexion = {
                    "user": self.entry_user.get(),
                    "password": self.entry_password.get(),
                    "dsn": self.combobox_odbc.get()
                }
                self.DICT_WIDGETS.register("DATABASE","CONEXIONDBA_SYBASE", ConexionSybase(**conexion))
                self.DICT_WIDGETS.register("DATABASE","CONEXION_INFORHARD", True)
            else:
                print("NO CONEXION INFORHARD")
            messagebox.showinfo("Estado Conexión", "Se ha actualizado el metodo de conexión")
            self.cambiar_estados_widgets_frame_odbc("disabled")
            self.button_agregar_datos_de_conexion.config(text="Actualizar datos", state="normal", command=self.command_modificado_button_actualizar_datos_de_conexion)
        except Exception as e:
            print(e)
            
    def command_importar_datos_INFORHARD(self):
        try:
            self.creacion_toplevel_carga_datos()
            threading.Thread(target=self.procesar_productos_completos).start()
        except Exception as e:
            print(e)
            
            
    def procesar_productos_completos(self):
        """Llama a todas las funciones para procesar los productos en conjunto."""
        
        # Paso 1: Obtener los datos de los artículos
        self.buscar_datos_en_tabla_ARTICULOS()

        # Paso 2: Obtener los códigos de barra adicionales
        self.buscar_datos_tabla_CODBARP()

        # Paso 3: Obtener los tipos de IVA
        self.buscar_datos_tabla_IVAS()

        # Paso 4: Actualizar los precios de los productos con el IVA correspondiente
        self.actualizar_precios_con_iva()

        # Paso 5: Insertar o actualizar los productos en la base de datos
        self.insertar_o_actualizar_productos()

        self.mostrar_accion("Proceso completo.")
        messagebox.showinfo("Proceso completo", "Se han insertado los nuevos productos y actualizados los pendientes.")
        self.top_level_carga.destroy()



    def mostrar_accion(self, texto):
        print(texto)
        """Actualiza el Entry con el texto de la acción que se está realizando."""
        self.entry_acciones.config(state="normal")
        self.entry_acciones.delete(0, "end")
        self.entry_acciones.insert(0, texto)
        self.entry_acciones.config(state="readonly")
        
    def actualizar_barra(self, progreso, total):            
        """Actualiza la barra de progreso con el porcentaje calculado."""
        porcentaje = (progreso / total) * 100
        
        barra_progreso = self.DICT_WIDGETS.get_widget("UI", "BARRA_PROGRESO")
        if barra_progreso is not None:
            barra_progreso['value'] = porcentaje  # Asegúrate de usar 'value' para actualizar la barra
            self.label_porcentaje.configure(text=f"{int(porcentaje)}%")
        else:
            self.mostrar_accion("Error: No se encontró el widget BARRA_PROGRESO.")




    #/////////////////////////////////////////// DATABASE ///////////////////////////////////////////
    def buscar_datos_en_tabla_ARTICULOS(self):
        """Obtiene los artículos con códigos de barras válidos y muestra información de lo que está haciendo."""
        CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS = """
            SELECT CREF, CDETALLE, CCODEBAR, CTIPOIVA, NPVP1 
            FROM ARTICULO 
            WHERE CCODEBAR IS NOT NULL AND CCODEBAR <> ''
            ORDER BY dFechaU ASC;
        """
        self.datos_ARTICULOS = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_ARTICULOS)

        self.mostrar_accion("Iniciando la carga de artículos...")
        time.sleep(0.75)

        # Primera actualización al 50%
        self.actualizar_barra(50, 100)

        self.mostrar_accion(f"{len(self.datos_ARTICULOS)} artículos encontrados.")
        time.sleep(0.75)

        # Última actualización al 100%
        self.actualizar_barra(100, 100)





    def buscar_datos_tabla_CODBARP(self):
        """Obtiene los códigos de barra adicionales y los une con la lista de productos."""
        self.datos_PRODUCTOS_COMPLETOS = []
        
        if not self.datos_ARTICULOS:
            self.mostrar_accion("No hay datos en ARTICULO")
            return
        
        crefs = tuple(producto[0] for producto in self.datos_ARTICULOS)
        
        CONSULTA_SQL_BUSCAR_DATOS_CODBARP = f"""
            SELECT CREF, CDETALLE, CCODEBAR 
            FROM CODBARP 
            WHERE CREF IN {crefs} AND CCODEBAR IS NOT NULL AND CCODEBAR <> ''
            ORDER BY dFechaU ASC;
        """
        
        self.mostrar_accion("Obteniendo códigos de barra adicionales...")
        datos_codbarp = self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA_SYBASE").ejecutar_consulta(CONSULTA_SQL_BUSCAR_DATOS_CODBARP)
        
        codbarp_dict = {}
        if datos_codbarp:
            for cref, cdetalle, ccodebar in datos_codbarp:
                if cref not in codbarp_dict:
                    codbarp_dict[cref] = []
                codbarp_dict[cref].append((cdetalle, ccodebar))
        
        total_productos = len(self.datos_ARTICULOS)
        total_codigos_barra = len(datos_codbarp)
        total = total_productos + total_codigos_barra
        progreso = 0

        for idx, producto in enumerate(self.datos_ARTICULOS):
            cref, cdetalle, ccodebar, ctipoiva, npvp1 = producto
            self.datos_PRODUCTOS_COMPLETOS.append(producto)
            progreso += 1
            if progreso % 10 == 0:  # Actualiza la barra cada 10 productos
                self.actualizar_barra(progreso, total)
            
            if cref in codbarp_dict:
                for cdetalle_extra, ccodebar_extra in codbarp_dict[cref]:
                    self.datos_PRODUCTOS_COMPLETOS.append((cref, cdetalle_extra, ccodebar_extra, ctipoiva, npvp1))
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

            producto_actualizado = list(producto)
            del producto_actualizado[3]
            producto_actualizado[3] = format(round(nuevo_precio, 2), ".2f")
            productos_actualizados.append(tuple(producto_actualizado))

            self.actualizar_barra(idx + 1, total_productos)

        self.datos_PRODUCTOS_COMPLETOS = productos_actualizados
        self.mostrar_accion(f"{len(self.datos_PRODUCTOS_COMPLETOS)} productos actualizados con IVA.")

            
        
    def insertar_o_actualizar_productos(self):
        """Elimina los datos y los reemplazo con los nuevos"""
        consulta_limpieza = """
        DELETE FROM productos
        """
        """Inserta o actualiza los productos en la base de datos SQLite y muestra el progreso."""
        self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA").ejecutar_consulta(consulta_limpieza)
        consulta = """
        INSERT OR REPLACE INTO productos (CREF, codigo, descripcion, precio) 
        VALUES (?, ?, ?, ?)
        """

        self.mostrar_accion("Insertando o actualizando productos...")
        
        total_productos = len(self.datos_PRODUCTOS_COMPLETOS)  # Número total de productos
        if total_productos == 0:
            self.mostrar_accion("No hay productos para insertar o actualizar.")
            return

        # Iniciar la barra de progreso en 0%
        self.actualizar_barra(0, total_productos)
        
        # Preparar todos los parámetros para la inserción o actualización
        parametros = [(producto[0], producto[2], producto[1], producto[3]) for producto in self.datos_PRODUCTOS_COMPLETOS]

        # Ejecutar la consulta para todos los productos a la vez
        self.DICT_WIDGETS.get_widget("DATABASE", "CONEXIONDBA").ejecutar_consultamany(consulta, parametros)
        
        # Actualizar la barra de progreso al 100% una vez que se han insertado/actualizado todos los productos
        self.actualizar_barra(total_productos, total_productos)

        self.mostrar_accion("Productos insertados o actualizados correctamente.")





            
    def cierre_top_level_configuracion(self):
        """Cierra la ventana y la elimina del gestor de ventanas"""
        VentanaManager.cerrar_ventana("configuracion")  # Llamamos al método de cierre
        self.top_level_configuracion.destroy()
        
    def obtener_datos_conexion_odbc(self):
        inserccion_sql = """
        SELECT * FROM VERIPRE_CONEXION
        """
        datos_conexion = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA").ejecutar_consulta(inserccion_sql)
        if not datos_conexion == None:
            for datos in datos_conexion:
                self.combobox_odbc.set(value=datos[0])                
                self.entry_user.insert("0", datos[1])                
                self.entry_password.insert("0", datos[2])                
                self.checkbox_var.set(datos[3])
                self.checkbox.config(variable=self.checkbox_var)
                self.cambiar_estados_widgets_frame_odbc("disabled")
                self.button_agregar_datos_de_conexion.config(text="Actualizar datos", state="normal", command=self.command_modificado_button_actualizar_datos_de_conexion)
        
    def cambiar_estados_widgets_frame_odbc(self, estado):
        if estado == "normal":
            self.combobox_odbc.config(state="readonly")
            self.entry_user.config(state=estado)
            self.entry_password.config(state=estado)
            self.checkbox.config(state=estado)
        elif estado == "disabled":
            self.combobox_odbc.config(state=estado)
            self.entry_user.config(state=estado)
            self.entry_password.config(state=estado)
            self.checkbox.config(state=estado)
    
    def seleccion_dispositivo(self, event):
        self.button_editar.config(state="normal")
        self.button_eliminar.config(state="normal")
        self.frame_contenedor_labelframe_datos_dispositivo.pack(fill="both", expand=True)
        dispositivo = self.combobox_dispositivos.get()
        print(f"Seleccionaste: {dispositivo}")

        # Actualizar los Labels con la información del dispositivo seleccionado
        self.label_nombre_contenido_labelframe_opciones.config(text=dispositivo)
        self.label_direccion_ip_der_contenido_labelframe_opciones.config(
            text=self.datos_dispositivos[dispositivo]["direccion_ip"]
        )
        self.label_puerto_der_contenido_labelframe_opciones.config(
            text=self.datos_dispositivos[dispositivo]["puerto"]
        )

        # Actualizar el contenido del Text para el comentario
        self.text_comentario_contenido_labelframe_opciones.config(state="normal")  # Habilitar edición
        self.text_comentario_contenido_labelframe_opciones.delete("1.0", "end")  # Eliminar texto anterior
        self.text_comentario_contenido_labelframe_opciones.insert("1.0", self.datos_dispositivos[dispositivo]["comentario"])  # Insertar nuevo comentario
        self.text_comentario_contenido_labelframe_opciones.config(state="disabled")  # Deshabilitar edición

        # Forzar la actualización de la interfaz
        self.top_level_configuracion.update_idletasks()

    def actualizar_datos_combobox(self):
        try:
            self.traer_todos_los_datos_de_VERIPRE_EQUIPOS()
            list_nombre_dispositivo = []
            for nombre_dispositivo in self.datos_dispositivos:
                list_nombre_dispositivo.append(nombre_dispositivo)
            return list_nombre_dispositivo
        except Exception as e:
            print(e)
            return []
    
    def traer_todos_los_datos_de_VERIPRE_EQUIPOS(self):
        try:
            sentencia_consulta = f""" 
            SELECT * FROM VERIPRE_EQUIPOS
            """
            self.datos_dispositivos = {}
            datos = self.DICT_WIDGETS.get_widget("DATABASE","CONEXIONDBA").ejecutar_consulta(sentencia_consulta)
            
            for datos_dispositivos in datos:
                datos_dict_dispositivo = {}
                datos_dict_dispositivo["direccion_ip"] = datos_dispositivos[1]
                datos_dict_dispositivo["puerto"] = datos_dispositivos[2]
                datos_dict_dispositivo["comentario"] = datos_dispositivos[3]
                self.datos_dispositivos[datos_dispositivos[0]] = datos_dict_dispositivo
        except Exception as e:
            return []
        
    def limpiar_frame_despues_actualizacion(self):
        self.button_editar.config(state="disable")
        self.button_eliminar.config(state="disable")
        self.combobox_dispositivos.config(values=self.actualizar_datos_combobox())
        self.combobox_dispositivos.set(value="")
        self.frame_contenedor_labelframe_datos_dispositivo.pack_forget()
        
    def bloquear_cierre(self):
        pass  # No hace nada al intentar cerrar
