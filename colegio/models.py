import calendar
import datetime
import os
import re

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

# Días de anticipación con que se avisa una reevaluación próxima.
DIAS_AVISO_REEVALUACION = 60
# Tamaño máximo de los archivos subidos (MB).
MAX_ARCHIVO_MB = 20


# ---------- Utilidades ----------
def sumar_meses(fecha, meses):
    """Suma meses a una fecha. Si el día no existe (ej. 31 de febrero) usa el último del mes."""
    m = fecha.month - 1 + meses
    anio, mes = fecha.year + m // 12, m % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return datetime.date(anio, mes, dia)


def validar_rut(valor):
    if not re.fullmatch(r"\d{7,8}-[\dkK]", valor or ""):
        raise ValidationError("Use el formato 12345678-9: sin puntos, con guion y dígito verificador.")


def validar_tamano(archivo):
    if archivo and archivo.size > MAX_ARCHIVO_MB * 1024 * 1024:
        raise ValidationError(f"El archivo supera el máximo de {MAX_ARCHIVO_MB} MB.")


def hoy():
    return timezone.localdate()


# ---------- Usuarios ----------
class Rol(models.TextChoices):
    DIRECCION = "direccion", "Dirección"
    PSICOLOGA = "psicologa", "Psicóloga"
    DOCENTE = "docente", "Docente"


class UsuarioManager(BaseUserManager):
    def create_user(self, rut, email, nombre, password=None, **extra):
        if not rut:
            raise ValueError("El RUT es obligatorio")
        user = self.model(rut=rut, email=self.normalize_email(email), nombre=nombre, **extra)
        user.set_password(password)  # se guarda hasheada, nunca en texto plano
        user.save(using=self._db)
        return user

    def create_superuser(self, rut, email, nombre, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("rol", Rol.DIRECCION)
        return self.create_user(rut, email, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Personal del colegio que usa la plataforma. Inicia sesión con su RUT."""
    rut = models.CharField("RUT", max_length=10, primary_key=True, validators=[validar_rut])
    nombre = models.CharField(max_length=60)
    email = models.EmailField("correo", max_length=60, unique=True)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.DOCENTE)
    asignatura = models.CharField(max_length=40, blank=True, help_text="Solo para docentes.")
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al panel de Django", default=False)

    USERNAME_FIELD = "rut"
    REQUIRED_FIELDS = ["email", "nombre"]
    objects = UsuarioManager()

    class Meta:
        ordering = ["nombre"]
        verbose_name = "usuario"

    def __str__(self):
        return self.nombre

    @property
    def es_direccion(self):
        return self.rol == Rol.DIRECCION

    @property
    def es_psicologa(self):
        return self.rol == Rol.PSICOLOGA

    @property
    def es_docente(self):
        return self.rol == Rol.DOCENTE


class Registro(models.Model):
    """Trazabilidad: quién creó o modificó cada registro y cuándo."""
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                   related_name="+", editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                       related_name="+", editable=False)
    modificado_en = models.DateTimeField(auto_now=True)
    # Si Dirección lo registró trabajando en reemplazo de otra persona, queda aquí quién fue.
    suplente = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="+", editable=False, verbose_name="realizado en reemplazo por")

    class Meta:
        abstract = True

    @property
    def fue_modificado(self):
        return (self.modificado_en - self.creado_en).total_seconds() > 5


# ---------- Cursos, pupilos y apoderados ----------
class Curso(models.Model):
    nivel = models.CharField(max_length=20, unique=True)
    capacidad = models.PositiveIntegerField(default=0)
    equipo = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Asignacion", related_name="cursos", blank=True)

    class Meta:
        ordering = ["nivel"]

    def __str__(self):
        return self.nivel

    @property
    def profesor_jefe(self):
        a = self.asignaciones.filter(profesor_jefe=True).select_related("usuario").first()
        return a.usuario if a else None


class Asignacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asignaciones")
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name="asignaciones")
    profesor_jefe = models.BooleanField(default=False)

    class Meta:
        unique_together = ("usuario", "curso")
        verbose_name = "asignación de curso"
        verbose_name_plural = "asignaciones de curso"


class Apoderado(models.Model):
    """Solo datos de contacto: los apoderados no entran al sistema."""
    rut = models.CharField("RUT", max_length=10, primary_key=True, validators=[validar_rut])
    nombre = models.CharField(max_length=60)
    telefono = models.CharField("teléfono", max_length=15, blank=True)
    email = models.EmailField("correo", max_length=60, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Alumno(Registro):
    rut = models.CharField("RUT", max_length=10, primary_key=True, validators=[validar_rut])
    nombre = models.CharField(max_length=60)
    fecha_nacimiento = models.DateField("fecha de nacimiento", null=True, blank=True)
    curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.SET_NULL, related_name="alumnos")
    activo = models.BooleanField(default=True)
    fecha_baja = models.DateField(null=True, blank=True)
    motivo_baja = models.CharField(max_length=200, blank=True)
    apoderados = models.ManyToManyField(Apoderado, through="AlumnoApoderado", related_name="alumnos")

    class Meta:
        ordering = ["nombre"]
        verbose_name = "pupilo"

    def __str__(self):
        return self.nombre


class AlumnoApoderado(models.Model):
    apoderado = models.ForeignKey(Apoderado, on_delete=models.CASCADE, related_name="vinculos")
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="vinculos")
    parentesco = models.CharField(max_length=30)
    es_principal = models.BooleanField("apoderado principal", default=False)

    class Meta:
        unique_together = ("apoderado", "alumno")
        ordering = ["-es_principal", "apoderado__nombre"]


# ---------- Asistencia ----------
class Atraso(Registro):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="atrasos")
    fecha = models.DateField(default=hoy)
    hora_llegada = models.TimeField("hora de llegada")
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-fecha", "-hora_llegada"]


class Inasistencia(Registro):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="inasistencias")
    fecha = models.DateField(default=hoy)
    justificada = models.BooleanField(default=False)
    motivo = models.CharField("motivo o justificación", max_length=200, blank=True)

    class Meta:
        ordering = ["-fecha"]
        unique_together = ("alumno", "fecha")


# ---------- Observaciones y seguimiento ----------
class Observacion(Registro):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="observaciones")
    fecha = models.DateField(default=hoy)
    contenido = models.TextField("observación")

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name_plural = "observaciones"


class Seguimiento(Registro):
    class Tipo(models.TextChoices):
        SEGUIMIENTO = "seguimiento", "Seguimiento"
        PLANIFICACION = "planificacion", "Planificación de apoyo"

    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="seguimientos")
    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.SEGUIMIENTO)
    fecha = models.DateField(default=hoy)
    titulo = models.CharField("título", max_length=120)
    contenido = models.TextField()
    confidencial = models.BooleanField(
        default=False, help_text="Solo psicóloga y Dirección podrán verlo (información psicológica).")

    class Meta:
        ordering = ["-fecha", "-pk"]


# ---------- Evaluaciones ----------
class TipoEvaluacion(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    periodicidad_meses = models.PositiveSmallIntegerField(
        "periodicidad (meses)", help_text="Cada cuántos meses corresponde reevaluar.")
    descripcion = models.CharField("descripción", max_length=200, blank=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "tipo de evaluación"
        verbose_name_plural = "tipos de evaluación"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for e in self.evaluaciones.all():  # recalcula si cambió la periodicidad
            e.save(update_fields=["proxima_reevaluacion"])


def estado_reevaluacion(fecha, dia=None):
    dia = dia or hoy()
    if fecha < dia:
        return "vencida"
    if fecha <= dia + datetime.timedelta(days=DIAS_AVISO_REEVALUACION):
        return "proxima"
    return "al_dia"


class Evaluacion(Registro):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="evaluaciones")
    tipo = models.ForeignKey(TipoEvaluacion, on_delete=models.PROTECT, related_name="evaluaciones")
    fecha = models.DateField(default=hoy)
    resultados = models.TextField()
    proxima_reevaluacion = models.DateField("próxima reevaluación", editable=False)

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name_plural = "evaluaciones"

    def save(self, *args, **kwargs):
        self.proxima_reevaluacion = sumar_meses(self.fecha, self.tipo.periodicidad_meses)
        super().save(*args, **kwargs)

    @property
    def estado(self):
        return estado_reevaluacion(self.proxima_reevaluacion)


def ultimas_evaluaciones(qs=None):
    """La evaluación más reciente de cada pupilo activo por tipo: de ella sale la próxima reevaluación."""
    if qs is None:
        qs = Evaluacion.objects.filter(alumno__activo=True)
    qs = qs.select_related("alumno__curso", "tipo", "creado_por").order_by("alumno_id", "tipo_id", "-fecha", "-pk")
    vistos, out = set(), []
    for e in qs:
        if (e.alumno_id, e.tipo_id) not in vistos:
            vistos.add((e.alumno_id, e.tipo_id))
            out.append(e)
    return sorted(out, key=lambda e: e.proxima_reevaluacion)


def reevaluaciones_pendientes():
    return [e for e in ultimas_evaluaciones() if e.estado != "al_dia"]


# ---------- Citaciones a apoderados ----------
class Citacion(Registro):
    class Estado(models.TextChoices):
        PROGRAMADA = "programada", "Programada"
        REALIZADA = "realizada", "Realizada"
        NO_ASISTIO = "no_asistio", "No asistió"
        REPROGRAMADA = "reprogramada", "Reprogramada"
        CANCELADA = "cancelada", "Cancelada"

    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="citaciones")
    apoderado = models.ForeignKey(Apoderado, null=True, blank=True, on_delete=models.SET_NULL, related_name="citaciones")
    fecha = models.DateField()
    hora = models.TimeField(null=True, blank=True)
    motivo = models.CharField(max_length=200)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PROGRAMADA)
    resultado = models.TextField("resultado o acuerdos", blank=True)

    class Meta:
        ordering = ["-fecha", "-hora"]
        verbose_name = "citación"
        verbose_name_plural = "citaciones"


# ---------- Mensajería interna ----------
class MensajeQuerySet(models.QuerySet):
    def conversaciones_de(self, usuario):
        """Conversaciones (mensajes iniciales) en las que participa el usuario."""
        return self.filter(hilo__isnull=True).filter(
            Q(creado_por=usuario) | Q(destinatarios=usuario)).distinct()


class Mensaje(Registro):
    """Mensajería interna entre Dirección, psicólogas y docentes.

    Un mensaje sin `hilo` inicia una conversación; las respuestas apuntan a él.
    El autor es `creado_por`.
    """
    hilo = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="respuestas")
    asunto = models.CharField(max_length=150, blank=True)
    cuerpo = models.TextField("mensaje")
    alumno = models.ForeignKey(Alumno, null=True, blank=True, on_delete=models.SET_NULL, related_name="mensajes",
                               verbose_name="estudiante relacionado")
    archivo = models.FileField("adjunto", upload_to="mensajes/%Y/", blank=True, validators=[validar_tamano])
    destinatarios = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Destinatario",
                                           related_name="mensajes_recibidos")

    objects = MensajeQuerySet.as_manager()

    class Meta:
        ordering = ["creado_en", "pk"]

    def __str__(self):
        return self.asunto or f"Respuesta a «{self.hilo}»"

    @property
    def raiz(self):
        return self.hilo or self

    def participantes(self):
        """Autor de la conversación, sus destinatarios y quienes han respondido."""
        raiz = self.raiz
        ids = set(raiz.entregas.values_list("usuario_id", flat=True)) | {raiz.creado_por_id}
        ids |= set(raiz.respuestas.values_list("creado_por_id", flat=True))
        return Usuario.objects.filter(pk__in=ids)

    def participa(self, usuario):
        raiz = self.raiz
        return (raiz.creado_por_id == usuario.pk or raiz.entregas.filter(usuario=usuario).exists()
                or raiz.respuestas.filter(creado_por=usuario).exists())

    @property
    def nombre_archivo(self):
        return os.path.basename(self.archivo.name)


class Destinatario(models.Model):
    mensaje = models.ForeignKey(Mensaje, on_delete=models.CASCADE, related_name="entregas")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entregas")
    leido_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("mensaje", "usuario")


# ---------- Recursos digitales ----------
class RecursoQuerySet(models.QuerySet):
    def visibles_para(self, usuario):
        """Filtro de visibilidad. Se usa en el servidor para listar y para descargar."""
        if usuario.es_direccion:
            return self.all()
        q = Q(para_todos=True) | Q(creado_por=usuario) | Q(usuarios=usuario)
        if usuario.es_docente:
            q |= Q(todos_docentes=True)
        if usuario.es_psicologa:
            q |= Q(todos_psicologos=True)
        return self.filter(q).distinct()


class Recurso(Registro):
    titulo = models.CharField("título", max_length=120)
    descripcion = models.TextField("descripción", blank=True)
    archivo = models.FileField(upload_to="recursos/%Y/%m/", validators=[validar_tamano])
    para_todos = models.BooleanField("Todos (docentes y psicólogos)", default=False)
    todos_docentes = models.BooleanField("Todos los docentes", default=False)
    todos_psicologos = models.BooleanField("Todos los psicólogos", default=False)
    usuarios = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="recursos_compartidos",
                                      verbose_name="Personas específicas")

    objects = RecursoQuerySet.as_manager()

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return self.titulo

    @property
    def nombre_archivo(self):
        return os.path.basename(self.archivo.name)

    @property
    def extension(self):
        return os.path.splitext(self.archivo.name)[1].lstrip(".").upper() or "ARCHIVO"


# ---------- Comisiones ----------
class Comision(Registro):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField("descripción", blank=True)
    integrantes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="comisiones", blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["-activa", "nombre"]
        verbose_name = "comisión"
        verbose_name_plural = "comisiones"

    def __str__(self):
        return self.nombre


class PublicacionComision(Registro):
    comision = models.ForeignKey(Comision, on_delete=models.CASCADE, related_name="publicaciones")
    texto = models.TextField("nota", blank=True)
    archivo = models.FileField("documento", upload_to="comisiones/%Y/", blank=True, validators=[validar_tamano])

    class Meta:
        ordering = ["-creado_en"]

    @property
    def nombre_archivo(self):
        return os.path.basename(self.archivo.name)


# ---------- Información general ----------
class Aviso(Registro):
    titulo = models.CharField("título", max_length=150)
    contenido = models.TextField()
    fecha = models.DateField("fecha de publicación", default=hoy)
    destacado = models.BooleanField(default=False, help_text="Aparece primero en la página de inicio.")

    class Meta:
        ordering = ["-destacado", "-fecha", "-pk"]

    def __str__(self):
        return self.titulo


# ---------- Reemplazos ----------
class Suplencia(models.Model):
    """Historial de cuándo alguien de Dirección trabajó en la cuenta de otra persona para reemplazarla."""
    direccion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="suplencias_hechas")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="suplencias_recibidas",
                                verbose_name="reemplazado(a)")
    motivo = models.CharField(max_length=200, blank=True)
    inicio = models.DateTimeField(auto_now_add=True)
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "reemplazo"

