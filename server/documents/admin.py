from django.contrib import admin
from django.utils.safestring import mark_safe
from nonrelated_inlines.admin import NonrelatedTabularInline

from server.admin import admin_site
from server.lib.admin import NoPermissionAdminMixin
from server.lib.truncate import truncate_str

from .models import Document, DocumentSummary


class NonrelatedDocumentTabularInline(NoPermissionAdminMixin, NonrelatedTabularInline):
    model = Document
    fields = ("simple_title", "kind", "link", "mime_type")
    readonly_fields = fields
    show_change_link = True
    extra = 0

    def get_form_queryset(self, obj):
        return obj.documents.all()

    def has_view_permission(self, request, obj=None) -> bool:
        return True

    def link(self, obj):
        return mark_safe(f'<a href="{obj.file.url}" target="_blank">View</a>')

    link.allow_tags = True

    def simple_title(self, obj):
        return obj.title.split("-")[-1]


class DocumentSummaryTabularInline(NoPermissionAdminMixin, admin.TabularInline):
    model = DocumentSummary
    fields = ("summarized_at", "summarizer_name", "document", "summary")
    readonly_fields = fields
    show_change_link = True
    extra = 0


class DocumentAdmin(NoPermissionAdminMixin, admin.ModelAdmin):
    list_display = ("title", "kind", "link", "mime_type")
    fields = ("url_link", "kind", "title", "mime_type", "raw_content")
    readonly_fields = fields
    inlines = (DocumentSummaryTabularInline,)

    def url_link(self, obj):
        return mark_safe(f'<a href="{obj.url}" target="_blank">{obj.url}</a>')

    url_link.allow_tags = True
    url_link.short_description = "Url"

    def link(self, obj):
        return mark_safe(f'<a href="{obj.file.url}" target="_blank">View</a>')

    link.allow_tags = True


class DocumentSummaryAdmin(NoPermissionAdminMixin, admin.ModelAdmin):
    list_display = (
        "summarized_at",
        "document",
        "summarizer_name",
        "short_summary",
    )
    fields = ("summarized_at", "document", "summarizer_name", "summary")
    readonly_fields = fields

    def short_summary(self, obj):
        return truncate_str(obj.summary, 100)

    short_summary.short_description = "Summary"


admin_site.register(Document, DocumentAdmin)
admin_site.register(DocumentSummary, DocumentSummaryAdmin)
