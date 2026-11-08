from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models


@admin.register(models.Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("rut", "nombre", "email", "is_staff")
    ordering = ("rut",)
    fieldsets = (
        (None, {"fields": ("rut", "password")}),
        ("Datos", {"fields": ("nombre", "email")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("rut", "nombre", "email", "password1", "password2")}),)
    search_fields = ("rut", "nombre", "email")


for m in (models.Profesor, models.Apoderado, models.Curso, models.ProfesorCurso,
          models.Alumno, models.AlumnoApoderado, models.Mensaje, models.Observacion):
    admin.site.register(m)
