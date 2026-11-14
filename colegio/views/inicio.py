from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from ..models import (Alumno, Atraso, Aviso, Citacion, Inasistencia, Usuario, hoy,
                      reevaluaciones_pendientes)
from ..permisos import alumnos_visibles
from .mensajes import conversaciones, sin_leer_por_conversacion


@login_required
def inicio(request):
    u, dia = request.user, hoy()
    mes = dia.replace(day=1)
    sin_leer = sin_leer_por_conversacion(u)
    pendientes_msj = list(conversaciones(u).filter(pk__in=sin_leer.keys())[:5])
    for c in pendientes_msj:
        c.sin_leer = sin_leer[c.pk]
    ctx = {"avisos": Aviso.objects.select_related("creado_por")[:4], "mensajes_pendientes": pendientes_msj}
    alumnos = alumnos_visibles(u)
    atrasos_mes = Atraso.objects.filter(alumno__in=alumnos, fecha__gte=mes).count()
    inasist_mes = Inasistencia.objects.filter(alumno__in=alumnos, fecha__gte=mes).count()

    if u.es_direccion or u.es_psicologa:
        pendientes = reevaluaciones_pendientes()
        vencidas = sum(1 for e in pendientes if e.estado == "vencida")
        ctx["reevaluaciones"] = pendientes[:8]
        ctx["citaciones"] = (Citacion.objects.filter(fecha__gte=dia, estado__in=["programada", "reprogramada"])
                             .select_related("alumno", "apoderado").order_by("fecha", "hora")[:6])
        ctx["indicadores"] = [
            (alumnos.count(), "Estudiantes activos", None),
            (vencidas, "Reevaluaciones vencidas", "alerta" if vencidas else None),
            (len(pendientes) - vencidas, "Reevaluaciones próximas", "aviso" if len(pendientes) - vencidas else None),
            (Citacion.objects.filter(fecha__gte=dia, estado="programada").count(), "Citaciones programadas", None),
        ]
        if u.es_direccion:
            ctx["indicadores"][3:3] = [(Usuario.objects.filter(is_active=True).count(), "Personal activo", None)]
            ctx["indicadores"] += [(atrasos_mes, "Atrasos este mes", None), (inasist_mes, "Inasistencias este mes", None)]
    else:
        ctx["cursos"] = u.cursos.annotate(n=Count("alumnos", filter=Q(alumnos__activo=True)))
        ctx["indicadores"] = [
            (ctx["cursos"].count(), "Mis cursos", None),
            (alumnos.count(), "Mis estudiantes", None),
            (Atraso.objects.filter(alumno__in=alumnos, fecha=dia).count(), "Atrasos hoy", None),
            (Inasistencia.objects.filter(alumno__in=alumnos, fecha=dia).count(), "Inasistencias hoy", None),
        ]
    return render(request, "colegio/inicio.html", ctx)
