from django.contrib import admin
from django.utils.safestring import mark_safe

from server.admin import admin_site

from .models import Action, Legislation, Meeting


class MeetingAdmin(admin.ModelAdmin):
    list_display = ("department_name", "date", "time", "location", "active", "link")
    readonly_fields = ("schema_data", "documents")

    def department_name(self, obj):
        return obj.schema.department.name

    def active(self, obj):
        return obj.is_active

    active.boolean = True

    def link(self, obj):
        return mark_safe(f'<a href="{obj.url}" target="_blank">View</a>')

    link.allow_tags = True


class LegislationAdmin(admin.ModelAdmin):
    list_display = ("record_no", "type", "title", "status", "link")
    readonly_fields = ("schema_data", "documents")

    def link(self, obj):
        return mark_safe(f'<a href="{obj.url}" target="_blank">View</a>')

    link.allow_tags = True


class ActionAdmin(admin.ModelAdmin):
    list_display = ("record_no", "title", "link")
    readonly_fields = ("schema_data",)

    def title(self, obj):
        return obj.schema.title

    def link(self, obj):
        return mark_safe(f'<a href="{obj.url}" target="_blank">View</a>')

    link.allow_tags = True


admin_site.register(Meeting, MeetingAdmin)
admin_site.register(Legislation, LegislationAdmin)
admin_site.register(Action, ActionAdmin)
