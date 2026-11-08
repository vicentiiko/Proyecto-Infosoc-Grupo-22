from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MensajeForm, ObservacionForm
from .models import Alumno, Curso


def solo_profesor(vista):
    @wraps(vista)
    @login_required
    def envoltura(request, *args, **kwargs):
        if not request.user.es_profesor:
            raise PermissionDenied
        return vista(request, request.user.profesor, *args, **kwargs)
    return envoltura


def solo_apoderado(vista):
    @wraps(vista)
    @login_required
    def envoltura(request, *args, **kwargs):
        if not request.user.es_apoderado:
            raise PermissionDenied
        return vista(request, request.user.apoderado, *args, **kwargs)
    return envoltura


@login_required
def inicio(request):
    if request.user.es_profesor:
        return redirect("profesor_panel")
    if request.user.es_apoderado:
        return redirect("apoderado_panel")
    return render(request, "colegio/sin_rol.html")


# ---------- Profesor ----------
@solo_profesor
def profesor_panel(request, profesor):
    cursos = profesor.cursos.all()
    mensajes = profesor.mensajes.prefetch_related("destinatarios__usuario")[:10]
    return render(request, "colegio/profesor_panel.html", {"cursos": cursos, "mensajes": mensajes})


@solo_profesor
def curso_detalle(request, profesor, curso_id):
    curso = get_object_or_404(profesor.cursos, pk=curso_id)
    return render(request, "colegio/curso_detalle.html", {"curso": curso, "alumnos": curso.alumnos.all()})


@solo_profesor
def alumno_profesor(request, profesor, rut):
    alumno = get_object_or_404(Alumno, pk=rut, curso__in=profesor.cursos.all())
    form = ObservacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obs = form.save(commit=False)
        obs.alumno, obs.profesor = alumno, profesor
        obs.save()
        return redirect("alumno_profesor", rut=rut)
    return render(request, "colegio/alumno_profesor.html", {
        "alumno": alumno, "form": form,
        "observaciones": alumno.observaciones.select_related("profesor__usuario"),
    })


@solo_profesor
def mensaje_nuevo(request, profesor):
    form = MensajeForm(request.POST or None, profesor=profesor)
    if request.method == "POST" and form.is_valid():
        msg = form.save(commit=False)
        msg.profesor = profesor
        msg.save()
        form.save_m2m()
        return redirect("profesor_panel")
    return render(request, "colegio/mensaje_nuevo.html", {"form": form})


# ---------- Apoderado ----------
@solo_apoderado
def apoderado_panel(request, apoderado):
    return render(request, "colegio/apoderado_panel.html", {
        "alumnos": apoderado.alumnos.select_related("curso"),
        "mensajes": apoderado.mensajes_recibidos.select_related("profesor__usuario"),
    })


@solo_apoderado
def alumno_apoderado(request, apoderado, rut):
    alumno = get_object_or_404(apoderado.alumnos, pk=rut)
    return render(request, "colegio/alumno_apoderado.html", {
        "alumno": alumno,
        "observaciones": alumno.observaciones.select_related("profesor__usuario"),
    })
