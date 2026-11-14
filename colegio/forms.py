from django import forms
from django.contrib.auth.password_validation import validate_password
from django.db.models import Case, When

from .models import (Alumno, Apoderado, Asignacion, Atraso, Aviso, Citacion, Comision, Curso, Destinatario,
                     Evaluacion, Inasistencia, Mensaje, Observacion, PublicacionComision, Recurso, Rol, Seguimiento,
                     TipoEvaluacion, Usuario, validar_rut)
from .permisos import alumnos_visibles

FECHA = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
HORA = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")


def texto(filas=4, placeholder=""):
    return forms.Textarea(attrs={"rows": filas, "placeholder": placeholder})


def personal_activo(*roles):
    return Usuario.objects.filter(is_active=True, rol__in=roles)


class EtiquetaPersona(forms.ModelMultipleChoiceField):
    def label_from_instance(self, u):
        extra = f" · {u.asignatura}" if u.asignatura else ""
        return f"{u.nombre} ({u.get_rol_display()}{extra})"


class FormBase(forms.ModelForm):
    """Pone en español la opción vacía de las listas desplegables (Django 6.1 la trae sin traducir)."""
    vacios = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre, campo in self.fields.items():
            texto_vacio = self.vacios.get(nombre, "— Ninguno —")
            if isinstance(campo, forms.ModelChoiceField) and not isinstance(campo, forms.ModelMultipleChoiceField):
                if campo.empty_label is not None:
                    campo.empty_label = texto_vacio
            elif isinstance(campo, forms.ChoiceField) and campo.choices and campo.choices[0][0] == "":
                campo.choices = [("", texto_vacio)] + list(campo.choices)[1:]


# ---------- Base para registros de un pupilo ----------
class RegistroAlumnoForm(FormBase):
    """Si el pupilo viene fijo (desde su ficha) se oculta el campo; si no, se limita a los pupilos visibles."""

    vacios = {"alumno": "— Elija un estudiante —", "apoderado": "— Sin indicar —", "tipo": "— Elija un tipo —"}

    def __init__(self, *args, usuario=None, alumno=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.alumno_fijo = alumno or (self.instance.alumno if self.instance.pk else None)
        if "alumno" in self.fields:
            if self.alumno_fijo:
                del self.fields["alumno"]
            else:
                self.fields["alumno"].queryset = alumnos_visibles(usuario)
                self.fields["alumno"].label = "Estudiante"
        if "apoderado" in self.fields:
            qs = Apoderado.objects.all()
            if self.alumno_fijo:
                qs = self.alumno_fijo.apoderados.all()
            self.fields["apoderado"].queryset = qs
            self.fields["apoderado"].help_text = "Opcional. Persona de contacto con quien se gestionó."

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.alumno_fijo:
            obj.alumno = self.alumno_fijo
        if obj._state.adding:
            obj.creado_por = self.usuario
        obj.modificado_por = self.usuario
        if commit:
            obj.save()
            self.save_m2m()
        return obj

    def clean(self):
        datos = super().clean()
        alumno = self.alumno_fijo or datos.get("alumno")
        ap = datos.get("apoderado")
        if alumno and ap and not alumno.apoderados.filter(pk=ap.pk).exists():
            self.add_error("apoderado", "Ese apoderado no está asociado al estudiante.")
        return datos


class AtrasoForm(RegistroAlumnoForm):
    class Meta:
        model = Atraso
        fields = ["alumno", "fecha", "hora_llegada", "motivo"]
        widgets = {"fecha": FECHA, "hora_llegada": HORA}


class InasistenciaForm(RegistroAlumnoForm):
    class Meta:
        model = Inasistencia
        fields = ["alumno", "fecha", "justificada", "motivo"]
        widgets = {"fecha": FECHA}

    def clean(self):
        datos = super().clean()
        alumno = self.alumno_fijo or datos.get("alumno")
        fecha = datos.get("fecha")
        if alumno and fecha:
            repetida = Inasistencia.objects.filter(alumno=alumno, fecha=fecha).exclude(pk=self.instance.pk)
            if repetida.exists():
                raise forms.ValidationError("Ya hay una inasistencia registrada para ese estudiante en esa fecha.")
        return datos


class ObservacionForm(RegistroAlumnoForm):
    class Meta:
        model = Observacion
        fields = ["alumno", "fecha", "contenido"]
        widgets = {"fecha": FECHA, "contenido": texto(5, "Describa avances, conducta o aspectos a reforzar…")}


class SeguimientoForm(RegistroAlumnoForm):
    class Meta:
        model = Seguimiento
        fields = ["alumno", "tipo", "fecha", "titulo", "contenido", "confidencial"]
        widgets = {"fecha": FECHA, "contenido": texto(7)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not (self.usuario and (self.usuario.es_psicologa or self.usuario.es_direccion)):
            del self.fields["confidencial"]  # solo psicóloga y Dirección marcan información reservada


class EvaluacionForm(RegistroAlumnoForm):
    class Meta:
        model = Evaluacion
        fields = ["alumno", "tipo", "fecha", "resultados"]
        widgets = {"fecha": FECHA, "resultados": texto(7, "Instrumentos aplicados, puntajes, conclusiones…")}
        labels = {"tipo": "Tipo de evaluación"}
        help_texts = {"fecha": "La próxima reevaluación se calcula sola a partir de esta fecha."}


class CitacionForm(RegistroAlumnoForm):
    class Meta:
        model = Citacion
        fields = ["alumno", "apoderado", "fecha", "hora", "motivo", "estado", "resultado"]
        widgets = {"fecha": FECHA, "hora": HORA, "resultado": texto(4)}


# ---------- Mensajería interna ----------
class MensajeForm(FormBase):
    GRUPOS = [(Rol.DIRECCION, "Toda la Dirección"), (Rol.PSICOLOGA, "Todas las psicólogas"),
              (Rol.DOCENTE, "Todos los docentes")]
    grupos = forms.MultipleChoiceField(choices=GRUPOS, required=False, widget=forms.CheckboxSelectMultiple,
                                       label="Enviar a grupos")
    curso = forms.ModelChoiceField(queryset=Curso.objects.all(), required=False, label="Equipo de un curso",
                                   help_text="Docentes y psicóloga asignados a ese curso.")
    personas = EtiquetaPersona(queryset=Usuario.objects.none(), required=False,
                               widget=forms.CheckboxSelectMultiple, label="Personas")

    field_order = ["asunto", "grupos", "curso", "personas", "alumno", "cuerpo", "archivo"]
    vacios = {"curso": "— Ninguno —", "alumno": "— Ninguno —"}

    class Meta:
        model = Mensaje
        fields = ["asunto", "alumno", "cuerpo", "archivo"]
        widgets = {"cuerpo": texto(7, "Escriba su mensaje…")}
        help_texts = {"alumno": "Opcional. El mensaje aparecerá también en la ficha del estudiante."}

    def __init__(self, *args, usuario=None, alumno=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields["asunto"].required = True
        self.fields["personas"].queryset = Usuario.objects.filter(is_active=True).exclude(pk=usuario.pk)
        self.fields["alumno"].queryset = alumnos_visibles(usuario)
        if alumno:
            self.fields["alumno"].initial = alumno

    def clean(self):
        datos = super().clean()
        ids = {u.pk for u in datos.get("personas") or []}
        grupos = datos.get("grupos") or []
        if grupos:
            ids |= set(Usuario.objects.filter(is_active=True, rol__in=grupos).values_list("pk", flat=True))
        if datos.get("curso"):
            ids |= set(datos["curso"].equipo.filter(is_active=True).values_list("pk", flat=True))
        ids.discard(self.usuario.pk)
        if not ids:
            raise forms.ValidationError("Elija al menos un destinatario.")
        self.ids_destinatarios = ids
        return datos

    def save(self, commit=True):
        m = super().save(commit=False)
        m.creado_por = m.modificado_por = self.usuario
        m.save()
        Destinatario.objects.bulk_create(Destinatario(mensaje=m, usuario_id=i) for i in self.ids_destinatarios)
        return m


class RespuestaForm(FormBase):
    class Meta:
        model = Mensaje
        fields = ["cuerpo", "archivo"]
        widgets = {"cuerpo": texto(4, "Escriba su respuesta…")}
        labels = {"cuerpo": "Respuesta"}

    def guardar(self, raiz, usuario):
        m = self.save(commit=False)
        m.hilo, m.creado_por, m.modificado_por = raiz, usuario, usuario
        m.save()
        otros = raiz.participantes().exclude(pk=usuario.pk)
        Destinatario.objects.bulk_create(Destinatario(mensaje=m, usuario=u) for u in otros)
        return m


# ---------- Tipos de evaluación ----------
class TipoEvaluacionForm(FormBase):
    class Meta:
        model = TipoEvaluacion
        fields = ["nombre", "periodicidad_meses", "descripcion"]


# ---------- Pasar lista ----------
class PasarListaForm(forms.Form):
    curso = forms.ModelChoiceField(queryset=Curso.objects.none(), empty_label=None)
    fecha = forms.DateField(widget=FECHA)

    def __init__(self, *args, cursos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["curso"].queryset = cursos


# ---------- Recursos ----------
class RecursoForm(FormBase):
    usuarios = EtiquetaPersona(queryset=Usuario.objects.none(), required=False,
                               widget=forms.CheckboxSelectMultiple, label="Personas específicas")

    class Meta:
        model = Recurso
        fields = ["titulo", "descripcion", "archivo", "para_todos", "todos_docentes", "todos_psicologos", "usuarios"]
        widgets = {"descripcion": texto(3)}

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields["usuarios"].queryset = personal_activo(Rol.DOCENTE, Rol.PSICOLOGA).exclude(pk=usuario.pk)
        self.fields["usuarios"].help_text = "Puede combinar personas con las opciones de arriba."


# ---------- Comisiones y avisos ----------
class ComisionForm(FormBase):
    integrantes = EtiquetaPersona(queryset=Usuario.objects.none(), required=False,
                                  widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Comision
        fields = ["nombre", "descripcion", "activa", "integrantes"]
        widgets = {"descripcion": texto(3)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["integrantes"].queryset = personal_activo(Rol.DOCENTE, Rol.PSICOLOGA)


class PublicacionForm(FormBase):
    class Meta:
        model = PublicacionComision
        fields = ["texto", "archivo"]
        widgets = {"texto": texto(3, "Escriba una nota para la comisión…")}

    def clean(self):
        datos = super().clean()
        if not datos.get("texto") and not datos.get("archivo"):
            raise forms.ValidationError("Escriba una nota o adjunte un documento.")
        return datos


class AvisoForm(FormBase):
    class Meta:
        model = Aviso
        fields = ["titulo", "fecha", "contenido", "destacado"]
        widgets = {"fecha": FECHA, "contenido": texto(7)}


# ---------- Gestión de usuarios ----------
class UsuarioForm(FormBase):
    cursos = forms.ModelMultipleChoiceField(queryset=Curso.objects.all(), required=False,
                                            widget=forms.CheckboxSelectMultiple, label="Cursos asignados")
    clave1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=False)
    clave2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput, required=False)

    class Meta:
        model = Usuario
        fields = ["rut", "nombre", "email", "rol", "asignatura", "cursos"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["rut"].disabled = True
            self.fields["cursos"].initial = self.instance.cursos.all()
            self.fields["clave1"].label = "Nueva contraseña"
            self.fields["clave1"].help_text = "Déjela en blanco para mantener la actual."
        else:
            self.fields["clave1"].required = self.fields["clave2"].required = True

    def clean(self):
        datos = super().clean()
        c1, c2 = datos.get("clave1"), datos.get("clave2")
        if c1 or c2:
            if c1 != c2:
                self.add_error("clave2", "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(c1, self.instance)
                except forms.ValidationError as e:
                    self.add_error("clave1", e)
        return datos

    def save(self, commit=True):
        u = super().save(commit=False)
        if self.cleaned_data.get("clave1"):
            u.set_password(self.cleaned_data["clave1"])
        u.save()
        nuevos = set(self.cleaned_data["cursos"])
        Asignacion.objects.filter(usuario=u).exclude(curso__in=nuevos).delete()
        for c in nuevos:
            Asignacion.objects.get_or_create(usuario=u, curso=c)
        return u


# ---------- Gestión de cursos ----------
class EtiquetaAlumno(forms.ModelMultipleChoiceField):
    def label_from_instance(self, a):
        actual = f" · hoy en {a.curso}" if a.curso else " · sin curso"
        return f"{a.nombre} ({a.rut}){actual}"


class CursoForm(FormBase):
    vacios = {"profesor_jefe": "— Sin asignar —"}
    profesor_jefe = forms.ModelChoiceField(queryset=Usuario.objects.none(), required=False,
                                           label="Profesor(a) jefe")
    alumnos = EtiquetaAlumno(
        queryset=Alumno.objects.none(), required=False, widget=forms.CheckboxSelectMultiple,
        label="Estudiantes del curso",
        help_text="Use el buscador para encontrarlos. Si un estudiante estaba en otro curso, pasa a este.")

    class Meta:
        model = Curso
        fields = ["nivel", "capacidad", "profesor_jefe", "alumnos"]

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields["profesor_jefe"].queryset = personal_activo(Rol.DOCENTE)
        qs = Alumno.objects.filter(activo=True).select_related("curso")
        if self.instance.pk:  # los que ya están en el curso aparecen primero
            qs = qs.annotate(en_curso=Case(When(curso=self.instance, then=0), default=1)).order_by("en_curso", "nombre")
        self.fields["alumnos"].queryset = qs
        if self.instance.pk:
            self.fields["profesor_jefe"].initial = self.instance.profesor_jefe
            self.fields["alumnos"].initial = self.instance.alumnos.filter(activo=True)

    def save(self, commit=True):
        curso = super().save()
        jefe = self.cleaned_data.get("profesor_jefe")
        curso.asignaciones.update(profesor_jefe=False)
        if jefe:
            Asignacion.objects.update_or_create(usuario=jefe, curso=curso, defaults={"profesor_jefe": True})
        elegidos = [a.pk for a in self.cleaned_data["alumnos"]]
        Alumno.objects.filter(curso=curso, activo=True).exclude(pk__in=elegidos).update(
            curso=None, modificado_por=self.usuario)
        Alumno.objects.filter(pk__in=elegidos).exclude(curso=curso).update(curso=curso, modificado_por=self.usuario)
        return curso


# ---------- Gestión de pupilos ----------
class AlumnoForm(FormBase):
    vacios = {"curso": "— Sin curso —"}

    class Meta:
        model = Alumno
        fields = ["rut", "nombre", "fecha_nacimiento", "curso"]
        widgets = {"fecha_nacimiento": FECHA}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.instance._state.adding:
            self.fields["rut"].disabled = True


class ApoderadoContactoForm(forms.Form):
    rut = forms.CharField(label="RUT", max_length=10, validators=[validar_rut])
    nombre = forms.CharField(max_length=60)
    parentesco = forms.CharField(max_length=30)
    telefono = forms.CharField(label="Teléfono", max_length=15, required=False)
    email = forms.EmailField(label="Correo", required=False)
    es_principal = forms.BooleanField(label="Principal", required=False)


ApoderadosFormSet = forms.formset_factory(ApoderadoContactoForm, extra=1, can_delete=True)


class BajaForm(forms.Form):
    motivo = forms.CharField(label="Motivo de la baja", max_length=200)
