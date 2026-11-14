from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from . import models


@admin.register(models.Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("rut", "nombre", "email", "rol", "is_active")
    list_filter = ("rol", "is_active")
    ordering = ("nombre",)
    fieldsets = (
        (None, {"fields": ("rut", "password")}),
        ("Datos", {"fields": ("nombre", "email", "rol", "asignatura")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",),
                             "fields": ("rut", "nombre", "email", "rol", "password1", "password2")}),)
    search_fields = ("rut", "nombre", "email")
    filter_horizontal = ()


class VinculoInline(admin.TabularInline):
    model = models.AlumnoApoderado
    extra = 0


@admin.register(models.Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ("rut", "nombre", "curso", "activo")
    list_filter = ("activo", "curso")
    search_fields = ("rut", "nombre")
    inlines = [VinculoInline]


for m in (models.Curso, models.Asignacion, models.Apoderado, models.Atraso, models.Inasistencia,
          models.Observacion, models.Seguimiento, models.TipoEvaluacion, models.Evaluacion, models.Citacion,
          models.Mensaje, models.Destinatario, models.Recurso, models.Comision, models.PublicacionComision, models.Aviso, models.Suplencia):
    admin.site.register(m)
