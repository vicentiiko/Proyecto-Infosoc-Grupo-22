"""Reemplazos: Dirección puede trabajar en la cuenta de una docente o psicóloga que falte.

Mientras dura el reemplazo, la sesión guarda quién de Dirección está actuando. Todo registro que se
guarde queda con `suplente` = esa persona, para que la trazabilidad muestre quién lo hizo en realidad.
"""
import contextvars

from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

CLAVE_SESION = "suplencia"
_suplente = contextvars.ContextVar("suplente", default=None)


def datos_suplencia(request):
    return request.session.get(CLAVE_SESION) if hasattr(request, "session") else None


class SuplenciaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        datos = datos_suplencia(request)
        token = _suplente.set(datos["direccion"] if datos else None)
        try:
            return self.get_response(request)
        finally:
            _suplente.reset(token)


@receiver(pre_save)
def marcar_suplente(sender, instance, update_fields=None, **kwargs):
    from .models import Registro
    rut = _suplente.get()
    if rut and isinstance(instance, Registro) and update_fields is None:
        instance.suplente_id = rut


@receiver(user_logged_out)
def cerrar_al_salir(sender, request, user, **kwargs):
    """Si se cierra sesión durante un reemplazo, el reemplazo queda terminado."""
    from .models import Suplencia
    datos = datos_suplencia(request) if request else None
    if datos:
        Suplencia.objects.filter(pk=datos["id"], fin__isnull=True).update(fin=timezone.now())
