"""Recursos digitales, comisiones e información general."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..forms import AvisoForm, ComisionForm, PublicacionForm, RecursoForm
from ..models import Aviso, Comision, PublicacionComision, Recurso
from ..permisos import requiere
from .base import descargar, eliminar, exigir_autor, formulario, paginar


def _con_autor(form, usuario):
    """Guarda un formulario de modelo con trazabilidad (creado/modificado por)."""
    obj = form.save(commit=False)
    if obj._state.adding:
        obj.creado_por = usuario
    obj.modificado_por = usuario
    obj.save()
    form.save_m2m()
    return obj


class ConAutor:
    """Envuelve un ModelForm para que form.save() registre al autor."""

    def __init__(self, form, usuario):
        self._form, self._usuario = form, usuario

    def __getattr__(self, nombre):
        return getattr(self._form, nombre)

    def __iter__(self):
        return iter(self._form)

    def save(self):
        return _con_autor(self._form, self._usuario)


# ---------- Recursos digitales (M-09) ----------
@requiere("recursos")
def recursos(request):
    qs = Recurso.objects.visibles_para(request.user).select_related("creado_por").prefetch_related("usuarios")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(titulo__icontains=q) | Q(descripcion__icontains=q))
    return render(request, "colegio/recursos.html", {"pagina": paginar(request, qs, 30), "q": q})


@requiere("recursos", editar=True)
def recurso_nuevo(request):
    form = RecursoForm(request.POST or None, request.FILES or None, usuario=request.user)
    return formulario(request, ConAutor(form, request.user), titulo="Subir recurso digital", antetitulo="Recursos",
                      volver=reverse("recursos"), migas=[("Recursos", reverse("recursos"))], boton="Subir recurso",
                      exito="Recurso subido.",
                      ayuda="Elija quién más puede verlo. Si no marca ninguna opción, quedará solo para usted.")


@requiere("recursos", editar=True)
def recurso_editar(request, pk):
    obj = get_object_or_404(Recurso, pk=pk)
    exigir_autor(request.user, obj)
    form = RecursoForm(request.POST or None, request.FILES or None, instance=obj, usuario=request.user)
    return formulario(request, ConAutor(form, request.user), titulo="Editar recurso", antetitulo=obj.titulo,
                      volver=reverse("recursos"), migas=[("Recursos", reverse("recursos"))])


@requiere("recursos", editar=True)
def recurso_eliminar(request, pk):
    obj = get_object_or_404(Recurso, pk=pk)
    exigir_autor(request.user, obj)
    return eliminar(request, obj, descripcion=f"el recurso «{obj.titulo}»", volver=reverse("recursos"))


@requiere("recursos")
def recurso_descargar(request, pk):
    # La visibilidad se valida aquí, en el servidor: si no le fue asignado, responde 404.
    obj = get_object_or_404(Recurso.objects.visibles_para(request.user), pk=pk)
    return descargar(obj.archivo)


# ---------- Comisiones (M-10) ----------
def _comisiones_de(usuario):
    if usuario.es_direccion:
        return Comision.objects.all()
    return usuario.comisiones.all()


@requiere("comisiones")
def comisiones(request):
    qs = _comisiones_de(request.user).prefetch_related("integrantes")
    return render(request, "colegio/comisiones.html", {"comisiones": qs})


@requiere("comisiones")
def comision(request, pk):
    c = get_object_or_404(_comisiones_de(request.user), pk=pk)
    form = PublicacionForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        pub = form.save(commit=False)
        pub.comision, pub.creado_por, pub.modificado_por = c, request.user, request.user
        pub.save()
        messages.success(request, "Publicado en la comisión.")
        return redirect("comision", pk=c.pk)
    return render(request, "colegio/comision.html", {
        "c": c, "form": form, "integrantes": c.integrantes.all(),
        "publicaciones": c.publicaciones.select_related("creado_por"),
    })


@requiere("comisiones", editar=True)
def comision_form(request, pk=None):
    obj = get_object_or_404(Comision, pk=pk) if pk else None
    form = ComisionForm(request.POST or None, instance=obj)
    return formulario(request, ConAutor(form, request.user),
                      titulo="Editar comisión" if obj else "Nueva comisión", antetitulo="Comisiones",
                      volver=reverse("comision", args=[obj.pk]) if obj else reverse("comisiones"),
                      migas=[("Comisiones", reverse("comisiones"))], exito="Comisión guardada.",
                      destino=lambda o: reverse("comision", args=[o.pk]))


@requiere("comisiones")
def publicacion_eliminar(request, pk):
    pub = get_object_or_404(PublicacionComision.objects.filter(comision__in=_comisiones_de(request.user)), pk=pk)
    if pub.creado_por_id != request.user.pk and not request.user.es_direccion:
        raise PermissionDenied
    return eliminar(request, pub, descripcion="esta publicación", volver=reverse("comision", args=[pub.comision_id]))


@requiere("comisiones")
def publicacion_descargar(request, pk):
    pub = get_object_or_404(PublicacionComision.objects.filter(comision__in=_comisiones_de(request.user)), pk=pk)
    return descargar(pub.archivo)


# ---------- Información general (M-11) ----------
@requiere("avisos")
def avisos(request):
    return render(request, "colegio/avisos.html", {
        "pagina": paginar(request, Aviso.objects.select_related("creado_por"), 15)})


@requiere("avisos", editar=True)
def aviso_form(request, pk=None):
    obj = get_object_or_404(Aviso, pk=pk) if pk else None
    form = AvisoForm(request.POST or None, instance=obj)
    return formulario(request, ConAutor(form, request.user),
                      titulo="Editar aviso" if obj else "Publicar aviso", antetitulo="Información general",
                      volver=reverse("avisos"), migas=[("Avisos", reverse("avisos"))],
                      boton="Publicar" if not obj else "Guardar", exito="Aviso publicado.")


@requiere("avisos", editar=True)
def aviso_eliminar(request, pk):
    obj = get_object_or_404(Aviso, pk=pk)
    return eliminar(request, obj, descripcion=f"el aviso «{obj.titulo}»", volver=reverse("avisos"))
