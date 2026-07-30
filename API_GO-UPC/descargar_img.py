import os
import re
import sys
import requests


def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip()


def fetch_product_json(base_url: str, api_key: str, code: str) -> dict:
    url = f"{base_url.rstrip('/')}/code/{code}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()


def download_image(img_url: str, out_path: str) -> None:
    r = requests.get(img_url, stream=True, timeout=30)
    r.raise_for_status()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(1024 * 64):
            if chunk:
                f.write(chunk)


def main():
    BASE_URL = "https://go-upc.com/api/v1"
    API_KEY = os.getenv("GO_UPC_API_KEY", "TU_API_KEY")

    if len(sys.argv) < 2:
        print("❌ Debés pasar el código (EAN/UPC)")
        print("Ejemplo: python descargar_img.py 7790990003039")
        sys.exit(1)

    CODE = sys.argv[1]

    # Nombre opcional
    custom_name = sys.argv[2] if len(sys.argv) > 2 else None

    if API_KEY == "TU_API_KEY":
        print("❌ Falta API KEY (GO_UPC_API_KEY)")
        sys.exit(1)

    try:
        data = fetch_product_json(BASE_URL, API_KEY, CODE)
        img_url = data.get("product", {}).get("imageUrl")

        if not img_url:
            print("❌ No se encontró imageUrl en la respuesta")
            sys.exit(2)

        # Extensión desde la URL
        ext = os.path.splitext(img_url.split("?")[0])[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"

        # 👉 nombre por defecto = código
        if custom_name:
            name = safe_filename(custom_name)
            filename = name if name.lower().endswith(ext) else name + ext
        else:
            filename = f"{safe_filename(CODE)}{ext}"

        out_path = os.path.join("imagenes", filename)

        download_image(img_url, out_path)

        print("✅ Imagen descargada correctamente")
        print("   Código :", CODE)
        print("   Archivo:", out_path)

    except Exception as e:
        print("❌ Error:", e)


if __name__ == "__main__":
    main()
