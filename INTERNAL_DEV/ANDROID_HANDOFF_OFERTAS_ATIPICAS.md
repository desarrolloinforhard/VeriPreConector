# Handoff Android - Ofertas por precio desde ATIPICAS

Fecha: `2026-07-31`
Fase Python relacionada: `VPC-F3`
Estado Python actual:

- `VPC-F3-001` completado
- `VPC-F3-002` completado
- `VPC-F3-003` completado
- `VPC-F3-004` en curso

## Objetivo

Extender el verificador Android para aceptar y mostrar oferta activa por producto, sin romper compatibilidad con el payload actual de `batch_productos`.

## Decisión funcional ya tomada en Python

Primera implementación de oferta:

- fuente única: `DBA.ATIPICAS`
- no usar todavía `OFCANASTA`
- no usar todavía `OFERTAP`
- no usar todavía `MIX_CANAS`
- no mezclar `precio_oferta` con `precios_adicionales`

Regla de oferta activa resuelta en Python:

- `CCLAVEC = 'O'`
- `DFECINI <= hoy`
- `DFECFIN IS NULL OR DFECFIN >= hoy`

El precio normal principal sigue siendo:

- `precio` = `NPVP1` final con IVA

La oferta viaja aparte como:

- `tiene_oferta`
- `precio_oferta`
- `oferta_desde`
- `oferta_hasta`
- `oferta_origen`
- `oferta_ccoddiv`
- `oferta_dto`

## Endpoint

Se mantiene el endpoint actual:

- `POST /api/veri/batch_productos`

No se creó endpoint nuevo.

## Compatibilidad requerida

Los campos nuevos son opcionales.

Si el APK viejo no los recibe, no debe romperse el procesamiento del producto.

Si el APK nuevo los recibe:

- debe guardarlos localmente
- debe mostrarlos al consultar el producto

## Payload esperado por producto

Ejemplo:

```json
{
  "codigo": "779218000166",
  "descripcion": "ACEITE CAÑUELAS GIRASOL 1,5L",
  "precio": "5288.48",
  "img_base64": null,
  "formato_imagen": null,
  "precios_adicionales": [
    {
      "tipo_precio": "npvp4",
      "categoria": "minorista",
      "origen": "packs_mini",
      "orden": 13003,
      "cantidad": 3,
      "titulo": "Llevando x 3",
      "detalle": "Llevando x 3",
      "precio": "6000.00",
      "nroprecio": "04",
      "dfechau": "2026-07-27 00:00:00"
    }
  ],
  "tiene_oferta": true,
  "precio_oferta": "5198.99",
  "oferta_desde": "2026-05-20 00:00:00",
  "oferta_hasta": "2026-06-15 00:00:00",
  "oferta_origen": "ATIPICAS",
  "oferta_ccoddiv": "PSO",
  "oferta_dto": "1.50"
}
```

## Qué debe hacer Android

### 1. Mantener compatibilidad

Si faltan esos campos:

- seguir guardando producto como hoy
- mostrar solo precio normal

### 2. Persistencia local

Agregar columnas en SQLite local del verificador para productos:

- `tiene_oferta INTEGER DEFAULT 0`
- `precio_oferta REAL NULL`
- `oferta_desde TEXT NULL`
- `oferta_hasta TEXT NULL`
- `oferta_origen TEXT NULL`
- `oferta_ccoddiv TEXT NULL`
- `oferta_dto REAL NULL`

Si ya existe la tabla:

- migrar con `ALTER TABLE`

### 3. Upsert de productos

Cuando llegue el producto:

- guardar `precio` normal como hoy
- si `tiene_oferta = true`, guardar los campos nuevos
- si `tiene_oferta` viene ausente o `false`, limpiar esos campos del producto local

### 4. Visualización

Cuando el usuario escanea:

- mostrar el precio normal como base
- si `tiene_oferta = true`, mostrar además el precio oferta claramente

Sugerencia visual mínima:

- precio normal
- badge o texto `OFERTA`
- precio oferta destacado

## Qué no hacer todavía

- no recalcular oferta en Android
- no consultar `ATIPICAS` desde Android
- no interpretar canastas
- no convertir `precios_adicionales` en `precio_oferta`

Android debe consumir la oferta ya resuelta por Python.

## Casos a probar

### Caso 1
Producto sin oferta:

- `tiene_oferta` ausente o `false`
- debe verse normal

### Caso 2
Producto con oferta:

- `precio` normal visible
- `precio_oferta` visible
- persiste en SQLite local

### Caso 3
Producto que antes tenía oferta y ahora no:

- Python enviará el producto sin oferta activa
- Android debe limpiar campos locales de oferta

### Caso 4
Compatibilidad:

- batch con productos mixtos: algunos con oferta, otros sin oferta

## Prompt sugerido para el chat Android

```text
Necesito que actualices el verificador Android para soportar oferta activa por producto, sin romper compatibilidad con el endpoint actual.

Contexto:
- Python sigue usando `POST /api/veri/batch_productos`
- no hay endpoint nuevo
- ahora algunos productos pueden traer campos opcionales de oferta

Regla ya resuelta del lado Python:
- la oferta viene desde `ATIPICAS`
- ya llega resuelta, Android no tiene que calcular nada

Campos nuevos opcionales por producto:
- `tiene_oferta`
- `precio_oferta`
- `oferta_desde`
- `oferta_hasta`
- `oferta_origen`
- `oferta_ccoddiv`
- `oferta_dto`

Ejemplo de payload:
{
  "codigo": "779218000166",
  "descripcion": "ACEITE CAÑUELAS GIRASOL 1,5L",
  "precio": "5288.48",
  "img_base64": null,
  "formato_imagen": null,
  "precios_adicionales": [],
  "tiene_oferta": true,
  "precio_oferta": "5198.99",
  "oferta_desde": "2026-05-20 00:00:00",
  "oferta_hasta": "2026-06-15 00:00:00",
  "oferta_origen": "ATIPICAS",
  "oferta_ccoddiv": "PSO",
  "oferta_dto": "1.50"
}

Necesito que hagas:
1. migracion SQLite local agregando columnas de oferta al producto
2. upsert de esos campos al procesar `batch_productos`
3. si el producto llega sin oferta, limpiar campos locales de oferta
4. mostrar en la UI del escaneo el precio normal y, si existe, el precio oferta
5. mantener compatibilidad con APKs viejos y payloads viejos

No implementar todavía:
- canastas
- mix
- promociones complejas
- cálculos de oferta en Android

Android solo debe persistir y mostrar la oferta ya resuelta por Python.

Quiero que me devuelvas:
- tablas/columnas nuevas
- cambios en el modelo
- cambios en el parser del endpoint
- cambios en la UI del detalle de producto
- consideraciones de compatibilidad
```
