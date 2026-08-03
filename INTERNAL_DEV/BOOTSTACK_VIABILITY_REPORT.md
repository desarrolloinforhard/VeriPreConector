# VPC-F2-001 - Viabilidad de migracion UI a Bootstack

Fecha de evaluacion: `2026-08-03`

Responsable: `Nicolas Gomez`

Version evaluada: `bootstack 0.1.6`

## Conclusion ejecutiva

**Resultado: viable con restricciones para una migracion incremental; no recomendable como reescritura productiva inmediata.**

Bootstack encaja con la base tecnica del proyecto porque sigue usando Tk, requiere Python 3.12 o superior y ofrece componentes de alto nivel para shell, navegacion, tablas, formularios, layouts y feedback visual. La prueba local sobre el entorno de VeriPre_Connector fue satisfactoria: Python 3.12.10, Tcl/Tk 8.6 y Bootstack 0.1.6 fueron reconocidos correctamente por `bootstack doctor`.

La adopcion no debe ser global todavia. Bootstack esta en la serie `0.x`, tiene una API distinta de Tk/ttkbootstrap y no se verifico un reemplazo nativo para preview de video ni para bandeja del sistema. Los flujos sensibles de threading, loader, instancia unica, permisos y multimedia necesitan POC y adaptadores antes de tocar produccion.

## Evidencia revisada

- La [documentacion oficial](https://bootstack.org/) describe Bootstack como una capa declarativa y reactiva construida sobre Tk, con mas de 60 widgets y herramientas de empaquetado.
- La [guia oficial de instalacion](https://bootstack.org/getting-started/installation.html) exige Python 3.12+ y Tk/Tcl. El proyecto local cumple ambos requisitos.
- La [API oficial de DataTable](https://bootstack.org/api-reference/generated/bootstack.DataTable.html) incluye busqueda, filtros, orden, seleccion, paginacion, exportacion y fuentes de datos configurables.
- `AppShell`, `PageStack`, `Toolbar` y `StatusBar` estan disponibles para modelar la navegacion principal. La barra de herramientas incluye soporte documentado para alternar el sidebar.
- `Picture` soporta imagenes redimensionables y GIF/WebP animados, segun la [API oficial de Picture](https://bootstack.org/api-reference/generated/bootstack.Picture.html).
- La instalacion local fijada en `bootstack==0.1.6` paso `bootstack doctor` y la comprobacion de imports.

## Encaje con VeriPre_Connector

| Necesidad actual | Cobertura Bootstack | Evaluacion inicial |
| --- | --- | --- |
| Shell y menu lateral | `AppShell`, `PageStack`, `Toolbar`, `StatusBar` | Directa para un POC; falta integrar permisos, instancia unica y tray. |
| Tabla de productos | `DataTable` | Buena cobertura funcional inicial; hay que validar volumen, seleccion, eventos e integracion con el DAO existente. |
| Formularios y configuracion | `Form`, `Tabs`, campos tipados, `PathField` | Cobertura alta; requiere adaptar validaciones y callbacks actuales. |
| Grid de publicidades | `Card`, `Grid`, `ScrollView`, `Picture`, `Gallery` | Cobertura parcial/alta para imagenes; necesita prueba con colecciones grandes. |
| Dialogos | `alert`, `confirm`, dialogs especializados | Existe cobertura, pero no mediante una clase raiz `Dialog`; requiere mapear cada uso actual. |
| Avisos no bloqueantes | `toast`, `Notification`, `Snackbar` | Cobertura disponible. |
| Progreso y estados | `ProgressBar`, `Gauge`, `StatusBar` | Cobertura disponible; debe validarse el retorno seguro al hilo UI. |
| Loader de inicio | `Splash` y componentes de progreso | Posible reemplazo, pendiente de POC con el bootstrap real. |
| Preview de imagen | `Picture`, `Gallery` | Cobertura directa para imagen y animacion soportada. |
| Preview de video/audio | No se encontro un widget nativo equivalente a VLC | Gap: mantener `python-vlc` mediante adaptador o vista legacy. |
| Bandeja del sistema | No se encontro integracion equivalente a `pystray` | Gap: mantener `pystray` y validar ciclo de vida con `AppShell`. |
| Mensajes/file dialogs Tk existentes | Hay alternativas Bootstack | Puede mantenerse convivencia temporal para reducir riesgo. |

## Riesgos y bloqueos

### 1. Madurez y estabilidad de API

La version evaluada es `0.1.6`. Aunque ya no aparece como una build alfa, sigue siendo una version `0.x`, por lo que no conviene acoplar toda la aplicacion sin fijar version y sin una capa de adaptacion.

Mitigacion:

- fijar la version exacta durante cada POC;
- encapsular Bootstack detras de vistas/adaptadores propios;
- actualizar solo con pruebas de regresion visual y funcional.

### 2. Modelo de UI diferente

Bootstack propone layouts declarativos, signals y una API propia. No es un cambio de tema sobre ttkbootstrap: migrar implica reescribir la construccion visual y parte del cableado de eventos.

Mitigacion:

- no mezclar la migracion con refactors de negocio;
- mantener DAOs y servicios actuales fuera de las vistas nuevas;
- migrar una vista piloto aislada antes del shell productivo.

### 3. Threading y ciclo de vida

VeriPre_Connector usa threads y llamadas `after(...)` para volver al hilo de Tk. Bootstack conserva Tk como runtime, pero debe comprobarse el mecanismo soportado para actualizar estado desde tareas de red y sincronizacion.

Mitigacion:

- crear una prueba con trabajo en segundo plano, cancelacion, progreso y cierre;
- no actualizar widgets desde hilos secundarios;
- conservar los servicios actuales y adaptar solo la entrega de eventos a UI.

### 4. Multimedia

`Picture` cubre imagenes y animaciones, pero no reemplaza el preview actual basado en VLC para video/audio.

Mitigacion:

- mantener la vista VLC existente inicialmente;
- probar un wrapper que inserte el handle nativo de VLC en un contenedor controlado;
- no elegir Publicidad como primera migracion completa.

### 5. Tray, instancia unica y permisos

La bandeja con pystray, el socket local por usuario y los permisos forman parte del arranque actual, no solo de la apariencia.

Mitigacion:

- preservar esos servicios durante el POC;
- comprobar mostrar/ocultar/cerrar `AppShell` desde pystray;
- construir la navegacion desde los permisos efectivos, sin ocultarla solo de forma cosmetica.

### 6. Empaquetado

Bootstack ofrece CLI de build, pero VeriPre_Connector ya posee PyInstaller, hooks, VLC e Inno Setup propios. Cambiar el pipeline en la misma fase agregaria riesgo innecesario.

Mitigacion:

- conservar inicialmente `scripts/build_and_package.ps1`;
- agregar Bootstack al build existente durante el POC;
- validar recursos, temas, iconos, VLC y ejecucion en Windows objetivo antes de evaluar el CLI propio.

## Componentes criticos

### Soportados o con equivalente claro

- shell con sidebar y paginas;
- toolbar y statusbar;
- tablas, arboles y listas;
- tabs, formularios y campos tipados;
- cards, grids y scroll;
- dialogos, confirmaciones y notificaciones;
- progreso y estados;
- imagenes y galerias;
- temas claros/oscuros;
- almacenamiento de preferencias e internacionalizacion.

### Sin reemplazo directo confirmado

- preview VLC de video/audio;
- bandeja del sistema con pystray;
- protocolo de instancia unica por usuario;
- compatibilidad exacta con todos los eventos y extensiones actuales de `ttkbootstrap.Tableview`/`Treeview`;
- integracion con el pipeline de build personalizado y sus recursos nativos.

## Recomendacion

Continuar con `VPC-F2-002` y construir la matriz completa de widgets. Luego realizar `VPC-F2-003` como POC separado, sin reemplazar `GUI/GUI_MAIN.py`, con estas pruebas minimas:

1. `AppShell` con paginas condicionadas por permisos.
2. Mostrar/ocultar ventana desde pystray.
3. Tarea en segundo plano con progreso y retorno seguro al hilo UI.
4. Vista legacy embebida o abierta desde el shell.
5. Build PyInstaller usando el pipeline actual.
6. Cierre limpio de ventana, threads, socket local y bandeja.

No usar `GUI/CONTENIDO_PUBLICIDAD.py` como primer piloto completo por su dependencia de VLC y su complejidad de media. Una vista documental o un shell aislado ofrecen una validacion inicial de menor riesgo.

## Decision de fase

- `VPC-F2-001`: **viable con restricciones**.
- Autorizar analisis y POC aislado: **si**.
- Autorizar migracion productiva global: **no**.
- Proximo paso: `VPC-F2-002`, matriz de reemplazo de widgets.
