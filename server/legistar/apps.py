from django.apps import AppConfig


class LegistarConfig(AppConfig):
    name = "server.legistar"
    verbose_name = "Legistar"

    def ready(self):
        pass
