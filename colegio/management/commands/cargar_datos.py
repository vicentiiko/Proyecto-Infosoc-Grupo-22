"""Carga los datos de prueba de colegio.sql usando el ORM de Django.

Uso:  python manage.py cargar_datos [ruta/a/colegio.sql]
Las contraseñas del SQL (de prueba) se guardan hasheadas.
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from colegio.models import (Alumno, AlumnoApoderado, Apoderado, Curso, Mensaje,
                            Observacion, Profesor, ProfesorCurso, Usuario)

TOKEN = re.compile(r"'((?:[^']|'')*)'|(TRUE|FALSE)|(-?\d+)", re.I)


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


class Command(BaseCommand):
    help = "Carga los datos de prueba desde colegio.sql"

    def add_arguments(self, parser):
        parser.add_argument("sql", nargs="?", default=str(Path(settings.BASE_DIR) / "colegio.sql"))

    @transaction.atomic
    def handle(self, *args, **opts):
        sql = Path(opts["sql"]).read_text(encoding="utf-8")
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)   # comentarios de bloque
        sql = re.sub(r"--[^\n]*", "", sql)                 # comentarios de línea

        for rut, nombre, email, clave in filas(sql, "usuario"):
            u, _ = Usuario.objects.get_or_create(rut=rut, defaults={"nombre": nombre, "email": email})
            u.set_password(clave)
            u.save()
        for rut, asig in filas(sql, "profesor"):
            Profesor.objects.get_or_create(usuario_id=rut, defaults={"asignatura": asig})
        for rut, tel in filas(sql, "apoderado"):
            Apoderado.objects.get_or_create(usuario_id=rut, defaults={"telefono": tel})
        for id_, nivel, tam in filas(sql, "curso"):
            Curso.objects.get_or_create(pk=id_, defaults={"nivel": nivel, "tamanio": tam})
        for rut_p, id_c, jefe in filas(sql, "profesor_curso"):
            ProfesorCurso.objects.get_or_create(profesor_id=rut_p, curso_id=id_c, defaults={"profesor_jefe": jefe})
        for rut, nombre, id_c in filas(sql, "alumno"):
            Alumno.objects.get_or_create(rut=rut, defaults={"nombre": nombre, "curso_id": id_c})
        for rut_a, rut_al, parentesco, principal in filas(sql, "alumno_apoderado"):
            AlumnoApoderado.objects.get_or_create(apoderado_id=rut_a, alumno_id=rut_al,
                                                  defaults={"parentesco": parentesco, "es_principal": principal})
        for id_, contenido, rut_p, fecha in filas(sql, "mensaje"):
            Mensaje.objects.get_or_create(pk=id_, defaults={"contenido": contenido, "profesor_id": rut_p, "fecha": fecha})
        for id_m, rut_a in filas(sql, "mensaje_apoderado"):
            Mensaje.objects.get(pk=id_m).destinatarios.add(rut_a)
        for id_, rut_al, rut_p, contenido in filas(sql, "observacion"):
            Observacion.objects.get_or_create(pk=id_, defaults={"alumno_id": rut_al, "profesor_id": rut_p, "contenido": contenido})

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {Usuario.objects.count()} usuarios, {Alumno.objects.count()} alumnos, {Curso.objects.count()} cursos."))
