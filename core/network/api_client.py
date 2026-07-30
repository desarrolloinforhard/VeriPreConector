import time

import requests


class DispositivoAPIClient:
    STATUS_ENDPOINT = "/api/veri/status"
    PLAYER_CONFIG_ENDPOINT = "/api/veri/configuracion_player"

    def __init__(self, url_base, estado_callback=None):
        self.url_base = url_base
        self.estado_callback = estado_callback or (lambda msg: print(msg))

    def enviar_post_json(self, data_json, headers=None, reintentos=3, timeout=60):
        headers = headers or {"Content-Type": "application/json"}
        for intento in range(reintentos):
            try:
                self.estado_callback(f"{self.url_base} -> intento {intento + 1}")
                response = requests.post(self.url_base, json=data_json, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    self.estado_callback(f"{self.url_base} -> respuesta OK")
                    return response
                self.estado_callback(f"{self.url_base} -> error HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.estado_callback(f"{self.url_base} -> excepcion: {e}")
            time.sleep(3)
        return None

    def enviar_post_multipart(self, files, reintentos=3):
        for intento in range(reintentos):
            try:
                self.estado_callback(f"{self.url_base} -> intento {intento + 1}")
                response = requests.post(self.url_base, files=files, timeout=30)
                if response.status_code == 200:
                    self.estado_callback(f"{self.url_base} -> respuesta OK")
                    return response
                self.estado_callback(f"{self.url_base} -> error HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.estado_callback(f"{self.url_base} -> excepcion: {e}")
            time.sleep(3)
        return None

    def enviar_delete(self, headers=None, reintentos=3):
        headers = headers or {"Content-Type": "application/json"}
        for intento in range(reintentos):
            try:
                self.estado_callback(f"{self.url_base} -> DELETE intento {intento + 1}")
                response = requests.delete(self.url_base, headers=headers, timeout=10)
                if response.status_code == 200:
                    self.estado_callback(f"{self.url_base} -> respuesta OK")
                    return response
                self.estado_callback(f"{self.url_base} -> error HTTP {response.status_code}: {response.text}")
            except Exception as e:
                self.estado_callback(f"{self.url_base} -> excepcion: {e}")
            time.sleep(2)
        return None

    def get_status_dispositivo(self, timeout=5):
        url_status = self._base_host() + self.STATUS_ENDPOINT
        try:
            response = requests.get(url_status, timeout=timeout)
            if response.status_code != 200:
                self.estado_callback(f"{url_status} -> status no disponible HTTP {response.status_code}")
                return None

            try:
                data = response.json()
            except ValueError:
                self.estado_callback(f"{url_status} -> respuesta no JSON")
                return None

            if not isinstance(data, dict):
                self.estado_callback(f"{url_status} -> formato de status invalido")
                return None
            return data
        except Exception as e:
            self.estado_callback(f"{url_status} -> status no disponible: {e}")
            return None

    def get_player_configuration(self, timeout=5):
        url_config = self._base_host() + self.PLAYER_CONFIG_ENDPOINT
        try:
            response = requests.get(url_config, timeout=timeout)
            if response.status_code != 200:
                self.estado_callback(f"{url_config} -> config player no disponible HTTP {response.status_code}")
                return None
            data = response.json()
            return data if isinstance(data, dict) else None
        except Exception as e:
            self.estado_callback(f"{url_config} -> error leyendo config player: {e}")
            return None

    def set_player_configuration(self, data_json, timeout=8):
        url_config = self._base_host() + self.PLAYER_CONFIG_ENDPOINT
        try:
            response = requests.post(
                url_config,
                json=data_json,
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            if response.status_code != 200:
                self.estado_callback(f"{url_config} -> error HTTP {response.status_code}: {response.text}")
                return None
            data = response.json()
            return data if isinstance(data, dict) else None
        except Exception as e:
            self.estado_callback(f"{url_config} -> error guardando config player: {e}")
            return None

    def obtener_json_respuesta(self, response):
        if response is None:
            return None
        try:
            data = response.json()
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def _base_host(self):
        return self.url_base.split("/api")[0]
