# Piloto Acerca de con Bootstack

## Alcance

El piloto implementa una vista informativa `Acerca de` sobre Bootstack `0.1.6` con la identidad verde y blanca de Inforhard. Es un entry point experimental y no reemplaza `main.py`.

No conecta SQLite, Sybase, dispositivos, multimedia ni servicios productivos. Tampoco modifica `config.json` durante una ejecucion de prueba.

## Feature flag

El flag persistente es `ui_bootstack_about` y su valor por defecto efectivo es `false` cuando no existe en la configuracion.

Para una prueba temporal, sin persistir el flag:

```powershell
.\.venv\Scripts\python.exe main_bootstack.py --about-pilot
```

Smoke test sin ejecutar el loop visual:

```powershell
.\.venv\Scripts\python.exe main_bootstack.py --smoke
```

Ejecutar `main_bootstack.py` sin flag ni argumento debe finalizar sin abrir una ventana e informar que el piloto esta desactivado.

## Rollback

El rollback consiste en mantener `ui_bootstack_about` ausente o en `false` y continuar iniciando SmartPrice con `main.py`. No hay datos ni contratos que revertir.

## Criterios de validacion

- el entry point productivo no cambia;
- el piloto apagado no abre UI;
- `--about-pilot` abre solamente `Acerca de`;
- se muestran version y usuario Windows reales en modo solo lectura;
- el tema usa verde institucional y superficies blancas;
- el smoke test construye y destruye el shell sin errores.
