from django.contrib import admin
from django.utils.safestring import mark_safe
from nonrelated_inlines.admin import NonrelatedTabularInline

from server.admin import admin_site
from server.lib.admin import NoPermissionAdminMixin

from .models import Document, DocumentSummary, DocumentText


class NonrelatedDocumentTabularInline(NoPermissionAdminMixin, NonrelatedTabularInline):
    model = Document
    fields = ("simple_title", "kind", "link", "mime_type")
    readonly_fields = fields
    show_change_link = True
    extra = 0

    def get_form_queryset(self, obj):
        return obj.documents_qs

    def has_view_permission(self, request, obj=None) -> bool:
        return True

    def link(self, obj):
        return mark_safe(f'<a href="{obj.file.url}" target="_blank">View</a>')

    link.allow_tags = True

    def simple_title(self, obj):
        return obj.title.split("-")[-1]


class DocumentTextTabularInline(NoPermissionAdminMixin, admin.TabularInline):
    model = DocumentText
    fields = ("extracted_at", "document", "short_text", "extra")
    readonly_fields = fields
    show_change_link = True
    extra = 0

    def short_text(self, obj):
        return obj.text[:255] + "..." if len(obj.text) > 100 else obj.text

    short_text.short_description = "Text"


class DocumentSummaryTabularInline(NoPermissionAdminMixin, admin.TabularInline):
    model = DocumentSummary
    fields = ("summarized_at", "document", "summary", "extra")
    readonly_fields = fields
    show_change_link = True
    extra = 0


class DocumentAdmin(NoPermissionAdminMixin, admin.ModelAdmin):
    list_display = ("title", "kind", "link", "mime_type")
    fields = ("url_link", "kind", "title", "mime_type", "file")
    readonly_fields = fields
    inlines = (DocumentTextTabularInline, DocumentSummaryTabularInline)

    def url_link(self, obj):
        return mark_safe(f'<a href="{obj.url}" target="_blank">{obj.url}</a>')

    url_link.allow_tags = True
    url_link.short_description = "Url"

    def link(self, obj):
        return mark_safe(f'<a href="{obj.file.url}" target="_blank">View</a>')

    link.allow_tags = True


class DocumentTextAdmin(NoPermissionAdminMixin, admin.ModelAdmin):
    list_display = ("extracted_at", "document", "short_text", "extra")
    fields = ("extracted_at", "document", "extra", "text")
    readonly_fields = fields

    def short_text(self, obj):
        return obj.text[:100] + "..." if len(obj.text) > 100 else obj.text

    short_text.short_description = "Text"


class DocumentSummaryAdmin(NoPermissionAdminMixin, admin.ModelAdmin):
    list_display = ("summarized_at", "document", "short_summary", "extra")
    fields = ("summarized_at", "document", "extra", "summary")
    readonly_fields = fields

    def short_summary(self, obj):
        return obj.summary[:100] + "..." if len(obj.summary) > 100 else obj.summary

    short_summary.short_description = "Summary"


admin_site.register(Document, DocumentAdmin)
admin_site.register(DocumentText, DocumentTextAdmin)
admin_site.register(DocumentSummary, DocumentSummaryAdmin)
