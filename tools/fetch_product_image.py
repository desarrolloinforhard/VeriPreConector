import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

import requests


# Configuracion fija para el exe. Los argumentos por consola pueden pisar estos valores.
IMAGE_DIR = Path(r"F:\Sp\IMAGEN")
DEFAULT_VERIPRE_INTERNAL = Path(r"F:\Sp\facturap\exes\veripre\_internal")
HARDCODED_IMAGE_API_URL = "http://190.7.6.80:5000/"
HARDCODED_GO_UPC_KEY = "ebc6686f13a3431841ee9d0419ae53ce7a8bec130f975dd66beb866e3f0fce75"
LOCAL_FORMATS = ("webp", "png", "jpg", "jpeg", "gif", "bmp")
CONTENT_TYPE_FORMATS = {
    "image/webp": "webp",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/bmp": "bmp",
}


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def candidate_base_dirs(extra_config=None):
    bases = [
        app_dir(),
        app_dir() / "_internal",
        app_dir().parent,
        app_dir().parent / "_internal",
        DEFAULT_VERIPRE_INTERNAL,
        Path.cwd(),
    ]
    if extra_config:
        config_path = Path(extra_config).expanduser()
        bases.insert(0, config_path.parent if config_path.suffix else config_path)

    unique = []
    seen = set()
    for base in bases:
        try:
            resolved = base.resolve()
        except Exception:
            resolved = base
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def load_config(extra_config=None):
    candidates = []
    if extra_config:
        path = Path(extra_config).expanduser()
        candidates.append(path if path.suffix else path / "config.json")

    candidates.extend(base / "config.json" for base in candidate_base_dirs(extra_config))
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f), path
    return {}, None


def http_get(url, **kwargs):
    with requests.Session() as session:
        session.trust_env = False
        return session.get(url, **kwargs)


def normalize_image_api_url(base_url, codigo):
    base_url = str(base_url or "").strip().rstrip("/")
    if not base_url:
        return None
    if base_url.endswith("/upload"):
        base_url = base_url[: -len("/upload")]
    if "/api/IMAGES" in base_url:
        return f"{base_url}/codigo/{quote(codigo)}"
    return f"{base_url}/api/IMAGES/codigo/{quote(codigo)}"


def existing_image(codigo):
    for ext in LOCAL_FORMATS:
        path = IMAGE_DIR / f"{codigo}.{ext}"
        if path.exists():
            return path
    return None


def format_from_response(response, fallback_url=None):
    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if content_type in CONTENT_TYPE_FORMATS:
        return CONTENT_TYPE_FORMATS[content_type]

    if fallback_url:
        ext = Path(str(fallback_url).split("?")[0]).suffix.lower().replace(".", "")
        if ext in LOCAL_FORMATS:
            return "jpg" if ext == "jpeg" else ext

    return "jpg"


def save_image(codigo, image_bytes, formato):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    formato = "jpg" if formato == "jpeg" else formato
    path = IMAGE_DIR / f"{codigo}.{formato}"
    path.write_bytes(image_bytes)
    return path


def save_go_upc_json(codigo, data):
    json_dir = IMAGE_DIR / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    path = json_dir / f"{codigo}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def normalize_upload_url(base_url):
    base_url = str(base_url or "").strip().rstrip("/")
    if not base_url:
        return None
    if base_url.endswith("/upload"):
        return base_url
    if "/api/IMAGES" in base_url:
        return f"{base_url}/upload"
    return f"{base_url}/api/IMAGES/upload"


def upload_to_local_api(codigo, image_bytes, formato, api_url):
    url = normalize_upload_url(api_url)
    if not url:
        return False, "API local no configurada"

    content_type = {
        "webp": "image/webp",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "bmp": "image/bmp",
    }.get(formato, "application/octet-stream")
    filename = f"{codigo}.{formato}"

    with requests.Session() as session:
        session.trust_env = False
        response = session.post(
            url,
            data={"codigo": codigo},
            files={"image": (filename, image_bytes, content_type)},
            timeout=20,
        )

    if response.status_code in (200, 201):
        return True, "subida OK"
    return False, f"HTTP {response.status_code}: {response.text[:200]}"


def fetch_from_local_api(codigo, api_url):
    url = normalize_image_api_url(api_url, codigo)
    if not url:
        return None

    response = http_get(url, timeout=15)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return {
        "bytes": response.content,
        "formato": format_from_response(response, url),
        "fuente": "api-local",
    }


def read_go_upc_key(cli_key=None, config=None, config_path=None):
    if cli_key:
        return cli_key.strip()

    if HARDCODED_GO_UPC_KEY:
        return HARDCODED_GO_UPC_KEY.strip()

    config = config or {}
    for key_name in ("go_upc_api_key", "go_upc_key", "api_key_go_upc"):
        value = config.get(key_name)
        if value:
            return str(value).strip()

    env_key = os.getenv("GO_UPC_API_KEY")
    if env_key:
        return env_key.strip()

    db_candidates = []
    if config_path:
        config_dir = Path(config_path).parent
        db_candidates.extend([
            config_dir / "DB" / "veripre.db",
            config_dir.parent / "DB" / "veripre.db",
            config_dir / "veripre.db",
        ])
    for base in candidate_base_dirs(config_path):
        db_candidates.extend([
            base / "DB" / "veripre.db",
            base.parent / "DB" / "veripre.db",
            base / "veripre.db",
        ])

    seen = set()
    for db_path in db_candidates:
        key = str(db_path).lower()
        if key in seen or not db_path.exists():
            continue
        seen.add(key)
        try:
            with sqlite3.connect(str(db_path)) as conn:
                row = conn.execute("SELECT api_key FROM api_key ORDER BY id DESC LIMIT 1").fetchone()
                if row and row[0]:
                    return str(row[0]).strip()
        except sqlite3.Error:
            continue
    return None


def fetch_from_go_upc(codigo, api_key, base_url="https://go-upc.com/api/v1"):
    if not api_key:
        return None

    url = f"{base_url.rstrip('/')}/code/{quote(codigo)}"
    response = http_get(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        timeout=20,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()

    data = response.json()
    json_path = save_go_upc_json(codigo, data)
    image_url = (data.get("product") or {}).get("imageUrl")
    if not image_url:
        return {"json_path": json_path, "sin_imagen": True}

    image_response = http_get(image_url, timeout=30)
    image_response.raise_for_status()
    return {
        "bytes": image_response.content,
        "formato": format_from_response(image_response, image_url),
        "fuente": "go-upc",
        "json_path": json_path,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        prog="TraerImagen",
        description="Descarga una imagen de producto por codigo de barras.",
    )
    parser.add_argument("-cod", "--codigo", required=True, help="Codigo de barras del producto.")
    parser.add_argument("--api-url", help="URL base de la API local de imagenes.")
    parser.add_argument("--go-upc-key", help="API KEY GO-UPC. Si se omite, usa DB o GO_UPC_API_KEY.")
    parser.add_argument("--config", help="Ruta al config.json o carpeta _internal de VeriPre.")
    parser.add_argument("--force", action="store_true", help="Descarga aunque ya exista una imagen local.")
    return parser.parse_args()


def main():
    args = parse_args()
    codigo = str(args.codigo).strip()
    if not codigo:
        print("ERROR: codigo vacio")
        return 2

    if not args.force:
        path = existing_image(codigo)
        if path:
            print(f"OK: ya existe imagen local: {path}")
            return 0

    config, config_path = load_config(args.config)
    api_url = (
        args.api_url
        or HARDCODED_IMAGE_API_URL
        or config.get("api_imagenes_url")
        or config.get("imagenes_api_url")
    )
    if config_path:
        print(f"INFO: config usado: {config_path}")
    else:
        print("AVISO: no se encontro config.json; se usaran solo parametros y variables de entorno")

    try:
        imagen = fetch_from_local_api(codigo, api_url)
        if imagen:
            path = save_image(codigo, imagen["bytes"], imagen["formato"])
            print(f"OK: imagen descargada desde API local: {path}")
            return 0
    except Exception as e:
        print(f"AVISO: no se pudo descargar desde API local: {e}")

    try:
        api_key = read_go_upc_key(args.go_upc_key, config=config, config_path=config_path)
        if not api_key:
            print("AVISO: no se encontro API KEY GO-UPC en config, entorno ni DB local")
            print("ERROR: no se encontro imagen en API local y no se pudo consultar GO-UPC")
            return 1
        imagen = fetch_from_go_upc(codigo, api_key)
        if imagen and imagen.get("sin_imagen"):
            print(f"AVISO: GO-UPC respondio JSON pero sin imagen. JSON guardado en: {imagen.get('json_path')}")
            print("ERROR: no se encontro imagen en API local ni GO-UPC")
            return 1
        if imagen:
            path = save_image(codigo, imagen["bytes"], imagen["formato"])
            print(f"OK: imagen descargada desde GO-UPC: {path}")
            if imagen.get("json_path"):
                print(f"OK: JSON GO-UPC guardado: {imagen['json_path']}")

            ok_upload, msg_upload = upload_to_local_api(
                codigo,
                imagen["bytes"],
                imagen["formato"],
                api_url,
            )
            if ok_upload:
                print("OK: imagen subida a API local")
            else:
                print(f"AVISO: no se pudo subir imagen a API local: {msg_upload}")
            return 0
    except Exception as e:
        print(f"AVISO: no se pudo descargar desde GO-UPC: {e}")

    print("ERROR: no se encontro imagen en API local ni GO-UPC")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
