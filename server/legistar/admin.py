from django.contrib import admin

from .models import Action, Legislation, Meeting


class MeetingAdmin(admin.ModelAdmin):
    list_display = ("department_name", "date", "time", "location")

    def department_name(self, obj):
        return obj.schema.department.name


class LegislationAdmin(admin.ModelAdmin):
    list_display = ("record_no", "type", "title", "status")


class ActionAdmin(admin.ModelAdmin):
    list_display = ("record_no", "title")

    def title(self, obj):
        return obj.schema.title


admin.site.register(Meeting, MeetingAdmin)
admin.site.register(Legislation, LegislationAdmin)
admin.site.register(Action, ActionAdmin)
