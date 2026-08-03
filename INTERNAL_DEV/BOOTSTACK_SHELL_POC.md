# VPC-F2-003 - POC de shell principal con AppShell

Fecha: `2026-08-03`

Implementacion aislada: `INTERNAL_DEV/poc_bootstack_appshell.py`

Entry point experimental: `main_bootstack.py`

Dependencia reproducible: `requirements-bootstack.txt`

## Decision de navegacion

Se recomienda **sidebar simple**, no rail + workspaces.

SmartPrice tiene cuatro destinos principales de primer nivel: Productos, Publicidad, Configuracion y Acerca de. No existen hoy multiples workspaces que justifiquen un rail adicional. Agregar dos niveles de navegacion aumentaria complejidad y espacio ocupado sin mejorar el modelo mental del usuario.

Configuracion debe quedar fijada al pie del sidebar. Acerca de puede vivir en el menu de aplicacion o tambien al pie. Los permisos efectivos determinan que paginas se construyen: un usuario `pantalla` debe recibir solo Publicidad, sin crear paginas ocultas de Productos o Configuracion.

## Identidad visual requerida

- verde institucional como color primario;
- blanco como superficie principal;
- variantes de verde para hover, seleccion, foco y acciones destacadas;
- grises neutros solo como apoyo para bordes, texto secundario y estados deshabilitados;
- contraste legible en tema claro y, si se conserva modo oscuro, una adaptacion explicita de la misma identidad;
- no dejar el azul predeterminado de Bootstack en la version objetivo.

Antes de implementar el tema definitivo se debe tomar el color exacto desde los recursos de marca existentes o confirmar su codigo hexadecimal con el equipo.

La paleta fue confirmada en `GUI_MAIN.py` e incorporada al experimento:

- primario: `#149455`;
- hover: `#DDF4E7`;
- superficie verde suave: `#F3FBF6`;
- texto principal: `#173227`;
- fondo principal: `#FFFFFF`.

## Estructura propuesta

```text
AppShell
├── Toolbar: toggle sidebar | SmartPrice | tema/usuario
├── Sidebar
│   ├── Productos (si tiene permiso)
│   ├── Publicidad (si tiene permiso)
│   └── Configuracion (footer, si tiene permiso)
├── PageStack
│   └── Una vista activa por vez
└── StatusBar: conexion, sync y mensajes pasivos
```

## Que valida el POC

- construccion real de `AppShell` con Bootstack 0.1.6;
- toolbar, toggle del sidebar y selector de tema;
- statusbar;
- paginas creadas condicionalmente por permisos;
- pagina Acerca de aislada y fijada al pie del sidebar;
- lectura no mutante del usuario Windows, version y permisos actuales;
- paginas de negocio creadas solamente cuando el permiso correspondiente esta activo;
- placeholder de `DataTable` para Productos;
- placeholder de Cards para Publicidad;
- Tabs y campos para Configuracion;
- navegacion inicial a la primera pagina autorizada;
- aislamiento completo respecto del codigo productivo.

## Integraciones conservadas

- `pystray` sigue controlando mostrar/ocultar/cerrar;
- el socket local por usuario sigue fuera de la vista;
- DAOs, sync, discovery y envios siguen en servicios existentes;
- VLC permanece como preview legacy o wrapper;
- config y permisos mantienen su fuente actual.

## Riesgos pendientes del POC productivo

1. Conectar pystray al ciclo de vida real del shell.
2. Ejecutar bootstrap progresivo sin congelar la primera pintura.
3. Validar actualizaciones desde workers mediante cola y callback en el hilo UI.
4. Abrir/cerrar vistas legacy desde el shell sin crear multiples roots Tk.
5. Empaquetar con el script PyInstaller existente.
6. Validar DPI y sesiones Windows Server.

## Criterio de aceptacion

El smoke test local finalizo con `POC_SMOKE_OK` usando Python 3.12.10, Tcl/Tk 8.6 y Bootstack 0.1.6. El POC aislado es suficiente para aprobar el diseño de sidebar simple. No autoriza reemplazar `GUI_MAIN.py`: ese paso requiere lock compartido, pruebas de tray/instancia unica y rollback operativo.
