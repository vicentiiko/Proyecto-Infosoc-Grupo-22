# Proyecto Infosoc – Grupo 22 (Colegio Diferencial)

Plataforma web de comunicación entre profesores y apoderados de un colegio diferencial.
Los profesores registran observaciones de sus alumnos y envían mensajes a los apoderados;
los apoderados entran a ver la información de sus pupilos.

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

## Cuentas de prueba (vienen de colegio.sql)
| Rol | RUT | Contraseña |
|---|---|---|
| Profesor | `92000001-1` | `PruebaProfesor001!` |
| Apoderado | `91000001-1` | `PruebaApoderado001!` |

Hay 20 profesores (RUT `92000001-1` a `92000020-0`) y 53 apoderados (RUT `91000001-1` a `91000053-3`); la contraseña sigue el mismo patrón (`PruebaProfesor002!`, `PruebaApoderado002!`, etc.).

## Problemas comunes
| Problema | Solución |
|---|---|
| `no se encontró Python` (Windows) | Instala Python marcando "Add to PATH", o usa `py` en vez de `python`. Si persiste, desactiva los alias `python.exe` / `python3.exe` en *Configuración → Aplicaciones → Configuración avanzada de aplicaciones → Alias de ejecución de aplicaciones*. Abre una terminal nueva después. |
| `ModuleNotFoundError: No module named 'django'` | Falta activar el `venv` o instalar las dependencias (`pip install -r requirements.txt` con el `venv` activo). |
| El login dice "RUT o contraseña incorrectos" | El RUT se escribe con guion y dígito verificador (ej: `92000001-1`). La contraseña distingue mayúsculas. |
| Quiero empezar con la base de datos limpia | Detén el servidor, borra `db.sqlite3` y repite los pasos 4 y 5. |

## Qué hay hecho
- Modelos para todas las tablas del esquema (`colegio/models.py`)
- Login por RUT, contraseñas hasheadas, panel de admin
- Profesor: ver sus cursos y alumnos, escribir observaciones, enviar mensajes a apoderados
- Apoderado: ver sus pupilos, observaciones y mensajes recibidos

## Páginas
| URL | Quién | Qué muestra |
|---|---|---|
| `/login/` | Todos | Ingreso con RUT y contraseña |
| `/` | Todos | Redirige al panel según el rol del usuario |
| `/profesor/` | Profesor | Sus cursos |
| `/profesor/curso/<id>/` | Profesor | Alumnos de un curso |
| `/profesor/alumno/<rut>/` | Profesor | Ficha del alumno y nueva observación |
| `/profesor/mensaje/nuevo/` | Profesor | Enviar mensaje a apoderados |
| `/apoderado/` | Apoderado | Sus pupilos y mensajes recibidos |
| `/apoderado/alumno/<rut>/` | Apoderado | Observaciones de un pupilo |
| `/admin/` | Superusuario | Panel de administración de Django |

Un usuario que no es profesor ni apoderado ve la página `sin_rol`.

## Modelo de datos
- **Usuario**: modelo de usuario propio; se identifica por RUT. Puede ser **Profesor** (asignatura) o **Apoderado** (teléfono).
- **Curso**: nivel y tamaño. Se une a profesores mediante **ProfesorCurso**, que indica si es profesor jefe.
- **Alumno**: pertenece a un curso. Se une a apoderados mediante **AlumnoApoderado** (parentesco y si es el apoderado principal).
- **Mensaje**: lo escribe un profesor y lo reciben uno o más apoderados.
- **Observacion**: la escribe un profesor sobre un alumno.

El diagrama del esquema está en `Diagrama en blanco.pdf`.

## Estructura del proyecto
```
config/          configuración de Django (settings, urls)
colegio/         app principal: modelos, vistas, formularios, plantillas
  management/commands/cargar_datos.py   carga colegio.sql con el ORM
templates/       base.html y login.html
static/css/      estilos
colegio.sql      esquema y datos de prueba originales
Diagrama en blanco.pdf   diagrama del modelo de datos
```

## Pendiente
- Pruebas automáticas: `colegio/tests.py` está vacío. Cuando existan, se corren con `python manage.py test`.
