import base64
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote
from io import BytesIO

import requests
from PIL import Image


class ProductImageResolver:
    DEFAULT_IMAGE_API_URL = "http://inforhardserver.ddns.net:5000"
    IMAGE_DIRS = (r"F:\Dba", r"F:\Sp\IMAGEN", r"S:\Sp\IMAGEN")
    FORMAT_PRIORITY = ("webp", "png", "jpg", "jpeg", "gif", "bmp")
    CONTENT_TYPES = {
        "webp": "image/webp",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "bmp": "image/bmp",
    }

    def __init__(
        self,
        db,
        config=None,
        estado_callback=None,
        incluir_api_propia=True,
        incluir_go_upc=True,
    ):
        self.db = db
        self.config = config or {}
        self.estado_callback = estado_callback or (lambda msg: None)
        self.incluir_api_propia = incluir_api_propia
        self.incluir_go_upc = incluir_go_upc

    def resolver(self, codigo, img_base64=None, formato=None):
        codigo = self._limpiar_codigo(codigo)
        if not codigo:
            return img_base64, formato

        if img_base64:
            return img_base64, formato

        img_base64, formato = self._buscar_en_sqlite(codigo)
        if img_base64:
            return img_base64, formato

        imagen = self._buscar_en_fuentes_concurrentes(codigo)
        if imagen:
            origen = imagen.get("origen")
            imagen = self._normalizar_imagen_producto(imagen["bytes"], imagen["formato"], codigo)
            self._guardar_en_sqlite(codigo, imagen["bytes"], imagen["formato"])
            if origen in {"carpetas", "api_propia", "go_upc"}:
                ruta = self._guardar_en_carpeta(codigo, imagen["bytes"], imagen["formato"])
            else:
                ruta = None
            if origen == "go_upc":
                self._subir_a_api_propia(codigo, imagen["bytes"], imagen["formato"], ruta)
            return self._a_base64(imagen["bytes"]), imagen["formato"]

        return None, None

    def _buscar_en_fuentes_concurrentes(self, codigo):
        tasks = [
            ("carpetas", self._buscar_en_carpetas),
        ]
        if self.incluir_api_propia:
            tasks.append(("api_propia", self._buscar_en_api_propia))
        if self.incluir_go_upc:
            tasks.append(("go_upc", self._buscar_en_go_upc))

        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            future_to_source = {
                executor.submit(func, codigo): source
                for source, func in tasks
            }
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    imagen = future.result()
                except Exception as e:
                    self.estado_callback(f"[imagenes] Fuente {source} fallo para {codigo}: {e}")
                    continue
                if not imagen:
                    continue
                imagen["origen"] = source
                self.estado_callback(f"[imagenes] Fuente {source} resolvio imagen para {codigo}")
                return imagen
        return None

    def _buscar_en_sqlite(self, codigo):
        try:
            rows = self.db.ejecutar_consulta(
                "SELECT img_base64, formato_imagen FROM productos WHERE codigo = ?",
                (codigo,),
            ) or []
            if rows and rows[0] and rows[0][0]:
                return rows[0][0], rows[0][1]
        except Exception as e:
            self.estado_callback(f"[imagenes] SQLite error codigo {codigo}: {e}")
        return None, None

    def _buscar_en_carpetas(self, codigo):
        for carpeta in self.IMAGE_DIRS:
            base = Path(carpeta)
            if not base.exists():
                continue
            for formato in self.FORMAT_PRIORITY:
                ruta = base / f"{codigo}.{formato}"
                if not ruta.exists():
                    continue
                try:
                    return {
                        "bytes": ruta.read_bytes(),
                        "formato": "jpg" if formato == "jpeg" else formato,
                        "ruta": str(ruta),
                    }
                except Exception as e:
                    self.estado_callback(f"[imagenes] No se pudo leer {ruta}: {e}")
        return None

    def _buscar_en_api_propia(self, codigo):
        base_url = self._api_imagenes_url()
        if not base_url:
            return None

        url = self._url_api_codigo(base_url, codigo)
        try:
            response = requests.get(url, timeout=12)
            if response.status_code != 200:
                return None
            formato = self._formato_desde_respuesta(response, url)
            return {"bytes": response.content, "formato": formato}
        except Exception as e:
            self.estado_callback(f"[imagenes] API propia no disponible para {codigo}: {e}")
            return None

    def _buscar_en_go_upc(self, codigo):
        api_key = self._go_upc_api_key()
        if not api_key:
            return None

        base_url = self.config.get("go_upc_base_url", "https://go-upc.com/api/v1")
        url = f"{str(base_url).rstrip('/')}/code/{quote(codigo)}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                return None
            data = response.json()
            img_url = (data.get("product") or {}).get("imageUrl")
            if not img_url:
                return None

            img_response = requests.get(img_url, timeout=30)
            if img_response.status_code != 200:
                return None
            formato = self._formato_desde_respuesta(img_response, img_url)
            return {"bytes": img_response.content, "formato": formato}
        except Exception as e:
            self.estado_callback(f"[imagenes] GO-UPC error codigo {codigo}: {e}")
            return None

    def _guardar_en_sqlite(self, codigo, imagen_bytes, formato):
        try:
            self.db.ejecutar_consulta(
                """
                UPDATE productos
                SET img_base64 = ?, formato_imagen = ?
                WHERE codigo = ?
                """,
                (self._a_base64(imagen_bytes), formato, codigo),
            )
        except Exception as e:
            self.estado_callback(f"[imagenes] No se pudo guardar en SQLite {codigo}: {e}")

    def _guardar_en_carpeta(self, codigo, imagen_bytes, formato):
        destino_dir = self._carpeta_destino()
        if not destino_dir:
            return None
        try:
            destino_dir.mkdir(parents=True, exist_ok=True)
            ruta = destino_dir / f"{codigo}.{formato}"
            ruta.write_bytes(imagen_bytes)
            return str(ruta)
        except Exception as e:
            self.estado_callback(f"[imagenes] No se pudo guardar archivo {codigo}: {e}")
            return None

    def _subir_a_api_propia(self, codigo, imagen_bytes, formato, ruta=None):
        base_url = self._api_imagenes_url()
        if not base_url:
            return

        url = self._url_api_upload(base_url)
        filename = os.path.basename(ruta) if ruta else f"{codigo}.{formato}"
        try:
            files = {
                "image": (
                    filename,
                    imagen_bytes,
                    self.CONTENT_TYPES.get(formato, "application/octet-stream"),
                )
            }
            response = requests.post(url, data={"codigo": codigo}, files=files, timeout=20)
            if response.status_code not in (200, 201):
                self.estado_callback(
                    f"[imagenes] API propia upload HTTP {response.status_code} para {codigo}"
                )
        except Exception as e:
            self.estado_callback(f"[imagenes] No se pudo subir {codigo} a API propia: {e}")

    def _go_upc_api_key(self):
        try:
            rows = self.db.ejecutar_consulta("SELECT api_key FROM api_key ORDER BY id DESC LIMIT 1") or []
            if rows and rows[0] and rows[0][0]:
                return str(rows[0][0]).strip()
        except Exception as e:
            self.estado_callback(f"[imagenes] No se pudo leer API KEY GO-UPC: {e}")
        return None

    def _api_imagenes_url(self):
        url = (
            self.config.get("api_imagenes_url")
            or self.config.get("imagenes_api_url")
            or self.DEFAULT_IMAGE_API_URL
        )
        return str(url).strip() if url else ""

    def _url_api_codigo(self, base_url, codigo):
        base_url = base_url.rstrip("/")
        if base_url.endswith("/upload"):
            base_url = base_url[: -len("/upload")]
        if "/api/IMAGES" in base_url:
            return f"{base_url}/codigo/{quote(codigo)}"
        return f"{base_url}/api/IMAGES/codigo/{quote(codigo)}"

    def _url_api_upload(self, base_url):
        base_url = base_url.rstrip("/")
        if base_url.endswith("/upload"):
            return base_url
        if "/api/IMAGES" in base_url:
            return f"{base_url}/upload"
        return f"{base_url}/api/IMAGES/upload"

    def _carpeta_destino(self):
        for carpeta in self.IMAGE_DIRS:
            ruta = Path(carpeta)
            if ruta.exists():
                return ruta
        return Path(self.IMAGE_DIRS[0])

    def _formato_desde_respuesta(self, response, url):
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        for formato, mime in self.CONTENT_TYPES.items():
            if content_type == mime:
                return "jpg" if formato == "jpeg" else formato

        ext = Path(str(url).split("?")[0]).suffix.lower().replace(".", "")
        if ext in self.FORMAT_PRIORITY:
            return "jpg" if ext == "jpeg" else ext
        return "jpg"

    def _limpiar_codigo(self, codigo):
        codigo = str(codigo).strip() if codigo is not None else ""
        if "/" in codigo or "\\" in codigo or "\x00" in codigo:
            return ""
        return codigo

    def _normalizar_imagen_producto(self, imagen_bytes, formato, codigo=None):
        try:
            img = Image.open(BytesIO(imagen_bytes))

            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")

            if img.mode == "RGBA":
                fondo = Image.new("RGB", img.size, (255, 255, 255))
                fondo.paste(img, mask=img.split()[3])
                img = fondo
            else:
                img = img.convert("RGB")

            maximo = (1400, 1400)
            objetivo = (1000, 1000)

            if img.width > maximo[0] or img.height > maximo[1]:
                img.thumbnail(maximo, Image.Resampling.LANCZOS)

            img.thumbnail(objetivo, Image.Resampling.LANCZOS)

            calidad = 88
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=calidad, optimize=True)
            contenido = buffer.getvalue()

            while len(contenido) > 700 * 1024 and calidad > 65:
                calidad -= 5
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=calidad, optimize=True)
                contenido = buffer.getvalue()

            if codigo:
                self.estado_callback(
                    f"[imagenes] Normalizada {codigo}: {img.width}x{img.height}px | {len(contenido) / 1024:.0f} KB"
                )

            return {"bytes": contenido, "formato": "jpg"}
        except Exception as e:
            self.estado_callback(f"[imagenes] No se pudo normalizar {codigo or '-'}: {e}")
            return {"bytes": imagen_bytes, "formato": "jpg" if formato == "jpeg" else formato}

    def _a_base64(self, imagen_bytes):
        return base64.b64encode(imagen_bytes).decode("utf-8")
