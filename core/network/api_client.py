import requests
import time

class DispositivoAPIClient:
    def __init__(self, url_base, estado_callback=None):
        """
        :param url_base: URL completa con endpoint (http://ip:puerto/endpoint)
        :param estado_callback: función para notificar el estado del envío
        """
        self.url_base = url_base
        self.estado_callback = estado_callback or (lambda msg: print(msg))

    def enviar_post_json(self, data_json, headers=None, reintentos=3):
        headers = headers or {"Content-Type": "application/json"}
        for intento in range(reintentos):
            try:
                self.estado_callback(f"{self.url_base} → Enviando intento {intento+1}")
                response = requests.post(self.url_base, json=data_json, headers=headers, timeout=60)
                if response.status_code == 200:
                    self.estado_callback(f"{self.url_base} → ✅ Éxito")
                    return response
                else:
                    self.estado_callback(f"{self.url_base} → ❌ Error {response.status_code}: {response.text}")
            except Exception as e:
                self.estado_callback(f"{self.url_base} → ❌ Excepción: {e}")
            time.sleep(3)
        return None

    def enviar_post_multipart(self, files, reintentos=3):
        for intento in range(reintentos):
            try:
                self.estado_callback(f"{self.url_base} → Enviando intento {intento+1}")
                response = requests.post(self.url_base, files=files, timeout=30)
                if response.status_code == 200:
                    self.estado_callback(f"{self.url_base} → ✅ Éxito")
                    return response
                else:
                    self.estado_callback(f"{self.url_base} → ❌ Error {response.status_code}: {response.text}")
            except Exception as e:
                self.estado_callback(f"{self.url_base} → ❌ Excepción: {e}")
            time.sleep(3)
        return None

    def enviar_delete(self, headers=None, reintentos=3):
        headers = headers or {"Content-Type": "application/json"}
        for intento in range(reintentos):
            try:
                self.estado_callback(f"{self.url_base} → Enviando DELETE intento {intento+1}")
                response = requests.delete(self.url_base, headers=headers, timeout=10)
                if response.status_code == 200:
                    self.estado_callback(f"{self.url_base} → ✅ Éxito")
                    return response
                else:
                    self.estado_callback(f"{self.url_base} → ❌ Error {response.status_code}: {response.text}")
            except Exception as e:
                self.estado_callback(f"{self.url_base} → ❌ Excepción: {e}")
            time.sleep(2)
        return None
