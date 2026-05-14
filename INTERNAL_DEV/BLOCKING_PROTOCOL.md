# Blocking Protocol

Este protocolo es obligatorio para evitar que Misa y Nico se pisen.

## 1. Regla general

Nadie edita un modulo compartido sin lock previo.

## 2. Modulos con lock obligatorio siempre

- `main.py`
- `GUI/GUI_MAIN.py`
- `GUI/GUI_CONFIG.py`
- `FUNC/config_json.py`
- `FUNC/create_widget.py`
- `DB/database.py`
- `DB/database_sybase.py`
- `core/network/*`
- `core/services/dispositivos_envio_service.py`
- `versionado/*`

## 3. Como tomar lock

Crear o actualizar una entrada en este formato dentro del commit de trabajo o en el canal interno:

```text
LOCK:
- Dev: Misa|Nico
- Fecha: YYYY-MM-DD HH:MM
- Modulos: ruta1, ruta2, ruta3
- Motivo: cambio corto y concreto
- ETA: 30m / 2h / 1 dia
```

## 4. Regla de bloqueo duro

Si Misa tiene lock sobre un archivo compartido:
- Nico no lo toca.
- Nico no hace refactor parcial “mientras tanto”.
- Nico no resuelve conflictos reescribiendo el archivo.

Lo mismo a la inversa.

## 5. Ownership sin lock

Si el modulo pertenece claramente al otro desarrollador, pedir traspaso antes de tocar.

## 6. Excepciones

Solo se rompe este protocolo si:
- hay caida productiva,
- el owner no responde,
- el cambio es de emergencia,
- y luego se deja documentado el motivo.
