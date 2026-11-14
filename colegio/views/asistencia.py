from django import forms
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from ..forms import AtrasoForm, InasistenciaForm, PasarListaForm
from ..models import Atraso, Inasistencia, hoy
from ..permisos import alumno_visible_o_404, alumnos_visibles, comprobar_alumno, cursos_visibles, requiere
from .base import FiltroForm, eliminar, formulario, leer_fecha, paginar

def _alumno_param(request):
    rut = request.GET.get("alumno")
    return alumno_visible_o_404(request.user, rut) if rut else None


def _volver(request, alumno, defecto):
    return reverse("ficha", args=[alumno.pk]) if alumno and request.GET.get("desde") == "ficha" else defecto


# ---------- Atrasos ----------
@requiere("asistencia")
def atrasos(request):
    u = request.user
    filtro = FiltroForm(request.GET or None, cursos=cursos_visibles(u))
    qs = filtro.aplicar(Atraso.objects.filter(alumno__in=alumnos_visibles(u, incluir_baja=True)))
    resumen = (qs.values("alumno__rut", "alumno__nombre", "alumno__curso__nivel")
               .annotate(total=Count("id")).order_by("-total", "alumno__nombre")[:15])
    return render(request, "colegio/atrasos.html", {
        "filtro": filtro, "resumen": resumen, "total": qs.count(),
        "pagina": paginar(request, qs.select_related("alumno__curso", "creado_por")),
    })


@requiere("asistencia", editar=True)
def atraso_nuevo(request):
    alumno = _alumno_param(request)
    volver = _volver(request, alumno, reverse("atrasos"))
    inicial = {"hora_llegada": timezone.localtime().strftime("%H:%M")}
    form = AtrasoForm(request.POST or None, usuario=request.user, alumno=alumno, initial=inicial)
    return formulario(request, form, titulo="Registrar atraso", antetitulo=alumno.nombre if alumno else "Asistencia",
                      volver=volver, migas=[("Atrasos", reverse("atrasos"))], exito="Atraso registrado.")


@requiere("asistencia", editar=True)
def atraso_editar(request, pk):
    obj = get_object_or_404(Atraso, pk=pk)
    comprobar_alumno(request.user, obj.alumno)
    form = AtrasoForm(request.POST or None, instance=obj, usuario=request.user)
    return formulario(request, form, titulo="Editar atraso", antetitulo=obj.alumno.nombre,
                      volver=reverse("atrasos"), migas=[("Atrasos", reverse("atrasos"))])


@requiere("asistencia", editar=True)
def atraso_eliminar(request, pk):
    obj = get_object_or_404(Atraso, pk=pk)
    comprobar_alumno(request.user, obj.alumno)
    return eliminar(request, obj, descripcion=f"el atraso de {obj.alumno} del {obj.fecha:%d-%m-%Y}",
                    volver=reverse("atrasos"))


# ---------- Inasistencias ----------
class FiltroInasistencias(FiltroForm):
    estado = forms.ChoiceField(required=False, choices=[("", "Todas"), ("si", "Justificadas"), ("no", "No justificadas")])


@requiere("asistencia")
def inasistencias(request):
    u = request.user
    filtro = FiltroInasistencias(request.GET or None, cursos=cursos_visibles(u))
    qs = filtro.aplicar(Inasistencia.objects.filter(alumno__in=alumnos_visibles(u, incluir_baja=True)))
    if filtro.is_valid() and filtro.cleaned_data["estado"]:
        qs = qs.filter(justificada=filtro.cleaned_data["estado"] == "si")
    resumen = (qs.values("alumno__rut", "alumno__nombre", "alumno__curso__nivel")
               .annotate(total=Count("id"), justificadas=Count("id", filter=Q(justificada=True)))
               .order_by("-total", "alumno__nombre")[:15])
    por_curso = (qs.values("alumno__curso__nivel")
                 .annotate(total=Count("id"), justificadas=Count("id", filter=Q(justificada=True)),
                           injustificadas=Count("id", filter=Q(justificada=False)))
                 .order_by("alumno__curso__nivel"))
    return render(request, "colegio/inasistencias.html", {
        "filtro": filtro, "resumen": resumen, "por_curso": por_curso, "total": qs.count(),
        "pagina": paginar(request, qs.select_related("alumno__curso", "creado_por")),
    })


@requiere("asistencia", editar=True)
def inasistencia_nueva(request):
    alumno = _alumno_param(request)
    volver = _volver(request, alumno, reverse("inasistencias"))
    form = InasistenciaForm(request.POST or None, usuario=request.user, alumno=alumno)
    return formulario(request, form, titulo="Registrar inasistencia",
                      antetitulo=alumno.nombre if alumno else "Asistencia", volver=volver,
                      migas=[("Inasistencias", reverse("inasistencias"))], exito="Inasistencia registrada.")


@requiere("asistencia", editar=True)
def inasistencia_editar(request, pk):
    obj = get_object_or_404(Inasistencia, pk=pk)
    comprobar_alumno(request.user, obj.alumno)
    form = InasistenciaForm(request.POST or None, instance=obj, usuario=request.user)
    return formulario(request, form, titulo="Editar inasistencia", antetitulo=obj.alumno.nombre,
                      volver=reverse("inasistencias"), migas=[("Inasistencias", reverse("inasistencias"))])


@requiere("asistencia", editar=True)
def inasistencia_eliminar(request, pk):
    obj = get_object_or_404(Inasistencia, pk=pk)
    comprobar_alumno(request.user, obj.alumno)
    return eliminar(request, obj, descripcion=f"la inasistencia de {obj.alumno} del {obj.fecha:%d-%m-%Y}",
                    volver=reverse("inasistencias"))


@requiere("asistencia", editar=True)
def pasar_lista(request):
    """Registro rápido de inasistencias de un curso completo para una fecha."""
    u = request.user
    cursos = cursos_visibles(u)
    datos = request.POST if request.method == "POST" else request.GET
    elegido = cursos.filter(pk=datos.get("curso")).first() or cursos.first()
    fecha = leer_fecha(datos.get("fecha"), hoy())
    selector = PasarListaForm(initial={"curso": elegido, "fecha": fecha}, cursos=cursos)
    alumnos = list(elegido.alumnos.filter(activo=True)) if elegido else []

    if request.method == "POST" and elegido:
        presentes = ausentes = 0
        with transaction.atomic():
            for a in alumnos:
                estado = request.POST.get(f"estado_{a.pk}", "presente")
                existente = Inasistencia.objects.filter(alumno=a, fecha=fecha).first()
                if estado in ("ausente", "justificada"):
                    obj = existente or Inasistencia(alumno=a, fecha=fecha, creado_por=u)
                    obj.justificada = estado == "justificada"
                    obj.modificado_por = u
                    obj.save()
                    ausentes += 1
                else:
                    if existente:
                        existente.delete()
                    presentes += 1
        messages.success(request, f"Asistencia de {elegido} del {fecha:%d-%m-%Y} guardada: "
                                  f"{presentes} presente(s) y {ausentes} ausente(s).")
        return redirect(f"{reverse('pasar_lista')}?curso={elegido.pk}&fecha={fecha:%Y-%m-%d}")

    registradas = {i.alumno_id: i for i in Inasistencia.objects.filter(alumno__in=alumnos, fecha=fecha)}
    filas = [(a, registradas.get(a.pk)) for a in alumnos]
    return render(request, "colegio/pasar_lista.html", {
        "selector": selector, "curso": elegido, "fecha": fecha, "filas": filas,
    })
