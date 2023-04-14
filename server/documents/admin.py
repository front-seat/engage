from django.contrib import admin

from .models import Document


class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "mime_type", "url")


admin.site.register(Document, DocumentAdmin)
