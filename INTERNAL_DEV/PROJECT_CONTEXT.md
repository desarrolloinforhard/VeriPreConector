# Project Context

Version actual: `1.16.5`

## 1. Objetivo del sistema

`VeriPre_Connector` es una aplicacion de escritorio Python con Tkinter y ttkbootstrap que:
- administra productos locales en SQLite,
- sincroniza productos desde Sybase por ODBC,
- envia catalogo y novedades a verificadores Android via HTTP,
- administra publicidades multimedia y logo principal,
- distribuye configuracion de imagenes y GO-UPC a dispositivos,
- puede correr con GUI o en modo headless por parametros.

## 2. Entry point y modos de ejecucion

Archivo principal: `main.py`

Modos:
- GUI normal: instancia `GUI_MAIN`.
- `--transmitir-completo`: envio completo sin abrir GUI.
- `--transmitir-novedades`: sincroniza/envia novedades sin abrir GUI.
- `--sin-ventana-progreso`: modo headless solo consola.

## 3. Mapa de carpetas actual

- `GUI/`
  - `GUI_MAIN.py`: ventana principal, menu, secciones, tray, bootstrap general.
  - `CONTENIDO_PRODUCTO.py`: tabla/busqueda de productos, detalle, novedades y envio.
  - `CONTENIDO_PUBLICIDAD.py`: grupos, globales, grid multimedia, preview, envio, biblioteca.
  - `GUI_CONFIG.py`: configuracion Sybase/SQLite/dispositivos/GO-UPC y toggles funcionales.
- `DB/`
  - `database.py`: wrapper SQLite.
  - `database_sybase.py`: acceso Sybase.
- `FUNC/`
  - `config_json.py`: config persistente del programa.
  - `ctk_components/ctk_components.py`: componentes CustomTk, loader.
  - `create_widget.py`: `WidgetRegistry`.
- `core/network/`
  - `api_client.py`: cliente HTTP hacia Android.
  - `dispositivo_sender.py`: selector de dispositivos y ventana de estado por dispositivo.
  - `urls_dispositivos.py`: rutas base hacia endpoints del verificador.
- `core/services/`
  - `dispositivos_envio_service.py`: logica de envio de productos/publicidades/logo/config.
  - `headless_envio_service.py`: modo CLI sin GUI.
  - `headless_progress_window.py`: ventana de progreso en modo headless.
  - `image_resolver.py`: resolucion/caching de imagenes del lado Python.
  - `productos_sync_service.py`: sync de productos y deteccion de cambios.
  - `ofertas_service.py`: soporte a generacion de ofertas.
- `tools/`
  - utilidades auxiliares como `fetch_product_image.py`.
- `versionado/`
  - version actual e historial corto de cambios.

## 4. Flujo real de datos

### Productos
1. `GUI_MAIN` inicializa DB SQLite y conexion Sybase.
2. `CONTENIDO_PRODUCTO` consulta SQLite para mostrar busqueda/lista.
3. `productos_sync_service.py` sincroniza desde Sybase hacia SQLite.
4. `dispositivos_envio_service.py` envia productos al Android por lotes.
5. Antes de enviar, tambien puede empujar GO-UPC key y URL de API propia de imagenes.

### Publicidades
1. `CONTENIDO_PUBLICIDAD` mantiene grupos y globales en config.
2. Desde `1.16.5` las publicidades se copian a storage interno administrado por SmartPrice.
3. El envio usa `dispositivo_sender.py` -> `dispositivos_envio_service.py`.
4. Android recibe imagenes/videos en endpoints separados.
5. Se reinicia launcher al finalizar.

### Configuracion
1. `GUI_CONFIG.py` edita DSN, API key, toggles y opciones de envio.
2. `FUNC/config_json.py` guarda configuracion persistente.
3. En modo compilado, la config se mueve a `C:\ProgramData\SmartPrice\config.json`.

## 5. Contratos vigentes con Android

Mantener compatibilidad con:
- `POST /api/veri/batch_productos`
- `DELETE /api/veri/batch_productos`
- `GET /api/veri/status`
- `DELETE /api/veri/vaciar_ad_medias`
- `POST /api/veri/ad_medias_images`
- `POST /api/veri/ad_medias_videos`
- `POST /api/veri/LOGO_PRINCIPAL`
- `POST /api/veri/GO_UPC_KEY`
- `GET /api/veri/GO_UPC_KEY`
- `POST /api/veri/reiniciar_launcher`
- `POST /api/veri/IMAGES_API_URL` (nuevo contrato para URL de API propia de imagenes)

## 6. Riesgos tecnicos actuales

- Alto acoplamiento entre GUI, servicios y `WidgetRegistry`.
- Persistencia de configuracion todavia muy transversal al codigo.
- Todavia hay zonas con Tkinter + threads que requieren cuidado.
- SQLite usa `check_same_thread=False`; no asumir seguridad total por eso.
- `CONTENIDO_PRODUCTO.py` y `CONTENIDO_PUBLICIDAD.py` siguen siendo modulos grandes.
- Envio incremental real de publicidades aun depende de cambios en Android.

## 7. Decisiones vigentes que no deben romperse

- Python ya no busca imagenes remotas para preview de productos; eso queda del lado Android al escanear.
- Publicidades se guardan en storage interno para no depender de rutas del usuario.
- Config compilada debe quedar fuera de `Program Files` para evitar perdida de datos entre usuarios.
- La app debe poder correr con GUI o headless sin duplicar logica de negocio.
