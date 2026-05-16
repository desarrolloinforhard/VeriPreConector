# Recent Evolution

Resumen de lo construido y estabilizado durante esta etapa de trabajo.

## Productos / Sync / Envios

- Corregido loop de sincronizacion automatica que repetia mensajes y recargas.
- Ajustado refresco de precios y novedades para que tome cambios de costo/precio.
- Mejorado estado visual durante envio de novedades.
- Agregado modo headless con parametros:
  - `--transmitir-completo`
  - `--transmitir-novedades`
  - `--sin-ventana-progreso`
- Agregada ventana de progreso para modo headless.
- Mejorado envio a dispositivos con resumen y estado por equipo.

## Imagenes

- Se creo `image_resolver.py` para resolver imagenes con estrategia controlada.
- Python dejo de usar APIs remotas para preview de productos y preparacion normal.
- Se preparo la coordinacion para que Android resuelva imagenes faltantes al escanear.
- Se agrego soporte para enviar GO-UPC key y URL de API propia de imagenes al verificador Android.
- Se creo utilidad externa `fetch_product_image.py` / `TraerImagen.exe`.

## Publicidades

- Se agregaron grupos de publicidades y publicidades globales.
- Se reorganizo la UI de Publicidades con panel de opciones colapsable.
- Se agrego opcion de mantener audio en videos como modo prueba.
- Se aumentaron timeouts para envio de videos pesados.
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
- Se ajusto el instalador para no pisar la base `veripre.db` en updates.
- Se actualizo el instalador para reflejar `1.16.17`.

## Robustez UI

- Corregido problema de `CTkLoader` con escalado/DPI entre usuarios de Windows.
- Varias ventanas de progreso y estado se movieron hacia un flujo mas seguro con `after(...)`.
- El arranque principal ahora muestra un loader por etapas antes de abrir completamente la pantalla inicial.
- `GUI_MAIN.py` ya no inicializa todo sincronicamente: primero pinta shell minima y luego bootstrapea base, variables globales, modulo inicial y bandeja.
- Se abandono el loader basado en `CustomTkinter` para el overlay de arranque; ahora usa `tk/ttk` por robustez entre sesiones Windows con distinto DPI/escalado.
- La apertura inicial de `Productos` y `Publicidad` ahora puede disparar carga lazy del modulo con loader reutilizable.

## Multiusuario / Permisos / Bandeja

- La instancia unica ya no es global a toda la maquina: ahora se resuelve por usuario Windows.
- Cada sesion de Windows puede abrir su propia instancia y mantener su propia bandeja.
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
