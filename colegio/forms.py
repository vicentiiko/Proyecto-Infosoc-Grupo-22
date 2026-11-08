from django import forms
from .models import Apoderado, Mensaje, Observacion


class MensajeForm(forms.ModelForm):
    class Meta:
        model = Mensaje
        fields = ["destinatarios", "contenido"]
        widgets = {
            "destinatarios": forms.CheckboxSelectMultiple,
            "contenido": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, profesor=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo apoderados de alumnos de los cursos del profesor
        self.fields["destinatarios"].queryset = (
            Apoderado.objects.filter(alumnos__curso__in=profesor.cursos.all())
            .distinct().select_related("usuario")
        )


class ObservacionForm(forms.ModelForm):
    class Meta:
        model = Observacion
        fields = ["contenido"]
        widgets = {"contenido": forms.Textarea(attrs={"rows": 3})}
