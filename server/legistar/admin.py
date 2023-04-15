import datetime

from django.contrib import admin
from django.utils.safestring import mark_safe
from nonrelated_inlines.admin import NonrelatedTabularInline

from server.admin import admin_site
from server.documents.admin import NonrelatedDocumentTabularInline

from .models import Action, Legislation, Meeting


class NonrelatedLegislationTabularInline(NonrelatedTabularInline):
    model = Legislation
    fields = ("record_no", "type", "title", "status", "link")
    readonly_fields = fields
    show_change_link = True
    extra = 0

    def get_form_queryset(self, meeting: Meeting):
        return meeting.legislations

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_view_permission(self, request, obj=None) -> bool:
        return True

    def link(self, legislation: Legislation):
        return mark_safe(f'<a href="{legislation.url}" target="_blank">View</a>')

    link.allow_tags = True


class UpcomingMeetingListFilter(admin.SimpleListFilter):
    title = "upcoming"
    parameter_name = "upcoming"

    def lookups(self, request, model_admin):
        return (
            ("upcoming", "Upcoming"),
            ("past", "Past"),
        )

    def queryset(self, request, queryset):
        if self.value() == "upcoming":
            return queryset.filter(date__gte=datetime.date.today())
        if self.value() == "past":
            return queryset.filter(date__lt=datetime.date.today())


class ActiveMeetingListFilter(admin.SimpleListFilter):
    title = "active"
    parameter_name = "active"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active"),
            ("inactive", "Inactive"),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(time__isnull=False)
        if self.value() == "inactive":
            return queryset.filter(time__isnull=True)


class DepartmentNameListFilter(admin.SimpleListFilter):
    title = "department"
    parameter_name = "department"

    _cached: list[str] | None = None

    def lookups(self, request, model_admin):
        if self._cached is None:
            self._cached = list(
                sorted(
                    set(
                        Meeting.objects.values_list(
                            "schema_data__department__name", flat=True
                        )
                    ),
                    key=str.lower,
                )
            )
        return ((name, name) for name in self._cached)

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(schema_data__department__name=self.value())


class MeetingAdmin(admin.ModelAdmin):
    list_display = ("department_name", "date", "time", "location", "active", "link")
    fields = (
        "legistar_id",
        "legistar_guid",
        "date",
        "time",
        "location",
    )
    readonly_fields = fields
    list_filter = (
        ActiveMeetingListFilter,
        UpcomingMeetingListFilter,
        DepartmentNameListFilter,
    )
    inlines = (NonrelatedDocumentTabularInline, NonrelatedLegislationTabularInline)

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
