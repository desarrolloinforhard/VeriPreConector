import json
import os
import requests

from FUNC.config_json import cargar_config
from core.network.api_client import DispositivoAPIClient
from core.dao.productos_dao import ProductosSQLiteDAO


class DispositivosEnvioService:
    BATCH_SIN_IMAGEN = 1500
    BATCH_CON_IMAGEN = 100
    PUBLICIDAD_TIMEOUT_IMAGEN = (10, 60)
    PUBLICIDAD_TIMEOUT_VIDEO = (10, 900)

    def __init__(self, conexion_dba, batch_size=1000):
        self.conexion_dba = conexion_dba
        self.batch_size = batch_size
        self.productos_sqlite_dao = ProductosSQLiteDAO(conexion_dba)

    def enviar_productos(self, url, datos, modo="completo", estado_callback=None):
        actualizar = estado_callback or (lambda msg: None)
        datos, omitidos = self._filtrar_productos_con_codigo(datos)
        if omitidos:
            actualizar(f"Advertencia: se omitieron {omitidos} productos sin codigo")
        if not datos:
            raise RuntimeError("no hay productos con codigo para enviar")

        precios_adicionales_map = self._cargar_precios_adicionales_map(datos)
        ofertas_map = self._cargar_ofertas_map(datos)
        total_con_packs = sum(1 for precios in precios_adicionales_map.values() if precios)
        total_con_oferta = sum(1 for oferta in ofertas_map.values() if oferta.get("tiene_oferta"))

        client = DispositivoAPIClient(url, estado_callback=actualizar)
        self.enviar_config_imagenes(url, actualizar)
        actualizar(f"Enviando ({modo})...")
        if total_con_packs:
            actualizar(f"Se adjuntaran precios adicionales en {total_con_packs} productos")
        if total_con_oferta:
            actualizar(f"Se adjuntaran ofertas activas en {total_con_oferta} productos")

        if modo == "novedades":
            self._enviar_novedades(client, datos, actualizar, precios_adicionales_map, ofertas_map)
        elif modo == "rango_fecha":
            self._enviar_rango_fecha(client, datos, actualizar, precios_adicionales_map, ofertas_map)
        else:
            self._enviar_completo(client, datos, actualizar, precios_adicionales_map, ofertas_map)

        actualizar("FINAL_OK: Enviado correctamente")

    def enviar_publicidades(self, url, items, estado_callback=None):
        actualizar = estado_callback or (lambda msg: None)

        soporta_multimonitor, monitores_conectados = self._soporta_multimonitor_publicidades(url, actualizar)
        items_preparados = self._preparar_items_publicidad_para_dispositivo(
            items,
            soporta_multimonitor,
            monitores_conectados,
            actualizar,
        )

        self.vaciar_ad_medias(url, actualizar)
        config = cargar_config()
        mantener_audio = bool(config.get("mantener_audio_publicidades", False))

        formatos_imagen = ["jpg", "jpeg", "png", "gif", "webp"]
        formatos_video = ["mp4", "avi", "mov", "mkv", "webm"]

        for item in items_preparados:
            filepath = item["filepath"]
            posicion = item["grid"][0] * 4 + item["grid"][1] + 1
            nombre_base = os.path.splitext(os.path.basename(filepath))[0]
            formato = os.path.splitext(filepath)[1][1:].lower()

            display_index = item.get("display_index")
            grupo = item.get("grupo")
            grupo_id = item.get("grupo_id")

            if soporta_multimonitor and display_index is not None:
                try:
                    display_index = int(display_index)
                except (TypeError, ValueError):
                    display_index = 0

                if display_index < 0:
                    display_index = 0

                if display_index >= monitores_conectados:
                    actualizar(
                        f"Advertencia: {nombre_base} apunta a pantalla {display_index + 1}, "
                        f"pero el dispositivo informa {monitores_conectados}. Se usara pantalla 1."
                    )
                    display_index = 0

                nombre = f"{nombre_base}_d{display_index}"
            else:
                display_index = None
                nombre = nombre_base

            if formato in formatos_imagen:
                path_api = "/api/veri/ad_medias_images"
                timeout = self.PUBLICIDAD_TIMEOUT_IMAGEN
            elif formato in formatos_video:
                path_api = "/api/veri/ad_medias_videos"
                timeout = self.PUBLICIDAD_TIMEOUT_VIDEO
            else:
                actualizar(f"ERROR: Formato no soportado: {formato}")
                continue

            url_post = url.split("/api")[0] + path_api
            json_data = {
                "nro_posicion": posicion,
                "nombre_media": nombre,
                "formato_media": formato,
            }

            if grupo:
                json_data["grupo"] = grupo

            if grupo_id:
                json_data["grupo_id"] = grupo_id

            if display_index is not None:
                json_data["display_index"] = display_index

            if formato in formatos_video and mantener_audio:
                json_data["mantener_audio"] = True

            with open(filepath, "rb") as f:
                files = {
                    "json": (None, json.dumps(json_data), "application/json"),
                    "file": (os.path.basename(filepath), f, "application/octet-stream"),
                }

                if formato in formatos_video:
                    if mantener_audio:
                        actualizar(f"Enviando video {nombre} con audio, puede tardar varios minutos...")
                    else:
                        actualizar(f"Enviando video {nombre}, puede tardar varios minutos...")
                else:
                    actualizar(f"Enviando {nombre}...")

                try:
                    response = requests.post(
                        url_post,
                        files=files,
                        timeout=timeout,
                        headers={"Connection": "close"},
                    )
                except requests.exceptions.Timeout:
                    actualizar(
                        f"FINAL_ERROR: Timeout enviando {nombre}. "
                        f"Tiempo maximo actual video={self.PUBLICIDAD_TIMEOUT_VIDEO[1]}s"
                    )
                    return
                except requests.exceptions.RequestException as e:
                    actualizar(f"FINAL_ERROR: Error enviando {nombre}: {e}")
                    return

                if response.status_code != 200:
                    detalle = response.text[:300] if response.text else ""
                    actualizar(
                        f"FINAL_ERROR: Error HTTP {response.status_code} enviando {nombre}: {detalle}"
                    )
                    return

        self.reiniciar_launcher(url, actualizar)
        actualizar("FINAL_OK: Publicidades enviadas correctamente")

    def _preparar_items_publicidad_para_dispositivo(self, items, soporta_multimonitor, monitores_conectados, actualizar):
        items_base = [dict(item) for item in items]
        hay_pantallas_explicitas = any(item.get("display_index") is not None for item in items_base)

        if soporta_multimonitor:
            if hay_pantallas_explicitas:
                return items_base

            if monitores_conectados >= 2:
                actualizar(
                    f"Sin pantallas configuradas por grupo; se duplicara el grupo activo en {monitores_conectados} pantallas."
                )
                duplicados = []
                for display_index in range(monitores_conectados):
                    for item in items_base:
                        item_copia = dict(item)
                        item_copia["display_index"] = display_index
                        duplicados.append(item_copia)
                return duplicados

            return items_base

        if hay_pantallas_explicitas:
            activos = []
            vistos = set()
            for item in items_base:
                clave = (item.get("grupo_id"), item.get("filepath"))
                if clave in vistos:
                    continue
                vistos.add(clave)
                item_copia = dict(item)
                item_copia.pop("display_index", None)
                activos.append(item_copia)

            grupo_nombre = ", ".join(
                sorted({item.get("grupo", "-") for item in activos if item.get("grupo")})
            ) or "-"
            actualizar(
                f"Dispositivo de una sola pantalla: se unificaran los grupos configurados ({grupo_nombre})."
            )
            return activos

        return items_base


    def enviar_logo_principal(self, url, ruta_imagen_logo, estado_callback=None):
        actualizar = estado_callback or (lambda msg: None)
        self.enviar_config_imagenes(url, actualizar)

        nombre = "!!!LOGO_PRINCIPAL!!!"
        formato = os.path.splitext(ruta_imagen_logo)[1][1:].lower()
        if formato not in ["jpg", "jpeg", "png", "webp"]:
            actualizar(f"FINAL_ERROR: Formato no soportado: {formato}")
            return

        url_post = url.split("/api")[0] + "/api/veri/LOGO_PRINCIPAL"
        json_data = {
            "nro_posicion": 0,
            "nombre_media": nombre,
            "formato_media": formato,
        }

        with open(ruta_imagen_logo, "rb") as f:
            files = {
                "json": (None, json.dumps(json_data), "application/json"),
                "file": (os.path.basename(ruta_imagen_logo), f, "application/octet-stream"),
            }
            actualizar("Enviando logo...")
            response = requests.post(url_post, files=files, timeout=60)
            if response.status_code == 200:
                actualizar("Logo enviado correctamente")
            else:
                actualizar(f"FINAL_ERROR: Error HTTP: {response.status_code}")
                return

        self.reiniciar_launcher(url, actualizar)
        actualizar("FINAL_OK: Logo enviado correctamente")

    def vaciar_ad_medias(self, url, estado_callback=None):
        actualizar = estado_callback or (lambda msg: None)
        try:
            url_delete = url.split("/api")[0] + "/api/veri/vaciar_ad_medias"
            respuesta = requests.delete(url_delete, timeout=30)
            if respuesta.status_code == 200:
                actualizar("Carpeta y base de datos ad_medias vaciadas")
            else:
                actualizar(f"Advertencia: No se pudo vaciar ad_medias: {respuesta.status_code}")
        except Exception as e:
            actualizar(f"ERROR: Error al vaciar ad_medias: {e}")

    def reiniciar_launcher(self, url, estado_callback=None):
        actualizar = estado_callback or (lambda msg: None)
        try:
            requests.post(url.split("/api")[0] + "/api/veri/reiniciar_launcher", timeout=10)
            actualizar("Launcher reiniciado")
        except Exception:
            actualizar("Advertencia: No se pudo reiniciar launcher")

    def obtener_go_upc_key_guardada(self):
        try:
            rows = self.conexion_dba.ejecutar_consulta("SELECT api_key FROM api_key LIMIT 1")
            if rows and rows[0] and rows[0][0]:
                return str(rows[0][0]).strip()
            return None
        except Exception as e:
            print(f"[GO-UPC] Error leyendo api_key local: {e}")
            return None

    def obtener_api_imagenes_url_guardada(self):
        try:
            config = cargar_config()
            url = config.get("api_imagenes_url") or config.get("imagenes_api_url")
            return str(url).strip() if url else None
        except Exception as e:
            print(f"[imagenes] Error leyendo api_imagenes_url: {e}")
            return None

    def enviar_config_imagenes(self, base_url, estado_callback=None):
        actualizar = estado_callback or (lambda msg: None)
        api_key = self.obtener_go_upc_key_guardada()
        api_imagenes_url = self.obtener_api_imagenes_url_guardada()

        if api_key:
            ok_key, msg_key = self.enviar_go_upc_key(base_url, api_key)
            if ok_key:
                actualizar(msg_key)
            else:
                actualizar(f"Advertencia: No se pudo enviar API KEY GO-UPC: {msg_key}")
        else:
            actualizar("Advertencia: No hay API KEY GO-UPC guardada para enviar")

        if api_imagenes_url:
            ok_url, msg_url = self.enviar_api_imagenes_url(base_url, api_imagenes_url)
            if ok_url:
                actualizar(msg_url)
            else:
                actualizar(f"Advertencia: No se pudo enviar API imagenes: {msg_url}")
        else:
            actualizar("API propia de imagenes no configurada")

    def enviar_go_upc_key(self, base_url, api_key):
        try:
            if not api_key:
                return False, "API KEY vacia"

            host = base_url.split("/api")[0]
            response = requests.post(
                host + "/api/veri/GO_UPC_KEY",
                json={"api_key": api_key},
                timeout=5,
            )
            if response.status_code == 200:
                return True, "API KEY enviada"
            return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, f"Error: {e}"

    def enviar_api_imagenes_url(self, base_url, api_imagenes_url):
        try:
            if not api_imagenes_url:
                return False, "URL vacia"

            host = base_url.split("/api")[0]
            response = requests.post(
                host + "/api/veri/IMAGES_API_URL",
                json={"url": api_imagenes_url},
                timeout=5,
            )
            if response.status_code == 200:
                return True, "URL API imagenes enviada"
            if response.status_code == 404:
                return False, "endpoint no disponible en este APK"
            return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, f"Error: {e}"

    def _enviar_novedades(self, client, datos, actualizar, precios_adicionales_map=None, ofertas_map=None):
        for art in datos:
            try:
                actualizar(f"Enviando: {art[0]} - {art[1]}")
                response = client.enviar_post_json([self._producto_payload(art, precios_adicionales_map, ofertas_map)])
                if response is None:
                    raise RuntimeError("sin respuesta OK del dispositivo")
                self._informar_resumen_productos(client, response, actualizar)
            except Exception as e:
                raise RuntimeError(f"Error con {art[0]} - {art[1]}: {e}") from e

    def _enviar_rango_fecha(self, client, datos, actualizar, precios_adicionales_map=None, ofertas_map=None):
        for i in range(0, len(datos), self.batch_size):
            batch = datos[i:i + self.batch_size]
            if batch:
                actualizar(f"Enviando producto de fecha: {batch[0][0]} - {batch[0][1]}")
            response = client.enviar_post_json(
                [self._producto_payload(art, precios_adicionales_map, ofertas_map) for art in batch]
            )
            if response is None:
                raise RuntimeError("sin respuesta OK del dispositivo")
            self._informar_resumen_productos(client, response, actualizar)
        actualizar("Rango de fecha enviado correctamente")

    def _enviar_completo(self, client, datos, actualizar, precios_adicionales_map=None, ofertas_map=None):
        response = client.enviar_delete()
        if response is None:
            raise RuntimeError("no se pudo limpiar productos en el dispositivo")

        productos_sin_imagen, productos_con_imagen = self._separar_por_imagen(datos)
        total = len(datos)
        enviados = 0

        actualizar(
            "Catalogo preparado: "
            f"{len(productos_sin_imagen)} sin imagen, {len(productos_con_imagen)} con imagen"
        )

        enviados = self._enviar_batches(
            client,
            productos_sin_imagen,
            self.BATCH_SIN_IMAGEN,
            enviados,
            total,
            "sin imagen",
            actualizar,
            precios_adicionales_map,
        )
        enviados = self._enviar_batches(
            client,
            productos_con_imagen,
            self.BATCH_CON_IMAGEN,
            enviados,
            total,
            "con imagen",
            actualizar,
            precios_adicionales_map,
        )
        self._informar_status_dispositivo(client, esperado_productos=enviados, actualizar=actualizar)

    def _separar_por_imagen(self, datos):
        productos_sin_imagen = []
        productos_con_imagen = []
        for producto in datos:
            if self._tiene_imagen(producto):
                productos_con_imagen.append(producto)
            else:
                productos_sin_imagen.append(producto)
        return productos_sin_imagen, productos_con_imagen

    def _tiene_imagen(self, producto):
        return len(producto) > 3 and bool(producto[3])

    def _enviar_batches(
        self,
        client,
        productos,
        batch_size,
        enviados,
        total,
        etiqueta,
        actualizar,
        precios_adicionales_map=None,
    ):
        if not productos:
            return enviados

        total_lotes = (len(productos) + batch_size - 1) // batch_size
        for numero_lote, inicio in enumerate(range(0, len(productos), batch_size), start=1):
            batch = productos[inicio:inicio + batch_size]
            actualizar(
                f"Enviando lote {numero_lote}/{total_lotes} {etiqueta} "
                f"({enviados + len(batch)}/{total})"
            )
            timeout = 120 if etiqueta == "con imagen" else 60
            response = client.enviar_post_json(
                [self._producto_payload(art, precios_adicionales_map, ofertas_map) for art in batch],
                timeout=timeout,
            )
            if response is None:
                raise RuntimeError(f"sin respuesta OK del dispositivo enviando lote {etiqueta}")
            self._informar_resumen_productos(client, response, actualizar)
            enviados += len(batch)

        return enviados

    def _informar_resumen_productos(self, client, response, actualizar):
        data = client.obtener_json_respuesta(response)
        if not data:
            return

        if data.get("ok") is False:
            mensaje = data.get("mensaje") or "respuesta marcada como error por el dispositivo"
            errores = data.get("errores") or []
            if errores:
                mensaje = f"{mensaje}. Errores: {self._resumen_errores(errores)}"
            raise RuntimeError(mensaje)

        partes = []
        for clave, etiqueta in (
            ("recibidos", "recibidos"),
            ("insertados", "insertados"),
            ("actualizados", "actualizados"),
        ):
            if clave in data:
                partes.append(f"{data[clave]} {etiqueta}")

        errores = data.get("errores") or []
        if errores:
            partes.append(f"{len(errores)} errores")

        if partes:
            actualizar("Resumen Android: " + ", ".join(partes))
        if errores:
            actualizar(f"Advertencia Android: {self._resumen_errores(errores)}")

    def _informar_status_dispositivo(self, client, esperado_productos, actualizar):
        status = client.get_status_dispositivo()
        if not status:
            actualizar("Status Android no disponible; se continua con compatibilidad anterior")
            return

        productos_android = status.get("productos")
        publicidades = status.get("publicidades")
        logo = status.get("logo_principal")
        api_key = status.get("go_upc_key")
        actualizar(
            "Status Android: "
            f"productos={productos_android}, publicidades={publicidades}, "
            f"logo={logo}, go_upc_key={api_key}"
        )

        try:
            productos_android_int = int(productos_android) if productos_android is not None else None
        except (TypeError, ValueError):
            productos_android_int = None

        if productos_android_int is not None and productos_android_int != int(esperado_productos):
            actualizar(
                "Advertencia: Android informa "
                f"{productos_android} productos, se esperaban {esperado_productos}"
            )

    def _resumen_errores(self, errores, limite=3):
        textos = [str(error) for error in errores[:limite]]
        if len(errores) > limite:
            textos.append(f"... +{len(errores) - limite} mas")
        return " | ".join(textos)

    def _filtrar_productos_con_codigo(self, datos):
        validos = []
        omitidos = 0

        for producto in datos:
            if not producto:
                omitidos += 1
                continue
            codigo = str(producto[0]).strip() if producto[0] is not None else ""
            if not codigo:
                omitidos += 1
                continue
            validos.append(producto)

        return validos, omitidos

    def _cargar_precios_adicionales_map(self, datos):
        codigos = [str(producto[0]).strip() for producto in datos if producto and producto[0] is not None]
        filas = self.productos_sqlite_dao.listar_precios_adicionales_por_codigos(codigos)
        precios_map = {}

        for fila in filas:
            codigo, tipo_precio, categoria, origen, orden, cantidad, titulo, detalle, precio, nroprecio, dfechau = fila
            precios_map.setdefault(str(codigo).strip(), []).append(
                {
                    "tipo_precio": tipo_precio,
                    "categoria": categoria,
                    "origen": origen,
                    "orden": orden,
                    "cantidad": cantidad,
                    "titulo": titulo,
                    "detalle": detalle,
                    "precio": format(round(float(precio or 0), 2), ".2f"),
                    "nroprecio": nroprecio,
                    "dfechau": dfechau,
                }
            )

        return precios_map

    def _cargar_ofertas_map(self, datos):
        codigos = [str(producto[0]).strip() for producto in datos if producto and producto[0] is not None]
        ofertas_map = {}

        for codigo in codigos:
            fila = self.productos_sqlite_dao.obtener_oferta_por_codigo(codigo)
            if not fila:
                continue

            _, tiene_oferta, precio_oferta, oferta_desde, oferta_hasta, oferta_origen, oferta_ccoddiv, oferta_dto = fila
            ofertas_map[codigo] = {
                "tiene_oferta": bool(tiene_oferta),
                "precio_oferta": format(round(float(precio_oferta or 0), 2), ".2f") if tiene_oferta and precio_oferta is not None else None,
                "oferta_desde": oferta_desde,
                "oferta_hasta": oferta_hasta,
                "oferta_origen": oferta_origen,
                "oferta_ccoddiv": oferta_ccoddiv,
                "oferta_dto": format(round(float(oferta_dto or 0), 2), ".2f") if tiene_oferta and oferta_dto is not None else None,
            }

        return ofertas_map

    def _producto_payload(self, art, precios_adicionales_map=None, ofertas_map=None):
        codigo = str(art[0]).strip() if art[0] is not None else ""
        payload = {
            "codigo": codigo,
            "descripcion": art[1],
            "precio": art[2],
            "img_base64": art[3],
            "formato_imagen": art[4],
        }
        precios_adicionales = (precios_adicionales_map or {}).get(codigo) or []
        if precios_adicionales:
            payload["precios_adicionales"] = precios_adicionales
        oferta = (ofertas_map or {}).get(codigo) or {}
        if oferta.get("tiene_oferta"):
            payload["tiene_oferta"] = True
            payload["precio_oferta"] = oferta.get("precio_oferta")
            payload["oferta_desde"] = oferta.get("oferta_desde")
            payload["oferta_hasta"] = oferta.get("oferta_hasta")
            payload["oferta_origen"] = oferta.get("oferta_origen")
            payload["oferta_ccoddiv"] = oferta.get("oferta_ccoddiv")
            payload["oferta_dto"] = oferta.get("oferta_dto")
        return payload

    def _soporta_multimonitor_publicidades(self, url, actualizar):
        try:
            client = DispositivoAPIClient(url, estado_callback=actualizar)
            config_player = client.get_player_configuration(timeout=4)

            if not config_player:
                actualizar("Player multi-monitor no disponible; envio legacy a una pantalla")
                return False, 1

            monitores = config_player.get("monitores_conectados")
            if monitores is None:
                pantallas = config_player.get("pantallas_detectadas", [])
                monitores = len(pantallas) if isinstance(pantallas, list) else 1

            try:
                monitores = int(monitores)
            except (TypeError, ValueError):
                monitores = 1

            if monitores >= 2:
                actualizar(f"Player multi-monitor detectado: {monitores} pantallas")
                return True, monitores

            actualizar("Player detectado con una sola pantalla; envio normal")
            return False, monitores

        except Exception as e:
            actualizar(f"Player multi-monitor no disponible; envio legacy: {e}")
            return False, 1
