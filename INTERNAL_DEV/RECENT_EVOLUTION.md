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

## Robustez UI

- Corregido problema de `CTkLoader` con escalado/DPI entre usuarios de Windows.
- Varias ventanas de progreso y estado se movieron hacia un flujo mas seguro con `after(...)`.
