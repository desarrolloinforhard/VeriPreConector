import os
import json

class ConfigManager:
    def __init__(self, carpeta="FUNC", archivo="config.json"):
        self.carpeta = carpeta
        self.archivo = os.path.join(self.carpeta, archivo)
        self._verificar_o_crear_config()

    def _verificar_o_crear_config(self):
        """Verifica si existe el archivo de configuración, si no lo crea con valores predeterminados."""
        if not os.path.exists(self.carpeta):
            os.makedirs(self.carpeta)

        if not os.path.exists(self.archivo):
            config_inicial = {}
            self._guardar_config(config_inicial)
            print(f"Archivo {self.archivo} creado con configuración predeterminada.")

    def _cargar_config(self):
        """Carga el archivo JSON y devuelve su contenido."""
        try:
            with open(self.archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error al leer el archivo de configuración.")
            return {}

    def _guardar_config(self, datos):
        """Guarda el JSON en el archivo."""
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4)

    def obtener_config(self, clave=None):
        """Obtiene la configuración completa o un valor específico."""
        config = self._cargar_config()
        if clave:
            return config.get(clave, None)
        return config

    def actualizar_config(self, clave, valor):
        """Actualiza o agrega una clave en la configuración."""
        config = self._cargar_config()
        config[clave] = valor
        self._guardar_config(config)
        print(f"Configuración actualizada: {clave} = {valor}")

    def eliminar_clave(self, clave):
        """Elimina una clave específica del JSON."""
        config = self._cargar_config()
        if clave in config:
            del config[clave]
            self._guardar_config(config)
            print(f"Clave '{clave}' eliminada.")
        else:
            print(f"La clave '{clave}' no existe en la configuración.")
            
    def eliminar_clave_de_clave(self, clave_1, clave_2):
        """Elimina una clave específica del JSON."""
        config = self._cargar_config()
        if clave_2 in config[clave_1]:
            del config[clave_1][clave_2]
            self._guardar_config(config)
            print(f"Clave '{clave_2}' eliminada.")
        else:
            print(f"La clave '{clave_2}' no existe en la configuración.")
        
    def agregar_a_clave(self, clave, nuevo_diccionario):
        """Agrega un diccionario dentro de una clave específica en la configuración."""
        config = self._cargar_config()

        # Si la clave no existe, se crea como un diccionario vacío
        if clave not in config:
            config[clave] = {}

        # Verifica que el valor en la clave sea un diccionario
        if isinstance(config[clave], dict):
            config[clave].update(nuevo_diccionario)
            self._guardar_config(config)
            print(f"Se ha agregado a '{clave}': {nuevo_diccionario}")
        else:
            print(f"Error: La clave '{clave}' no contiene un diccionario.")
            
            
    def obtener_claves_de(self, clave_principal):
        """Devuelve una lista con las claves dentro de una clave específica del archivo de configuración."""
        config = self._cargar_config()
        if clave_principal in config and isinstance(config[clave_principal], dict):
            return list(config[clave_principal].keys())
        return []


