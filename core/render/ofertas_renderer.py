import os
import re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont


class OfertasRenderer:
    """
    Genera imágenes PNG para mostrar ofertas.
    MVP: plantilla CARD_1.
    """

    def __init__(self, output_dir="OUTPUT/ofertas"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Tipografías (fallback seguro)
        self.font_title = self._load_font(24, bold=True)
        self.font_desc = self._load_font(22, bold=False)
        self.font_price_big = self._load_font(44, bold=True)
        self.font_price_small = self._load_font(22, bold=False)

    def _load_font(self, size: int, bold: bool = False):
        # Windows: Segoe UI / Arial; si no está, PIL default
        candidates = []
        if bold:
            candidates += ["segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf"]
        else:
            candidates += ["segoeui.ttf", "arial.ttf", "Arial.ttf"]

        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def render(self, oferta: dict, items: list, template="CARD_1", items_por_imagen=1):
        template = (template or "CARD_1").upper()
        items_por_imagen = max(1, int(items_por_imagen or 1))

        if template != "CARD_1":
            raise ValueError(f"Template no soportado aún: {template}")

        # agrupar items
        chunks = [items[i:i + items_por_imagen] for i in range(0, len(items), items_por_imagen)]

        out_paths = []
        for idx, chunk in enumerate(chunks, start=1):
            img = self._render_card_1(oferta, chunk)
            fname = self._build_filename(oferta, idx)
            path = os.path.join(self.output_dir, fname)
            img.save(path, "PNG")
            out_paths.append(path)

        return out_paths

    def _build_filename(self, oferta: dict, idx: int):
        noferta = oferta.get("noferta")
        tipo = (oferta.get("tipo") or "OF").strip()
        titulo = (oferta.get("titulo") or "").strip()
        safe = re.sub(r"[^a-zA-Z0-9\-_ ]+", "", titulo)[:40].strip().replace(" ", "_")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"OF_{tipo}_{noferta}_{safe}_{ts}_{idx:02d}.png"

    def _money(self, v):
        try:
            if v is None:
                return ""
            return f"${float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return str(v)

    def _render_card_1(self, oferta: dict, chunk: list):
        # tamaño “card” pensado para tus slots (ajustable)
        W, H = 800, 450
        img = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(img)

        # Header
        tipo = (oferta.get("tipo") or "").strip()
        titulo = (oferta.get("titulo") or "").strip()
        noferta = oferta.get("noferta")

        header = f"{tipo} #{noferta}"
        draw.text((20, 15), header, font=self.font_title, fill="black")
        draw.text((20, 55), titulo[:50], font=self.font_desc, fill="black")

        # Producto principal (si items_por_imagen=1, es el único)
        y = 120
        for it in chunk:
            desc = (it.get("descripcion") or "").strip()
            cref = (it.get("cref") or "").strip()
            p_lista = it.get("precio_lista")
            p_oferta = it.get("precio_oferta")

            # Descripción
            draw.text((20, y), f"{desc[:48]}", font=self.font_desc, fill="black")
            draw.text((20, y + 35), f"CREF: {cref}", font=self.font_price_small, fill="black")

            # Precios
            y_prices = y + 90
            if p_oferta is not None:
                draw.text((20, y_prices), f"OFERTA {self._money(p_oferta)}", font=self.font_price_big, fill="black")
                if p_lista is not None and float(p_lista or 0) > 0:
                    draw.text((20, y_prices + 55), f"Lista {self._money(p_lista)}", font=self.font_price_small, fill="black")
            else:
                # si no hay precio oferta (canasta/mix), mostramos lista
                draw.text((20, y_prices), f"{self._money(p_lista)}", font=self.font_price_big, fill="black")

            # separador si hay más de uno por imagen
            y += 200

        # Footer
        draw.text((20, H - 35), "Generado por VeriPre - Ofertas", font=self.font_price_small, fill="gray")
        return img