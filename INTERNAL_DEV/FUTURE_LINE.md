# Future Line

## Objetivo

Mantener compatibilidad con el sistema actual mientras se reduce el acoplamiento y se separan responsabilidades.

## Linea de refactor recomendada

### Etapa 1 - Estabilidad
- Terminar de blindar configuracion persistente.
- Seguir sacando logica de negocio de `GUI/`.
- Mantener logs consistentes y trazabilidad de envios.

### Etapa 2 - Servicios claros
- Consolidar `core/services/` como capa real.
- Introducir DAOs para productos, config, publicidades e historial.
- Reducir dependencia directa de `WidgetRegistry` en modulos de negocio.

### Etapa 3 - Publicidades maduras
- Biblioteca con IDs internos reales.
- Scheduler por grupo/horario.
- Envio incremental real de media.
- Estado de sincronizacion con Android por hashes.

### Etapa 4 - Contratos estables
- Versionar mejor el contrato Python-Android.
- Agregar compatibilidad declarativa por `api_version`.
- Separar endpoints legacy de endpoints optimizados.

### Etapa 5 - Mantenimiento a largo plazo
- Dividir `CONTENIDO_PRODUCTO.py` y `CONTENIDO_PUBLICIDAD.py`.
- Minimizar hilos manuales y centralizar workers.
- Mover mas datos de `config.json` a almacenamiento modelado cuando corresponda.

## Principios que no se negocian

- No romper clientes por refactor.
- No mezclar cambios de arquitectura con urgencias productivas.
- Siempre dejar fallback cuando cambie un contrato con Android.
- Documentar cada decision relevante en esta carpeta interna.
