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
6. Cerrar linea pendiente de multiprecios y `PACKS_MINI`:
   - `VPC-F1-006` sync local SQLite de multiprecios y packs (`86e2hfxp6`)
   - `VPC-F1-007` envio en datos completos y novedades (`86e2hfxrv`)
   - `VPC-F1-008` visualizacion en UI de Productos (`86e2hfxvn`)
   - `VPC-F1-009` cierre de integracion Python-Android (`86e2hfxz2`)
7. Consolidar descubrimiento de dispositivos en red:
   - `VPC-F1-010` deteccion automatica de dispositivos y alta desde GUI (`86e2jhakm`)
8. Abrir linea de ofertas por precio desde `ATIPICAS`:
   - `VPC-F3-001` esquema SQLite y snapshot local de ofertas activas (`86e2k22vh`) [completado]
   - `VPC-F3-002` sync Sybase -> SQLite usando `ATIPICAS` (`86e2k22vu`) [completado]
   - `VPC-F3-003` envio Android en `batch_productos` con `tiene_oferta` y `precio_oferta` (`86e2k22wb`) [completado]
   - `VPC-F3-004` visualizacion y validacion en UI / verificador (`86e2k22wr`) [en curso]

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

## Anexo fase VPC-F2

Responsable acordado: `Nicolas Gomez`

Tareas ClickUp activadas para esta linea:
- `VPC-F2-001` viabilidad general Bootstack (`86e2hfey7`)
- `VPC-F2-002` matriz de reemplazo de widgets (`86e2hff25`)
- `VPC-F2-003` POC de shell con `AppShell` (`86e2hff8k`)
- `VPC-F2-004` analisis de pantallas de datos (`86e2hffd1`)
- `VPC-F2-005` estrategia incremental (`86e2hffgr`)

Documento base obligatorio para esta fase:
- `INTERNAL_DEV/BOOTSTACK_MIGRATION_BASE.md`

## Anexo fase VPC-F3

Responsable acordado: `Misael Ramirez`

Objetivo tecnico inicial:
- No mezclar canastas ni packs con precio oferta.
- Primera implementacion usando solo `DBA.ATIPICAS`.
- Regla activa: `CCLAVEC = 'O'` + `DFECINI/DFECFIN` vigentes.
- `NPRECIO` se considera `precio_oferta`.
- `NPVP1` se mantiene como precio principal normal.

Contrato candidato para Android / Verificador:
- reutilizar `POST /api/veri/batch_productos`
- agregar campos opcionales:
  - `tiene_oferta`
  - `precio_oferta`
  - `oferta_desde`
  - `oferta_hasta`
  - `oferta_origen`
  - `oferta_ccoddiv`
  - `oferta_dto`

Notas:
- Esta fase debe dejar trazabilidad suficiente para pasarse al chat del verificador de precio.
- No se incorpora todavia `OFCANASTA`, `OFERTAP` ni `MIX_CANAS` al payload operativo principal.
