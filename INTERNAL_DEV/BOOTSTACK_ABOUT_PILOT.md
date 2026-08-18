# Piloto Acerca de con Bootstack

## Alcance

El piloto implementa una vista informativa `Acerca de` sobre Bootstack `0.1.6` con la identidad verde y blanca de Inforhard. Es un entry point experimental y no reemplaza `main.py`.

No conecta SQLite, Sybase, dispositivos, multimedia ni servicios productivos. Tampoco modifica `config.json` durante una ejecucion de prueba.

## Feature flag

El flag persistente es `ui_bootstack_about` y su valor por defecto efectivo es `false` cuando no existe en la configuracion.

La pagina informativa de Configuracion usa `ui_bootstack_config_simple`, tambien con valor efectivo `false` cuando el flag no existe.

La primera escritura controlada usa `ui_bootstack_config_sync_write`, apagado por defecto e independiente del flag de lectura.

Para una prueba temporal, sin persistir el flag:

```powershell
.\.venv\Scripts\python.exe main_bootstack.py --about-pilot
```

Para probar Acerca de y Configuracion sin persistir flags:

```powershell
.\.venv\Scripts\python.exe main_bootstack.py --about-pilot --config-pilot
```

La pagina Configuracion muestra version, usuario, sincronizacion automatica y permisos efectivos. No lee ni modifica DSN, credenciales, API keys o dispositivos y no presenta acciones de guardado.

Para habilitar temporalmente solo la escritura de sincronizacion automatica:

```powershell
.\.venv\Scripts\python.exe main_bootstack.py --config-write-pilot
```

Al desactivar la sincronizacion tambien se desactiva `envio_automatico_novedades`, igual que en la pantalla productiva. El cambio se guarda atomicamente bajo el lock existente y se aplica a SmartPrice productivo en el siguiente inicio.

Smoke test sin ejecutar el loop visual:

```powershell
.\.venv\Scripts\python.exe main_bootstack.py --smoke
```

## Build experimental de 64 bits

El ejecutable se construye en un pipeline separado y no modifica el build ni el instalador productivos:

```powershell
.\scripts\build_bootstack_about.ps1 -Clean
```

Salida esperada:

```text
dist\bootstack-about\SmartPrice-Bootstack-About.exe
```

El ejecutable abre directamente el piloto al hacer doble clic. Su smoke test es:

```powershell
.\dist\bootstack-about\SmartPrice-Bootstack-About.exe --smoke
```

Para activar temporalmente Configuracion en el ejecutable:

```powershell
.\dist\bootstack-about\SmartPrice-Bootstack-About.exe --config-pilot
```

Escritura controlada desde el ejecutable:

```powershell
.\dist\bootstack-about\SmartPrice-Bootstack-About.exe --config-write-pilot
```

Este artefacto es Windows x64. No conecta Sybase, SQLite, VLC, red ni servicios productivos y no se integra a `Script_SmartPrice.iss`.

Ejecutar `main_bootstack.py` sin flag ni argumento debe finalizar sin abrir una ventana e informar que el piloto esta desactivado.

## Rollback

El rollback consiste en mantener `ui_bootstack_about` ausente o en `false` y continuar iniciando SmartPrice con `main.py`. No hay datos ni contratos que revertir.

## Criterios de validacion

- el entry point productivo no cambia;
- el piloto apagado no abre UI;
- `--about-pilot` abre solamente `Acerca de`;
- `--config-pilot` agrega Configuracion solo para usuarios con permiso efectivo;
- Configuracion no ofrece escrituras ni muestra datos sensibles;
- la escritura requiere `--config-write-pilot` o su feature flag especifico;
- un error de persistencia restaura visualmente el valor anterior;
- se muestran version y usuario Windows reales en modo solo lectura;
- el tema usa verde institucional y superficies blancas;
- el smoke test construye y destruye el shell sin errores.
