"""Mensajería interna entre Dirección, psicólogas y docentes.

Cada conversación la ven sus participantes. Dirección puede ver todas.
"""
from django.contrib import messages
from django.db.models import Max, Q
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from ..forms import MensajeForm, RespuestaForm
from ..models import Destinatario, Mensaje
from ..permisos import alumno_visible_o_404, requiere
from .base import descargar, paginar


def sin_leer_por_conversacion(usuario):
    """{id de la conversación: cantidad de mensajes sin leer}"""
    conteo = {}
    for raiz_id, mensaje_id in (Destinatario.objects.filter(usuario=usuario, leido_en__isnull=True)
                                .values_list("mensaje__hilo_id", "mensaje_id")):
        k = raiz_id or mensaje_id
        conteo[k] = conteo.get(k, 0) + 1
    return conteo


def conversaciones(usuario, todas=False):
    base = Mensaje.objects.filter(hilo__isnull=True) if todas else Mensaje.objects.conversaciones_de(usuario)
    return (base
            .annotate(ultima=Coalesce(Max("respuestas__creado_en"), "creado_en"))
            .select_related("creado_por", "alumno").prefetch_related("destinatarios")
            .order_by("-ultima"))


@requiere("mensajes")
def bandeja(request):
    u = request.user
    vista = request.GET.get("ver", "todos")
    q = request.GET.get("q", "").strip()
    if vista == "todas" and not u.es_direccion:
        vista = "todos"
    qs = conversaciones(u, todas=vista == "todas")
    sin_leer = sin_leer_por_conversacion(u)
    if vista == "sin_leer":
        qs = qs.filter(pk__in=sin_leer.keys())
    elif vista == "enviados":
        qs = qs.filter(creado_por=u)
    elif vista == "recibidos":
        qs = qs.exclude(creado_por=u)
    if q:
        qs = qs.filter(Q(asunto__icontains=q) | Q(cuerpo__icontains=q) | Q(respuestas__cuerpo__icontains=q)
                       | Q(alumno__nombre__icontains=q)).distinct()
    pagina = paginar(request, qs, 25)
    for c in pagina:
        c.sin_leer = sin_leer.get(c.pk, 0)
    return render(request, "colegio/mensajes.html", {"pagina": pagina, "vista": vista, "q": q})


@requiere("mensajes")
def nuevo(request):
    rut = request.GET.get("alumno")
    alumno = alumno_visible_o_404(request.user, rut) if rut else None
    form = MensajeForm(request.POST or None, request.FILES or None, usuario=request.user, alumno=alumno)
    if request.method == "POST" and form.is_valid():
        m = form.save()
        messages.success(request, f"Mensaje enviado a {len(form.ids_destinatarios)} persona(s).")
        return redirect("conversacion", pk=m.pk)
    volver = reverse("ficha", args=[alumno.pk]) + "#mensajes" if alumno else reverse("mensajes")
    return render(request, "colegio/form.html", {
        "form": form, "titulo": "Nuevo mensaje", "antetitulo": alumno.nombre if alumno else "Mensajes",
        "volver": volver, "migas": [("Mensajes", reverse("mensajes"))], "boton": "Enviar",
        "ayuda": "Puede combinar grupos, el equipo de un curso y personas específicas. "
                 "La conversación la verán usted, los destinatarios y Dirección.",
    })


@requiere("mensajes")
def conversacion(request, pk):
    raiz = get_object_or_404(Mensaje.objects.select_related("creado_por", "alumno__curso"), pk=pk, hilo__isnull=True)
    u = request.user
    if not (raiz.participa(u) or u.es_direccion):
        raise Http404
    form = RespuestaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.guardar(raiz, u)
        messages.success(request, "Respuesta enviada.")
        return redirect(reverse("conversacion", args=[raiz.pk]) + "#ultimo")
    hilo = [raiz] + list(raiz.respuestas.select_related("creado_por", "suplente"))
    Destinatario.objects.filter(usuario=u, leido_en__isnull=True).filter(
        Q(mensaje=raiz) | Q(mensaje__hilo=raiz)).update(leido_en=timezone.now())
    return render(request, "colegio/conversacion.html", {
        "raiz": raiz, "hilo": hilo, "form": form, "participantes": raiz.participantes(),
        "participa": raiz.participa(u),
    })


@requiere("mensajes")
def adjunto(request, pk):
    m = get_object_or_404(Mensaje, pk=pk)
    if not (m.participa(request.user) or request.user.es_direccion):
        raise Http404
    return descargar(m.archivo)
