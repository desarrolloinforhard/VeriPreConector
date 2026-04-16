import sqlite3
from core.logging.logger import get_logger

logger = get_logger(__name__)


class SQLiteDB:
    def __init__(self, db_name):
        """Inicializa la conexión con la base de datos."""
        self.db_name = db_name
        self.ruta_db = db_name
        self.connection = None
        self.cursor = None

        logger.info("SQLiteDB inicializado | db_name=%s", self.db_name)

    def conectar(self):
        """Establece la conexión con la base de datos."""
        try:
            self.connection = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cursor = self.connection.cursor()
            logger.debug("Conexión SQLite abierta | db_name=%s", self.db_name)
        except sqlite3.Error:
            logger.exception("Error al conectar con la base de datos SQLite | db_name=%s", self.db_name)

    def crear_tablas(self):
        """Crea las tablas necesarias en la base de datos."""
        try:
            logger.info("Iniciando creación/verificación de tablas SQLite.")
            self.conectar()
            self.crear_tabla_VERIPRE_EQUIPOS()
            self.crear_tabla_VERIPRE_productos()
            self.crear_tabla_VERIPRE_ad_medias()
            self.crear_tabla_VERIPRE_CONEXION()
            self.crear_tabla_API_KEY()
            logger.info("Proceso de creación/verificación de tablas finalizado correctamente.")
        except sqlite3.Error:
            logger.exception("Error al crear las tablas en SQLite.")
        finally:
            self.cerrar_conexion()

    def ejecutar_consulta(self, consulta, parametros=()):
        """Ejecuta una consulta SQL con o sin parámetros."""
        try:
            if not self.conexion_activa():
                logger.debug("SQLite sin conexión activa. Reconectando.")
                self.conectar()

            logger.debug("SQL SQLite: %s", consulta.strip())
            if parametros:
                logger.debug("SQL SQLite params: %s", parametros)

            self.cursor.execute(consulta, parametros)
            self.connection.commit()
            resultados = self.cursor.fetchall()

            logger.debug("Consulta SQLite ejecutada correctamente | filas=%s", len(resultados))
            return resultados

        except sqlite3.Error:
            logger.exception("Error al ejecutar consulta SQLite.")
            return None

    def ejecutar_consultamany(self, consulta, parametros=()):
        """Ejecuta una consulta SQL con o sin parámetros en múltiples registros."""
        try:
            if not self.conexion_activa():
                logger.debug("SQLite sin conexión activa. Reconectando.")
                self.conectar()

            logger.debug("SQL SQLite executemany: %s", consulta.strip())
            logger.debug("Cantidad de registros para executemany: %s", len(parametros))

            self.cursor.executemany(consulta, parametros)
            self.connection.commit()

            logger.info("executemany SQLite ejecutado correctamente | registros=%s", len(parametros))
            return True

        except sqlite3.Error:
            logger.exception("Error al ejecutar executemany en SQLite.")
            return False

    def conexion_activa(self):
        """Verifica si la conexión a SQLite sigue activa y funcional."""
        try:
            if self.connection:
                self.connection.execute("SELECT 1")
                return True
        except Exception:
            logger.warning("La conexión SQLite no está activa o se perdió.")
            return False
        return False

    def ejecutar_transaccion(self, consulta_borrar, consulta_insertar, parametros):
        """Ejecuta una transacción con las consultas de borrar e insertar."""
        conn = None
        cursor = None

        try:
            conn = self.obtener_conexion()
            cursor = conn.cursor()

            logger.info("Iniciando transacción SQLite.")

            if consulta_borrar:
                logger.debug("SQL SQLite (borrado transacción): %s", consulta_borrar.strip())
                cursor.execute(consulta_borrar)

            logger.debug("SQL SQLite (insert transacción): %s", consulta_insertar.strip())
            logger.debug("Cantidad de parámetros en transacción: %s", len(parametros))
            cursor.executemany(consulta_insertar, parametros)

            conn.commit()
            logger.info("Transacción SQLite confirmada correctamente.")

        except sqlite3.Error:
            if conn:
                conn.rollback()
                logger.exception("Error en transacción SQLite. Se realizó rollback.")
            raise

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Conexión SQLite cerrada al finalizar transacción.")

    def obtener_columnas(self, nombre_tabla):
        """Obtiene los nombres de las columnas de una tabla."""
        try:
            self.conectar()
            consulta = f"PRAGMA table_info({nombre_tabla})"
            logger.debug("Obteniendo columnas de tabla SQLite | tabla=%s", nombre_tabla)

            self.cursor.execute(consulta)
            columnas = [columna[1] for columna in self.cursor.fetchall()]

            logger.debug("Columnas obtenidas | tabla=%s | cantidad=%s", nombre_tabla, len(columnas))
            return columnas

        except sqlite3.Error:
            logger.exception("Error al obtener las columnas de la tabla SQLite | tabla=%s", nombre_tabla)
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
        logger.debug("Creando/verificando tabla SQLite: productos")
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
        logger.debug("Creando/verificando tabla SQLite: VERIPRE_EQUIPOS")
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
        logger.debug("Creando/verificando tabla SQLite: ad_medias")
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
        logger.debug("Creando/verificando tabla SQLite: VERIPRE_CONEXION")
        self.ejecutar_consulta(consulta)

    def crear_tabla_API_KEY(self):
        """Crea la tabla para almacenar la API KEY (Go-UPC)."""
        consulta = """
            CREATE TABLE IF NOT EXISTS api_key (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL
            )
        """
        logger.debug("Creando/verificando tabla SQLite: api_key")
        self.ejecutar_consulta(consulta)

    def cerrar_conexion(self):
        """Cierra la conexión con la base de datos."""
        if self.connection:
            try:
                self.connection.close()
                logger.debug("Conexión SQLite cerrada.")
            except sqlite3.Error:
                logger.exception("Error al cerrar la conexión SQLite.")
            finally:
                self.connection = None
                self.cursor = None

    def obtener_conexion(self):
        """Devuelve la conexión activa o la crea si no existe."""
        if self.connection is None:
            logger.debug("No existe conexión SQLite activa. Se crea una nueva.")
            self.conectar()
        return self.connection