import sqlite3
from pathlib import Path

from core.logging.logger import get_logger

logger = get_logger(__name__)


class SQLiteDB:
    def __init__(self, db_name):
        """Inicializa la conexión con la base de datos."""
        self.db_name = db_name
        self.ruta_db = db_name
        self.connection = None
        self.cursor = None

        logger.debug("SQLiteDB inicializado | db_name=%s", self.db_name)

    def conectar(self):
        """Establece la conexión con la base de datos."""
        try:
            Path(self.db_name).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cursor = self.connection.cursor()
            logger.debug("Conexión SQLite abierta | db_name=%s", self.db_name)
        except sqlite3.Error:
            self.connection = None
            self.cursor = None
            logger.exception("Error al conectar con la base de datos SQLite | db_name=%s", self.db_name)
            raise

    def crear_tablas(self):
        """Crea las tablas necesarias en la base de datos."""
        try:
            logger.info("Iniciando creación/verificación de tablas SQLite.")
            self.conectar()
            self.crear_tabla_VERIPRE_EQUIPOS()
            self.crear_tabla_VERIPRE_productos()
            self.crear_tabla_VERIPRE_producto_precios()
            self.crear_tabla_VERIPRE_ofertas_plu()
            self.crear_tabla_VERIPRE_ofertas_plu_parametros()
            self.crear_tabla_VERIPRE_ofertas_plu_productos()
            self.crear_tabla_VERIPRE_ad_medias()
            self.crear_tabla_VERIPRE_CONEXION()
            self.crear_tabla_API_KEY()
            logger.info("Proceso de creación/verificación de tablas finalizado correctamente.")
        except sqlite3.Error:
            logger.exception("Error al crear las tablas en SQLite.")
            raise
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
                dFechaU TEXT,
                TIENE_OFERTA INTEGER DEFAULT 0,
                PRECIO_OFERTA REAL,
                OFERTA_DESDE TEXT,
                OFERTA_HASTA TEXT,
                OFERTA_ORIGEN TEXT,
                OFERTA_CCODDIV TEXT,
                OFERTA_DTO REAL
            )
        """
        logger.debug("Creando/verificando tabla SQLite: productos")
        self.ejecutar_consulta(consulta)
        self._asegurar_columnas_productos()

    def crear_tabla_VERIPRE_producto_precios(self):
        """Crea la tabla de precios y packs adicionales por producto."""
        consulta = """
            CREATE TABLE IF NOT EXISTS producto_precios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                CREF TEXT,
                codigo TEXT NOT NULL,
                tipo_precio TEXT NOT NULL,
                categoria TEXT NOT NULL,
                origen TEXT NOT NULL,
                orden INTEGER NOT NULL,
                cantidad INTEGER,
                titulo TEXT NOT NULL,
                detalle TEXT,
                precio REAL NOT NULL,
                nroprecio TEXT,
                dFechaU TEXT
            )
        """
        logger.debug("Creando/verificando tabla SQLite: producto_precios")
        self.ejecutar_consulta(consulta)

    def crear_tabla_VERIPRE_ofertas_plu(self):
        """Crea la cabecera local de ofertas OFPLU."""
        consulta = """
            CREATE TABLE IF NOT EXISTS ofertas_plu (
                noferta INTEGER PRIMARY KEY,
                tipo_oferta TEXT NOT NULL,
                detalle TEXT,
                fecha_inicio TEXT,
                fecha_fin TEXT,
                habilitada INTEGER DEFAULT 1,
                ccoddiv TEXT,
                origen TEXT DEFAULT 'OFPLU',
                uid TEXT,
                dFechaU TEXT
            )
        """
        logger.debug("Creando/verificando tabla SQLite: ofertas_plu")
        self.ejecutar_consulta(consulta)

    def crear_tabla_VERIPRE_ofertas_plu_parametros(self):
        """Crea la tabla local de parámetros de ofertas OFPLU."""
        consulta = """
            CREATE TABLE IF NOT EXISTS ofertas_plu_parametros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                noferta INTEGER NOT NULL,
                orden INTEGER NOT NULL,
                variable TEXT NOT NULL,
                cparametro0 TEXT,
                cparametro1 TEXT,
                cparametro2 TEXT,
                cparametro3 TEXT,
                cparametro4 TEXT,
                cparametro5 TEXT,
                cparametro6 TEXT,
                cparametro7 TEXT,
                cparametro8 TEXT,
                cparametro9 TEXT,
                hora_desde TEXT,
                hora_hasta TEXT,
                acumulador TEXT,
                modifica_subtotal TEXT,
                mixmatch_generico TEXT,
                deshabilitada INTEGER DEFAULT 0,
                relacion TEXT,
                cantidad INTEGER,
                tipo_valor TEXT,
                signo TEXT,
                valor_raw REAL,
                valor_visible REAL,
                modo TEXT,
                detalle TEXT,
                uid TEXT,
                dFechaU TEXT,
                UNIQUE(noferta, orden, variable)
            )
        """
        logger.debug("Creando/verificando tabla SQLite: ofertas_plu_parametros")
        self.ejecutar_consulta(consulta)

    def crear_tabla_VERIPRE_ofertas_plu_productos(self):
        """Crea la tabla local de proyección por producto de ofertas OFPLU."""
        consulta = """
            CREATE TABLE IF NOT EXISTS ofertas_plu_productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                noferta INTEGER NOT NULL,
                cref TEXT NOT NULL,
                codigo TEXT,
                descripcion TEXT,
                precio_oferta REAL,
                ndto REAL,
                fecha_inicio TEXT,
                fecha_fin TEXT,
                ccoddiv TEXT,
                cclavec TEXT,
                cclavea TEXT,
                nmodop TEXT,
                nmodod TEXT,
                detalle TEXT,
                uid TEXT,
                dFechaU TEXT,
                UNIQUE(noferta, cref, ccoddiv, cclavec, cclavea)
            )
        """
        logger.debug("Creando/verificando tabla SQLite: ofertas_plu_productos")
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

    def _asegurar_columnas_productos(self):
        columnas_requeridas = {
            "TIENE_OFERTA": "INTEGER DEFAULT 0",
            "PRECIO_OFERTA": "REAL",
            "OFERTA_DESDE": "TEXT",
            "OFERTA_HASTA": "TEXT",
            "OFERTA_ORIGEN": "TEXT",
            "OFERTA_CCODDIV": "TEXT",
            "OFERTA_DTO": "REAL",
        }

        columnas_actuales = {col.upper() for col in self.obtener_columnas("productos")}
        if not columnas_actuales:
            return

        columnas_obsoletas = {"CODIGO_ORIGINAL", "CODIGO_NORMALIZADO"}
        if columnas_actuales.intersection(columnas_obsoletas):
            self._migrar_tabla_productos_sin_codigos_legacy()
            columnas_actuales = {col.upper() for col in self.obtener_columnas("productos")}
            if not columnas_actuales:
                return

        for nombre, definicion in columnas_requeridas.items():
            if nombre in columnas_actuales:
                continue

            sql = f"ALTER TABLE productos ADD COLUMN {nombre} {definicion}"
            logger.info("Agregando columna faltante en productos | columna=%s", nombre)
            self.ejecutar_consulta(sql)

    def _migrar_tabla_productos_sin_codigos_legacy(self):
        logger.info("Migrando tabla productos para eliminar columnas legacy de codigo.")
        try:
            if not self.conexion_activa():
                self.conectar()

            self.cursor.execute("BEGIN")
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS productos_new (
                    CREF TEXT,
                    codigo TEXT UNIQUE,
                    descripcion TEXT,
                    precio REAL,
                    img_base64 TEXT,
                    formato_imagen TEXT,
                    dFechaU TEXT,
                    TIENE_OFERTA INTEGER DEFAULT 0,
                    PRECIO_OFERTA REAL,
                    OFERTA_DESDE TEXT,
                    OFERTA_HASTA TEXT,
                    OFERTA_ORIGEN TEXT,
                    OFERTA_CCODDIV TEXT,
                    OFERTA_DTO REAL
                )
                """
            )
            self.cursor.execute("DELETE FROM productos_new")
            self.cursor.execute(
                """
                INSERT INTO productos_new (
                    CREF, codigo, descripcion, precio, img_base64, formato_imagen,
                    dFechaU, TIENE_OFERTA, PRECIO_OFERTA, OFERTA_DESDE,
                    OFERTA_HASTA, OFERTA_ORIGEN, OFERTA_CCODDIV, OFERTA_DTO
                )
                SELECT
                    CREF, codigo, descripcion, precio, img_base64, formato_imagen,
                    dFechaU, TIENE_OFERTA, PRECIO_OFERTA, OFERTA_DESDE,
                    OFERTA_HASTA, OFERTA_ORIGEN, OFERTA_CCODDIV, OFERTA_DTO
                FROM productos
                """
            )
            self.cursor.execute("DROP TABLE productos")
            self.cursor.execute("ALTER TABLE productos_new RENAME TO productos")
            self.connection.commit()
            logger.info("Migracion de tabla productos completada correctamente.")
        except sqlite3.Error:
            if self.connection:
                self.connection.rollback()
            logger.exception("Error migrando tabla productos sin columnas legacy.")
            raise
