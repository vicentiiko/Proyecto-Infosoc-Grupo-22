from django.urls import path

from .views import asistencia, comunidad, estudiantes, gestion, inicio, mensajes, registros as r

urlpatterns = [
    path("", inicio.inicio, name="inicio"),

    # Estudiantes y cursos
    path("estudiantes/", estudiantes.lista, name="estudiantes"),
    path("estudiantes/<str:rut>/", estudiantes.ficha, name="ficha"),
    path("cursos/<int:pk>/", estudiantes.curso, name="curso"),

    # Asistencia (M-02, M-03)
    path("asistencia/atrasos/", asistencia.atrasos, name="atrasos"),
    path("asistencia/atrasos/nuevo/", asistencia.atraso_nuevo, name="atraso_nuevo"),
    path("asistencia/atrasos/<int:pk>/editar/", asistencia.atraso_editar, name="atraso_editar"),
    path("asistencia/atrasos/<int:pk>/eliminar/", asistencia.atraso_eliminar, name="atraso_eliminar"),
    path("asistencia/inasistencias/", asistencia.inasistencias, name="inasistencias"),
    path("asistencia/inasistencias/nueva/", asistencia.inasistencia_nueva, name="inasistencia_nueva"),
    path("asistencia/inasistencias/<int:pk>/editar/", asistencia.inasistencia_editar, name="inasistencia_editar"),
    path("asistencia/inasistencias/<int:pk>/eliminar/", asistencia.inasistencia_eliminar, name="inasistencia_eliminar"),
    path("asistencia/pasar-lista/", asistencia.pasar_lista, name="pasar_lista"),

    # Observaciones (M-04) y seguimiento (M-08)
    path("observaciones/nueva/", r.observacion_nueva, name="observacion_nueva"),
    path("observaciones/<int:pk>/editar/", r.observacion_editar, name="observacion_editar"),
    path("observaciones/<int:pk>/eliminar/", r.observacion_eliminar, name="observacion_eliminar"),
    path("seguimiento/nuevo/", r.seguimiento_nuevo, name="seguimiento_nuevo"),
    path("seguimiento/<int:pk>/editar/", r.seguimiento_editar, name="seguimiento_editar"),
    path("seguimiento/<int:pk>/eliminar/", r.seguimiento_eliminar, name="seguimiento_eliminar"),

    # Evaluaciones (M-05)
    path("evaluaciones/", r.evaluaciones, name="evaluaciones"),
    path("evaluaciones/nueva/", r.evaluacion_nueva, name="evaluacion_nueva"),
    path("evaluaciones/<int:pk>/", r.evaluacion_detalle, name="evaluacion"),
    path("evaluaciones/<int:pk>/editar/", r.evaluacion_editar, name="evaluacion_editar"),
    path("evaluaciones/tipos/", r.tipos_evaluacion, name="tipos_evaluacion"),
    path("evaluaciones/tipos/nuevo/", r.tipo_evaluacion_form, name="tipo_evaluacion_nuevo"),
    path("evaluaciones/tipos/<int:pk>/editar/", r.tipo_evaluacion_form, name="tipo_evaluacion_editar"),

    # Citaciones a apoderados (M-06)
    path("citaciones/", r.citaciones, name="citaciones"),
    path("citaciones/nueva/", r.citacion_nueva, name="citacion_nueva"),
    path("citaciones/<int:pk>/editar/", r.citacion_editar, name="citacion_editar"),

    # Mensajería interna (reemplaza a M-07)
    path("mensajes/", mensajes.bandeja, name="mensajes"),
    path("mensajes/nuevo/", mensajes.nuevo, name="mensaje_nuevo"),
    path("mensajes/<int:pk>/", mensajes.conversacion, name="conversacion"),
    path("mensajes/adjunto/<int:pk>/", mensajes.adjunto, name="mensaje_adjunto"),

    # Recursos digitales (M-09)
    path("recursos/", comunidad.recursos, name="recursos"),
    path("recursos/nuevo/", comunidad.recurso_nuevo, name="recurso_nuevo"),
    path("recursos/<int:pk>/editar/", comunidad.recurso_editar, name="recurso_editar"),
    path("recursos/<int:pk>/eliminar/", comunidad.recurso_eliminar, name="recurso_eliminar"),
    path("recursos/<int:pk>/descargar/", comunidad.recurso_descargar, name="recurso_descargar"),

    # Comisiones (M-10)
    path("comisiones/", comunidad.comisiones, name="comisiones"),
    path("comisiones/nueva/", comunidad.comision_form, name="comision_nueva"),
    path("comisiones/<int:pk>/", comunidad.comision, name="comision"),
    path("comisiones/<int:pk>/editar/", comunidad.comision_form, name="comision_editar"),
    path("comisiones/publicacion/<int:pk>/eliminar/", comunidad.publicacion_eliminar, name="publicacion_eliminar"),
    path("comisiones/publicacion/<int:pk>/descargar/", comunidad.publicacion_descargar, name="publicacion_descargar"),

    # Información general (M-11)
    path("avisos/", comunidad.avisos, name="avisos"),
    path("avisos/nuevo/", comunidad.aviso_form, name="aviso_nuevo"),
    path("avisos/<int:pk>/editar/", comunidad.aviso_form, name="aviso_editar"),
    path("avisos/<int:pk>/eliminar/", comunidad.aviso_eliminar, name="aviso_eliminar"),

    # Gestión (M-01)
    path("gestion/usuarios/", gestion.usuarios, name="usuarios"),
    path("gestion/usuarios/nuevo/", gestion.usuario_form, name="usuario_nuevo"),
    path("gestion/usuarios/<str:rut>/editar/", gestion.usuario_form, name="usuario_editar"),
    path("gestion/usuarios/<str:rut>/estado/", gestion.usuario_estado, name="usuario_estado"),
    path("gestion/cursos/", gestion.cursos, name="cursos"),
    path("gestion/cursos/nuevo/", gestion.curso_form, name="curso_nuevo"),
    path("gestion/cursos/<int:pk>/editar/", gestion.curso_form, name="curso_editar"),
    path("gestion/pupilos/", gestion.pupilos, name="pupilos"),
    path("gestion/pupilos/nuevo/", gestion.pupilo_form, name="pupilo_nuevo"),
    path("gestion/pupilos/<str:rut>/editar/", gestion.pupilo_form, name="pupilo_editar"),
    path("gestion/pupilos/<str:rut>/baja/", gestion.pupilo_baja, name="pupilo_baja"),
    path("gestion/pupilos/<str:rut>/reactivar/", gestion.pupilo_reactivar, name="pupilo_reactivar"),
    path("gestion/usuarios/<str:rut>/reemplazar/", gestion.actuar_como, name="actuar_como"),
    path("gestion/reemplazos/", gestion.suplencias, name="suplencias"),
    path("reemplazo/terminar/", gestion.volver_a_mi_cuenta, name="volver_a_mi_cuenta"),
]
