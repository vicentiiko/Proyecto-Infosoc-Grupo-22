# Proyecto Infosoc – Grupo 22 (Escuela Especial Diversidad)

Plataforma web interna de gestión escolar. Reúne en un solo historial por estudiante la asistencia,
las observaciones, las evaluaciones y las citaciones, e incluye mensajería interna entre los tres roles que la usan:
**Dirección**, **Psicóloga** y **Docentes**. Los apoderados **no** son usuarios: quedan solo como datos de contacto.

Implementa el *Documento de mejoras* (M-01 a M-11).

**Tecnologías:** Python 3.12+, Django 6.1, SQLite. Interfaz en español (`es-cl`, hora de Santiago).

## Requisitos
- **Python 3.12 o superior** (Django 6 lo requiere). Descargar desde https://www.python.org/downloads/
  - En Windows, al instalar marca **"Add python.exe to PATH"**.
  - Comprueba que quedó bien con `python --version` (o `py --version` en Windows).
- Git (opcional, para clonar el repositorio).

## Puesta en marcha

Todos los comandos se escriben en una terminal abierta **en la carpeta del proyecto** (donde está `manage.py`).

### Primera vez (instalación)

1. Crear el entorno virtual:
   ```bash
   python -m venv venv
   ```
   (En Windows, si `python` no funciona, usa `py -m venv venv`. En Linux/Mac puede ser `python3`.)

2. Activar el entorno virtual:
   - **Windows (PowerShell):**
     ```powershell
     venv\Scripts\activate
     ```
     Si sale el error *"la ejecución de scripts está deshabilitada"*, corre una sola vez
     `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a activar.
   - **Linux / Mac:**
     ```bash
     source venv/bin/activate
     ```
   Sabrás que quedó activo porque la terminal muestra `(venv)` al inicio de la línea.

3. Instalar las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Crear la base de datos (SQLite, se genera sola como `db.sqlite3`):
   ```bash
   python manage.py migrate
   ```

5. Cargar los datos de prueba desde `colegio.sql`:
   ```bash
   python manage.py cargar_datos
   ```

6. (Opcional) Crear un superusuario para entrar a `/admin/`:
   ```bash
   python manage.py createsuperuser
   ```

### Ver la página

```bash
python manage.py runserver
```
Abrir http://127.0.0.1:8000/ en el navegador. Se redirige al login.

Para **detener** el servidor, presiona `Ctrl + C` en la terminal.

### Las próximas veces

Los pasos 1, 3, 4 y 5 se hacen una sola vez. Después solo necesitas:
```bash
venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
python manage.py runserver
```

### Después de bajar cambios del repositorio (`git pull`)
Con el `venv` activo:
```bash
pip install -r requirements.txt
python manage.py migrate
```
`migrate` aplica los cambios de estructura a la base sin borrar los datos.
Si vienes de la versión anterior, donde los apoderados iniciaban sesión, la estructura cambió por completo: borra `db.sqlite3` y repite los pasos 4 y 5.

## Cuentas de prueba
| Rol | Nombre | RUT | Contraseña | Cursos |
|---|---|---|---|---|
| Dirección | Patricia Soto | `93000001-1` | `PruebaDireccion001!` | — |
| Dirección | Jorge Contreras | `93000002-2` | `PruebaDireccion002!` | — |
| Psicóloga | Valentina Fuentes | `94000001-1` | `PruebaPsicologa001!` | 8voA, 7moB |
| Psicóloga | Camila Rojas | `94000002-2` | `PruebaPsicologa002!` | 8voB |
| Docente | Ana González | `92000001-1` | `PruebaProfesor001!` | 8voA, 7moB |
| Docente | Rodrigo Muñoz | `95000001-1` | `PruebaDocente001!` | 7moB, 8voB |

Además hay 20 docentes del SQL (RUT `92000001-1` a `92000020-0`, contraseñas `PruebaProfesor002!`, `PruebaProfesor003!`, etc.).
Los apoderados de `colegio.sql` se cargan como contactos y no inician sesión.

`cargar_datos` también crea un aviso, una citación y dos conversaciones de ejemplo: una de Dirección a todo el personal y una de Ana González a Valentina Fuentes sobre una estudiante.
**No** crea tipos de evaluación: el colegio los define en *Evaluaciones → Tipos y periodicidad* antes de registrar evaluaciones.

## Guía rápida de uso

**Primeros pasos (Dirección)**
1. *Gestión → Usuarios*: crear las cuentas del personal y asignar a cada docente y psicóloga sus cursos.
2. *Gestión → Cursos*: crear los cursos, elegir el profesor(a) jefe y marcar sus estudiantes (con buscador).
3. *Gestión → Pupilos*: crear estudiantes y sus apoderados (solo datos de contacto). Dar de baja conserva el historial.
4. *Evaluaciones → Tipos y periodicidad* (Dirección o psicóloga): definir los tipos de evaluación antes de registrar la primera.
5. *Avisos*: publicar información para todo el personal.

**Tareas del día a día**
| Quiero… | Dónde |
|---|---|
| Pasar lista de un curso | *Asistencia → Pasar lista* (Presente / Ausente / Justificada, botón «Todos presentes») |
| Registrar un atraso | *Asistencia → Atrasos → Registrar atraso*, o desde la ficha del estudiante |
| Ver todo sobre un estudiante | *Estudiantes* → «Ver ficha» |
| Registrar una evaluación | *Evaluaciones → Registrar evaluación* (la próxima reevaluación se calcula sola) |
| Citar a un apoderado | *Citaciones → Nueva citación* (luego «Actualizar» para cambiar el estado) |
| Escribir al equipo | *Mensajes → Nuevo mensaje* (a grupos, al equipo de un curso o a personas) |
| Compartir un archivo | *Recursos → Subir recurso* y elegir quién lo ve |
| Cubrir a alguien que faltó | *Gestión → Usuarios → Reemplazar* (solo Dirección) |

## Problemas comunes
| Problema | Solución |
|---|---|
| `no se encontró Python` (Windows) | Instala Python marcando "Add to PATH", o usa `py` en vez de `python`. Si persiste, desactiva los alias `python.exe` / `python3.exe` en *Configuración → Aplicaciones → Configuración avanzada de aplicaciones → Alias de ejecución de aplicaciones*. Abre una terminal nueva después. |
| `ModuleNotFoundError: No module named 'django'` | Falta activar el `venv` o instalar las dependencias (`pip install -r requirements.txt` con el `venv` activo). |
| El login dice "RUT o contraseña incorrectos" | El RUT se escribe con guion y dígito verificador (ej: `92000001-1`). La contraseña distingue mayúsculas. |
| Quiero empezar con la base de datos limpia | Detén el servidor, borra `db.sqlite3` y repite los pasos 4 y 5. |
| Error `no such column` o `no such table` después de actualizar | Falta aplicar los cambios de estructura: `python manage.py migrate`. Si sigue fallando, borra `db.sqlite3` y repite los pasos 4 y 5. |
| «Registrar evaluación» me lleva a «Tipos y periodicidad» | Aún no hay tipos de evaluación. Cree al menos uno primero. |
| Una docente no ve a un estudiante | Solo ve los estudiantes de sus cursos. Revise en *Gestión → Usuarios* que tenga el curso asignado y que el estudiante esté en ese curso. |
| Quedé atrapado en «Modo reemplazo» | Use el botón **Volver a mi cuenta** de la franja naranja, o cierre sesión. |

## Módulos (documento de mejoras)
| Código | Módulo | Dónde |
|---|---|---|
| M-01 | Gestión de usuarios, pupilos y cursos (crear, editar, desactivar, dar de baja). Al crear o editar un curso se eligen sus estudiantes desde una lista con buscador | `/gestion/` |
| M-02 | Atrasos con fecha y hora, filtros por curso, estudiante y fechas | `/asistencia/atrasos/` |
| M-03 | Inasistencias justificadas o no, totales por estudiante y curso. *Pasar lista*: cada estudiante se marca Presente, Ausente o Justificada | `/asistencia/inasistencias/` |
| M-04 | Observaciones con fecha y autor | Ficha del estudiante |
| M-05 | Evaluaciones con cálculo automático de la próxima reevaluación y avisos | `/evaluaciones/` |
| M-06 | Citaciones a apoderados con estado e historial | `/citaciones/` |
| M-07 | **Reemplazado por mensajería interna** entre Dirección, psicólogas y docentes: conversaciones, respuestas, adjuntos, mensajes sin leer y opción de asociar un estudiante | `/mensajes/` |
| M-08 | Seguimiento integral y planificaciones de apoyo | Ficha del estudiante |
| M-09 | Recursos digitales con visibilidad configurable | `/recursos/` |
| M-10 | Comisiones con integrantes, notas y documentos | `/comisiones/` |
| M-11 | Avisos para todos, publicados por Dirección | `/avisos/` e inicio |

La **ficha del estudiante** (`/estudiantes/<rut>/`) reúne todo su historial en una página.

### Permisos por rol
Base: tabla 4 del documento (V = ve, E = crea o edita), con **acceso total para Dirección**. Se revisan en el servidor (`colegio/permisos.py`), no solo en la pantalla.

| Módulo | Dirección | Psicóloga | Docentes |
|---|---|---|---|
| Usuarios, pupilos y cursos | V / E | – | – |
| Atrasos e inasistencias | V / E | V | V / E |
| Observaciones | V / E | V / E | V / E |
| Evaluaciones | V / E | V / E | – |
| Citaciones | V / E | V / E | – |
| Mensajes internos | V / E (todas las conversaciones) | V / E (las suyas) | V / E (las suyas) |
| Seguimiento integral | V / E | V / E | V / E |
| Recursos digitales | V / E (todos) | V / E (según visibilidad) | V / E (según visibilidad) |
| Comisiones | V / E | V | V |
| Información general | V / E | V | V |

Además:
- Cada docente solo ve a los estudiantes de sus cursos. Dirección y psicóloga ven a todos.
- Observaciones, seguimiento y recursos los edita o borra quien los creó, o Dirección. La asistencia la puede corregir cualquier docente del curso, y las evaluaciones y citaciones cualquier psicóloga.
- La psicóloga (o Dirección) puede marcar un seguimiento como **confidencial**: entonces solo psicólogas y Dirección lo ven.
- Los integrantes de una comisión pueden publicar notas y documentos en su espacio. Solo Dirección crea comisiones y elige a sus integrantes.
- Una conversación de mensajes la ven sus participantes y Dirección. Si Dirección responde, pasa a ser participante.
- Los archivos subidos se guardan en `media/` y no tienen una URL pública: se descargan por una vista que revisa los permisos.
- Cada registro guarda quién lo creó o modificó y cuándo.

### Reemplazos
Si una docente o psicóloga falta, Dirección puede trabajar en su cuenta: *Gestión → Usuarios → Reemplazar*.
- Mientras dura, Dirección ve la plataforma como esa persona (sus cursos, mensajes y permisos). Arriba aparece una franja naranja con el botón **Volver a mi cuenta**.
- Lo que se registre queda a nombre de la persona reemplazada, con la nota «en reemplazo, lo hizo …» (campo `suplente` de cada registro).
- *Gestión → Reemplazos* guarda el historial: quién reemplazó a quién, cuándo empezó y cuándo terminó. Cerrar sesión también termina el reemplazo.
- No se puede reemplazar a otra persona de Dirección.

### Decisiones pendientes (preguntas del documento)
- **Tipos de evaluación y periodicidad:** no hay tipos precargados. Se crean en *Evaluaciones → Tipos y periodicidad*; si se cambia la periodicidad, las fechas se recalculan solas. El aviso aparece 60 días antes (`DIAS_AVISO_REEVALUACION` en `colegio/models.py`).
- **Recursos "para todos":** incluye a docentes y psicólogas; Dirección ve todos los recursos siempre.
- **Psicóloga:** ve a todos los estudiantes, no solo a los que atiende.
- **Importar estudiantes desde Excel:** no está implementado.
- **Respaldos:** basta con copiar `db.sqlite3` y la carpeta `media/`.

## Modelo de datos
Todos los registros heredan de `Registro`, que guarda quién lo creó y modificó, cuándo, y si se hizo en reemplazo (`suplente`).

| Modelo | Qué guarda |
|---|---|
| `Usuario` | Personal que inicia sesión con su RUT: rol (Dirección, Psicóloga, Docente), asignatura y estado activo |
| `Curso`, `Asignacion` | Cursos y qué personal está asignado a cada uno (con profesor jefe) |
| `Alumno` | Pupilos: curso, fecha de nacimiento, activo o dado de baja |
| `Apoderado`, `AlumnoApoderado` | Datos de contacto de los apoderados y su parentesco con cada pupilo |
| `Atraso`, `Inasistencia` | Asistencia: fecha y hora de llegada; inasistencias justificadas o no |
| `Observacion`, `Seguimiento` | Observaciones generales y seguimiento integral (este último puede ser confidencial) |
| `TipoEvaluacion`, `Evaluacion` | Tipos con su periodicidad y evaluaciones con la próxima reevaluación calculada |
| `Citacion` | Citaciones a apoderados con fecha, motivo, estado y resultado |
| `Mensaje`, `Destinatario` | Mensajería interna: conversaciones, respuestas y quién leyó cada mensaje |
| `Recurso` | Archivos compartidos y su visibilidad |
| `Comision`, `PublicacionComision` | Comisiones, integrantes y sus notas o documentos |
| `Aviso` | Información general publicada por Dirección |
| `Suplencia` | Historial de reemplazos |

El diagrama `Diagrama en blanco.pdf` corresponde al esquema original (antes de las mejoras).

## Estructura del proyecto
```
config/                 configuración de Django (settings, urls)
colegio/
  models.py             modelos (usuarios, pupilos, asistencia, evaluaciones, mensajes, recursos…)
  permisos.py           permisos por rol y qué estudiantes ve cada usuario
  suplencia.py          modo reemplazo: marca lo que Dirección registra en nombre de otra persona
  context_processors.py datos del menú (mensajes sin leer, reevaluaciones, aviso de reemplazo)
  forms.py              formularios
  views/                vistas por módulo (inicio, estudiantes, asistencia, registros, mensajes, comunidad, gestion)
  migrations/           cambios de estructura de la base de datos
  templates/colegio/    plantillas de cada página
  tests.py              pruebas automáticas
  management/commands/cargar_datos.py   carga colegio.sql y datos de ejemplo
templates/              base.html, login.html, páginas de error y piezas reutilizables (partials/)
static/                 estilos (css/estilo.css) e imagen del logo (img/logo.png)
media/                  archivos subidos (se crea solo, no se sube a git)
colegio.sql             esquema y datos de prueba originales
```

## Pruebas
```bash
python manage.py test colegio
```
Revisan permisos por rol, visibilidad de recursos, cálculo de reevaluaciones, pasar lista, gestión de usuarios, cursos y pupilos, mensajería (destinatarios, privacidad, no leídos), reemplazos, y que todas las páginas carguen con cada rol. Usan una base de datos temporal: no tocan `db.sqlite3`.

## Antes de publicar en producción
La configuración actual es para desarrollo. Antes de publicarla en un servidor:
- Cambiar `SECRET_KEY` en `config/settings.py` (idealmente leerla de una variable de entorno) y poner `DEBUG = False`.
- Completar `ALLOWED_HOSTS` con el dominio del sitio.
- Ejecutar `python manage.py collectstatic` y servir los archivos estáticos desde el servidor web.
- Programar respaldos periódicos de `db.sqlite3` y de la carpeta `media/`.
- Cambiar o eliminar las cuentas de prueba (`cargar_datos` no debe ejecutarse en producción).

