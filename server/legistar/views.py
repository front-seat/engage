import typing as t

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html_join
from django.views.decorators.http import require_GET

from server.documents.models import Document, DocumentSummary
from server.lib.truncate import truncate_str

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


LEGISLATION_SUMMARY_STYLES: dict[Style, str] = {
    "educated-layperson": "summarize_legislation_gpt35_educated_layperson",
    "high-school": "summarize_legislation_gpt35_high_school",
    "catchy-clickbait": "summarize_legislation_gpt35_entertaining_blog_post",
}

LEGISLATION_HEADLINE_STYLES: dict[Style, str] = {
    "educated-layperson": "summarize_legislation_gpt35_newspaper_headline",
    "high-school": "summarize_legislation_gpt35_high_school_essay_title",
    "catchy-clickbait": "summarize_legislation_gpt35_catchy_controversial_headline",
}

DOCUMENT_SUMMARY_STYLES: dict[Style, str] = {
    "educated-layperson": "summarize_gpt35_educated_layperson",
    "high-school": "summarize_gpt35_high_school",
    "catchy-clickbait": "summarize_gpt35_entertaining_blog_post",
}

DOCUMENT_HEADLINE_STYLES: dict[Style, str] = {
    "educated-layperson": "summarize_gpt35_newspaper_headline",
    "high-school": "summarize_gpt35_high_school_essay_title",
    "catchy-clickbait": "summarize_gpt35_catchy_controversial_headline",
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


def _make_legislation_mini_description(legislation: Legislation, style: str) -> dict:
    if style not in STYLES:
        raise Http404("invalid style")
    headline_summarizer_name = LEGISLATION_HEADLINE_STYLES[style]
    headline = get_object_or_404(
        LegislationSummary,
        legislation=legislation,
        summarizer_name=headline_summarizer_name,
    )
    clean_headline = _clean_headline(headline.summary)
    return {
        "legistar_id": legislation.legistar_id,
        "url": legislation.url,
        "title": legislation.title,
        "truncated_title": legislation.truncated_title,
        "type": legislation.type,
        "kind": legislation.kind,
        "headline": clean_headline,
        "truncated_headline": truncate_str(clean_headline, 24),
    }


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
    clean_headline = _clean_headline(headline.summary)
    return {
        "legistar_id": meeting.legistar_id,
        "url": meeting.url,
        "date": meeting.date,
        "time": meeting.time,
        "location": meeting.location,
        "department": meeting.schema.department,
        "headline": clean_headline,
        "truncated_headline": truncate_str(clean_headline, 24),
        "summary": _summary_as_html(summary.summary),
        "legislations": [
            _make_legislation_mini_description(legislation, style)
            for legislation in meeting.legislations
        ],
    }


def _make_document_mini_description(document: Document, style: str) -> dict:
    if style not in STYLES:
        raise Http404("invalid style")
    headline_summarizer_name = DOCUMENT_HEADLINE_STYLES[style]
    headline = get_object_or_404(
        DocumentSummary, document=document, summarizer_name=headline_summarizer_name
    )
    clean_headline = _clean_headline(headline.summary)
    return {
        "pk": document.pk,
        "url": document.url,
        "kind": document.kind.replace("_", " ").title(),
        "title": document.short_title,
        "truncated_title": document.truncated_title,
        "headline": clean_headline,
        "truncated_headline": truncate_str(clean_headline, 24),
    }


def _make_legislation_description(legislation: Legislation, style: str) -> dict:
    if style not in STYLES:
        raise Http404("invalid style")
    summarizer_name = LEGISLATION_SUMMARY_STYLES[style]
    headline_summarizer_name = LEGISLATION_HEADLINE_STYLES[style]
    summary = get_object_or_404(
        LegislationSummary,
        legislation=legislation,
        summarizer_name=summarizer_name,
    )
    headline = get_object_or_404(
        LegislationSummary,
        legislation=legislation,
        summarizer_name=headline_summarizer_name,
    )
    return {
        "legistar_id": legislation.legistar_id,
        "url": legislation.url,
        "title": legislation.title,
        "truncated_title": legislation.truncated_title,
        "type": legislation.type,
        "kind": legislation.kind,
        "headline": _clean_headline(headline.summary),
        "summary": _summary_as_html(summary.summary),
        "documents": [
            _make_document_mini_description(document, style)
            for document in legislation.documents_qs
        ],
    }


def _make_document_description(document: Document, style: str) -> dict:
    if style not in STYLES:
        raise Http404("invalid style")
    summarizer_name = DOCUMENT_SUMMARY_STYLES[style]
    headline_summarizer_name = DOCUMENT_HEADLINE_STYLES[style]
    summary = get_object_or_404(
        DocumentSummary, document=document, summarizer_name=summarizer_name
    )
    headline = get_object_or_404(
        DocumentSummary, document=document, summarizer_name=headline_summarizer_name
    )
    clean_headline = _clean_headline(headline.summary)
    return {
        "pk": document.pk,
        "url": document.url,
        "kind": document.kind.replace("_", " ").title(),
        "title": document.short_title,
        "truncated_title": document.truncated_title,
        "headline": clean_headline,
        "truncated_headline": truncate_str(clean_headline, 24),
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
    meeting_ = get_object_or_404(Meeting, legistar_id=legistar_id)
    meeting_description = _make_meeting_description(meeting_, style)
    return render(
        request,
        "meeting.dhtml",
        {"style": style, "meeting_description": meeting_description},
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
    legislation_ = get_object_or_404(Legislation, legistar_id=legistar_id)
    legislation_description = _make_legislation_description(legislation_, style)
    return render(
        request,
        "legislation.dhtml",
        {"style": style, "legislation_description": legislation_description},
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
    document_ = get_object_or_404(Document, pk=document_pk)
    document_description = _make_document_description(document_, style)
    return render(
        request,
        "document.dhtml",
        {"style": style, "document_description": document_description},
    )


@require_GET
def index(request):
    return render(request, "index.dhtml")
