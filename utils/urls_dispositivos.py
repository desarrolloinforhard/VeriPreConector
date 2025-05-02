class VeriPreDispositivosURLBuilder:
    def __init__(self, conexion_dba):
        self.conexion_dba = conexion_dba

    def obtener_urls_api(self, endpoint="/api/veri/ad_medias_images"):
        """
        Devuelve una lista de URLs armadas usando los dispositivos registrados en VERIPRE_EQUIPOS.

        :param endpoint: Ruta de la API a invocar (por defecto: /api/veri/ad_medias_images)
        :return: Lista de URLs completas
        """
        try:
            consulta = "SELECT direccion_conexion, puerto FROM VERIPRE_EQUIPOS"
            dispositivos = self.conexion_dba.ejecutar_consulta(consulta)
            urls = []

            for direccion, puerto in dispositivos:
                url = f"http://{direccion}:{puerto}{endpoint}"
                urls.append(url)

            return urls

        except Exception as e:
            print(f"Error al obtener URLs de dispositivos: {e}")
            return []
