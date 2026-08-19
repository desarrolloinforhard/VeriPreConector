# Project Context

Version actual: `1.16.32`

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
  - `GUI_CONFIG.py`: configuracion Sybase/SQLite/dispositivos/GO-UPC, toggles funcionales y permisos por usuario Windows.
- `DB/`
- `database.py`: wrapper SQLite; desde `1.16.32` usa lock interno por proceso, `busy_timeout` y WAL para reducir `database is locked` en `F:\Dba\veripre.db`.
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
  - `device_discovery_service.py`: descubrimiento de verificadores e InforTV en red local con cache corta.
  - `dispositivos_envio_service.py`: logica de envio de productos/publicidades/logo/config.
  - `headless_envio_service.py`: modo CLI sin GUI.
  - `headless_progress_window.py`: ventana de progreso en modo headless.
  - `image_resolver.py`: resolucion/caching de imagenes del lado Python, con normalizacion automatica y busqueda concurrente entre carpeta local, API propia y GO-UPC para la vista previa de productos.
  - `productos_sync_service.py`: sync de productos y deteccion de cambios.
  - `ofertas_service.py`: soporte a generacion de ofertas.
  - linea pendiente VPC-F3: snapshot local de ofertas activas desde `ATIPICAS` para integracion futura con verificador.
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
5. El selector manual y el autoenvio pueden descubrir verificadores por red local si no hay equipos online registrados.
6. Antes de enviar, tambien puede empujar GO-UPC key y URL de API propia de imagenes.
7. La UI de `Productos` ahora trabaja con layout de dos columnas: listado a la izquierda y panel lateral de preview/acciones a la derecha, con refresco en vivo del producto seleccionado.
8. La siguiente fase prevista agrega columnas locales de oferta por producto (`TIENE_OFERTA`, `PRECIO_OFERTA`, vigencias y origen) para que la SQLite refleje promociones activas provenientes de `DBA.ATIPICAS`.

### Publicidades
1. `CONTENIDO_PUBLICIDAD` mantiene grupos y globales en config.
2. Desde `1.16.5` las publicidades se copian a storage interno administrado por SmartPrice.
3. El envio usa `dispositivo_sender.py` -> `dispositivos_envio_service.py`.
4. El selector de envio puede descubrir automaticamente InforTV por puerto/API antes de elegir destino.
5. Android recibe imagenes/videos en endpoints separados.
6. Se reinicia launcher al finalizar.

### Configuracion
1. `GUI_CONFIG.py` edita DSN, API key, toggles y opciones de envio.
2. `GUI_CONFIG.py` tambien expone pestaÃ±a `Usuarios y Permisos` para ver/editar perfiles por usuario Windows.
3. `GUI_CONFIG.py` ahora permite buscar dispositivos por red local desde la pestaÃ±a `Dispositivos`, con filtro visual y edicion previa del nombre detectado.
4. `GUI_CONFIG.py` ahora muestra una guia visible de especificaciones de imagen para Android y valida tecnicamente el logo seleccionado.
5. `FUNC/config_json.py` guarda configuracion persistente con lock de archivo para reducir colisiones entre sesiones/usuarios.
6. En modo compilado, la config se mueve a `C:\ProgramData\SmartPrice\config.json`.

### Imagenes
1. La imagen de producto puede ingresar por carga manual, carpeta local, API propia o GO-UPC.
2. Toda imagen nueva que no provenga ya de SQLite se normaliza antes de persistirse:
   - maximo `1400x1400`,
   - objetivo `1000x1000`,
   - salida `JPEG`,
   - compresion orientada a quedar debajo de `700 KB`.
3. El logo principal se normaliza a PNG con proporcion `4:1` y margen interno para evitar recortes en Android.
4. Esta normalizacion se aplica para reducir payload base64, consumo de memoria y tiempos de render del verificador.

### Multiusuario
1. `GUI_MAIN.py` calcula una instancia unica por usuario Windows, no global a toda la maquina.
2. Cada usuario obtiene su propia instancia, su propia bandeja y sus permisos efectivos.
3. Si una segunda ejecucion del mismo usuario detecta la instancia existente, intenta mostrar la ventana ya abierta via socket local.
4. Los permisos actuales son por nombre de usuario Windows y viven en `config.json -> perfiles_usuario`.
5. La base SQLite sigue siendo compartida por instalacion, por lo que los usuarios comparten datos aunque no compartan permisos de UI.

## 5. Contratos vigentes con Android

Mantener compatibilidad con:
- `POST /api/veri/batch_productos`
- `DELETE /api/veri/batch_productos`
- `GET /api/veri/status`
- `GET /api/veri/configuracion_player`
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
- El descubrimiento en red actual recorre subredes privadas tipo `/24`; en redes grandes o segmentadas puede requerir optimizacion futura.
- Multiusuario comparte la misma SQLite: funciona para escenarios controlados, pero puede exponer `database is locked` o demoras si dos sesiones escriben fuerte al mismo tiempo.
- Aunque `config.json` ya usa lock y reintentos, sigue siendo un archivo compartido: hay que seguir evitando cambios innecesarios y escrituras redundantes.
- La seguridad actual es de capa aplicacion/UI; cualquier modulo nuevo debe integrarse explicitamente al sistema de permisos para no abrir bypasses.
- `CustomTkinter` mostro fragilidad en loaders/overlays bajo ciertas sesiones Windows Server con distinto escalado; para overlays criticos conviene priorizar `tk/ttk` puro.
- La rama `publicidades` del config es compartida entre usuarios; las vistas de Publicidad deben refrescar desde disco antes de operar para no trabajar con copias stale en memoria.
- La deteccion por red diferencia por tipo de dispositivo (`verificador` vs `infotv`) y esa separacion no debe perderse en futuros flujos de envio.
- La futura integracion de ofertas no debe mezclar `precio_oferta` con `precios_adicionales` de `PACKS_MINI`; son contratos distintos y deben viajar separados al verificador.
- La futura normalizacion de codigos no debe asumir que cualquier valor de `12` digitos es automaticamente UPC-A o GS1 valido; la fase inicial se limita a fallback `EAN-13` para clientes legacy documentados.
- La conexion ODBC legacy a SQL Anywhere/Sybase sigue teniendo un ciclo de vida fragil:
  - `GUI_MAIN.py` registra una instancia global de `ConexionSybase`,
  - esa instancia puede quedar viva mientras la app sigue minimizada en bandeja,
  - los `SELECT` en `DB/database_sybase.py` no fuerzan `commit` ni `rollback` al finalizar,
  - la misma instancia puede reutilizarse desde hilos de sincronizacion automatica.
- Este punto puede dejar sesiones DBA abiertas mas tiempo del debido y provocar bloqueos/interferencias con otros ejecutables del cliente que usan la misma base legacy.
- Ademas, `ConexionSybase` conserva `self.cursor` aunque la ejecucion real usa cursores locales por `with`, lo que deja un recurso persistente innecesario.

## 7. Decisiones vigentes que no deben romperse

- Python ya no busca imagenes remotas para preview de productos; eso queda del lado Android al escanear.
- Toda imagen nueva incorporada desde Python debe persistirse ya optimizada para Android; no volver a guardar originales pesados en SQLite si el flujo pasa por `image_resolver.py` o por la carga manual de Productos.
- Publicidades se guardan en storage interno para no depender de rutas del usuario.
- Config compilada debe quedar fuera de `Program Files` para evitar perdida de datos entre usuarios.
- La app debe poder correr con GUI o headless sin duplicar logica de negocio.
- El usuario `pantalla` debe poder operar solo `Publicidad` sin acceder a `Productos` ni `Configuracion`.
- La instancia unica debe ser por usuario Windows para no bloquear sesiones distintas en la misma PC/Windows Server.
- El arranque debe mostrar feedback visible de carga y evitar congelar la primera pantalla; la shell de GUI debe pintar antes del bootstrap pesado.
- Productos y Publicidad no deben mezclar destinos: descubrimiento y selector deben filtrar verificadores para catalogo y dispositivos InforTV para multimedia.
- Mientras no cierre `VPC-F4`, SmartPrice sigue guardando y enviando `codigo` tal cual viene de Sybase; no asumir normalizacion implicita.
- La futura correccion de ODBC/DBA debe preservar comportamiento funcional de sync y ofertas:
  - no romper `ProductosSyncService`,
  - no romper `OfertasPLUSyncService`,
  - no romper la carga manual/automatica de productos,
  - no romper el modo headless ni el envio incremental.

## 8. Incidente operativo abierto: posible bloqueo de DBA legacy

Fecha de registro: `2026-08-14`

### Sintoma observado

En cliente `Novo`, otros ejecutables del ecosistema (por ejemplo calculo de precios) reportan que el DBA queda bloqueado mientras `SmartPrice` esta en ejecucion.

### Evidencia ya relevada

- `DB/database_sybase.py` abre conexion persistente y no finaliza explicitamente la transaccion luego de `SELECT`.
- `GUI_MAIN.py` crea y registra `CONEXIONDBA_SYBASE` como objeto global compartido por GUI y servicios.
- `GUI_MAIN.py` oculta la app a bandeja en lugar de cerrarla, por lo que una sesion ODBC puede quedar viva durante horas.
- `CONTENIDO_PRODUCTO.py` usa sincronizacion automatica cada `5s` y reusa servicios que consumen la conexion Sybase.
- Los logs del cliente muestran polling repetido con `SELECT MAX(CONVERT(VARCHAR, dFechaU, 120))` sobre:
  - `DBA.ARTICULO`
  - `DBA.CODBARP`
  - `DBA.PACKS_MINI`
  - `DBA.ATIPICAS`
  - `DBA.OFERTAT`
  - `DBA.OFERTAL`
- No se encontro evidencia de escrituras directas actuales sobre tablas `DBA.*` como causa primaria del bloqueo.

### Hipotesis tecnica principal

La causa probable no es un `UPDATE/DELETE` legacy activo, sino una combinacion de:

- conexion ODBC global de larga vida,
- lectura sin `commit/rollback` explicito,
- reuse desde threads,
- proceso minimizado a bandeja.

### Estado

- `actual`: riesgo documentado y reproducible como sospecha fuerte.
- `pendiente de confirmar`: falta validacion final en cliente luego de aplicar refactor de ciclo de vida de conexion.

### Mitigacion implementada el 2026-08-14

- `DB/database_sybase.py` ahora:
  - usa `autocommit=True`,
  - elimina `self.cursor` persistente,
  - valida estado de la conexion antes de reutilizarla,
  - serializa acceso con `RLock`,
  - cierra la conexion ante error de ejecucion.
- `GUI_MAIN.py` ahora:
  - cierra la instancia previa de `CONEXIONDBA_SYBASE` al reconfigurarla,
  - fuerza `desconectar()` al cerrar realmente la app.
- `GUI_CONFIG.py` ahora:
  - cierra la conexion global previa antes de reemplazar `CONEXIONDBA_SYBASE`.

### Pendiente posterior al fix

- validar en cliente `Novo` que:
  - SmartPrice minimizado a bandeja no deje bloqueado el DBA,
  - otros EXE legacy vuelvan a operar en paralelo,
  - la sincronizacion automatica siga funcionando sin regresiones.
