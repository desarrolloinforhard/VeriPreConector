import os
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import StringVar, IntVar, messagebox

from core.services.ofertas_service import OfertasService
from core.dao.ofertas_dao import OfertasDAO
from core.render.ofertas_renderer import OfertasRenderer
from core.logging.logger import get_logger
from core.ui.responsive import fit_toplevel_to_workarea

logger = get_logger(__name__)


class GeneradorOfertasToplevel(ttk.Toplevel):
    """
    Toplevel para:
      1) listar ofertas vigentes (OFERTAT)
      2) seleccionar oferta
      3) traer productos según tipo (OFPLU / OFCANASTA)
      4) generar PNGs (plantillas)
      5) devolver lista de paths PNG a un callback (para cargar al grid)
    """

    def __init__(
        self,
        master,
        sybase_conn,
        on_imagenes_generadas=None,
        output_dir="OUTPUT/ofertas",
    ):
        logger.info(
            "Inicializando GeneradorOfertasToplevel | output_dir=%s | tiene_callback=%s",
            output_dir,
            callable(on_imagenes_generadas)
        )

        super().__init__(master)

        self.title("Generador de Publicidad desde Ofertas")
        fit_toplevel_to_workarea(self, 1250, 720, min_width=980, min_height=620)
        self.place_window_center()
        self.grab_set()
        self.focus_force()

        self.sybase_conn = sybase_conn
        self.on_imagenes_generadas = on_imagenes_generadas

        # Backend
        logger.debug("Inicializando backend de ofertas.")
        self.dao = OfertasDAO(self.sybase_conn)
        self.service = OfertasService(self.dao)
        self.renderer = OfertasRenderer(output_dir=output_dir)

        # Estado
        self._ofertas = []
        self._oferta_actual = None
        self._items_actuales = []
        self._imagenes_generadas = []

        # Vars UI
        self.var_tipo = StringVar(value="TODAS")
        self.var_buscar = StringVar(value="")
        self.var_plantilla = StringVar(value="CARD_1")
        self.var_items_por_imagen = IntVar(value=1)

        self._build_ui()

        logger.info("GeneradorOfertasToplevel inicializado correctamente.")

    # ---------------- UI ----------------
    def _build_ui(self):
        logger.debug("Construyendo UI de GeneradorOfertasToplevel.")

        # Top bar
        bar = ttk.Frame(self, padding=10)
        bar.pack(fill="x")

        ttk.Button(bar, text="🔄 Cargar ofertas", command=self.cargar_ofertas).pack(side="left")

        ttk.Label(bar, text="Tipo:").pack(side="left", padx=(15, 5))
        ttk.Combobox(
            bar,
            textvariable=self.var_tipo,
            values=["TODAS", "OFPLU", "OFCANASTA"],
            width=12,
            state="readonly",
        ).pack(side="left")

        ttk.Label(bar, text="Buscar:").pack(side="left", padx=(15, 5))
        ent = ttk.Entry(bar, textvariable=self.var_buscar, width=35)
        ent.pack(side="left")
        ent.bind("<KeyRelease>", lambda _e: self._refrescar_tabla_ofertas())

        ttk.Label(bar, text="Plantilla:").pack(side="left", padx=(15, 5))
        ttk.Combobox(
            bar,
            textvariable=self.var_plantilla,
            values=["CARD_1"],
            width=10,
            state="readonly",
        ).pack(side="left")

        ttk.Label(bar, text="Prod/imagen:").pack(side="left", padx=(15, 5))
        ttk.Spinbox(bar, from_=1, to=20, textvariable=self.var_items_por_imagen, width=6).pack(side="left")

        ttk.Button(bar, text="🧩 Generar imágenes", command=self.generar_imagenes).pack(side="right")
        ttk.Button(bar, text="➕ Cargar al grid", command=self.cargar_al_grid).pack(side="right", padx=(0, 10))

        # Split
        pane = ttk.PanedWindow(self, orient=HORIZONTAL)
        pane.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        lf_left = ttk.Labelframe(pane, text="Ofertas", padding=8)
        lf_right = ttk.Labelframe(pane, text="Productos de la oferta", padding=8)
        pane.add(lf_left, weight=1)
        pane.add(lf_right, weight=2)

        # Tabla ofertas
        self.tv_ofertas = ttk.Treeview(
            lf_left,
            columns=("noferta", "tipo", "titulo", "desde", "hasta"),
            show="headings",
            height=18
        )
        cols = [
            ("noferta", "N°", 70),
            ("tipo", "Tipo", 110),
            ("titulo", "Título", 360),
            ("desde", "Desde", 150),
            ("hasta", "Hasta", 150),
        ]
        for c, t, w in cols:
            self.tv_ofertas.heading(c, text=t)
            self.tv_ofertas.column(c, width=w, anchor="w")
        self.tv_ofertas.pack(fill="both", expand=True)
        self.tv_ofertas.bind("<<TreeviewSelect>>", self._on_select_oferta)

        # Tabla productos
        self.tv_prod = ttk.Treeview(
            lf_right,
            columns=("cref", "desc", "pvp1", "poferta"),
            show="headings",
            height=18
        )
        cols2 = [
            ("cref", "CREF", 140),
            ("desc", "Descripción", 560),
            ("pvp1", "Lista", 120),
            ("poferta", "Oferta", 120),
        ]
        for c, t, w in cols2:
            self.tv_prod.heading(c, text=t)
            self.tv_prod.column(c, width=w, anchor="w")
        self.tv_prod.pack(fill="both", expand=True)

        # Bottom status
        bottom = ttk.Frame(self, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")
        self.lbl_estado = ttk.Label(bottom, text="Listo.", anchor="w")
        self.lbl_estado.pack(fill="x")

        logger.debug("UI de GeneradorOfertasToplevel construida correctamente.")

    # ---------------- Actions ----------------
    def cargar_ofertas(self):
        logger.info("Solicitando carga de ofertas.")

        try:
            self._ofertas = self.service.listar_ofertas()
            logger.info("Ofertas cargadas correctamente | cantidad=%s", len(self._ofertas))

            self._refrescar_tabla_ofertas()
            self._set_estado(f"✅ Ofertas cargadas: {len(self._ofertas)}")

        except Exception as e:
            logger.exception("Error al cargar ofertas.")
            self._set_estado(f"❌ Error cargando ofertas: {e}")
            messagebox.showerror("Error", f"No se pudieron cargar ofertas.\n\n{e}")

    def _refrescar_tabla_ofertas(self):
        try:
            tipo = (self.var_tipo.get() or "TODAS").strip().upper()
            buscar = (self.var_buscar.get() or "").strip().lower()

            logger.debug(
                "Refrescando tabla de ofertas | filtro_tipo=%s | buscar=%s | total_ofertas=%s",
                tipo, buscar, len(self._ofertas)
            )

            self.tv_ofertas.delete(*self.tv_ofertas.get_children())

            def match(o):
                if tipo != "TODAS" and o["tipo"].upper() != tipo:
                    return False
                if buscar:
                    hay = (o.get("titulo") or "").lower()
                    if buscar not in hay:
                        return False
                return True

            count = 0
            for o in self._ofertas:
                if not match(o):
                    continue
                self.tv_ofertas.insert("", "end", values=(
                    o["noferta"], o["tipo"], o["titulo"], o["desde"], o["hasta"]
                ))
                count += 1

            logger.debug("Tabla de ofertas refrescada | visibles=%s | total=%s", count, len(self._ofertas))
            self._set_estado(f"Mostrando ofertas: {count} / {len(self._ofertas)}")

        except Exception:
            logger.exception("Error al refrescar tabla de ofertas.")
            self._set_estado("❌ Error refrescando tabla de ofertas.")

    def _on_select_oferta(self, _evt=None):
        try:
            sel = self.tv_ofertas.selection()
            if not sel:
                logger.debug("Selección de oferta vacía.")
                return

            noferta, tipo, titulo, desde, hasta = self.tv_ofertas.item(sel[0], "values")
            self._oferta_actual = {
                "noferta": int(noferta),
                "tipo": str(tipo).strip(),
                "titulo": str(titulo).strip(),
                "desde": desde,
                "hasta": hasta,
            }

            logger.info(
                "Oferta seleccionada | noferta=%s | tipo=%s | titulo=%s | desde=%s | hasta=%s",
                self._oferta_actual["noferta"],
                self._oferta_actual["tipo"],
                self._oferta_actual["titulo"],
                self._oferta_actual["desde"],
                self._oferta_actual["hasta"],
            )

            res = self.service.traer_productos(self._oferta_actual)
            self._items_actuales = res.get("items", [])
            modo = res.get("modo", "?")

            logger.info(
                "Productos resueltos para oferta | noferta=%s | cantidad=%s | modo=%s",
                self._oferta_actual["noferta"],
                len(self._items_actuales),
                modo
            )

            self._cargar_tabla_productos(self._items_actuales)
            self._set_estado(
                f"✅ Oferta {noferta} ({tipo}) → {len(self._items_actuales)} productos | modo={modo}"
            )

        except Exception as e:
            logger.exception("Error al seleccionar oferta.")
            self._items_actuales = []
            self._cargar_tabla_productos([])
            self._set_estado(f"❌ Error trayendo productos: {e}")
            messagebox.showerror("Error", f"No se pudieron traer productos.\n\n{e}")

    def _cargar_tabla_productos(self, items):
        try:
            logger.debug("Cargando tabla de productos | cantidad=%s", len(items))

            self.tv_prod.delete(*self.tv_prod.get_children())
            for it in items:
                self.tv_prod.insert("", "end", values=(
                    it.get("cref"),
                    it.get("descripcion"),
                    it.get("precio_lista"),
                    it.get("precio_oferta"),
                ))

            logger.debug("Tabla de productos cargada correctamente.")

        except Exception:
            logger.exception("Error al cargar tabla de productos.")
            self._set_estado("❌ Error cargando tabla de productos.")

    def generar_imagenes(self):
        try:
            if not self._oferta_actual:
                logger.warning("Se intentó generar imágenes sin oferta seleccionada.")
                messagebox.showwarning("Atención", "Seleccioná una oferta primero.")
                return

            if not self._items_actuales:
                logger.warning(
                    "Se intentó generar imágenes sin productos | noferta=%s",
                    self._oferta_actual.get("noferta") if self._oferta_actual else None
                )
                messagebox.showwarning("Atención", "La oferta seleccionada no tiene productos.")
                return

            plantilla = self.var_plantilla.get()
            items_por_img = min(1, int(self.var_items_por_imagen.get() or 1))

            logger.info(
                "Generando imágenes de oferta | noferta=%s | plantilla=%s | items=%s | items_por_imagen=%s",
                self._oferta_actual.get("noferta"),
                plantilla,
                len(self._items_actuales),
                items_por_img
            )

            self._imagenes_generadas = self.renderer.render(
                oferta=self._oferta_actual,
                items=self._items_actuales,
                template=plantilla,
                items_por_imagen=items_por_img,
            )

            logger.info("Imágenes generadas correctamente | cantidad=%s", len(self._imagenes_generadas))

            self._set_estado(f"✅ Imágenes generadas: {len(self._imagenes_generadas)}")
            if self._imagenes_generadas:
                messagebox.showinfo("OK", f"Se generaron {len(self._imagenes_generadas)} imágenes.")

        except Exception as e:
            logger.exception("Error al generar imágenes.")
            self._imagenes_generadas = []
            self._set_estado(f"❌ Error generando imágenes: {e}")
            messagebox.showerror("Error", f"No se pudieron generar imágenes.\n\n{e}")

    def cargar_al_grid(self):
        try:
            if not self._imagenes_generadas:
                logger.warning("Se intentó cargar al grid sin imágenes generadas.")
                messagebox.showwarning("Atención", "Primero generá imágenes.")
                return

            logger.info("Cargando imágenes al grid | cantidad=%s", len(self._imagenes_generadas))

            if callable(self.on_imagenes_generadas):
                self.on_imagenes_generadas(self._imagenes_generadas)
                logger.info("Imágenes enviadas al callback del grid correctamente.")
                self._set_estado(f"✅ Enviadas al grid: {len(self._imagenes_generadas)}")
            else:
                logger.warning("No hay callback configurado para cargar imágenes al grid.")
                messagebox.showinfo("Info", "No hay callback configurado para cargar al grid.")

        except Exception:
            logger.exception("Error al cargar imágenes al grid.")
            self._set_estado("❌ Error cargando imágenes al grid.")

    def _set_estado(self, msg: str):
        try:
            logger.debug("Estado UI GeneradorOfertas: %s", msg)
            self.lbl_estado.config(text=msg)
        except Exception:
            logger.exception("Error al actualizar label de estado en GeneradorOfertasToplevel.")
