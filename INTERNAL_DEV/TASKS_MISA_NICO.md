# Tareas y Ownership

## Regla madre

Mantener una sola linea tecnica:
- Misa lidera datos, sync, headless, config, empaquetado.
- Nico lidera publicidades, experiencia visual relacionada a media y contratos Android de media/imagenes.

Si un cambio cruza ambas lineas, se define contrato primero y luego cada uno implementa su lado.

## Misa - Ownership principal

### Modulos
- `main.py`
- `DB/`
- `core/services/productos_sync_service.py`
- `core/services/headless_envio_service.py`
- `core/services/headless_progress_window.py`
- `core/services/dispositivos_envio_service.py`
- `core/network/api_client.py`
- `core/network/urls_dispositivos.py`
- `GUI/CONTENIDO_PRODUCTO.py`
- `GUI/GUI_CONFIG.py`
- `versionado/`
- instalador / compilacion / Inno Setup

### Backlog sugerido
1. Seguir separando SQL y logica de sync fuera de la GUI.
2. Mejorar sincronizacion automatica y debounce de novedades.
3. Revisar seguridad de threads + SQLite.
4. Consolidar config persistente y mover datos sensibles fuera de flujo visual.
5. Preparar refactor de `CONTENIDO_PRODUCTO.py` por servicios.

## Nico - Ownership principal

### Modulos
- `GUI/CONTENIDO_PUBLICIDAD.py`
- `GUI/OFERTAS_GENERADOR.py`
- `core/services/ofertas_service.py`
- contratos Android de publicidades, logo e imagenes
- herramientas de preview media
- politica de audio/video y flujo visual de envios multimedia

### Backlog sugerido
1. Completar biblioteca de publicidades con mejor vista y filtros.
2. Diseñar envio incremental real junto con cambios en Android.
3. Agregar programacion por horario/dia/grupo.
4. Mejorar panel de control de multimedia y estado visual por item.
5. Consolidar reglas de media global vs grupo.

## Modulos compartidos con lock obligatorio

- `GUI/GUI_MAIN.py`
- `GUI/GUI_CONFIG.py`
- `FUNC/config_json.py`
- `core/network/dispositivo_sender.py`
- `core/services/dispositivos_envio_service.py`

## Contratos que deben respetar ambos

- API Android existente no se rompe.
- Config persistente no vuelve a rutas relativas fragiles.
- No volver a buscar imagenes remotas en Python para preview de productos.
- Publicidades siempre desde storage interno de SmartPrice.
