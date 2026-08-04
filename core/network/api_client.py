import time

import requests


class DispositivoAPIClient:
    STATUS_ENDPOINT = "/api/veri/status"
    PLAYER_CONFIG_ENDPOINT = "/api/veri/configuracion_player"
    GO_UPC_KEY_ENDPOINT = "/api/veri/GO_UPC_KEY"
    IMAGES_API_URL_ENDPOINT = "/api/veri/IMAGES_API_URL"
    PRODUCTOS_DELETE_ENDPOINTS = (
        "/api/veri/batch_productos",
        "/api/veri/ALL_PRODUCTOS",
    )

    def __init__(self, url_base, estado_callback=None):
        self.url_base = url_base
        self.estado_callback = estado_callback or (lambda msg: print(msg))
        self.ultimo_error = None
        self.ultimo_delete_ok = None

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
        self.ultimo_error = None
        self.ultimo_delete_ok = None
        endpoints = self._resolver_delete_endpoints()
        for endpoint in endpoints:
            for intento in range(reintentos):
                url_delete = self._base_host() + endpoint
                try:
                    self.estado_callback(f"{url_delete} -> DELETE intento {intento + 1}")
                    response = requests.delete(url_delete, headers=headers, timeout=10)
                    if response.status_code == 200:
                        self.estado_callback(f"{url_delete} -> respuesta OK")
                        self.ultimo_delete_ok = url_delete
                        self.ultimo_error = None
                        return response
                    detalle = f"{url_delete} -> error HTTP {response.status_code}: {response.text}"
                    self.ultimo_error = detalle
                    self.estado_callback(detalle)
                    print(detalle)
                except Exception as e:
                    detalle = f"{url_delete} -> excepcion: {e}"
                    self.ultimo_error = detalle
                    self.estado_callback(detalle)
                    print(detalle)
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

    def set_go_upc_key(self, api_key, timeout=5):
        url_config = self._base_host() + self.GO_UPC_KEY_ENDPOINT
        try:
            response = requests.post(
                url_config,
                json={"api_key": api_key},
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            if response.status_code != 200:
                self.estado_callback(f"{url_config} -> error HTTP {response.status_code}: {response.text}")
                return False, f"HTTP {response.status_code}"
            return True, "API KEY enviada"
        except Exception as e:
            self.estado_callback(f"{url_config} -> error enviando GO-UPC key: {e}")
            return False, f"Error: {e}"

    def set_images_api_url(self, api_imagenes_url, timeout=5):
        url_config = self._base_host() + self.IMAGES_API_URL_ENDPOINT
        try:
            response = requests.post(
                url_config,
                json={"url": api_imagenes_url},
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            if response.status_code == 200:
                return True, "URL API imagenes enviada"
            if response.status_code == 404:
                self.estado_callback(f"{url_config} -> endpoint no disponible HTTP 404")
                return False, "endpoint no disponible en este APK"
            self.estado_callback(f"{url_config} -> error HTTP {response.status_code}: {response.text}")
            return False, f"HTTP {response.status_code}"
        except Exception as e:
            self.estado_callback(f"{url_config} -> error enviando IMAGES_API_URL: {e}")
            return False, f"Error: {e}"

    def get_images_api_url(self, timeout=5):
        url_config = self._base_host() + self.IMAGES_API_URL_ENDPOINT
        try:
            response = requests.get(url_config, timeout=timeout)
            if response.status_code != 200:
                self.estado_callback(f"{url_config} -> URL API imagenes no disponible HTTP {response.status_code}")
                return None
            data = response.json()
            return data if isinstance(data, dict) else None
        except Exception as e:
            self.estado_callback(f"{url_config} -> error leyendo IMAGES_API_URL: {e}")
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

    def _resolver_delete_endpoints(self):
        try:
            url_normalizada = self.url_base.strip()
            if "/api/" in url_normalizada:
                path_actual = "/api/" + url_normalizada.split("/api/", 1)[1].lstrip("/")
            elif url_normalizada.endswith("/api"):
                path_actual = "/api"
            else:
                path_actual = self.PRODUCTOS_DELETE_ENDPOINTS[0]
        except Exception:
            path_actual = self.PRODUCTOS_DELETE_ENDPOINTS[0]

        endpoints = []
        if path_actual not in endpoints:
            endpoints.append(path_actual)

        for endpoint in self.PRODUCTOS_DELETE_ENDPOINTS:
            if endpoint not in endpoints:
                endpoints.append(endpoint)
        return tuple(endpoints)
