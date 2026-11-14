"""Piezas comunes a todas las vistas."""
import datetime

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render

from ..forms import FECHA


def formulario(request, form, *, titulo, antetitulo="", volver, migas=(), boton="Guardar",
               exito="Cambios guardados.", destino=None, ayuda=""):
    """Muestra un formulario genérico y, si es válido, lo guarda y redirige."""
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, exito)
        if callable(destino):
            return redirect(destino(obj))
        return redirect(destino or volver)
    return render(request, "colegio/form.html", {
        "form": form, "titulo": titulo, "antetitulo": antetitulo, "volver": volver,
        "migas": migas, "boton": boton, "ayuda": ayuda,
    })


def eliminar(request, obj, *, descripcion, volver, migas=()):
    """Pide confirmación y borra el registro (y su archivo, si tiene)."""
    if request.method == "POST":
        archivo = getattr(obj, "archivo", None)
        obj.delete()
        if archivo:
            archivo.delete(save=False)
        messages.success(request, "Registro eliminado.")
        return redirect(volver)
    return render(request, "colegio/eliminar.html", {"descripcion": descripcion, "volver": volver, "migas": migas})


def exigir_autor(usuario, obj):
    """Solo quien creó el registro (o Dirección) puede editarlo o borrarlo."""
    if obj.creado_por_id != usuario.pk and not usuario.es_direccion:
        raise PermissionDenied


def descargar(archivo):
    if not archivo:
        raise Http404
    try:
        f = archivo.open("rb")
    except FileNotFoundError:
        raise Http404("El archivo ya no existe.")
    return FileResponse(f, as_attachment=True, filename=archivo.name.rsplit("/", 1)[-1])


def paginar(request, qs, por_pagina=40):
    return Paginator(qs, por_pagina).get_page(request.GET.get("pagina"))


class FiltroForm(forms.Form):
    """Filtros de listados: texto, curso y rango de fechas."""
    q = forms.CharField(label="Buscar estudiante", required=False,
                        widget=forms.TextInput(attrs={"placeholder": "Nombre o RUT"}))
    curso = forms.ModelChoiceField(queryset=None, required=False, empty_label="Todos los cursos")
    desde = forms.DateField(required=False, widget=FECHA)
    hasta = forms.DateField(required=False, widget=FECHA)

    def __init__(self, *args, cursos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["curso"].queryset = cursos

    def aplicar(self, qs, campo_fecha="fecha", prefijo="alumno__"):
        if not self.is_valid():
            return qs
        d = self.cleaned_data
        if d["q"]:
            from django.db.models import Q
            qs = qs.filter(Q(**{f"{prefijo}nombre__icontains": d["q"]}) | Q(**{f"{prefijo}rut__icontains": d["q"]}))
        if d["curso"]:
            qs = qs.filter(**{f"{prefijo}curso": d["curso"]})
        if d["desde"]:
            qs = qs.filter(**{f"{campo_fecha}__gte": d["desde"]})
        if d["hasta"]:
            qs = qs.filter(**{f"{campo_fecha}__lte": d["hasta"]})
        return qs


def primer_dia_mes(dia):
    return dia.replace(day=1)


def leer_fecha(texto, defecto):
    try:
        return datetime.date.fromisoformat(texto)
    except (TypeError, ValueError):
        return defecto
