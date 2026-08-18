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
        self.cursor = None
        self.usuario = kwargs["user"]
        self.contrasena = kwargs["password"]
        self.dsn_name = kwargs["dsn"]

        logger.debug(
            "ConexionSybase inicializada | dsn=%s | user=%s",
            self.dsn_name,
            self.usuario,
        )

    def conectar(self):
        """Conexion de la base de datos."""
        try:
            logger.debug("Intentando conectar a Sybase | dsn=%s", self.dsn_name)

            self.conexion = pypyodbc.connect(
                DSN=self.dsn_name,
                user=self.usuario,
                password=self.contrasena,
                Driver="{Adaptive Server Anywhere 9.0}",
            )
            self.cursor = self.conexion.cursor()

            logger.debug("Conexion a Sybase establecida correctamente | dsn=%s", self.dsn_name)
            return True

        except pypyodbc.Error:
            logger.exception("Error al conectar a Sybase | dsn=%s", self.dsn_name)
            return False

    def ejecutar_consulta(self, sentencia_sql, parametros=None):
        """
        Ejecuta una consulta SQL en Sybase.
        Acepta parametros opcionales para mantener compatibilidad y mejorar seguridad.
        """
        try:
            if not self.conexion:
                logger.debug("No habia conexion Sybase activa. Se intentara conectar.")
                self.conectar()

            if not self.conexion:
                logger.error("No se pudo ejecutar SQL en Sybase porque no hay conexion activa.")
                return None

            parametros = parametros or ()

            logger.debug("SQL Sybase: %s", sentencia_sql.strip())
            if parametros:
                logger.debug("SQL Sybase params: %s", parametros)

            with self.conexion.cursor() as cursor:
                try:
                    cursor.execute("SELECT 1")
                except pypyodbc.Error:
                    logger.warning("Conexion Sybase caida. Reintentando reconexion.")
                    self.conectar()
                    cursor = self.conexion.cursor()

                if parametros:
                    cursor.execute(sentencia_sql, parametros)
                else:
                    cursor.execute(sentencia_sql)

                if sentencia_sql.strip().upper().startswith("SELECT"):
                    resultados = cursor.fetchall()
                    logger.debug("Consulta Sybase ejecutada correctamente | filas=%s", len(resultados))
                    return resultados
                else:
                    self.conexion.commit()
                    logger.info("Operacion Sybase ejecutada correctamente | tipo=no-select")
                    return "Operacion exitosa"

        except pypyodbc.Error:
            logger.exception("Error al ejecutar consulta Sybase.")
            return None
        except Exception:
            logger.exception("Error inesperado al ejecutar consulta Sybase.")
            return None

    def desconectar(self):
        """Desconectar de la base de datos."""
        try:
            if self.conexion and self.conexion.connected:
                self.conexion.close()
                logger.debug("Conexion Sybase cerrada correctamente.")
            else:
                logger.debug("La conexion Sybase ya estaba cerrada.")
        except pypyodbc.Error:
            logger.exception("Error al cerrar la conexion Sybase.")
        finally:
            self.conexion = None
            self.cursor = None
