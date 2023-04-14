from django.contrib import admin

from server.admin import admin_site

from .models import Action, Legislation, Meeting


class MeetingAdmin(admin.ModelAdmin):
    list_display = ("department_name", "date", "time", "location", "is_canceled")
    readonly_fields = ("schema_data", "documents")

    def department_name(self, obj):
        return obj.schema.department.name


class LegislationAdmin(admin.ModelAdmin):
    list_display = ("record_no", "type", "title", "status")
    readonly_fields = ("schema_data", "documents")


class ActionAdmin(admin.ModelAdmin):
    list_display = ("record_no", "title")
    readonly_fields = ("schema_data",)

    def title(self, obj):
        return obj.schema.title


admin_site.register(Meeting, MeetingAdmin)
admin_site.register(Legislation, LegislationAdmin)
admin_site.register(Action, ActionAdmin)
