from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User


class EngageAdminSite(admin.AdminSite):
    site_header = "Engage! admin"
    site_title = "Engage! admin"
    index_title = "Engage! admin"
    enable_nav_sidebar = False


admin_site = EngageAdminSite()
admin_site.register(Group, GroupAdmin)
admin_site.register(User, UserAdmin)
