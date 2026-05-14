# Locks

Este directorio existe para materializar bloqueos de trabajo cuando haga falta.

Formato sugerido de archivo:
- `LOCK_Misa_YYYYMMDD_HHMM.md`
- `LOCK_Nico_YYYYMMDD_HHMM.md`

Contenido minimo:

```md
# LOCK

- Dev: Misa|Nico
- Fecha: YYYY-MM-DD HH:MM
- Modulos:
  - ruta/modulo_1.py
  - ruta/modulo_2.py
- Motivo: cambio concreto
- ETA: 30m / 2h / 1 dia
- Estado: activo / liberado
```

Cuando el trabajo termina:
- actualizar `Estado: liberado`, o
- borrar el lock si el equipo prefiere limpieza inmediata.
