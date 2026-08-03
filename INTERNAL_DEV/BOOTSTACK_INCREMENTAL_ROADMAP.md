# VPC-F2-005 - Estrategia incremental de migracion a Bootstack

Fecha: `2026-08-03`

## Principios

- una vista nueva no modifica contratos de red, SQL ni servicios;
- la identidad visual usa verde institucional como color primario y blanco como superficie principal; no se adopta la paleta azul predeterminada de Bootstack;
- los tonos secundarios, hover, seleccion, foco y estados deben derivarse de esa paleta manteniendo contraste accesible;
- UI legacy y Bootstack pueden convivir durante la transicion;
- cada vista tiene feature flag y rollback inmediato;
- version de Bootstack fijada y actualizada solo con regresion completa;
- ningun modulo compartido se edita sin lock Nico/Misa;
- el pipeline PyInstaller/Inno Setup actual se conserva inicialmente.

## Fase 0 - Base reproducible

Entregables:

- dependencia Bootstack fijada;
- prueba `bootstack doctor`;
- smoke test del POC;
- checklist de Windows, DPI y build.
- tema Bootstack inicial con verde institucional y blanco, validado en estados normal, hover, seleccion, foco y deshabilitado.

Criterio de salida: POC construye, abre/cierra y empaqueta sin afectar produccion.

Rollback: eliminar la dependencia y el POC aislado; impacto productivo nulo.

## Fase 1 - Shell paralelo

Crear un entry point experimental que reutilice permisos, servicios e instancia unica, pero no reemplace `main.py`. El shell debe abrir paginas placeholder y una vista Acerca de.

Dependencias: lock de `GUI_MAIN.py` solo si se extraen interfaces compartidas; coordinacion con Misael.

Criterio de salida: tray, cierre, reapertura, permisos, loader, DPI y sesiones distintas funcionan.

Rollback: seguir arrancando exclusivamente el entry point legacy.

## Fase 2 - Primera vista piloto

Migrar una tab simple de Configuracion o una vista informativa. El acceso se decide mediante feature flag persistente o argumento experimental.

Criterio de salida: paridad funcional, persistencia correcta, cero bypass de permisos y build validado.

Rollback: el flag vuelve a la vista ttkbootstrap.

## Fase 3 - Publicidad por zonas

Migrar biblioteca de imagenes y grupos. Mantener preview VLC y envio en ventanas legacy hasta probar wrappers y progreso.

Criterio de salida: storage interno, globales/grupos, seleccion y refresco multiusuario conservados.

Rollback: abrir `CONTENIDO_PUBLICIDAD.py` legacy con los mismos datos persistidos.

## Fase 4 - Productos por zonas

Migrar detalle y filtros antes de sustituir la tabla. Conectar `DataTable` mediante adaptador a DAOs existentes; no crear una segunda fuente de verdad.

Criterio de salida: busqueda, imagen, multiprecios, ofertas, novedades y seleccion coinciden con legacy sobre datasets reales.

Rollback: feature flag por vista; base de datos y servicios no cambian.

## Fase 5 - Integraciones complejas

Migrar discovery, progreso de envios, perfiles y dialogos restantes. Resolver wrapper VLC y compatibilidad de tray.

Criterio de salida: pruebas multiusuario, red lenta, cancelacion, cierre durante tarea y dispositivos offline.

Rollback: conservar ventanas legacy invocables desde el shell.

## Fase 6 - Corte productivo

Activar Bootstack por defecto solo despues de un ciclo estable. Mantener rollback a legacy durante al menos una version productiva y retirar codigo anterior por modulo, no en un unico cambio.

## Feature flags sugeridos

```text
ui_bootstack_shell
ui_bootstack_config_simple
ui_bootstack_publicidad_biblioteca
ui_bootstack_producto_detalle
ui_bootstack_producto_tabla
ui_bootstack_envios
```

Los flags deben tener default `false` hasta aprobar cada fase. No deben modificar contratos ni duplicar datos.

## Matriz de riesgos y mitigaciones

| Riesgo | Mitigacion | Rollback |
| --- | --- | --- |
| Cambio de API Bootstack | Version fija + adaptadores propios | Volver a version validada. |
| Congelamiento UI | Cola/after en hilo principal + pruebas con red lenta | Vista legacy. |
| Regresion de permisos | Construir paginas desde permisos efectivos + tests por perfil | Shell legacy. |
| Fallo de tray/instancia unica | POC obligatorio con dos sesiones/usuarios | Entry point legacy. |
| Preview multimedia roto | Mantener VLC legacy hasta wrapper validado | Ventana multimedia legacy. |
| Incompatibilidad PyInstaller | Conservar pipeline y probar artefacto por fase | Build anterior. |
| Colision entre desarrolladores | Locks en modulos compartidos y PRs acotados | Detener integracion, no reescribir trabajo ajeno. |
| Diferencias DPI/Windows Server | Checklist visual en entornos objetivo | Tema/vista legacy. |

## Primera implementacion recomendada

El primer piloto debe ser el shell experimental con Acerca de y placeholders, seguido de una tab de Configuracion de bajo riesgo. No comenzar por la tabla de Productos ni por preview multimedia.

## Decision final

La migracion puede continuar como programa incremental. El corte global queda condicionado a evidencia de estabilidad en shell, threading, permisos, tray, multimedia y build. Cada fase debe poder revertirse sin migrar ni transformar datos.
