from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    # profesor
    path("profesor/", views.profesor_panel, name="profesor_panel"),
    path("profesor/curso/<int:curso_id>/", views.curso_detalle, name="curso_detalle"),
    path("profesor/alumno/<str:rut>/", views.alumno_profesor, name="alumno_profesor"),
    path("profesor/mensaje/nuevo/", views.mensaje_nuevo, name="mensaje_nuevo"),
    # apoderado
    path("apoderado/", views.apoderado_panel, name="apoderado_panel"),
    path("apoderado/alumno/<str:rut>/", views.alumno_apoderado, name="alumno_apoderado"),
]
