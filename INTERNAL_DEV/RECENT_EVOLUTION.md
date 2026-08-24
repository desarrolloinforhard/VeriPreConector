# Recent Evolution

Resumen de lo construido y estabilizado durante esta etapa de trabajo.

## Frontend ttkbootstrap 1.16.35

- Agregado menu lateral plegable con modos expandido y compacto estables.
- Fijada la geometria de Configuracion y Acerca de para evitar saltos durante hover y cambios de estado.
- Cacheados logo e iconos y aplicado repintado atomico en Windows para reducir demoras y parpadeos.
- Corregida la apertura de Acerca de y reforzada la navegacion Volver.
- Agregado selector persistente de tema claro/oscuro en el menu lateral.
- Adaptado el contraste de la tabla de Productos y eliminado el destello blanco del overlay de carga.
- Incorporado Home informativo con metricas locales, estado de conexion, dispositivos registrados, accesos guiados y barra de estado.
- Renovada la identidad visual con logos por tema, icono de Inicio y paleta corporativa verde/blanca.
- Unificado el lenguaje visual de Productos y Publicidad mediante tarjetas, jerarquia de superficies y acciones compactas.

## Productos / Sync / Envios

- El icono de bandeja ahora se crea solo al minimizar a tray y se destruye al restaurar/cerrar para reducir iconos fantasma en Windows.
- `Transmitir Novedades` dejo de depender solo del estado en memoria y ahora recompone pendientes desde SQLite con una marca persistida de ultima transmision exitosa.
- `Recargar Productos` ahora limpia filtros/estado del `Tableview` antes de repoblar la lista local.
- Endurecido el acceso a `F:\Dba\veripre.db` para instalaciones compartidas con lock interno por proceso, `busy_timeout`, WAL y eliminacion de `commit()` en lecturas.
- Registrado el incidente `database is locked` observado en cliente Novo como problema de contencion SQLite local entre polling automatico, UI y escrituras.
- Corregido loop de sincronizacion automatica que repetia mensajes y recargas.
- Ajustado refresco de precios y novedades para que tome cambios de costo/precio.
- Mejorado estado visual durante envio de novedades.
- Agregada deteccion automatica de verificadores en red local para selector manual, autoenvio y modo headless.
- Si no hay verificadores online registrados, el envio de productos puede intentar descubrirlos por red antes de abortar.
- Agregado modo headless con parametros:
  - `--transmitir-completo`
  - `--transmitir-novedades`
  - `--sin-ventana-progreso`
- Agregada ventana de progreso para modo headless.
- Mejorado envio a dispositivos con resumen y estado por equipo.
- La pantalla `Productos` se reorganizo en layout de dos columnas:
  - listado y busqueda a la izquierda,
  - preview/resumen/acciones a la derecha.
- El panel lateral ahora refleja la seleccion actual mostrando:
  - descripcion,
  - codigo,
  - precio principal,
  - estado de oferta,
  - contador de precios adicionales.
- La ventana de detalle del producto tambien se rediseño con mejor separacion entre:
  - datos base,
  - precios adicionales,
  - preview,
  - bloque de oferta activa.

## Imagenes

- Se creo `image_resolver.py` para resolver imagenes con estrategia controlada.
- Python dejo de usar APIs remotas para preview de productos y preparacion normal.
- Se preparo la coordinacion para que Android resuelva imagenes faltantes al escanear.
- Se agrego soporte para enviar GO-UPC key y URL de API propia de imagenes al verificador Android.
- Se creo utilidad externa `fetch_product_image.py` / `TraerImagen.exe`.
- `Configuracion de Datos` ahora muestra una guia tecnica visible para imagen de producto y logo segun restricciones del verificador Android.
- La seleccion de logo ahora normaliza automaticamente a PNG con proporcion 4:1 y margen interno antes de guardarlo en `assets/!!!LOGO_PRINCIPAL!!!.png`.
- La GUI de Productos ahora optimiza imagenes cargadas manualmente antes de guardarlas en SQLite:
  - maximo `1400x1400`,
  - objetivo `1000x1000`,
  - conversion a `JPEG`,
  - compresion para intentar quedar por debajo de `700 KB`.
- `image_resolver.py` ahora aplica la misma normalizacion automatica a imagenes que entran desde carpetas locales, API propia y GO-UPC antes de persistirlas en SQLite/carpeta.
- El preview lateral de productos ahora usa carga asincronica con loader local sobre el frame de imagen.
- La API propia de imagenes queda con fallback operativo por defecto en `http://inforhardserver.ddns.net:5000`, pero sigue siendo configurable desde `Configuracion`.
- El preview ya no espera a una sola fuente lineal: si SQLite no resuelve, dispara busqueda concurrente entre carpeta, API propia y GO-UPC y toma la primera valida.

## Publicidades

- Se agregaron grupos de publicidades y publicidades globales.
- Se reorganizo la UI de Publicidades con panel de opciones colapsable.
- Se agrego opcion de mantener audio en videos como modo prueba.
- Se aumentaron timeouts para envio de videos pesados.
- El selector de envio de publicidades ahora puede descubrir automaticamente dispositivos InforTV en red local.
- Desde `1.16.5`:
  - las publicidades se copian a storage interno,
  - se migran publicidades antiguas,
  - se valida antes de enviar,
  - se guarda historial por dispositivo,
  - se expone una biblioteca interna con metadata y estado,
  - se marca si hay cambios pendientes.

## Config / Persistencia / Instalacion

- `config.json` ahora usa ruta persistente mas estable en compilado:
  - `C:\ProgramData\SmartPrice\config.json`
- Guardado de config convertido a flujo atomico.
- Guardado de config reforzado con lock de archivo y reintentos para escenarios multiusuario.
- Se ajusto el instalador para no pisar la base `veripre.db` en updates.
- El instalador ahora prepara `C:\ProgramData\SmartPrice` con permisos de escritura para usuarios.
- `Configuracion > Dispositivos` ahora incluye busqueda manual en red con filtro por tipo, cache corta y alta en lote de equipos detectados.
- La ventana de deteccion ahora permite:
  - editar nombres en panel lateral,
  - aplicar nombres masivos a la seleccion,
  - filtrar `Solo nuevos` / `Solo registrados` / `Todos`,
  - distinguir visualmente `Nuevo` vs `Ya registrado`.

## Robustez UI

- Corregido problema de `CTkLoader` con escalado/DPI entre usuarios de Windows.
- Varias ventanas de progreso y estado se movieron hacia un flujo mas seguro con `after(...)`.
- El arranque principal ahora muestra un loader por etapas antes de abrir completamente la pantalla inicial.
- `GUI_MAIN.py` ya no inicializa todo sincronicamente: primero pinta shell minima y luego bootstrapea base, variables globales, modulo inicial y bandeja.
- Se abandono el loader basado en `CustomTkinter` para el overlay de arranque; ahora usa `tk/ttk` por robustez entre sesiones Windows con distinto DPI/escalado.
- La apertura inicial de `Productos` y `Publicidad` ahora puede disparar carga lazy del modulo con loader reutilizable.
- `config.json` ahora usa lock de archivo y reintentos para mejorar el guardado compartido entre sesiones/usuarios.
- `Publicidad` ahora refresca la configuracion compartida desde disco antes de leer y guardar, para que distintas sesiones vean los mismos grupos e items.

## Multiusuario / Permisos / Bandeja

- La instancia unica ya no es global a toda la maquina: ahora se resuelve por usuario Windows.
- Cada sesion de Windows puede abrir su propia instancia y mantener su propia bandeja.
- Si el usuario relanza la app y ya existe una instancia propia, SmartPrice intenta reactivar la ventana existente.
- Se agrego modelo de permisos por usuario Windows en `config.json`:
  - `administrador`: acceso completo
  - `pantalla`: solo `Publicidad`
  - `default`: fallback con acceso completo
- `GUI_MAIN.py` ahora arma menu, seccion inicial y accesos segun permisos efectivos.
- `GUI_CONFIG.py` ahora incorpora pestaña `Usuarios y Permisos`:
  - vista de perfiles configurados,
  - permisos efectivos del usuario actual,
  - alta de perfiles,
  - edicion de modulos por perfil.
- Se agregaron protecciones para:
  - no dejar perfiles sin ningun modulo,
  - no quitarse a uno mismo el acceso a `Configuracion` desde la GUI.
- Se blindaron accesos secundarios:
  - `Configuracion` valida permiso antes de abrir,
  - `GUI_CONFIG` rechaza apertura si el usuario no tiene permiso,
  - `VentanaManager` tolera aperturas denegadas,
  - `selector_seccion()` hace fallback si se intenta forzar una pantalla restringida.
- Se documento el proceso de validacion en `INTERNAL_DEV/MULTIUSER_TEST_CHECKLIST.md`.

## Sidebar / Shell visual

- El sidebar principal fue rediseñado hacia una linea visual mas tipo card/soft UI.
- Se reemplazo el texto/branding viejo por el logo horizontal `INFORHARD_HORIZONTAL.png`.
- Se ajustaron estados hover/activo con paleta verde alineada a la marca.
- Se compactaron anchos, paddings y cards del menu para reducir el peso visual de la columna lateral.
- El tray icon ahora tiene limpieza mas robusta:
  - cleanup en `atexit`,
  - cleanup al salir de `mainloop`,
  - salida controlada desde el menu del tray,
  - ocultado explicito antes de `stop()` para reducir iconos fantasma en Windows.

## Linea futura UI / Bootstack

- Se abrio fase `VPC-F2` para evaluar migracion de UI hacia `Bootstack`.
- La migracion queda marcada por ahora como `piloto`, no como implementacion directa.
- Se crearon tareas ClickUp asignadas a Nicolas para:
  - viabilidad,
  - matriz de widgets,
  - POC de `AppShell`,
  - analisis de pantallas de datos,
  - roadmap incremental.
- Se agrega `INTERNAL_DEV/BOOTSTACK_MIGRATION_BASE.md` como documento base de arranque.

## Incidente documentado 2026-08-14 - DBA / ODBC

- En cliente Novo se relevo una posible interferencia entre SmartPrice y otros ejecutables legacy que usan la misma base SQL Anywhere/DBA.
- La evidencia actual apunta a:
  - conexion Sybase global registrada en GUI,
  - proceso persistente en bandeja,
  - reuse desde sincronizacion automatica,
  - lecturas `SELECT` sin cierre explicito de transaccion en el wrapper ODBC.
- Los logs muestran polling recurrente cada `5s` con `SELECT MAX(CONVERT(VARCHAR, dFechaU, 120))` sobre:
  - `DBA.ARTICULO`
  - `DBA.CODBARP`
  - `DBA.PACKS_MINI`
  - `DBA.ATIPICAS`
  - `DBA.OFERTAT`
  - `DBA.OFERTAL`
- No se encontro evidencia de escrituras directas actuales sobre tablas `DBA.*` como causa primaria.
- Se abre fase nueva de hardening para refactorizar ciclo de vida de `ConexionSybase`, aislar hilos y validar cierre real de sesiones ODBC.

Mitigacion aplicada en esta misma fecha:
- `ConexionSybase` pasa a `autocommit=True`.
- Se elimina `self.cursor` persistente.
- Se agrega cierre defensivo de conexion ante error y reconexion limpia.
- `GUI_MAIN` y `GUI_CONFIG` cierran la instancia previa al reemplazar la conexion global.
- `GUI_MAIN.cerrar_aplicacion()` fuerza cierre explicito de Sybase antes de destruir la ventana.

Estado:
- `implementado`: hardening basico del wrapper y de los reemplazos/cierre GUI.
- `pendiente de confirmar`: validacion operativa final en entorno cliente con otros EXE legacy abiertos.
