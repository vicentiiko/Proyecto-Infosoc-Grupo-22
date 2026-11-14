"""Observaciones, seguimiento, evaluaciones y citaciones."""
from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..forms import (CitacionForm, EvaluacionForm, ObservacionForm, SeguimientoForm,
                     TipoEvaluacionForm)
from ..models import (Citacion, Evaluacion, Observacion, Seguimiento, TipoEvaluacion, hoy,
                      ultimas_evaluaciones)
from ..permisos import alumno_visible_o_404, comprobar_alumno, cursos_visibles, requiere, seguimientos_visibles
from .base import FiltroForm, eliminar, exigir_autor, formulario, paginar


def _ficha(alumno, seccion=""):
    return reverse("ficha", args=[alumno.pk]) + (f"#{seccion}" if seccion else "")


def _alumno_param(request):
    rut = request.GET.get("alumno")
    return alumno_visible_o_404(request.user, rut) if rut else None


def _nuevo(request, form_class, *, titulo, seccion, lista=None, exito):
    """Crear un registro, desde la ficha del pupilo (?alumno=rut) o desde un listado."""
    alumno = _alumno_param(request)
    form = form_class(request.POST or None, request.FILES or None, usuario=request.user, alumno=alumno)
    volver = _ficha(alumno, seccion) if alumno else (lista or reverse("estudiantes"))
    migas = [("Estudiantes", reverse("estudiantes"))] + ([(alumno.nombre, _ficha(alumno))] if alumno else [])
    return formulario(request, form, titulo=titulo, antetitulo=alumno.nombre if alumno else "Nuevo registro",
                      volver=volver, migas=migas, exito=exito,
                      destino=lambda o: lista if (lista and not alumno) else _ficha(o.alumno, seccion))


def _editar(request, obj, form_class, *, titulo, seccion, solo_autor=True):
    comprobar_alumno(request.user, obj.alumno)
    if solo_autor:
        exigir_autor(request.user, obj)
    form = form_class(request.POST or None, request.FILES or None, instance=obj, usuario=request.user)
    return formulario(request, form, titulo=titulo, antetitulo=obj.alumno.nombre,
                      volver=_ficha(obj.alumno, seccion),
                      migas=[("Estudiantes", reverse("estudiantes")), (obj.alumno.nombre, _ficha(obj.alumno))])


def _eliminar(request, obj, *, que, seccion):
    comprobar_alumno(request.user, obj.alumno)
    exigir_autor(request.user, obj)
    return eliminar(request, obj, descripcion=f"{que} de {obj.alumno} del {obj.fecha:%d-%m-%Y}",
                    volver=_ficha(obj.alumno, seccion))


# ---------- Observaciones (M-04) ----------
@requiere("observaciones", editar=True)
def observacion_nueva(request):
    return _nuevo(request, ObservacionForm, titulo="Nueva observación", seccion="observaciones",
                  exito="Observación registrada.")


@requiere("observaciones", editar=True)
def observacion_editar(request, pk):
    return _editar(request, get_object_or_404(Observacion, pk=pk), ObservacionForm,
                   titulo="Editar observación", seccion="observaciones")


@requiere("observaciones", editar=True)
def observacion_eliminar(request, pk):
    return _eliminar(request, get_object_or_404(Observacion, pk=pk), que="la observación", seccion="observaciones")


# ---------- Seguimiento integral (M-08) ----------
@requiere("seguimiento", editar=True)
def seguimiento_nuevo(request):
    return _nuevo(request, SeguimientoForm, titulo="Nuevo registro de seguimiento", seccion="seguimiento",
                  exito="Seguimiento registrado.")


@requiere("seguimiento", editar=True)
def seguimiento_editar(request, pk):
    obj = get_object_or_404(seguimientos_visibles(request.user, Seguimiento.objects.all()), pk=pk)
    return _editar(request, obj, SeguimientoForm, titulo="Editar seguimiento", seccion="seguimiento")


@requiere("seguimiento", editar=True)
def seguimiento_eliminar(request, pk):
    obj = get_object_or_404(seguimientos_visibles(request.user, Seguimiento.objects.all()), pk=pk)
    return _eliminar(request, obj, que="el seguimiento", seccion="seguimiento")


# ---------- Evaluaciones y reevaluaciones (M-05) ----------
class FiltroEvaluaciones(FiltroForm):
    tipo = forms.ModelChoiceField(queryset=TipoEvaluacion.objects.all(), required=False, empty_label="Todos los tipos")
    estado = forms.ChoiceField(required=False, choices=[
        ("", "Todos los estados"), ("vencida", "Vencidas"), ("proxima", "Próximas"), ("al_dia", "Al día")])


@requiere("evaluaciones")
def evaluaciones(request):
    filtro = FiltroEvaluaciones(request.GET or None, cursos=cursos_visibles(request.user))
    qs = filtro.aplicar(Evaluacion.objects.filter(alumno__activo=True))
    if filtro.is_valid() and filtro.cleaned_data["tipo"]:
        qs = qs.filter(tipo=filtro.cleaned_data["tipo"])
    estado_actual = ultimas_evaluaciones(qs)
    if filtro.is_valid() and filtro.cleaned_data["estado"]:
        estado_actual = [e for e in estado_actual if e.estado == filtro.cleaned_data["estado"]]
    return render(request, "colegio/evaluaciones.html", {
        "filtro": filtro, "estado_actual": estado_actual,
        "conteo": {k: sum(1 for e in ultimas_evaluaciones() if e.estado == k) for k in ("vencida", "proxima", "al_dia")},
        "recientes": qs.select_related("alumno__curso", "tipo", "creado_por")[:15],
    })


@requiere("evaluaciones")
def evaluacion_detalle(request, pk):
    e = get_object_or_404(Evaluacion.objects.select_related("alumno__curso", "tipo", "creado_por", "modificado_por"), pk=pk)
    historial = e.alumno.evaluaciones.filter(tipo=e.tipo).select_related("creado_por")
    return render(request, "colegio/evaluacion.html", {"e": e, "historial": historial})


@requiere("evaluaciones", editar=True)
def evaluacion_nueva(request):
    if not TipoEvaluacion.objects.exists():
        messages.error(request, "Primero cree al menos un tipo de evaluación con su periodicidad.")
        return redirect("tipos_evaluacion")
    return _nuevo(request, EvaluacionForm, titulo="Registrar evaluación", seccion="evaluaciones",
                  lista=reverse("evaluaciones"), exito="Evaluación registrada. La próxima reevaluación quedó calculada.")


@requiere("evaluaciones", editar=True)
def evaluacion_editar(request, pk):
    return _editar(request, get_object_or_404(Evaluacion, pk=pk), EvaluacionForm,
                   titulo="Editar evaluación", seccion="evaluaciones", solo_autor=False)


@requiere("evaluaciones")
def tipos_evaluacion(request):
    return render(request, "colegio/tipos_evaluacion.html", {"tipos": TipoEvaluacion.objects.all()})


@requiere("evaluaciones", editar=True)
def tipo_evaluacion_form(request, pk=None):
    obj = get_object_or_404(TipoEvaluacion, pk=pk) if pk else None
    form = TipoEvaluacionForm(request.POST or None, instance=obj)
    return formulario(request, form, titulo="Editar tipo de evaluación" if obj else "Nuevo tipo de evaluación",
                      antetitulo="Evaluaciones", volver=reverse("tipos_evaluacion"),
                      migas=[("Evaluaciones", reverse("evaluaciones")), ("Tipos", reverse("tipos_evaluacion"))],
                      ayuda="Si cambia la periodicidad, las fechas de reevaluación se recalculan automáticamente.")


# ---------- Citaciones a apoderados (M-06) ----------
class FiltroCitaciones(FiltroForm):
    estado = forms.ChoiceField(required=False, choices=[("", "Todos los estados")] + Citacion.Estado.choices)


@requiere("citaciones")
def citaciones(request):
    filtro = FiltroCitaciones(request.GET or None, cursos=cursos_visibles(request.user))
    qs = filtro.aplicar(Citacion.objects.all())
    if filtro.is_valid() and filtro.cleaned_data["estado"]:
        qs = qs.filter(estado=filtro.cleaned_data["estado"])
    proximas = (Citacion.objects.filter(fecha__gte=hoy(), estado__in=["programada", "reprogramada"])
                .select_related("alumno__curso", "apoderado").order_by("fecha", "hora"))
    return render(request, "colegio/citaciones.html", {
        "filtro": filtro, "proximas": proximas,
        "pagina": paginar(request, qs.select_related("alumno__curso", "apoderado", "creado_por", "modificado_por")),
    })


@requiere("citaciones", editar=True)
def citacion_nueva(request):
    return _nuevo(request, CitacionForm, titulo="Nueva citación", seccion="citaciones",
                  lista=reverse("citaciones"), exito="Citación registrada.")


@requiere("citaciones", editar=True)
def citacion_editar(request, pk):
    return _editar(request, get_object_or_404(Citacion, pk=pk), CitacionForm,
                   titulo="Actualizar citación", seccion="citaciones", solo_autor=False)
