import sqlite3

class SQLiteDB:
    def __init__(self, db_name="database.db"):
        """Inicializa la conexión con la base de datos."""
        self.db_name = db_name
        self.connection = None
        self.cursor = None

    def conectar(self):
        """Establece la conexión con la base de datos."""
        try:
            self.connection = sqlite3.connect(self.db_name)
            self.cursor = self.connection.cursor()
            #self.crear_tablas()
            print("Conexión establecida con la base de datos.")
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos: {e}")
            
    def crear_tablas(self):
        try:
            self.conectar()
            self.crear_tabla_VERIPRE_EQUIPOS()
            self.crear_tabla_VERIPRE_productos()
            self.crear_tabla_VERIPRE_ad_medias()
            self.crear_tabla_VERIPRE_CONEXION()
            self.cerrar_conexion()
        except sqlite3.Error as e:
            print(e)

    def ejecutar_consulta(self, consulta, parametros=()):
        """Ejecuta una consulta SQL con o sin parámetros."""
        try:
            self.conectar()
            self.cursor.execute(consulta, parametros)
            self.connection.commit()
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            return None
        finally:
            self.cerrar_conexion()
    def obtener_columnas(self, nombre_tabla):
        
        self.conectar()

        # Ejecutar PRAGMA para obtener información de la tabla
        self.cursor.execute(f"PRAGMA table_info({nombre_tabla})")
        
        # Extraer los nombres de las columnas
        columnas = [columna[1] for columna in self.cursor.fetchall()]

        # Cerrar conexión
        self.cerrar_conexion()

        return columnas
    
    def crear_tabla_VERIPRE_productos(self):
        self.ejecutar_consulta("""
            CREATE TABLE productos (
            CREF TEXT,
            codigo TEXT UNIQUE,
            descripcion TEXT,
            precio REAL,
            img_base64 TEXT,
            formato_imagen TEXT
            )""")
        
        
    def crear_tabla_VERIPRE_EQUIPOS(self):
        self.ejecutar_consulta("""
            CREATE TABLE "VERIPRE_EQUIPOS" (
                "nombre"	TEXT,
                "direccion_conexion"	TEXT,
                "puerto"	TEXT,
                "comentarios"	TEXT,
                "fecha_alta"	TEXT,
                "fecha_ultimo_envio"	TEXT,
                PRIMARY KEY("direccion_conexion")
            )""")
        
        
    def crear_tabla_VERIPRE_ad_medias(self):
        self.ejecutar_consulta("""
            CREATE TABLE ad_medias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            formato TEXT NOT NULL
            )""")
        
    def crear_tabla_VERIPRE_CONEXION(self):
        self.ejecutar_consulta("""
            CREATE TABLE VERIPRE_CONEXION (
            dsn TEXT NOT NULL PRIMARY KEY,
            user TEXT NOT NULL,
            password TEXT NOT NULL,
            activo BIT
            )""")

    def cerrar_conexion(self):
        """Cierra la conexión con la base de datos."""
        if self.connection:
            self.connection.close()
            print("Conexión cerrada.")
            
            
    