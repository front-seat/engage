import typing as t

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html_join
from django.views.decorators.http import require_GET

from server.documents.models import Document, DocumentSummary

from .models import Legislation, LegislationSummary, Meeting, MeetingSummary

Style: t.TypeAlias = t.Literal["educated-layperson", "high-school", "catchy-clickbait"]

STYLES: list[Style] = [
    "educated-layperson",
    "high-school",
    "catchy-clickbait",
]

MEETING_SUMMARY_STYLES: dict[Style, str] = {
    "educated-layperson": "summarize_meeting_gpt35_educated_layperson",
    "high-school": "summarize_meeting_gpt35_high_school",
    "catchy-clickbait": "summarize_meeting_gpt35_entertaining_blog_post",
}

MEETING_HEADLINE_STYLES: dict[Style, str] = {
    "educated-layperson": "summarize_meeting_gpt35_newspaper_headline",
    "high-school": "summarize_meeting_gpt35_high_school_essay_title",
    "catchy-clickbait": "summarize_meeting_gpt35_catchy_controversial_headline",
}


def distill_calendars():
    for style in STYLES:
        yield {"style": style}


def _summary_as_html(summary: str):
    splits = [s.strip() for s in summary.split("\n")]
    return format_html_join("\n", "<p>{}</p>", ((s,) for s in splits if s))


def _clean_headline(headline: str):
    headline = headline.strip()
    if headline.startswith("“") or headline.startswith('"'):
        headline = headline[1:]
    if headline.endswith("”") or headline.endswith('"'):
        headline = headline[:-1]
    return headline


def _make_meeting_description(meeting: Meeting, style: str) -> dict:
    if style not in STYLES:
        raise Http404("invalid style")
    summarizer_name = MEETING_SUMMARY_STYLES[style]
    headline_summarizer_name = MEETING_HEADLINE_STYLES[style]
    summary = get_object_or_404(
        MeetingSummary, meeting=meeting, summarizer_name=summarizer_name
    )
    headline = get_object_or_404(
        MeetingSummary, meeting=meeting, summarizer_name=headline_summarizer_name
    )
    return {
        "legistar_id": meeting.legistar_id,
        "date": meeting.date,
        "time": meeting.time,
        "location": meeting.location,
        "department": meeting.schema.department,
        "headline": _clean_headline(headline.summary),
        "summary": _summary_as_html(summary.summary),
    }


@require_GET
def calendar(request, style: str):
    meetings = Meeting.objects.future().exclude(time=None).order_by("date")
    meeting_descriptions = [_make_meeting_description(m, style) for m in meetings]
    return render(
        request,
        "calendar.dhtml",
        {"style": style, "meeting_descriptions": meeting_descriptions},
    )


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
