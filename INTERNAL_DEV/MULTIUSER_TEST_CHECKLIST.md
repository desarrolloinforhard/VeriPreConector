# Multiuser Test Checklist

Checklist operativo para validar SmartPrice / VeriPre_Connector en escenario multiusuario sobre la misma instalacion y la misma base local.

Contexto esperado:
- Version objetivo: `1.16.16` o superior.
- Misma instalacion compartida entre usuarios Windows.
- Misma base SQLite compartida por la app.
- Perfiles iniciales:
  - `administrador`: acceso completo
  - `pantalla`: solo `Publicidad`

## 1. Apertura por usuario

- [ ] Abrir SmartPrice con `Administrador`
- [ ] Confirmar que abre normal
- [ ] Confirmar que aparece icono en su bandeja
- [ ] Abrir SmartPrice con `Pantalla`
- [ ] Confirmar que tambien abre normal
- [ ] Confirmar que aparece icono en la bandeja de `Pantalla`
- [ ] Volver a ejecutar SmartPrice una segunda vez en `Pantalla`
- [ ] Confirmar que muestra mensaje de app ya abierta para ese mismo usuario

## 2. Menu visible por permisos

- [ ] En `Administrador`, verificar que se vea `Productos`
- [ ] En `Administrador`, verificar que se vea `Publicidad`
- [ ] En `Administrador`, verificar que se vea `Configuracion`
- [ ] En `Pantalla`, verificar que se vea `Publicidad`
- [ ] En `Pantalla`, verificar que NO se vea `Productos`
- [ ] En `Pantalla`, verificar que NO se vea `Configuracion`

## 3. Bloqueo de accesos

- [ ] En `Pantalla`, intentar entrar a `Productos` por navegacion o estado raro
- [ ] Confirmar que no entra
- [ ] En `Pantalla`, intentar abrir `Configuracion`
- [ ] Confirmar que no abre
- [ ] Confirmar que muestra `Acceso restringido` si corresponde

## 4. Gestion de permisos desde Administrador

- [ ] Abrir `Configuracion > Usuarios y Permisos`
- [ ] Verificar usuario actual mostrado correctamente
- [ ] Verificar tabla de perfiles cargada
- [ ] Seleccionar perfil `pantalla`
- [ ] Verificar checkboxes correctos
- [ ] Crear un perfil nuevo de prueba
- [ ] Guardar permisos del perfil nuevo
- [ ] Intentar dejar un perfil sin ningun modulo
- [ ] Confirmar que no lo permite
- [ ] Intentar quitarle `Configuracion` al propio admin actual
- [ ] Confirmar que no lo permite

## 5. Persistencia de permisos

- [ ] Cambiar permisos de `pantalla`
- [ ] Guardar cambios
- [ ] Cerrar SmartPrice en `Pantalla`
- [ ] Volver a abrir SmartPrice en `Pantalla`
- [ ] Confirmar que toma los permisos nuevos

## 6. Uso simultaneo con misma base

- [ ] Con `Administrador`, hacer un cambio en datos o publicidad
- [ ] Con `Pantalla`, abrir `Publicidad`
- [ ] Confirmar que ve los cambios
- [ ] Usar ambos usuarios al mismo tiempo
- [ ] Verificar que no haya errores raros
- [ ] Observar si aparece lentitud o bloqueo

## 7. Bandeja del sistema

- [ ] Minimizar SmartPrice de `Administrador` a bandeja
- [ ] Confirmar icono en su sesion
- [ ] Minimizar SmartPrice de `Pantalla` a bandeja
- [ ] Confirmar icono en su sesion
- [ ] Click izquierdo en bandeja de `Pantalla`
- [ ] Confirmar que restaura su ventana

## 8. Resultado esperado final

### Administrador

- [ ] acceso completo
- [ ] puede usar `Configuracion`
- [ ] puede editar permisos
- [ ] puede usar `Productos` y `Publicidad`

### Pantalla

- [ ] solo usa `Publicidad`
- [ ] no entra a `Productos`
- [ ] no entra a `Configuracion`
- [ ] comparte datos necesarios con la misma base

## Observaciones de prueba

Registrar aca cualquier comportamiento inesperado:

- Fecha:
- Usuario:
- Caso:
- Resultado observado:
- Captura / evidencia:
- Accion siguiente:
