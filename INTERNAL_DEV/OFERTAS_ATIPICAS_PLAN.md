# Fase VPC-F3 - Ofertas por precio desde ATIPICAS

Fecha de apertura: `2026-07-31`
Responsable principal: `Misael Ramirez`

## Objetivo

Incorporar ofertas por precio a la linea operativa de productos usando una primera implementacion acotada y estable:

- fuente unica: `DBA.ATIPICAS`
- sin mezclar `OFCANASTA`, `OFERTAP`, `MIX_CANAS`
- sin mezclar `precio_oferta` con `producto_precios` / `PACKS_MINI`

## Regla de negocio inicial

Un producto tiene oferta activa si existe registro en `DBA.ATIPICAS` que cumpla:

- `CCLAVEC = 'O'`
- `DFECINI <= hoy`
- `DFECFIN IS NULL OR DFECFIN >= hoy`

Campos relevantes:

- `CREF`
- `NPRECIO` -> `PRECIO_OFERTA`
- `NDTO` -> `OFERTA_DTO`
- `DFECINI` -> `OFERTA_DESDE`
- `DFECFIN` -> `OFERTA_HASTA`
- `CCODDIV` -> `OFERTA_CCODDIV`

## Modelo local SQLite

Tabla: `productos`

Columnas agregadas:

- `TIENE_OFERTA INTEGER DEFAULT 0`
- `PRECIO_OFERTA REAL`
- `OFERTA_DESDE TEXT`
- `OFERTA_HASTA TEXT`
- `OFERTA_ORIGEN TEXT`
- `OFERTA_CCODDIV TEXT`
- `OFERTA_DTO REAL`

Notas:

- `NPVP1` sigue siendo el precio principal normal.
- `PRECIO_OFERTA` no reemplaza `precio`.
- `producto_precios` queda reservado para multiprecios / `PACKS_MINI`.

## Contrato candidato para Android / Verificador

Se mantiene el endpoint existente:

- `POST /api/veri/batch_productos`

Campos opcionales nuevos por producto:

```json
{
  "tiene_oferta": true,
  "precio_oferta": 5198.99,
  "oferta_desde": "2026-05-20",
  "oferta_hasta": "2026-06-15",
  "oferta_origen": "ATIPICAS",
  "oferta_ccoddiv": "PSO",
  "oferta_dto": 1.5
}
```

## Fases

### VPC-F3-001
Esquema SQLite y snapshot local de ofertas activas.

Estado: `completado`

ClickUp:
- `86e2k22vh`
- <https://app.clickup.com/t/86e2k22vh>

### VPC-F3-002
Sync Sybase -> SQLite usando `ATIPICAS`.

Estado: `completado`

ClickUp:
- `86e2k22vu`
- <https://app.clickup.com/t/86e2k22vu>

### VPC-F3-003
Extender `batch_productos` con oferta activa.

Estado: `completado`

ClickUp:
- `86e2k22wb`
- <https://app.clickup.com/t/86e2k22wb>

### VPC-F3-004
Visualizacion y validacion en UI / verificador.

Estado: `en curso`

ClickUp:
- `86e2k22wr`
- <https://app.clickup.com/t/86e2k22wr>

## Riesgos a controlar

- no asumir que toda promo compleja se puede bajar a `precio_oferta`
- no mezclar promociones de canasta con promociones simples por precio
- evitar que novedades ignore cambios de oferta cuando no cambia `NPVP1`
- mantener compatibilidad con APKs viejos si los campos nuevos no existen del lado Android
