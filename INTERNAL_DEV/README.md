# Internal Dev Hub

Este directorio es la fuente de verdad interna para mantener una sola linea de trabajo en `VeriPre_Connector`.

Objetivos:
- Centralizar contexto tecnico del proyecto.
- Documentar contratos entre Python y Android.
- Definir reglas obligatorias de bloqueo entre desarrolladores.
- Separar ownership entre Misa y Nico.
- Mantener continuidad sin depender de memoria oral.

Archivos principales:
- `PROJECT_CONTEXT.md`: arquitectura actual, flujos y decisiones vigentes.
- `SKILLS.md`: criterios tecnicos y habilidades operativas esperadas para tocar el proyecto.
- `TASKS_MISA_NICO.md`: ownership y backlog separado por desarrollador.
- `BLOCKING_PROTOCOL.md`: protocolo obligatorio para bloquear archivos y modulos antes de editar.
- `RECENT_EVOLUTION.md`: resumen de lo agregado y estabilizado hasta `1.16.5`.
- `FUTURE_LINE.md`: direccion de arquitectura a futuro.
- `MULTIUSER_TEST_CHECKLIST.md`: checklist operativo para validar escenarios multiusuario, permisos por usuario Windows y bandeja por sesion.

Uso obligatorio:
1. Leer `BLOCKING_PROTOCOL.md` antes de modificar codigo.
2. Tomar lock si se toca un modulo compartido.
3. Registrar cambios relevantes en `RECENT_EVOLUTION.md`.
4. Mantener el ownership de `TASKS_MISA_NICO.md` salvo coordinacion explicita.

## Anexo reciente

- Se agrega `BOOTSTACK_MIGRATION_BASE.md` como base de trabajo para la fase `VPC-F2` de evaluacion/migracion UI hacia Bootstack.
