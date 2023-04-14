from django.contrib import admin
from django.utils.safestring import mark_safe

from server.admin import admin_site

from .models import Document


class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "link", "mime_type")

    def link(self, obj):
        return mark_safe(f'<a href="{obj.file.url}" target="_blank">View</a>')

    link.allow_tags = True


admin_site.register(Document, DocumentAdmin)
