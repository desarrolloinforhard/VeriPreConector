import threading

import pypyodbc
from core.logging.logger import get_logger

logger = get_logger(__name__)


def dsn_configurados():
    try:
        dsn_list = pypyodbc.dataSources()
        logger.debug("DSN configurados obtenidos correctamente.")
        return dsn_list
    except pypyodbc.Error:
        logger.exception("Error al obtener la lista de DSNs.")
        return {}


class ConexionSybase:
    def __init__(self, **kwargs):
        self.conexion = None
        self.usuario = kwargs["user"]
        self.contrasena = kwargs["password"]
        self.dsn_name = kwargs["dsn"]
        self._lock = threading.RLock()

        logger.info(
            "ConexionSybase inicializada | dsn=%s | user=%s",
            self.dsn_name,
            self.usuario,
        )

    def _cerrar_conexion_actual(self):
        if not self.conexion:
            return
        try:
            self.conexion.close()
            logger.info("Conexion Sybase cerrada correctamente.")
        except pypyodbc.Error:
            logger.exception("Error al cerrar la conexion Sybase.")
        finally:
            self.conexion = None

    def _conexion_activa(self):
        if not self.conexion:
            return False
        try:
            with self.conexion.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except pypyodbc.Error:
            logger.warning("Conexion Sybase caida o invalida. Se reiniciara.")
            self._cerrar_conexion_actual()
            return False

    def conectar(self):
        """Conexion de la base de datos."""
        with self._lock:
            try:
                if self._conexion_activa():
                    logger.debug("Conexion Sybase ya activa | dsn=%s", self.dsn_name)
                    return True

                logger.debug("Intentando conectar a Sybase | dsn=%s", self.dsn_name)
                self._cerrar_conexion_actual()
                self.conexion = pypyodbc.connect(
                    DSN=self.dsn_name,
                    user=self.usuario,
                    password=self.contrasena,
                    Driver="{Adaptive Server Anywhere 9.0}",
                    autocommit=True,
                )

                logger.info("Conexion a Sybase establecida correctamente | dsn=%s", self.dsn_name)
                return True

            except pypyodbc.Error:
                self.conexion = None
                logger.exception("Error al conectar a Sybase | dsn=%s", self.dsn_name)
                return False

    def ejecutar_consulta(self, sentencia_sql, parametros=None):
        """
        Ejecuta una consulta SQL en Sybase.
        Acepta parametros opcionales para mantener compatibilidad y mejorar seguridad.
        """
        with self._lock:
            try:
                if not self._conexion_activa():
                    logger.debug("No habia conexion Sybase activa. Se intentara conectar.")
                    self.conectar()

                if not self.conexion:
                    logger.error("No se pudo ejecutar SQL en Sybase porque no hay conexion activa.")
                    return None

                parametros = parametros or ()
                sentencia_limpia = sentencia_sql.strip()

                logger.debug("SQL Sybase: %s", sentencia_limpia)
                if parametros:
                    logger.debug("SQL Sybase params: %s", parametros)

                with self.conexion.cursor() as cursor:
                    if parametros:
                        cursor.execute(sentencia_sql, parametros)
                    else:
                        cursor.execute(sentencia_sql)

                    if sentencia_limpia.upper().startswith("SELECT"):
                        resultados = cursor.fetchall()
                        logger.debug("Consulta Sybase ejecutada correctamente | filas=%s", len(resultados))
                        return resultados

                    logger.info("Operacion Sybase ejecutada correctamente | tipo=no-select")
                    return "Operacion exitosa"

            except pypyodbc.Error:
                logger.exception("Error al ejecutar consulta Sybase.")
                self._cerrar_conexion_actual()
                return None
            except Exception:
                logger.exception("Error inesperado al ejecutar consulta Sybase.")
                self._cerrar_conexion_actual()
                return None

    def desconectar(self):
        """Desconectar de la base de datos."""
        with self._lock:
            if not self.conexion:
                logger.debug("La conexion Sybase ya estaba cerrada.")
                return
            self._cerrar_conexion_actual()
