"""Carga los datos de prueba de colegio.sql usando el ORM de Django.

Uso:  python manage.py cargar_datos [ruta/a/colegio.sql]

- Los profesores del SQL pasan a ser usuarios con rol Docente.
- Los apoderados del SQL quedan solo como datos de contacto (no inician sesión).
- Se agregan cuentas de prueba de Dirección, Psicóloga y Docente, un aviso y mensajes de ejemplo.
- No se crean tipos de evaluación: los define el colegio desde la plataforma.
Las contraseñas se guardan hasheadas.
"""
import datetime
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from colegio.models import (Alumno, AlumnoApoderado, Apoderado, Asignacion, Aviso, Citacion, Curso, Destinatario,
                            Mensaje, Observacion, Rol, Usuario, hoy)

TOKEN = re.compile(r"'((?:[^']|'')*)'|(TRUE|FALSE)|(-?\d+)", re.I)

# Cuentas de prueba extra: rut, nombre, correo, contraseña, rol, asignatura, cursos (id)
PERSONAL_DEMO = [
    ("93000001-1", "Patricia Soto", "direccion@escueladiversidad.cl", "PruebaDireccion001!", Rol.DIRECCION, "", []),
    ("93000002-2", "Jorge Contreras", "subdireccion@escueladiversidad.cl", "PruebaDireccion002!", Rol.DIRECCION, "", []),
    ("94000001-1", "Valentina Fuentes", "psicologa@escueladiversidad.cl", "PruebaPsicologa001!", Rol.PSICOLOGA, "", [1, 2]),
    ("94000002-2", "Camila Rojas", "psicologa2@escueladiversidad.cl", "PruebaPsicologa002!", Rol.PSICOLOGA, "", [3]),
    ("95000001-1", "Rodrigo Muñoz", "docente.prueba@escueladiversidad.cl", "PruebaDocente001!", Rol.DOCENTE,
     "Educación Especial", [2, 3]),
]


def filas(sql, tabla):
    """Devuelve las filas (listas de valores) del INSERT INTO <tabla>."""
    m = re.search(rf"INSERT\s+INTO\s+{tabla}\s+VALUES(.*?);", sql, re.S | re.I)
    if not m:
        return []
    out = []
    for tupla in re.findall(r"\(([^()]*)\)", m.group(1)):
        fila = []
        for s, b, n in TOKEN.findall(tupla):
            if b:
                fila.append(b.upper() == "TRUE")
            elif n and not s:
                fila.append(int(n))
            else:
                fila.append(s.replace("''", "'"))
        out.append(fila)
    return out


def enviar(autor, destinatarios, asunto, cuerpo, alumno=None):
    if Mensaje.objects.filter(asunto=asunto).exists():
        return
    m = Mensaje.objects.create(creado_por=autor, modificado_por=autor, asunto=asunto, cuerpo=cuerpo, alumno=alumno)
    Destinatario.objects.bulk_create(Destinatario(mensaje=m, usuario=u) for u in destinatarios if u != autor)
    return m


class Command(BaseCommand):
    help = "Carga los datos de prueba desde colegio.sql"

    def add_arguments(self, parser):
        parser.add_argument("sql", nargs="?", default=str(Path(settings.BASE_DIR) / "colegio.sql"))

    @transaction.atomic
    def handle(self, *args, **opts):
        sql = Path(opts["sql"]).read_text(encoding="utf-8")
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)   # comentarios de bloque
        sql = re.sub(r"--[^\n]*", "", sql)                 # comentarios de línea

        personas = {rut: (nombre, email, clave) for rut, nombre, email, clave in filas(sql, "usuario")}

        # Docentes del SQL
        for rut, asignatura in filas(sql, "profesor"):
            nombre, email, clave = personas[rut]
            u, _ = Usuario.objects.get_or_create(rut=rut, defaults={
                "nombre": nombre, "email": email, "rol": Rol.DOCENTE, "asignatura": asignatura})
            u.set_password(clave)
            u.save()

        # Apoderados: solo contacto
        for rut, telefono in filas(sql, "apoderado"):
            nombre, email, _ = personas[rut]
            Apoderado.objects.get_or_create(rut=rut, defaults={"nombre": nombre, "email": email, "telefono": telefono})

        for id_, nivel, capacidad in filas(sql, "curso"):
            Curso.objects.get_or_create(pk=id_, defaults={"nivel": nivel, "capacidad": capacidad})
        for rut_p, id_c, jefe in filas(sql, "profesor_curso"):
            Asignacion.objects.get_or_create(usuario_id=rut_p, curso_id=id_c, defaults={"profesor_jefe": jefe})

        # Cuentas de prueba extra
        for rut, nombre, email, clave, rol, asignatura, cursos in PERSONAL_DEMO:
            u, _ = Usuario.objects.get_or_create(rut=rut, defaults={
                "nombre": nombre, "email": email, "rol": rol, "asignatura": asignatura})
            u.set_password(clave)
            u.save()
            for id_c in cursos:
                Asignacion.objects.get_or_create(usuario=u, curso_id=id_c)
        direccion = Usuario.objects.get(rut="93000001-1")
        psicologa = Usuario.objects.get(rut="94000001-1")
        docente = Usuario.objects.get(rut="92000001-1")

        for rut, nombre, id_c in filas(sql, "alumno"):
            Alumno.objects.get_or_create(rut=rut, defaults={"nombre": nombre, "curso_id": id_c, "creado_por": direccion})
        for rut_a, rut_al, parentesco, principal in filas(sql, "alumno_apoderado"):
            AlumnoApoderado.objects.get_or_create(apoderado_id=rut_a, alumno_id=rut_al,
                                                  defaults={"parentesco": parentesco, "es_principal": principal})
        for id_, rut_al, rut_p, contenido in filas(sql, "observacion"):
            Observacion.objects.get_or_create(pk=id_, defaults={
                "alumno_id": rut_al, "contenido": contenido, "creado_por_id": rut_p, "modificado_por_id": rut_p})

        # Ejemplos para probar la plataforma
        alumno = Alumno.objects.order_by("rut").first()
        if alumno and not Citacion.objects.exists():
            Citacion.objects.create(alumno=alumno, apoderado=alumno.apoderados.first(),
                                    fecha=hoy() + datetime.timedelta(days=3), hora=datetime.time(10, 0),
                                    motivo="Entrevista con el apoderado", creado_por=psicologa,
                                    modificado_por=psicologa)
        if not Aviso.objects.exists():
            Aviso.objects.create(
                titulo="Bienvenidos a la nueva plataforma",
                contenido="Desde ahora los atrasos, inasistencias, observaciones, evaluaciones y citaciones "
                          "se registran en esta plataforma. Ante dudas, consulte con Dirección.",
                destacado=True, creado_por=direccion, modificado_por=direccion)
        personal = list(Usuario.objects.filter(is_active=True))
        enviar(direccion, personal, "Reunión de equipo el viernes",
               "Estimados: el viernes a las 15:00 tendremos reunión de equipo en la sala de profesores. "
               "Por favor confirmen su asistencia respondiendo este mensaje.")
        if alumno:
            enviar(docente, [psicologa], f"Consulta sobre {alumno.nombre}",
                   f"Hola, he notado que {alumno.nombre} se distrae mucho en clases esta semana. "
                   "¿Podríamos conversar sobre cómo apoyarle?", alumno=alumno)

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {Usuario.objects.count()} usuarios, {Alumno.objects.count()} pupilos, "
            f"{Apoderado.objects.count()} apoderados (contacto), {Curso.objects.count()} cursos."))
