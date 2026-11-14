from .models import Destinatario, reevaluaciones_pendientes
from .permisos import tabla_permisos
from .suplencia import datos_suplencia


def portal(request):
    """Datos que usan el menú y los avisos en todas las páginas."""
    u = request.user
    if not u.is_authenticated:
        return {}
    datos = {"permisos": tabla_permisos(u),
             "n_mensajes": Destinatario.objects.filter(usuario=u, leido_en__isnull=True).count()}
    datos["suplencia"] = datos_suplencia(request)
    if u.es_direccion or u.es_psicologa:
        datos["n_reevaluaciones"] = len(reevaluaciones_pendientes())
    return datos
