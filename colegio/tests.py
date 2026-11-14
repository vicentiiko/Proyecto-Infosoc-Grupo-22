import datetime
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (Alumno, AlumnoApoderado, Apoderado, Asignacion, Atraso, Aviso, Citacion, Comision,
                     Curso, Destinatario, Evaluacion, Inasistencia, Mensaje, Observacion, Recurso, Rol, Seguimiento,
                     Suplencia, TipoEvaluacion, Usuario, estado_reevaluacion, hoy, reevaluaciones_pendientes, sumar_meses)

MEDIA = tempfile.mkdtemp()
CLAVE = "ClaveSegura123!"


def usuario(rut, nombre, rol, **extra):
    return Usuario.objects.create_user(rut, f"{rut}@test.cl", nombre, CLAVE, rol=rol, **extra)


@override_settings(MEDIA_ROOT=MEDIA)
class Base(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.dir = usuario("10000001-1", "Directora", Rol.DIRECCION)
        cls.psi = usuario("10000002-2", "Psicóloga", Rol.PSICOLOGA)
        cls.doc = usuario("10000003-3", "Docente Uno", Rol.DOCENTE, asignatura="Lenguaje")
        cls.doc2 = usuario("10000004-4", "Docente Dos", Rol.DOCENTE)
        cls.c1 = Curso.objects.create(nivel="1A")
        cls.c2 = Curso.objects.create(nivel="2B")
        Asignacion.objects.create(usuario=cls.doc, curso=cls.c1, profesor_jefe=True)
        Asignacion.objects.create(usuario=cls.doc2, curso=cls.c2)
        cls.a1 = Alumno.objects.create(rut="20000001-1", nombre="Ana", curso=cls.c1)
        cls.a2 = Alumno.objects.create(rut="20000002-2", nombre="Beto", curso=cls.c2)
        cls.apo = Apoderado.objects.create(rut="30000001-1", nombre="Mamá de Ana", telefono="912345678")
        AlumnoApoderado.objects.create(alumno=cls.a1, apoderado=cls.apo, parentesco="Madre", es_principal=True)
        cls.tipo = TipoEvaluacion.objects.create(nombre="Psicopedagógica", periodicidad_meses=12)

    def entrar(self, u):
        self.client.force_login(u)


class UtilidadesTests(TestCase):
    def test_sumar_meses(self):
        self.assertEqual(sumar_meses(datetime.date(2024, 1, 31), 1), datetime.date(2024, 2, 29))
        self.assertEqual(sumar_meses(datetime.date(2024, 11, 15), 3), datetime.date(2025, 2, 15))
        self.assertEqual(sumar_meses(datetime.date(2024, 5, 10), 36), datetime.date(2027, 5, 10))

    def test_estado_reevaluacion(self):
        d = datetime.date(2026, 1, 1)
        self.assertEqual(estado_reevaluacion(datetime.date(2025, 12, 31), d), "vencida")
        self.assertEqual(estado_reevaluacion(datetime.date(2026, 2, 1), d), "proxima")
        self.assertEqual(estado_reevaluacion(datetime.date(2026, 6, 1), d), "al_dia")


class EvaluacionesTests(Base):
    def test_proxima_reevaluacion_se_calcula_y_recalcula(self):
        e = Evaluacion.objects.create(alumno=self.a1, tipo=self.tipo, fecha=datetime.date(2025, 3, 10), resultados="x")
        self.assertEqual(e.proxima_reevaluacion, datetime.date(2026, 3, 10))
        self.tipo.periodicidad_meses = 24
        self.tipo.save()
        e.refresh_from_db()
        self.assertEqual(e.proxima_reevaluacion, datetime.date(2027, 3, 10))

    def test_pendientes_usa_la_ultima_evaluacion(self):
        Evaluacion.objects.create(alumno=self.a1, tipo=self.tipo, fecha=sumar_meses(hoy(), -24), resultados="vieja")
        self.assertEqual(len(reevaluaciones_pendientes()), 1)
        Evaluacion.objects.create(alumno=self.a1, tipo=self.tipo, fecha=hoy(), resultados="nueva")
        self.assertEqual(len(reevaluaciones_pendientes()), 0)

    def test_psicologa_registra_evaluacion(self):
        self.entrar(self.psi)
        r = self.client.post(reverse("evaluacion_nueva") + f"?alumno={self.a1.pk}",
                             {"tipo": self.tipo.pk, "fecha": "2026-01-15", "resultados": "Bien"})
        self.assertEqual(r.status_code, 302)
        e = Evaluacion.objects.get()
        self.assertEqual((e.alumno, e.creado_por, e.proxima_reevaluacion), (self.a1, self.psi, datetime.date(2027, 1, 15)))


class PermisosTests(Base):
    def test_docente_no_ve_informacion_psicologica(self):
        self.entrar(self.doc)
        for nombre in ("evaluaciones", "citaciones", "tipos_evaluacion"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, nombre)
        r = self.client.get(reverse("ficha", args=[self.a1.pk]))
        self.assertNotContains(r, 'id="evaluaciones"')

    def test_docente_solo_ve_sus_cursos(self):
        self.entrar(self.doc)
        self.assertEqual(self.client.get(reverse("ficha", args=[self.a1.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("ficha", args=[self.a2.pk])).status_code, 404)
        r = self.client.post(reverse("atraso_nuevo") + f"?alumno={self.a2.pk}", {"fecha": "2026-01-01", "hora_llegada": "08:30"})
        self.assertEqual(r.status_code, 404)

    def test_psicologa_no_registra_asistencia_y_direccion_si(self):
        self.entrar(self.psi)
        self.assertEqual(self.client.get(reverse("atraso_nuevo")).status_code, 403)
        self.assertEqual(self.client.get(reverse("atrasos")).status_code, 200)
        self.entrar(self.dir)
        r = self.client.post(reverse("atraso_nuevo") + f"?alumno={self.a2.pk}", {"fecha": "2026-01-01", "hora_llegada": "08:30"})
        self.assertEqual(r.status_code, 302)

    def test_direccion_edita_registros_de_otros(self):
        o = Observacion.objects.create(alumno=self.a1, contenido="x", creado_por=self.doc)
        self.entrar(self.dir)
        self.assertEqual(self.client.get(reverse("observacion_editar", args=[o.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("evaluacion_nueva")).status_code, 200)

    def test_solo_direccion_gestiona(self):
        for u in (self.psi, self.doc):
            self.entrar(u)
            self.assertEqual(self.client.get(reverse("usuarios")).status_code, 403)
            self.assertEqual(self.client.get(reverse("aviso_nuevo")).status_code, 403)

    def test_docente_no_edita_observacion_ajena(self):
        o = Observacion.objects.create(alumno=self.a1, contenido="x", creado_por=self.psi)
        self.entrar(self.doc)
        self.assertEqual(self.client.get(reverse("observacion_editar", args=[o.pk])).status_code, 403)

    def test_seguimiento_confidencial(self):
        Seguimiento.objects.create(alumno=self.a1, titulo="Secreto", contenido="x", confidencial=True, creado_por=self.psi)
        self.entrar(self.doc)
        self.assertNotContains(self.client.get(reverse("ficha", args=[self.a1.pk])), "Secreto")
        self.entrar(self.dir)
        self.assertContains(self.client.get(reverse("ficha", args=[self.a1.pk])), "Secreto")

    def test_usuario_desactivado_no_entra(self):
        self.doc2.is_active = False
        self.doc2.save()
        self.assertFalse(self.client.login(rut=self.doc2.rut, password=CLAVE))


class RecursosTests(Base):
    def recurso(self, **vis):
        r = Recurso.objects.create(titulo="Guía", archivo=SimpleUploadedFile("guia.pdf", b"%PDF"), creado_por=self.doc, **vis)
        return r

    def test_visibilidad_por_persona_y_grupo(self):
        r = self.recurso(todos_psicologos=True)
        r.usuarios.add(self.doc2)
        visibles = lambda u: set(Recurso.objects.visibles_para(u))
        self.assertIn(r, visibles(self.psi))
        self.assertIn(r, visibles(self.doc2))
        self.assertIn(r, visibles(self.dir))     # Dirección ve todo
        self.assertIn(r, visibles(self.doc))     # autor
        otro = usuario("10000005-5", "Docente Tres", Rol.DOCENTE)
        self.assertNotIn(r, visibles(otro))

    def test_descarga_validada_en_servidor(self):
        r = self.recurso()
        self.entrar(self.doc2)
        self.assertEqual(self.client.get(reverse("recurso_descargar", args=[r.pk])).status_code, 404)
        self.entrar(self.dir)
        self.assertEqual(self.client.get(reverse("recurso_descargar", args=[r.pk])).status_code, 200)

    def test_subir_recurso(self):
        self.entrar(self.doc)
        r = self.client.post(reverse("recurso_nuevo"), {
            "titulo": "PPT", "archivo": SimpleUploadedFile("c.pptx", b"x"), "todos_docentes": "on",
            "usuarios": [self.psi.pk]})
        self.assertEqual(r.status_code, 302)
        rec = Recurso.objects.get(titulo="PPT")
        self.assertTrue(rec.todos_docentes)
        self.assertEqual(list(rec.usuarios.all()), [self.psi])
        self.assertEqual(rec.creado_por, self.doc)


class AsistenciaTests(Base):
    def test_pasar_lista(self):
        self.entrar(self.doc)
        url = reverse("pasar_lista")
        base = {"curso": self.c1.pk, "fecha": "2026-03-02"}
        self.client.post(url, {**base, f"estado_{self.a1.pk}": "ausente"})
        i = Inasistencia.objects.get()
        self.assertEqual((i.alumno, i.justificada, i.creado_por), (self.a1, False, self.doc))
        self.client.post(url, {**base, f"estado_{self.a1.pk}": "justificada"})
        self.assertTrue(Inasistencia.objects.get().justificada)
        r = self.client.post(url, {**base, f"estado_{self.a1.pk}": "presente"})
        self.assertFalse(Inasistencia.objects.exists())
        self.assertEqual(r.status_code, 302)

    def test_inasistencia_duplicada(self):
        Inasistencia.objects.create(alumno=self.a1, fecha=datetime.date(2026, 3, 2))
        self.entrar(self.doc)
        r = self.client.post(reverse("inasistencia_nueva") + f"?alumno={self.a1.pk}", {"fecha": "2026-03-02"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Inasistencia.objects.count(), 1)

    def test_filtro_por_fechas(self):
        Atraso.objects.create(alumno=self.a1, fecha=datetime.date(2026, 1, 5), hora_llegada=datetime.time(8, 40))
        Atraso.objects.create(alumno=self.a1, fecha=datetime.date(2026, 2, 5), hora_llegada=datetime.time(8, 40))
        self.entrar(self.dir)
        r = self.client.get(reverse("atrasos"), {"desde": "2026-02-01"})
        self.assertEqual(r.context["total"], 1)


class GestionTests(Base):
    def test_crear_usuario_con_cursos(self):
        self.entrar(self.dir)
        r = self.client.post(reverse("usuario_nuevo"), {
            "rut": "11111111-1", "nombre": "Nueva", "email": "n@test.cl", "rol": "docente",
            "cursos": [self.c1.pk, self.c2.pk], "clave1": "OtraClave456!", "clave2": "OtraClave456!"})
        self.assertEqual(r.status_code, 302)
        u = Usuario.objects.get(rut="11111111-1")
        self.assertEqual(set(u.cursos.all()), {self.c1, self.c2})
        self.assertTrue(u.check_password("OtraClave456!"))

    def test_crear_pupilo_con_apoderado_y_baja(self):
        self.entrar(self.dir)
        datos = {"rut": "22222222-2", "nombre": "Nuevo", "curso": self.c1.pk,
                 "ap-TOTAL_FORMS": "1", "ap-INITIAL_FORMS": "0",
                 "ap-0-rut": "33333333-3", "ap-0-nombre": "Papá", "ap-0-parentesco": "Padre", "ap-0-telefono": "999"}
        self.assertEqual(self.client.post(reverse("pupilo_nuevo"), datos).status_code, 302)
        a = Alumno.objects.get(rut="22222222-2")
        self.assertEqual(a.apoderados.get().nombre, "Papá")
        self.client.post(reverse("pupilo_baja", args=[a.pk]), {"motivo": "Traslado"})
        a.refresh_from_db()
        self.assertFalse(a.activo)
        self.entrar(self.doc)
        self.assertEqual(self.client.get(reverse("ficha", args=[a.pk])).status_code, 404)

    def test_curso_con_estudiantes(self):
        self.entrar(self.dir)
        r = self.client.post(reverse("curso_nuevo"), {"nivel": "3C", "capacidad": 20, "alumnos": [self.a1.pk, self.a2.pk]})
        self.assertEqual(r.status_code, 302)
        nuevo = Curso.objects.get(nivel="3C")
        self.assertEqual(set(nuevo.alumnos.all()), {self.a1, self.a2})
        self.client.post(reverse("curso_editar", args=[nuevo.pk]), {"nivel": "3C", "capacidad": 20, "alumnos": [self.a1.pk]})
        self.a2.refresh_from_db()
        self.assertIsNone(self.a2.curso)

    def test_no_puede_desactivarse_a_si_misma(self):
        self.entrar(self.dir)
        self.client.post(reverse("usuario_estado", args=[self.dir.pk]))
        self.dir.refresh_from_db()
        self.assertTrue(self.dir.is_active)


class PaginasTests(Base):
    """Recorre todas las páginas con cada rol para asegurar que cargan."""

    def test_todas_las_paginas_cargan(self):
        obs = Observacion.objects.create(alumno=self.a1, contenido="o", creado_por=self.doc)
        ev = Evaluacion.objects.create(alumno=self.a1, tipo=self.tipo, resultados="r", creado_por=self.psi)
        cit = Citacion.objects.create(alumno=self.a1, apoderado=self.apo, fecha=hoy(), motivo="m", creado_por=self.psi)
        msj = Mensaje.objects.create(asunto="Hola", cuerpo="c", creado_por=self.dir)
        Destinatario.objects.create(mensaje=msj, usuario=self.doc)
        Destinatario.objects.create(mensaje=msj, usuario=self.psi)
        comi = Comision.objects.create(nombre="Convivencia")
        comi.integrantes.add(self.doc, self.psi)
        Aviso.objects.create(titulo="Hola", contenido="c", creado_por=self.dir)
        comunes = ["inicio", "estudiantes", "atrasos", "inasistencias", "mensajes", "mensaje_nuevo", "recursos", "comisiones", "avisos"]
        casos = {
            self.dir: comunes + ["evaluaciones", "citaciones", "tipos_evaluacion", "usuarios", "pupilos", "cursos",
                                 "usuario_nuevo", "pupilo_nuevo", "curso_nuevo", "aviso_nuevo", "comision_nueva",
                                 ("ficha", self.a1.pk), ("evaluacion", ev.pk), ("comision", comi.pk),
                                 ("usuario_editar", self.doc.pk), ("pupilo_editar", self.a1.pk), ("curso", self.c1.pk),
                                 ("curso_editar", self.c1.pk), ("conversacion", msj.pk)],
            self.psi: comunes + ["evaluaciones", "citaciones", "evaluacion_nueva", "citacion_nueva", "recurso_nuevo",
                                 "tipo_evaluacion_nuevo", ("ficha", self.a1.pk), ("citacion_editar", cit.pk),
                                 ("evaluacion_editar", ev.pk), ("comision", comi.pk)],
            self.doc: comunes + ["pasar_lista", "atraso_nuevo", "inasistencia_nueva", "observacion_nueva",
                                 "seguimiento_nuevo", "recurso_nuevo", ("ficha", self.a1.pk),
                                 ("observacion_editar", obs.pk), ("conversacion", msj.pk), ("curso", self.c1.pk),
                                 ("comision", comi.pk)],
        }
        for u, nombres in casos.items():
            self.entrar(u)
            for n in nombres:
                url = reverse(n[0], args=[n[1]]) if isinstance(n, tuple) else reverse(n)
                with self.subTest(rol=u.rol, url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_login_y_anonimo(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inicio")).status_code, 302)
        r = self.client.post(reverse("login"), {"username": self.doc.rut, "password": CLAVE})
        self.assertRedirects(r, reverse("inicio"))


class MensajesTests(Base):
    def test_enviar_a_grupo_y_curso(self):
        self.entrar(self.dir)
        r = self.client.post(reverse("mensaje_nuevo"), {
            "asunto": "Reunión", "cuerpo": "Mañana", "grupos": ["psicologa"], "curso": self.c2.pk})
        self.assertEqual(r.status_code, 302)
        m = Mensaje.objects.get()
        self.assertEqual(set(m.destinatarios.all()), {self.psi, self.doc2})

    def test_sin_destinatarios_no_envia(self):
        self.entrar(self.doc)
        r = self.client.post(reverse("mensaje_nuevo"), {"asunto": "x", "cuerpo": "y"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Mensaje.objects.exists())

    def test_conversacion_privada_y_leida(self):
        self.entrar(self.doc)
        self.client.post(reverse("mensaje_nuevo"), {"asunto": "Consulta", "cuerpo": "Hola", "personas": [self.psi.pk],
                                                    "alumno": self.a1.pk})
        m = Mensaje.objects.get()
        self.assertEqual(m.alumno, self.a1)
        # Otro docente no participa: no la ve. Dirección sí la ve aunque no participe.
        self.entrar(self.doc2)
        self.assertEqual(self.client.get(reverse("conversacion", args=[m.pk])).status_code, 404)
        self.entrar(self.dir)
        self.assertEqual(self.client.get(reverse("conversacion", args=[m.pk])).status_code, 200)
        self.assertIn(m, list(self.client.get(reverse("mensajes"), {"ver": "todas"}).context["pagina"]))
        self.assertNotIn(m, list(self.client.get(reverse("mensajes")).context["pagina"]))
        # La psicóloga la lee y responde; la respuesta llega al autor
        self.entrar(self.psi)
        self.assertEqual(self.client.get(reverse("inicio")).context["n_mensajes"], 1)
        self.client.get(reverse("conversacion", args=[m.pk]))
        self.assertEqual(self.client.get(reverse("inicio")).context["n_mensajes"], 0)
        self.client.post(reverse("conversacion", args=[m.pk]), {"cuerpo": "Conversemos"})
        respuesta = m.respuestas.get()
        self.assertEqual(list(respuesta.destinatarios.all()), [self.doc])
        self.entrar(self.doc)
        self.assertEqual(self.client.get(reverse("mensajes")).context["n_mensajes"], 1)

    def test_adjunto_solo_participantes(self):
        m = Mensaje.objects.create(asunto="Doc", cuerpo="c", creado_por=self.doc,
                                   archivo=SimpleUploadedFile("a.pdf", b"%PDF"))
        Destinatario.objects.create(mensaje=m, usuario=self.psi)
        self.entrar(self.psi)
        self.assertEqual(self.client.get(reverse("mensaje_adjunto", args=[m.pk])).status_code, 200)
        self.entrar(self.doc2)
        self.assertEqual(self.client.get(reverse("mensaje_adjunto", args=[m.pk])).status_code, 404)


class ReemplazoTests(Base):
    def test_direccion_reemplaza_a_docente(self):
        self.entrar(self.dir)
        self.client.post(reverse("actuar_como", args=[self.doc.pk]))
        r = self.client.get(reverse("inicio"))
        self.assertEqual(r.context["user"], self.doc)
        self.assertContains(r, "Modo reemplazo")
        # Lo que registra queda a nombre de la docente, marcando a Dirección como suplente
        self.client.post(reverse("observacion_nueva") + f"?alumno={self.a1.pk}", {"fecha": "2026-05-05", "contenido": "Hecho en reemplazo"})
        o = Observacion.objects.get()
        self.assertEqual((o.creado_por, o.suplente), (self.doc, self.dir))
        self.assertContains(self.client.get(reverse("ficha", args=[self.a1.pk])), "en reemplazo, lo hizo Directora")
        # Mientras reemplaza tiene los permisos de la docente
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 403)
        # Vuelve a su cuenta y el reemplazo queda cerrado
        self.client.post(reverse("volver_a_mi_cuenta"))
        self.assertEqual(self.client.get(reverse("inicio")).context["user"], self.dir)
        s = Suplencia.objects.get()
        self.assertEqual((s.direccion, s.usuario), (self.dir, self.doc))
        self.assertIsNotNone(s.fin)
        # Lo que hace después ya no se marca como reemplazo
        self.client.post(reverse("observacion_nueva") + f"?alumno={self.a1.pk}", {"fecha": "2026-05-06", "contenido": "Normal"})
        self.assertIsNone(Observacion.objects.get(contenido="Normal").suplente)

    def test_solo_direccion_puede_reemplazar(self):
        self.entrar(self.psi)
        self.assertEqual(self.client.post(reverse("actuar_como", args=[self.doc.pk])).status_code, 403)
        otra_dir = usuario("10000009-9", "Subdirector", Rol.DIRECCION)
        self.entrar(self.dir)
        self.assertEqual(self.client.post(reverse("actuar_como", args=[otra_dir.pk])).status_code, 403)
        self.assertFalse(Suplencia.objects.exists())

    def test_cerrar_sesion_termina_reemplazo(self):
        self.entrar(self.dir)
        self.client.post(reverse("actuar_como", args=[self.psi.pk]))
        self.client.post(reverse("logout"))
        self.assertIsNotNone(Suplencia.objects.get().fin)
