# Barcode Normalization Plan

Fecha: `2026-07-31`
Responsable propuesto: `Misael Ramirez`
Fase: `VPC-F4`

## Problema detectado

Hay clientes que mantienen `CCODEBAR` en formato legacy de `12` digitos sin digito verificador.

Ejemplo real:

- origen Sybase: `779038701414`
- `EAN-13` esperado: `7790387014143`

Hoy SmartPrice:

- guarda el codigo tal cual viene de Sybase
- busca en SQLite por ese mismo valor
- envia al verificador ese mismo valor

Eso deja al Android recibiendo un codigo incompleto para algunos clientes legacy.

## Decision tecnica inicial

Primera implementacion:

1. mantener `codigo_original`
2. calcular `codigo_normalizado` cuando el origen tenga `12` digitos numericos
3. usar algoritmo `EAN-13`
4. no reemplazar ciegamente todos los codigos legacy en memoria sin conservar el original

## Algoritmo inicial a soportar

### EAN-13

Entrada:
- `12` digitos numericos base

Salida:
- `13` digitos con digito verificador calculado

Casos directos:
- `13` digitos numericos: dejar como esta
- `12` digitos numericos: calcular check digit y completar

## Fases

### VPC-F4-001
Definir helper reutilizable de normalizacion

- funcion de calculo `EAN-13`
- pruebas unitarias minimas
- decision explicita sobre limites:
  - solo numerico
  - solo 12 -> 13
  - 13 queda igual

### VPC-F4-002
Persistencia local

- agregar columnas SQLite:
  - `CODIGO_ORIGINAL`
  - `CODIGO_NORMALIZADO`
- migracion segura por `ALTER TABLE`
- no perder compatibilidad con datos existentes

### VPC-F4-003
Sync y busqueda local

- al sincronizar:
  - guardar original
  - guardar normalizado
- al buscar/localizar producto:
  - fallback por `codigo_original`
  - fallback por `codigo_normalizado`

### VPC-F4-004
Envio a Android

- enviar `codigo` normalizado cuando exista
- evaluar agregar tambien:
  - `codigo_original`
- mantener compatibilidad con payload actual

## Riesgos

- un valor de `12` digitos puede no ser siempre base de `EAN-13`
- no mezclar esta fase con `UPC-A` sin evidencia de negocio
- no reusar el mismo campo `codigo` para dos semanticas distintas sin trazabilidad

## Regla operativa actual mientras no este implementado

Si el cliente usa base legacy de `12` digitos, hoy el problema sigue vigente:

- SQLite local queda con `12`
- Android recibe `12`

Hasta cerrar `VPC-F4`, no asumir correccion automatica en runtime.
