from django_distill import distill_path

from . import views

app_name = "legistar"
urlpatterns = [
    distill_path(
        "calendar/<slug:config_name>/",
        views.calendar,
        name="calendar",
        distill_func=views.distill_calendars,
        distill_file="calendar/{config_name}/index.html",
    ),
    distill_path(
        "meeting/<int:meeting_id>/<slug:config_name>/",
        views.meeting,
        name="meeting",
        distill_func=views.distill_meetings,
        distill_file="meeting/{meeting_id}/{config_name}/index.html",
    ),
    distill_path(
        "legislation/<int:meeting_id>/<int:legislation_id>/<slug:config_name>/",
        views.legislation,
        name="legislation",
        distill_func=views.distill_legislations,
        distill_file="legislation/{meeting_id}/{legislation_id}/{config_name}/index.html",
    ),
    distill_path(
        "document/<int:meeting_id>/<int:legislation_id>/<int:document_pk>/<slug:config_name>/",
        views.document,
        name="document",
        distill_func=views.distill_documents,
        distill_file="document/{meeting_id}/{legislation_id}/{document_pk}/{config_name}/index.html",
    ),
    distill_path("", views.index, name="index", distill_file="index.html"),
]
