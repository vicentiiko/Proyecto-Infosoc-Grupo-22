from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from ..models import Mensaje, ultimas_evaluaciones
from ..permisos import (alumno_visible_o_404, alumnos_visibles, cursos_visibles, puede_ver,
                        seguimientos_visibles)
from .base import FiltroForm, paginar


@login_required
def lista(request):
    u = request.user
    filtro = FiltroForm(request.GET or None, cursos=cursos_visibles(u))
    qs = alumnos_visibles(u)
    if filtro.is_valid():
        d = filtro.cleaned_data
        if d["q"]:
            qs = qs.filter(Q(nombre__icontains=d["q"]) | Q(rut__icontains=d["q"]))
        if d["curso"]:
            qs = qs.filter(curso=d["curso"])
    qs = qs.annotate(n_atrasos=Count("atrasos", distinct=True), n_inasist=Count("inasistencias", distinct=True)).order_by("nombre")
    return render(request, "colegio/estudiantes.html", {"filtro": filtro, "pagina": paginar(request, qs)})


@login_required
def ficha(request, rut):
    u = request.user
    alumno = alumno_visible_o_404(u, rut)
    ctx = {
        "alumno": alumno,
        "vinculos": alumno.vinculos.select_related("apoderado"),
        "observaciones": alumno.observaciones.select_related("creado_por", "modificado_por"),
        "atrasos": alumno.atrasos.select_related("creado_por")[:15],
        "n_atrasos": alumno.atrasos.count(),
        "inasistencias": alumno.inasistencias.select_related("creado_por")[:15],
        "n_inasist": alumno.inasistencias.count(),
        "n_justificadas": alumno.inasistencias.filter(justificada=True).count(),
        "mensajes": ((Mensaje.objects.filter(hilo__isnull=True) if u.es_direccion
                      else Mensaje.objects.conversaciones_de(u)).filter(alumno=alumno)
                     .select_related("creado_por").order_by("-creado_en")),
        "seguimientos": seguimientos_visibles(u, alumno.seguimientos.select_related("creado_por")),
    }
    if puede_ver(u, "evaluaciones"):
        ctx["evaluaciones"] = alumno.evaluaciones.select_related("tipo", "creado_por")
        ctx["estado_evaluaciones"] = ultimas_evaluaciones(alumno.evaluaciones.all())
    if puede_ver(u, "citaciones"):
        ctx["citaciones"] = alumno.citaciones.select_related("apoderado", "creado_por")
    return render(request, "colegio/ficha.html", ctx)


@login_required
def curso(request, pk):
    u = request.user
    c = get_object_or_404(cursos_visibles(u), pk=pk)
    alumnos = c.alumnos.filter(activo=True).annotate(
        n_atrasos=Count("atrasos", distinct=True),
        n_inasist=Count("inasistencias", distinct=True),
        n_injust=Count("inasistencias", filter=Q(inasistencias__justificada=False), distinct=True),
    )
    return render(request, "colegio/curso.html", {
        "curso": c, "alumnos": alumnos,
        "equipo": c.asignaciones.select_related("usuario").order_by("-profesor_jefe", "usuario__nombre"),
    })
