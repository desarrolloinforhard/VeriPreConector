ENDPOINT_PRODUCTOS_BATCH = "/api/veri/batch_productos"
ENDPOINT_STATUS = "/api/veri/status"
ENDPOINT_CONFIGURACION_PLAYER = "/api/veri/configuracion_player"


class VeriPreDispositivosURLBuilder:
    def __init__(self, conexion_dba):
        self.conexion_dba = conexion_dba

    def obtener_urls_api(self, endpoint="/api/veri/ad_medias_images"):
        """
        Devuelve una lista de diccionarios con 'nombre' y 'url' de los dispositivos registrados.

        :param endpoint: Ruta de la API a invocar (por defecto: /api/veri/ad_medias_images)
        :return: Lista de diccionarios [{'nombre': ..., 'url': ...}]
        """
        try:
            consulta = "SELECT nombre, direccion_conexion, puerto FROM VERIPRE_EQUIPOS"
            dispositivos = self.conexion_dba.ejecutar_consulta(consulta)
            urls = []

            for nombre, direccion, puerto in dispositivos:
                url = f"http://{direccion}:{puerto}{endpoint}"
                urls.append({"nombre": nombre, "url": url})

            return urls

        except Exception as e:
            print(f"Error al obtener URLs de dispositivos: {e}")
            return []

