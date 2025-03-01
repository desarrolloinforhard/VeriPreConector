import pypyodbc
#import json
import traceback


def dsn_configurados():
    try:
        # Obtener una lista de DSNs
        dsn_list = pypyodbc.dataSources()
        return dsn_list
    except pypyodbc.Error as ex:
        print("Error al obtener la lista de DSNs:", ex)

class ConexionSybase:
    def __init__(self, **kwargs):
        self.conexion = None
        self.cursor = None
        self.usuario = kwargs["user"]
        self.contrasena = kwargs["password"]
        self.dsn_name = kwargs["dsn"]

    #CONEXION DE LA BASE DE DATOS
    def conectar(self):
        try:
            self.conexion = pypyodbc.connect(
                DSN=self.dsn_name,
                user=self.usuario,
                password=self.contrasena,
                Driver="{Adaptive Server Anywhere 9.0}",                
            )
            self.cursor = self.conexion.cursor()  # Crea el cursor
            return True
        except pypyodbc.Error as err:
            print(f"Error al conectar a Sybase: {err}")
            return False
        
    def ejecutar_consulta(self, sentencia_sql):
        try:
            # Intentar conectar si no se ha hecho antes
            if not self.conexion:
                self.conectar()

            # Crear un cursor para ejecutar la sentencia SQL
            with self.conexion.cursor() as cursor:
                # Verificación antes de ejecutar la consulta para asegurarse de que la conexión esté activa
                try:
                    # Intentar ejecutar una consulta de prueba (como un SELECT vacío)
                    cursor.execute('SELECT 1')
                except pypyodbc.Error:
                    # Si la conexión se ha cerrado, reconectar
                    self.conectar()
                
                # Ahora ejecutar la consulta principal
                cursor.execute(sentencia_sql)
                
                # Obtener los resultados si la consulta es un SELECT
                if sentencia_sql.strip().upper().startswith('SELECT'):
                    resultados = cursor.fetchall()
                    return resultados
                else:
                    # Para otros tipos de consultas (INSERT, UPDATE, DELETE)
                    self.conexion.commit()
                    return "Operación exitosa"

        except pypyodbc.Error as e:
            error_traceback = traceback.format_exc()
            print(f"Error al recargar dispositivos: {e}\nTraceback:\n{error_traceback}")
            print(f"Error al ejecutar la consulta: {e}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
        
    # DESCONECTAR DE LA BASE DE DATOS
    def desconectar(self):
        try:
            if self.conexion and self.conexion.connected:
                self.conexion.close()
            else:
                print("La conexión ya estaba cerrada.")
        except pypyodbc.Error as err:
            print(f"Error al cerrar la conexión: {err}")