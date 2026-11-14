"""Gestión de usuarios, cursos y pupilos (M-01). Solo Dirección."""
from django.contrib import messages
from django.contrib.auth import login
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..forms import AlumnoForm, ApoderadosFormSet, BajaForm, CursoForm, UsuarioForm
from ..models import Alumno, AlumnoApoderado, Apoderado, Curso, Rol, Suplencia, Usuario, hoy
from ..permisos import requiere
from ..suplencia import CLAVE_SESION, datos_suplencia
from .base import formulario, paginar


# ---------- Usuarios ----------
@requiere("gestion")
def usuarios(request):
    qs = Usuario.objects.prefetch_related("cursos")
    rol, estado, q = request.GET.get("rol", ""), request.GET.get("estado", "activos"), request.GET.get("q", "").strip()
    if rol:
        qs = qs.filter(rol=rol)
    if estado == "activos":
        qs = qs.filter(is_active=True)
    elif estado == "inactivos":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(rut__icontains=q) | Q(email__icontains=q))
    return render(request, "colegio/gestion_usuarios.html", {
        "pagina": paginar(request, qs), "roles": Rol.choices, "rol": rol, "estado": estado, "q": q})


@requiere("gestion", editar=True)
def usuario_form(request, rut=None):
    obj = get_object_or_404(Usuario, pk=rut) if rut else None
    form = UsuarioForm(request.POST or None, instance=obj)
    return formulario(request, form, titulo=f"Editar a {obj.nombre}" if obj else "Nuevo usuario",
                      antetitulo="Gestión de usuarios", volver=reverse("usuarios"),
                      migas=[("Usuarios", reverse("usuarios"))], exito="Usuario guardado.",
                      ayuda="Los apoderados no son usuarios: se registran como contacto en la ficha del pupilo.")


@requiere("gestion", editar=True)
def usuario_estado(request, rut):
    u = get_object_or_404(Usuario, pk=rut)
    if request.method == "POST":
        if u == request.user:
            messages.error(request, "No puede desactivar su propia cuenta.")
        else:
            u.is_active = not u.is_active
            u.save(update_fields=["is_active"])
            messages.success(request, f"Cuenta de {u.nombre} {'activada' if u.is_active else 'desactivada'}.")
    return redirect("usuarios")


# ---------- Cursos ----------
@requiere("gestion")
def cursos(request):
    qs = Curso.objects.annotate(n=Count("alumnos", filter=Q(alumnos__activo=True))).prefetch_related(
        "asignaciones__usuario")
    return render(request, "colegio/gestion_cursos.html", {"cursos": qs})


@requiere("gestion", editar=True)
def curso_form(request, pk=None):
    obj = get_object_or_404(Curso, pk=pk) if pk else None
    form = CursoForm(request.POST or None, instance=obj, usuario=request.user)
    return formulario(request, form, titulo=f"Editar {obj}" if obj else "Nuevo curso", antetitulo="Gestión de cursos",
                      volver=reverse("cursos"), migas=[("Cursos", reverse("cursos"))], exito="Curso guardado.",
                      ayuda="Los docentes y la psicóloga se asignan a cursos desde Gestión → Usuarios.")


# ---------- Pupilos ----------
@requiere("gestion")
def pupilos(request):
    qs = Alumno.objects.select_related("curso").prefetch_related("vinculos__apoderado")
    curso, estado, q = request.GET.get("curso", ""), request.GET.get("estado", "activos"), request.GET.get("q", "").strip()
    if curso:
        qs = qs.filter(curso_id=curso)
    if estado == "activos":
        qs = qs.filter(activo=True)
    elif estado == "baja":
        qs = qs.filter(activo=False)
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(rut__icontains=q))
    return render(request, "colegio/gestion_pupilos.html", {
        "pagina": paginar(request, qs), "cursos": Curso.objects.all(), "curso": curso, "estado": estado, "q": q})


def _guardar_apoderados(alumno, formset):
    vistos = set()
    for f in formset.forms:
        d = f.cleaned_data
        if not d or d.get("DELETE"):
            continue
        ap, _ = Apoderado.objects.update_or_create(
            rut=d["rut"], defaults={"nombre": d["nombre"], "telefono": d["telefono"], "email": d["email"]})
        AlumnoApoderado.objects.update_or_create(
            alumno=alumno, apoderado=ap, defaults={"parentesco": d["parentesco"], "es_principal": d["es_principal"]})
        vistos.add(ap.pk)
    alumno.vinculos.exclude(apoderado__in=vistos).delete()


@requiere("gestion", editar=True)
def pupilo_form(request, rut=None):
    obj = get_object_or_404(Alumno, pk=rut) if rut else None
    inicial = [{"rut": v.apoderado.rut, "nombre": v.apoderado.nombre, "telefono": v.apoderado.telefono,
                "email": v.apoderado.email, "parentesco": v.parentesco, "es_principal": v.es_principal}
               for v in obj.vinculos.select_related("apoderado")] if obj else []
    form = AlumnoForm(request.POST or None, instance=obj)
    formset = ApoderadosFormSet(request.POST or None, initial=inicial, prefix="ap")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            alumno = form.save(commit=False)
            if alumno._state.adding:
                alumno.creado_por = request.user
            alumno.modificado_por = request.user
            alumno.save()
            _guardar_apoderados(alumno, formset)
        messages.success(request, "Pupilo guardado.")
        return redirect("pupilos")
    return render(request, "colegio/gestion_pupilo_form.html", {"form": form, "formset": formset, "obj": obj})


@requiere("gestion", editar=True)
def pupilo_baja(request, rut):
    obj = get_object_or_404(Alumno, pk=rut, activo=True)
    form = BajaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj.activo, obj.fecha_baja, obj.motivo_baja = False, hoy(), form.cleaned_data["motivo"]
        obj.modificado_por = request.user
        obj.save()
        messages.success(request, f"{obj.nombre} quedó dado de baja. Su historial se conserva.")
        return redirect("pupilos")
    return render(request, "colegio/form.html", {
        "form": form, "titulo": f"Dar de baja a {obj.nombre}", "antetitulo": "Gestión de pupilos",
        "volver": reverse("pupilos"), "migas": [("Pupilos", reverse("pupilos"))], "boton": "Dar de baja",
        "ayuda": "El pupilo deja de aparecer en los listados, pero su historial queda guardado y se puede reactivar.",
    })


@requiere("gestion", editar=True)
def pupilo_reactivar(request, rut):
    obj = get_object_or_404(Alumno, pk=rut, activo=False)
    if request.method == "POST":
        obj.activo, obj.fecha_baja, obj.motivo_baja, obj.modificado_por = True, None, "", request.user
        obj.save()
        messages.success(request, f"{obj.nombre} fue reactivado.")
    return redirect("pupilos")


# ---------- Reemplazos ----------
BACKEND = "django.contrib.auth.backends.ModelBackend"


@requiere("gestion", editar=True)
def actuar_como(request, rut):
    """Dirección entra a la cuenta de una docente o psicóloga para reemplazarla."""
    if request.method != "POST":
        return redirect("usuarios")
    if datos_suplencia(request):
        messages.error(request, "Ya está trabajando en un reemplazo. Vuelva a su cuenta primero.")
        return redirect("inicio")
    otro = get_object_or_404(Usuario, pk=rut, is_active=True)
    if otro.es_direccion:
        raise PermissionDenied
    yo = request.user
    s = Suplencia.objects.create(direccion=yo, usuario=otro, motivo=request.POST.get("motivo", "")[:200])
    login(request, otro, backend=BACKEND)  # cambia la sesión a la otra cuenta
    request.session[CLAVE_SESION] = {"direccion": yo.pk, "nombre": yo.nombre, "id": s.pk}
    messages.success(request, f"Ahora está trabajando en reemplazo de {otro.nombre}.")
    return redirect("inicio")


def volver_a_mi_cuenta(request):
    datos = datos_suplencia(request)
    if request.method != "POST" or not datos:
        return redirect("inicio")
    from django.utils import timezone
    Suplencia.objects.filter(pk=datos["id"], fin__isnull=True).update(fin=timezone.now())
    reemplazado = request.user.nombre
    yo = get_object_or_404(Usuario, pk=datos["direccion"], is_active=True)
    login(request, yo, backend=BACKEND)
    request.session.pop(CLAVE_SESION, None)
    messages.success(request, f"Terminó el reemplazo de {reemplazado}. Volvió a su cuenta.")
    return redirect("usuarios")


@requiere("gestion")
def suplencias(request):
    qs = Suplencia.objects.select_related("direccion", "usuario")
    return render(request, "colegio/gestion_suplencias.html", {"pagina": paginar(request, qs)})
