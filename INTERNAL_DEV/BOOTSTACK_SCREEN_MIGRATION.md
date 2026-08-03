# VPC-F2-004 - Migracion de pantallas de datos

Fecha: `2026-08-03`

## Productos

| Zona | Propuesta | Riesgo |
| --- | --- | --- |
| Tabla principal | `DataTable` conectado mediante adaptador al DAO | Alto: volumen, busqueda, IDs, seleccion y refresco incremental. |
| Busqueda/filtros | Busqueda de DataTable + campos externos cuando el filtro sea de negocio | Medio: evitar duplicar SQL y filtros en memoria. |
| Detalle de producto | `Card` + `Form`/campos read-only + `Picture` | Medio: preservar carga de imagen y multiprecios. |
| Fechas/novedades | `DateField`, `Window`, `ProgressBar` | Medio: locale, cancelacion y estado de sync. |
| Acciones de envio | `Toolbar`/botones + dialogs + statusbar | Alto: red y progreso desde threads. |

Migracion recomendada: tardia. Es una pantalla critica y acoplada a sync, SQLite y Sybase.

## Publicidad

| Zona | Propuesta | Riesgo |
| --- | --- | --- |
| Biblioteca de imagenes | `Gallery` o `Grid` de `Card` + `Picture` | Medio/alto: volumen, seleccion multiple y metadata. |
| Grupos/globales | `Tabs` o `Select` + cards | Medio: refresco desde config compartida. |
| Acciones por item | `ContextMenu`, `MenuButton`, toolbar | Medio. |
| Preview imagen | `Picture` | Bajo. |
| Preview video/audio | VLC legacy en wrapper o ventana separada | Alto: no hay reemplazo nativo confirmado. |
| Progreso de envio | `Window` + `ProgressBar`/`StatusBar` | Alto: multipantalla y callbacks. |

Migracion recomendada: intermedia por partes. Empezar por biblioteca solo de imagenes o panel de grupos; dejar VLC y envio en vistas legacy.

## Configuracion

| Zona | Propuesta | Riesgo |
| --- | --- | --- |
| Secciones | `Tabs` | Bajo/medio. |
| Campos | `Form`, `TextField`, `PasswordField`, `NumberField`, `PathField`, `Select`, `Switch` | Bajo/medio. |
| Perfiles | `DataTable` + formulario | Alto: permisos y usuarios Windows. |
| Dispositivos | `DataTable` + dialogs | Alto: discovery en segundo plano. |
| Logo | `PathField` + `Picture` | Medio: conservar normalizacion tecnica. |
| Progreso | `ProgressBar`, toast/notification | Medio/alto. |

Migracion recomendada: temprana por una tab de bajo riesgo, no por la ventana completa. Una tab informativa o de campos sin discovery es la mejor candidata funcional.

## Shell y Acerca de

El shell aislado y una pagina Acerca de son los candidatos de menor riesgo. Permiten validar tema, layout, navegacion, DPI y empaquetado sin conectar bases ni red.

## Orden sugerido

1. POC aislado de shell y pagina Acerca de.
2. Una tab simple de Configuracion en modo lectura/escritura controlada.
3. Biblioteca de Publicidad solo para imagenes, manteniendo acciones legacy.
4. Resto de Configuracion, excepto discovery/perfiles.
5. Publicidad con grupos y envio; VLC permanece legacy hasta tener wrapper estable.
6. Productos: detalle primero y tabla principal despues.
7. Discovery, progreso complejo, perfiles y flujos de envio como cierre.

## Criterios de avance

- misma funcionalidad observable que la vista anterior;
- UI nunca actualizada desde un worker;
- permisos verificados por usuario Windows;
- rollback mediante selector/feature flag por vista;
- build instalable probado en Windows objetivo;
- sin cambios simultaneos de contrato Android, SQL o negocio.

## Resultado

Bootstack cubre los widgets necesarios, pero Productos y Publicidad no deben migrarse como bloques completos. La estrategia correcta es convivencia temporal y reemplazo por zonas con rollback.
