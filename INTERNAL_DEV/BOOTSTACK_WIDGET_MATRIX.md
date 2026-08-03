# VPC-F2-002 - Matriz de reemplazo de widgets por Bootstack

Fecha: `2026-08-03`

Insumos: codigo actual de `GUI_MAIN.py`, `CONTENIDO_PRODUCTO.py`, `CONTENIDO_PUBLICIDAD.py` y `GUI_CONFIG.py`; Bootstack `0.1.6`.

Escala de dificultad: baja, media, alta.

| Componente actual | Archivo origen | Uso actual | Reemplazo Bootstack | Tipo | Dificultad | Notas / gaps |
| --- | --- | --- | --- | --- | --- | --- |
| `ttk.Window` + frames de navegacion | `GUI_MAIN.py` | Ventana raiz y cambio entre secciones | `AppShell` + `PageStack`/`page_nav` | Compuesto | Alta | El layout encaja, pero deben preservarse instancia unica, permisos, bootstrap y tray. |
| Frames de menu lateral | `GUI_MAIN.py` | Productos, Publicidad, Configuracion y Acerca de | Sidebar de `AppShell` | Directo | Media | Crear paginas solo para permisos efectivos; no limitarse a deshabilitar botones. |
| Botones de menu | `GUI_MAIN.py` | Navegacion y acciones principales | Items de `page_nav`; `Toolbar` para comandos | Directo | Baja | `Toolbar.add_sidebar_toggle()` cubre expandir/contraer. |
| Labels/frames de cabecera y estado | `GUI_MAIN.py` | Branding, usuario y estado | `Toolbar`, `StatusBar`, `Label`, `Card` | Compuesto | Baja | Separar estado pasivo de acciones. |
| `CTkLoader` | `GUI_MAIN.py` | Feedback durante bootstrap pesado | `Splash`, `ProgressBar`, `Notification` | Compuesto | Alta | Validar que el shell pinte antes del trabajo pesado y que los callbacks vuelvan al hilo UI. |
| `pystray` | `GUI_MAIN.py` | Ocultar, mostrar y cerrar | Sin reemplazo nativo confirmado | Wrapper legacy | Alta | Mantener pystray y adaptar show/hide/close de `AppShell`. |
| `tk.Canvas` | `GUI_MAIN.py` | Elementos visuales custom | `Canvas` si la API publica cubre el caso, o widget Tk encapsulado | Wrapper | Media | Revisar cada dibujo; no migrar automaticamente. |
| `messagebox` | Todos | Alertas, confirmaciones y errores | `alert`, `confirm`, dialogs especializados | Directo | Baja | La API es funcional; no existe una clase raiz `Dialog` exportada. |
| `Tableview` | `CONTENIDO_PRODUCTO.py` | Tabla principal con busqueda/seleccion | `DataTable` | Directo/compuesto | Alta | Validar volumen real, IDs, seleccion, paginado, callbacks y actualizacion incremental. |
| `ttk.Treeview` | Productos/Config/Publicidad | Multiprecios, perfiles, dispositivos y listados | `DataTable` o `Tree` | Directo | Media | Elegir `Tree` solo si existe jerarquia; para filas tabulares usar `DataTable`. |
| `DateEntry` | `CONTENIDO_PRODUCTO.py` | Filtros por fecha | `DateField` | Directo | Baja | Validar locale y formato argentino. |
| `Entry` | Productos/Config | Busqueda y edicion | `TextField`, `NumberField`, `PasswordField` | Directo | Baja | El tipo debe reflejar validaciones actuales. |
| `Combobox` | Config/Publicidad | Seleccion de dispositivo, grupo y opciones | `Select` | Directo | Baja | Verificar refresco de opciones descubiertas dinamicamente. |
| `Checkbutton`/`BooleanVar` | Config/Publicidad | Toggles y seleccion | `Checkbox`, `Switch`, signals | Directo | Baja | Reemplazar variables Tk por estado/signal solo dentro de vistas migradas. |
| `Notebook` | `GUI_CONFIG.py` | Secciones de configuracion | `Tabs` | Directo | Media | Buena candidata para migracion por tab, manteniendo tabs legacy temporalmente. |
| `Text` | `GUI_CONFIG.py` | Texto multilinea | `TextArea` o `CodeEditor` | Directo | Baja | Usar `CodeEditor` solo para contenido tecnico. |
| `Toplevel` | Todos | Dialogos, detalle, progreso y selectores | `Window`, dialogs y `FormDialog` | Compuesto | Media | Clasificar primero modal/no modal y ciclo de vida. |
| `Progressbar`/`Floodgauge` | Productos/Config/red | Progreso determinado/indeterminado | `ProgressBar`, `Gauge`, `StatusBar` | Directo | Media | Mantener cola/after o mecanismo equivalente para workers. |
| `ScrolledFrame` | Publicidad/red | Contenido vertical dinamico | `ScrollView` | Directo | Media | Probar rendimiento con muchos items y previews. |
| Canvas + labels de miniaturas | `CONTENIDO_PUBLICIDAD.py` | Grid de media | `Gallery`, `Grid`, `Card`, `Picture` | Compuesto | Alta | `Gallery` cubre imagen; metadata/acciones por item pueden requerir cards propias. |
| `PIL.ImageTk` | Productos/Publicidad | Preview y escalado | `Picture` + `bootstack.images.Image` | Directo | Media | Picture soporta imagen y GIF/WebP; conservar pipeline de normalizacion existente. |
| `python-vlc` embebido | `CONTENIDO_PUBLICIDAD.py` | Preview video/audio | Sin reemplazo nativo confirmado | Wrapper legacy | Alta | Mantener VLC; evaluar embedding en contenedor nativo controlado. |
| `Listbox` | `CONTENIDO_PUBLICIDAD.py` | Selecciones/listas auxiliares | `ListView` | Directo | Baja | Validar seleccion multiple. |
| `Menu` contextual | `CONTENIDO_PUBLICIDAD.py` | Acciones por item | `ContextMenu`/`MenuButton` | Directo | Media | Verificar posicionamiento sobre tiles dinamicos. |
| `LabelFrame` | Config/Publicidad | Agrupacion visual | `GroupBox` o `Card` | Directo | Baja | `GroupBox` preserva semantica de titulo. |
| Scrollbar manual | Varias | Scroll de trees/canvas | Integrada en `DataTable`, `Tree`, `ScrollView`, `Gallery` | Directo | Baja | Evita cableado manual. |

## Widgets que requieren adaptacion propia

1. Puente `AppShell` ↔ pystray y protocolo de instancia unica.
2. Host para preview VLC dentro de una vista Bootstack o apertura de vista legacy.
3. Adaptador de tareas en segundo plano que entregue resultados al hilo Tk.
4. Adaptador de datos entre DAOs/servicios y `DataTable`, sin duplicar SQLite.
5. Navegacion construida a partir de permisos efectivos por usuario Windows.
6. Compatibilidad temporal para abrir Toplevels y messageboxes legacy.
7. Integracion de Bootstack con el PyInstaller/Inno Setup existente.

## Resultado

La cobertura visual es suficiente para continuar. Los gaps no estan en controles basicos sino en integraciones de aplicacion: multimedia, tray, threading, permisos y empaquetado. La matriz respalda un POC aislado de shell antes de migrar pantallas.
