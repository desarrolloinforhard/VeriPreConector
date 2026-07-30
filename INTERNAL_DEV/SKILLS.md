# Skills Operativos del Proyecto

## 1. Skills tecnicos obligatorios

### UI Tkinter / ttkbootstrap
- Nunca actualizar widgets directamente desde un hilo secundario.
- Usar `after(...)` para volver al hilo de UI.
- Mantener tamaños estables en grids/tablas/previews.

### SQLite / Persistencia
- Asumir que SQLite puede recibir lecturas/escrituras desde distintas zonas del programa.
- Minimizar escrituras innecesarias y preferir guardado atomico.
- No introducir nuevas rutas relativas para datos persistentes.

### Sybase / Sync
- No mezclar SQL Sybase dentro de componentes visuales nuevos.
- Toda logica de sync nueva debe ir hacia `core/services/`.

### Android API / Envios
- Mantener backward compatibility cuando se agregan endpoints.
- Siempre contemplar fallback para APKs viejos.
- Si se cambia payload, documentarlo tambien en `PROJECT_CONTEXT.md`.

### Imagenes
- Del lado Python: productos solo desde SQLite/carpetas locales.
- Del lado Android: puede resolver API local y GO-UPC al escanear.
- Si GO-UPC devuelve imagen nueva, cachearla y propagarla donde corresponda.

### Publicidades
- Toda publicidad nueva debe vivir en storage interno, no en rutas prestadas del usuario.
- Mantener metadata por archivo: hash, estado, duracion, tamaño, ultimo envio.
- No perder la distincion entre grupo activo y publicidades globales.

## 2. Skills de colaboracion

- Antes de tocar un modulo compartido, tomar lock obligatorio.
- No mezclar refactorizacion estructural con cambios funcionales urgentes.
- Documentar contratos nuevos apenas se estabilizan.
- Si un cambio toca Python y Android, definir primero el contrato.

## 3. Skills de criterio

- Priorizar estabilidad del cliente por encima de elegancia interna.
- Si algo se rompe con usuarios distintos de Windows, revisar primero rutas, permisos y DPI.
- Si una mejora requiere API Android nueva, dejar fallback del lado Python hasta migracion completa.
