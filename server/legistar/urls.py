from django_distill import distill_path

from . import views

app_name = "legistar"
urlpatterns = [
    distill_path(
        "calendar/<slug:style>/",
        views.calendar,
        name="calendar",
        distill_func=views.distill_calendars,
        distill_file="calendar/{style}/index.html",
    ),
    distill_path(
        "meeting/<int:meeting_id>/<slug:style>/",
        views.meeting,
        name="meeting",
        distill_func=views.distill_meetings,
        distill_file="meeting/{meeting_id}/{style}/index.html",
    ),
    distill_path(
        "legislation/<int:meeting_id>/<int:legislation_id>/<slug:style>/",
        views.legislation,
        name="legislation",
        distill_func=views.distill_legislations,
        distill_file="legislation/{meeting_id}/{legislation_id}/{style}/index.html",
    ),
    distill_path(
        "document/<int:meeting_id>/<int:legislation_id>/<int:document_pk>/<slug:style>/",
        views.document,
        name="document",
        distill_func=views.distill_documents,
        distill_file="document/{meeting_id}/{legislation_id}/{document_pk}/{style}/index.html",
    ),
    distill_path("", views.index, name="index", distill_file="index.html"),
]
