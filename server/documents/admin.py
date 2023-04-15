from django.contrib import admin
from django.utils.safestring import mark_safe
from nonrelated_inlines.admin import NonrelatedTabularInline

from server.admin import admin_site

from .models import Document


class NonrelatedDocumentTabularInline(NonrelatedTabularInline):
    model = Document
    fields = ("title", "kind", "link", "mime_type")
    readonly_fields = fields
    show_change_link = True
    extra = 0

    def get_form_queryset(self, obj):
        return obj.documents_qs

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_view_permission(self, request, obj=None) -> bool:
        return True

    def link(self, obj):
        return mark_safe(f'<a href="{obj.file.url}" target="_blank">View</a>')

    link.allow_tags = True


class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "link", "mime_type")

    def link(self, obj):
        return mark_safe(f'<a href="{obj.file.url}" target="_blank">View</a>')

    link.allow_tags = True


admin_site.register(Document, DocumentAdmin)
