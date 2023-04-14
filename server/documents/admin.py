from django.contrib import admin
from django.utils.safestring import mark_safe

from server.admin import admin_site

from .models import Document


class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "view_file", "mime_type")

    def view_file(self, obj):
        return mark_safe(f'<a href="{obj.file.url}" target="_blank">View</a>')

    view_file.allow_tags = True


admin_site.register(Document, DocumentAdmin)
