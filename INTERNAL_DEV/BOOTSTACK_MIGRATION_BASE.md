# Bootstack Migration Base

Base de arranque para la fase `VPC-F2` orientada a evaluar una posible migracion de la UI de `VeriPre_Connector` hacia `Bootstack`.

Estado documental: `piloto`

Fecha base: `2026-07-28`

## 1. Objetivo de esta fase

No migrar la aplicacion todavia.

El objetivo es responder con evidencia:
- si `Bootstack` es viable para este proyecto,
- que widgets actuales se pueden reemplazar de forma directa,
- que partes requeriran wrappers o convivencia temporal,
- y como migrar sin romper produccion.

## 2. Hechos confirmados

- La UI actual mezcla `tkinter`, `ttkbootstrap` y algunos componentes auxiliares/custom.
- La app tiene modulos grandes y sensibles:
  - `GUI/GUI_MAIN.py`
  - `GUI/CONTENIDO_PRODUCTO.py`
  - `GUI/CONTENIDO_PUBLICIDAD.py`
  - `GUI/GUI_CONFIG.py`
- El sistema tiene dependencias funcionales que no deben degradarse durante una migracion visual:
  - bandeja del sistema,
  - bootstrap con loader,
  - permisos por usuario Windows,
  - instancia unica por usuario,
  - pantallas con datos,
  - envios HTTP y progreso,
  - preview de multimedia.
- La documentacion oficial de Bootstack indica que el proyecto esta en `pre-release` y que la API puede cambiar antes de `1.0`.
- `AppShell` ya trae:
  - sidebar expandido / compacto / oculto,
  - rail por workspaces,
  - toolbar superior,
  - statusbar,
  - paginas navegables.

## 3. Hipotesis de trabajo

### Hipotesis A

`GUI_MAIN.py` podria simplificarse bastante con `AppShell`, especialmente en:
- sidebar,
- footer de navegacion,
- barra de estado,
- contenedor principal de secciones.

### Hipotesis B

Las pantallas de datos no deben migrarse todas juntas.

Lo mas probable es que convenga:
1. migrar primero el shell general,
2. luego una pantalla de menor riesgo,
3. y dejar convivencia temporal entre vistas legacy y vistas Bootstack.

### Hipotesis C

No todos los widgets actuales tendran reemplazo 1:1.

Puntos con riesgo:
- tablas con comportamiento custom,
- overlays/progreso,
- preview multimedia,
- integracion con bandeja,
- dialogs ya mezclados con flujo legacy.

## 4. Correspondencia inicial a validar

Esta tabla es una propuesta preliminar. Debe ser validada en `VPC-F2-002`.

| Zona actual | Archivo actual | Widget/patron Bootstack sugerido | Estado |
| --- | --- | --- | --- |
| Shell principal | `GUI/GUI_MAIN.py` | `AppShell` | inferencia |
| Menu lateral | `GUI/GUI_MAIN.py` | `AppShell` sidebar / footer pages | inferencia |
| Navegacion entre modulos | `GUI/GUI_MAIN.py` | `PageStack` o `AppShell.add_page()` | inferencia |
| Barra superior / acciones | `GUI/GUI_MAIN.py` | `Toolbar` | inferencia |
| Estado general / mensajes pasivos | `GUI/GUI_MAIN.py` | `StatusBar` | inferencia |
| Tabla de productos | `GUI/CONTENIDO_PRODUCTO.py` | `DataTable` | inferencia |
| Formularios de configuracion | `GUI/GUI_CONFIG.py` | `Form`, `TextField`, `Select`, `Switch`, `Tabs` | inferencia |
| Grid/publicidades | `GUI/CONTENIDO_PUBLICIDAD.py` | `Card`, `Grid`, `ScrollView`, `Picture`, `Gallery` | inferencia |
| Progreso y estados de envio | varios | `ProgressBar`, `Dialog`, `Toast` | inferencia |
| Mensajes de confirmacion | varios | `Message Dialogs` / `Input Dialogs` | inferencia |

## 5. Riesgos iniciales

### Riesgo 1: dependencia de una libreria en pre-release

Impacto:
- cambios de API,
- widgets incompletos,
- necesidad de adaptar codigo mas de una vez.

Mitigacion:
- no migrar produccion sin POC,
- aislar wrappers,
- empezar por shell y pantalla piloto.

### Riesgo 2: mezcla UI + logica de negocio

Impacto:
- migrar la vista puede arrastrar cambios funcionales no deseados.

Mitigacion:
- separar tareas de evaluacion visual de tareas de refactor funcional,
- no reescribir sync/envios durante la fase de investigacion.

### Riesgo 3: regresiones en threading / bootstrap / bandeja

Impacto:
- bloqueos al iniciar,
- ventanas congeladas,
- comportamientos raros en multiusuario.

Mitigacion:
- mantener primero la arquitectura de arranque,
- validar `AppShell` sin tocar la logica de instancia, tray y loaders hasta tener una base estable.

### Riesgo 4: tablas y multimedia

Impacto:
- `Productos` y `Publicidad` son los modulos mas exigentes visualmente.

Mitigacion:
- no definir la migracion solo por estetica,
- comprobar si `DataTable`, `Card`, `Grid`, `ScrollView`, `Dialog` y `Picture/Gallery` cubren lo necesario.

## 6. Tareas ClickUp abiertas para esta fase

- `VPC-F2-001` - Viabilidad general Bootstack
  ClickUp: `86e2hfey7`
- `VPC-F2-002` - Matriz de reemplazo de widgets
  ClickUp: `86e2hff25`
- `VPC-F2-003` - POC de shell con `AppShell`
  ClickUp: `86e2hff8k`
- `VPC-F2-004` - Migracion de pantallas de datos a widgets Bootstack
  ClickUp: `86e2hffd1`
- `VPC-F2-005` - Estrategia incremental sin romper produccion
  ClickUp: `86e2hffgr`

Responsable acordado para esta linea: `Nicolas Gomez`

## 7. Orden de trabajo recomendado

1. `VPC-F2-001`
   Confirmar si seguir vale la pena.
2. `VPC-F2-002`
   Mapear widgets reales del proyecto contra Bootstack.
3. `VPC-F2-003`
   Disenar un shell tecnico realista con `AppShell`.
4. `VPC-F2-004`
   Determinar que pantallas migran primero y con que widgets.
5. `VPC-F2-005`
   Cerrar roadmap incremental y criterios de corte.

## 8. Recomendacion tecnica actual

No hacer una migracion global inmediata.

La recomendacion actual es:
- evaluar,
- mapear,
- hacer POC del shell,
- elegir una vista piloto,
- y recien despues decidir si Bootstack pasa a ser `objetivo` real o queda solo como `piloto`.

## 9. Primer entregable esperado para Nicolas

Para `VPC-F2-001`, el primer entregable esperado deberia responder:

1. Que partes de SmartPrice encajan natural con `AppShell`.
2. Que widgets de Bootstack cubren `Productos`, `Publicidad` y `Configuracion`.
3. Que gaps aparecen contra la implementacion actual.
4. Si conviene migrar ahora o esperar mas madurez de la libreria.
