import datetime
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


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
        return self.create_user(rut, email, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Tabla `usuario` del esquema. Inicia sesión con RUT."""
    rut = models.CharField(max_length=10, primary_key=True)
    nombre = models.CharField(max_length=60)
    email = models.EmailField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "rut"
    REQUIRED_FIELDS = ["email", "nombre"]
    objects = UsuarioManager()

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

    @property
    def es_profesor(self):
        return hasattr(self, "profesor")

    @property
    def es_apoderado(self):
        return hasattr(self, "apoderado")


class Profesor(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    asignatura = models.CharField(max_length=40)

    def __str__(self):
        return f"{self.usuario.nombre} – {self.asignatura}"


class Apoderado(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    telefono = models.CharField(max_length=12)

    def __str__(self):
        return self.usuario.nombre


class Curso(models.Model):
    nivel = models.CharField(max_length=12)
    tamanio = models.PositiveIntegerField(default=0)
    profesores = models.ManyToManyField(Profesor, through="ProfesorCurso", related_name="cursos")

    def __str__(self):
        return f"Curso {self.pk} – {self.nivel}"


class ProfesorCurso(models.Model):
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    profesor_jefe = models.BooleanField(default=False)

    class Meta:
        unique_together = ("profesor", "curso")


class Alumno(models.Model):
    rut = models.CharField(max_length=10, primary_key=True)
    nombre = models.CharField(max_length=60)
    curso = models.ForeignKey(Curso, null=True, on_delete=models.SET_NULL, related_name="alumnos")
    apoderados = models.ManyToManyField(Apoderado, through="AlumnoApoderado", related_name="alumnos")

    def __str__(self):
        return self.nombre


class AlumnoApoderado(models.Model):
    apoderado = models.ForeignKey(Apoderado, on_delete=models.CASCADE)
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    parentesco = models.CharField(max_length=30)
    es_principal = models.BooleanField(default=False)

    class Meta:
        unique_together = ("apoderado", "alumno")


class Mensaje(models.Model):
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE, related_name="mensajes")
    contenido = models.TextField()
    fecha = models.DateField(default=datetime.date.today)
    destinatarios = models.ManyToManyField(Apoderado, related_name="mensajes_recibidos")

    class Meta:
        ordering = ["-fecha", "-pk"]


class Observacion(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="observaciones")
    profesor = models.ForeignKey(Profesor, on_delete=models.CASCADE, related_name="observaciones")
    contenido = models.TextField()
    fecha = models.DateField(default=datetime.date.today)  # aparece en el diagrama, falta en el SQL

    class Meta:
        ordering = ["-fecha", "-pk"]
