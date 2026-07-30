import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.network.api_client import DispositivoAPIClient


class DeviceDiscoveryService:
    PORT_VERIFICADOR = 8080
    PORT_PLAYER = 2727
    _CACHE_DATA = []
    _CACHE_TS = 0
    _CACHE_TTL = 180

    def __init__(self, timeout_socket=0.2, timeout_http=0.8, max_workers=64):
        self.timeout_socket = timeout_socket
        self.timeout_http = timeout_http
        self.max_workers = max_workers

    def discover(self, progress_callback=None, tipos=None, use_cache=True, force_refresh=False):
        notify = progress_callback or (lambda _msg: None)
        tipos = tuple(tipos or ("verificador", "infotv"))

        if use_cache and not force_refresh and self._cache_valid():
            notify("Usando cache reciente de dispositivos detectados.")
            return self._filtrar_por_tipo(list(self._CACHE_DATA), tipos)

        candidates = self._build_candidates()
        notify(f"Escaneando red local... hosts candidatos: {len(candidates)}")

        found = []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(1, len(candidates)))) as executor:
            futures = {executor.submit(self._probe_host, ip): ip for ip in candidates}
            completados = 0
            total = len(futures)
            for future in as_completed(futures):
                completados += 1
                if completados % 25 == 0 or completados == total:
                    notify(f"Buscando dispositivos en red... {completados}/{total}")
                result = future.result()
                if result:
                    found.extend(result)

        notify(f"Detección finalizada. Dispositivos encontrados: {len(found)}")
        found.sort(key=lambda item: (item.get("tipo", ""), item.get("ip", ""), int(item.get("puerto", 0))))
        self._CACHE_DATA = list(found)
        self._CACHE_TS = time.time()
        return self._filtrar_por_tipo(found, tipos)

    def clear_cache(self):
        self._CACHE_DATA = []
        self._CACHE_TS = 0

    def _cache_valid(self):
        return bool(self._CACHE_DATA) and (time.time() - self._CACHE_TS) <= self._CACHE_TTL

    def _filtrar_por_tipo(self, dispositivos, tipos):
        permitidos = set(tipos or ())
        return [disp for disp in dispositivos if disp.get("tipo") in permitidos]

    def _build_candidates(self):
        ips_locales = self._get_local_ipv4s()
        hosts = set()
        for ip_str in ips_locales:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            if not ip.is_private or ip.is_loopback:
                continue
            network = ipaddress.ip_network(f"{ip}/24", strict=False)
            for host in network.hosts():
                host_str = str(host)
                if host_str != ip_str:
                    hosts.add(host_str)
        return sorted(hosts)

    def _get_local_ipv4s(self):
        ips = set()
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM):
                ip = info[4][0]
                if ip and not ip.startswith("127."):
                    ips.add(ip)
        except OSError:
            pass

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                ip = sock.getsockname()[0]
                if ip and not ip.startswith("127."):
                    ips.add(ip)
        except OSError:
            pass

        return sorted(ips)

    def _probe_host(self, ip):
        encontrados = []

        if self._is_port_open(ip, self.PORT_VERIFICADOR):
            verificador = self._confirm_verificador(ip, self.PORT_VERIFICADOR)
            if verificador:
                encontrados.append(verificador)

        if self._is_port_open(ip, self.PORT_PLAYER):
            player = self._confirm_player(ip, self.PORT_PLAYER)
            if player:
                encontrados.append(player)

        return encontrados

    def _is_port_open(self, ip, port):
        try:
            with socket.create_connection((ip, port), timeout=self.timeout_socket):
                return True
        except OSError:
            return False

    def _confirm_verificador(self, ip, port):
        base_url = f"http://{ip}:{port}/api/veri/batch_productos"
        client = DispositivoAPIClient(base_url, estado_callback=lambda _msg: None)
        status = client.get_status_dispositivo(timeout=self.timeout_http)
        if not status:
            return None

        nombre = (
            status.get("device_name")
            or status.get("nombre")
            or status.get("api")
            or f"Verificador {ip}"
        )
        return {
            "nombre": str(nombre).strip(),
            "ip": ip,
            "puerto": port,
            "tipo": "verificador",
            "status": status,
            "comentario": "Detectado automaticamente en red",
        }

    def _confirm_player(self, ip, port):
        base_url = f"http://{ip}:{port}/api/veri/batch_productos"
        client = DispositivoAPIClient(base_url, estado_callback=lambda _msg: None)

        status = client.get_status_dispositivo(timeout=self.timeout_http)
        player = client.get_player_configuration(timeout=self.timeout_http)

        if not status and not player:
            return None

        nombre = None
        if isinstance(status, dict):
            nombre = status.get("device_name") or status.get("nombre")
        if not nombre and isinstance(player, dict):
            nombre = player.get("device_name") or player.get("api")
        if not nombre:
            nombre = f"InforTV {ip}"

        return {
            "nombre": str(nombre).strip(),
            "ip": ip,
            "puerto": port,
            "tipo": "infotv",
            "status": status or {},
            "player": player or {},
            "comentario": "Detectado automaticamente en red",
        }
