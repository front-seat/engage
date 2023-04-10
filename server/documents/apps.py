from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    name = "server.documents"
    verbose_name = "Documents"

    def ready(self):
        pass
