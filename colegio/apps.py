from django.apps import AppConfig


class ColegioConfig(AppConfig):
    name = 'colegio'

    def ready(self):
        from . import suplencia  # noqa: F401  (registra las señales)
