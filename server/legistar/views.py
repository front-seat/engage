from django.shortcuts import render
from django.views.decorators.http import require_GET

from server.documents.models import Document, DocumentSummary

from .models import Legislation, LegislationSummary, Meeting, MeetingSummary

# Create your views here.

STYLES = [
    "educated-layperson",
    "high-school",
    "catchy-clickbait",
]


def distill_calendars():
    for style in STYLES:
        yield {"style": style}


@require_GET
def calendar(request, style: str):
    return render(request, "calendar.dhtml", {"style": style})


def distill_meetings(upcoming_only: bool = True):
    qs = Meeting.objects.future() if upcoming_only else Meeting.objects.all()
    # Choose non-canceled meetings only
    qs = qs.exclude(time=None)
    # Query for all Meeting objects that have at least one associated MeetingSummary.
    meeting_pks_with_summaries = set(
        MeetingSummary.objects.values_list("meeting_id", flat=True)
    )
    qs = qs.filter(pk__in=meeting_pks_with_summaries)
    for style in STYLES:
        for meeting in qs:
            yield {"legistar_id": meeting.legistar_id, "style": style}


@require_GET
def meeting(request, legistar_id: int, style: str):
    return render(
        request, "meeting.dhtml", {"legistar_id": legistar_id, "style": style}
    )


def distill_legislations():
    legislation_pks_with_summaries = set(
        LegislationSummary.objects.values_list("legislation_id", flat=True)
    )
    qs = Legislation.objects.filter(pk__in=legislation_pks_with_summaries)
    for style in STYLES:
        for legislation in qs:
            yield {"legistar_id": legislation.legistar_id, "style": style}


@require_GET
def legislation(request, legistar_id: int, style: str):
    return render(
        request, "legislation.dhtml", {"legistar_id": legistar_id, "style": style}
    )


def distill_documents():
    document_pks_with_summaries = set(
        DocumentSummary.objects.values_list("document_id", flat=True)
    )
    qs = Document.objects.filter(pk__in=document_pks_with_summaries)
    for style in STYLES:
        for document in qs:
            yield {"document_pk": document.id, "style": style}


@require_GET
def document(request, document_pk: int, style: str):
    return render(
        request, "document.dhtml", {"document_pk": document_pk, "style": style}
    )


@require_GET
def index(request):
    return render(request, "index.dhtml")
