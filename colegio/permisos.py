"""Permisos por rol. Base: tabla 4 del documento de mejoras; Dirección tiene acceso total.

Todas las vistas pasan por aquí, así que los permisos se validan en el servidor
y no solo en la pantalla.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Alumno, Rol

D, P, DOC = Rol.DIRECCION, Rol.PSICOLOGA, Rol.DOCENTE
TODOS = {D, P, DOC}

# módulo: (roles que ven, roles que crean o editan)
MODULOS = {
    "gestion": ({D}, {D}),
    "asistencia": (TODOS, {D, DOC}),
    "observaciones": (TODOS, TODOS),
    "evaluaciones": ({D, P}, {D, P}),
    "citaciones": ({D, P}, {D, P}),
    "mensajes": (TODOS, TODOS),
    "seguimiento": (TODOS, TODOS),
    "recursos": (TODOS, TODOS),
    "comisiones": (TODOS, {D}),
    "avisos": (TODOS, {D}),
}


def puede_ver(usuario, modulo):
    return usuario.is_authenticated and usuario.is_active and usuario.rol in MODULOS[modulo][0]


def puede_editar(usuario, modulo):
    return usuario.is_authenticated and usuario.is_active and usuario.rol in MODULOS[modulo][1]


def tabla_permisos(usuario):
    return {m: {"ver": puede_ver(usuario, m), "editar": puede_editar(usuario, m)} for m in MODULOS}


def requiere(modulo, editar=False):
    """Decorador: exige sesión iniciada y permiso sobre el módulo."""
    def deco(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            ok = puede_editar(request.user, modulo) if editar else puede_ver(request.user, modulo)
            if not ok:
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envoltura
    return deco


def alumnos_visibles(usuario, incluir_baja=False):
    """Dirección y psicóloga ven a todos los pupilos; cada docente, solo los de sus cursos."""
    qs = Alumno.objects.select_related("curso")
    if not incluir_baja:
        qs = qs.filter(activo=True)
    if usuario.es_direccion or usuario.es_psicologa:
        return qs
    return qs.filter(curso__in=usuario.cursos.all())


def alumno_visible_o_404(usuario, rut):
    return get_object_or_404(alumnos_visibles(usuario, incluir_baja=usuario.es_direccion), pk=rut)


def comprobar_alumno(usuario, alumno):
    """Lanza 403 si el usuario no tiene acceso al pupilo de un registro."""
    if not alumnos_visibles(usuario, incluir_baja=True).filter(pk=alumno.pk).exists():
        raise PermissionDenied


def cursos_visibles(usuario):
    from .models import Curso
    if usuario.es_direccion or usuario.es_psicologa:
        return Curso.objects.all()
    return usuario.cursos.all()


def seguimientos_visibles(usuario, qs):
    if usuario.es_direccion or usuario.es_psicologa:
        return qs
    from django.db.models import Q
    return qs.filter(Q(confidencial=False) | Q(creado_por=usuario))
