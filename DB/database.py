import sqlite3

class SQLiteDB:
    def __init__(self, db_name):
        """Inicializa la conexión con la base de datos."""
        self.db_name = db_name
        self.ruta_db = db_name  # 👈 Agregá esto
        self.connection = None
        self.cursor = None


    def conectar(self):
        """Establece la conexión con la base de datos."""
        try:
            self.connection = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cursor = self.connection.cursor()
        except sqlite3.Error as e:
            print(f"Error al conectar con la base de datos: {e}")
            
    def crear_tablas(self):
        """Crea las tablas necesarias en la base de datos."""
        try:
            self.conectar()
            self.crear_tabla_VERIPRE_EQUIPOS()
            self.crear_tabla_VERIPRE_productos()
            self.crear_tabla_VERIPRE_ad_medias()
            self.crear_tabla_VERIPRE_CONEXION()
        except sqlite3.Error as e:
            print(f"Error al crear las tablas: {e}")
        finally:
            self.cerrar_conexion()

    def ejecutar_consulta(self, consulta, parametros=()):
        """Ejecuta una consulta SQL con o sin parámetros."""
        try:
            if not self.conexion_activa():
                self.conectar()
            self.cursor.execute(consulta, parametros)
            self.connection.commit()
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            return None
        
    def ejecutar_consultamany(self, consulta, parametros=()):
        """Ejecuta una consulta SQL con o sin parámetros en múltiples registros."""
        try:
            if not self.conexion_activa():
                self.conectar()
            self.cursor.executemany(consulta, parametros)  # Ejecuta la consulta para todos los parámetros
            self.connection.commit()  # Guarda los cambios en la base de datos
            return True  # Retorna True para indicar que la operación fue exitosa
        except sqlite3.Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            return False  # Retorna False en caso de error
        
    def conexion_activa(self):
        """Verifica si la conexión a SQLite sigue activa y funcional."""
        try:
            if self.connection:
                self.connection.execute("SELECT 1")
                return True
        except:
            return False
        return False

    def ejecutar_transaccion(self, consulta_borrar, consulta_insertar, parametros):
        """Ejecuta una transacción con las consultas de borrar e insertar."""
        try:
            # Crear una conexión y un cursor
            conn = self.obtener_conexion()
            cursor = conn.cursor()

            # Si tienes una consulta de borrar, ejecutarla
            if consulta_borrar:
                cursor.execute(consulta_borrar)
            
            # Ejecutar la consulta de inserción
            cursor.executemany(consulta_insertar, parametros)

            # Confirmar la transacción
            conn.commit()

        except sqlite3.Error as e:
            # Manejar el error y hacer un rollback si hay un problema
            conn.rollback()
            print(f"Error en la transacción: {e}")
            raise  # Relanzar la excepción para que la maneje el código que llama a esta función

        finally:
            # Asegurarse de cerrar el cursor y la conexión
            if cursor:
                cursor.close()  # Cerrar el cursor
            if conn:
                conn.close()  # Cerrar la conexión


    def obtener_columnas(self, nombre_tabla):
        """Obtiene los nombres de las columnas de una tabla."""
        try:
            self.conectar()
            self.cursor.execute(f"PRAGMA table_info({nombre_tabla})")
            columnas = [columna[1] for columna in self.cursor.fetchall()]
            return columnas
        except sqlite3.Error as e:
            print(f"Error al obtener las columnas de la tabla {nombre_tabla}: {e}")
            return []
        finally:
            self.cerrar_conexion()

    def crear_tabla_VERIPRE_productos(self):
        """Crea la tabla de productos con campo de fecha de última actualización."""
        consulta = """
            CREATE TABLE IF NOT EXISTS productos (
                CREF TEXT,
                codigo TEXT UNIQUE,
                descripcion TEXT,
                precio REAL,
                img_base64 TEXT,
                formato_imagen TEXT,
                dFechaU TEXT
            )
        """
        self.ejecutar_consulta(consulta)


    def crear_tabla_VERIPRE_EQUIPOS(self):
        """Crea la tabla VERIPRE_EQUIPOS."""
        consulta = """
            CREATE TABLE IF NOT EXISTS VERIPRE_EQUIPOS (
                nombre TEXT,
                direccion_conexion TEXT,
                puerto TEXT,
                comentarios TEXT,
                fecha_alta TEXT,
                fecha_ultimo_envio TEXT,
                PRIMARY KEY(direccion_conexion)
            )
        """
        self.ejecutar_consulta(consulta)

    def crear_tabla_VERIPRE_ad_medias(self):
        """Crea la tabla ad_medias."""
        consulta = """
            CREATE TABLE IF NOT EXISTS ad_medias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                formato TEXT NOT NULL
            )
        """
        self.ejecutar_consulta(consulta)

    def crear_tabla_VERIPRE_CONEXION(self):
        """Crea la tabla VERIPRE_CONEXION."""
        consulta = """
            CREATE TABLE IF NOT EXISTS VERIPRE_CONEXION (
                dsn TEXT NOT NULL PRIMARY KEY,
                user TEXT NOT NULL,
                password TEXT NOT NULL,
                activo BIT
            )
        """
        self.ejecutar_consulta(consulta)

    def cerrar_conexion(self):
        """Cierra la conexión con la base de datos."""
        if self.connection:
            self.connection.close()
            print("Conexión cerrada.")
            
    def obtener_conexion(self):
        """Devuelve la conexión activa o la crea si no existe."""
        if self.connection is None:
            self.conectar()
        return self.connection
