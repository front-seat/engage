import datetime
import typing as t

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html_join
from django.views.decorators.http import require_GET

from server.documents.models import Document, DocumentSummary
from server.lib.truncate import truncate_str

from .models import Legislation, LegislationSummary, Meeting, MeetingSummary

Style: t.TypeAlias = t.Literal["concise"]

STYLES: list[Style] = ["concise"]

MEETING_SUMMARY_STYLES: dict[Style, str] = {
    "concise": "summarize_meeting_gpt35_concise",
}

MEETING_HEADLINE_STYLES: dict[Style, str] = {
    "concise": "summarize_meeting_gpt35_concise_headline",
}

LEGISLATION_SUMMARY_STYLES: dict[Style, str] = {
    "concise": "summarize_legislation_gpt35_concise",
}

LEGISLATION_HEADLINE_STYLES: dict[Style, str] = {
    "concise": "summarize_legislation_gpt35_concise_headline",
}

DOCUMENT_SUMMARY_STYLES: dict[Style, str] = {
    "concise": "summarize_gpt35_concise",
}

DOCUMENT_HEADLINE_STYLES: dict[Style, str] = {
    "concise": "summarize_gpt35_concise_headline",
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
    if meeting.is_active:
        summary = get_object_or_404(
            MeetingSummary, meeting=meeting, summarizer_name=summarizer_name
        )
        headline = get_object_or_404(
            MeetingSummary, meeting=meeting, summarizer_name=headline_summarizer_name
        )
        clean_headline = _clean_headline(headline.summary)
        return {
            "is_active": True,
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
    else:
        return {
            "is_active": False,
            "legistar_id": meeting.legistar_id,
            "url": meeting.url,
            "date": meeting.date,
            "time": meeting.time,
            "location": meeting.location,
            "department": meeting.schema.department,
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


PAST_CUTOFF_DELTA = datetime.timedelta(days=5)


def _get_relative_to() -> datetime.date:
    return datetime.date.today() - PAST_CUTOFF_DELTA


@require_GET
def calendar(request, style: str):
    meetings = Meeting.objects.future(relative_to=_get_relative_to()).order_by("-date")
    meeting_descriptions = [_make_meeting_description(m, style) for m in meetings]
    return render(
        request,
        "calendar.dhtml",
        {"style": style, "meeting_descriptions": meeting_descriptions},
    )


def _meetings_qs():
    qs = Meeting.objects.future(relative_to=_get_relative_to())
    qs = qs.exclude(time=None)
    meeting_pks_with_summaries = set(
        MeetingSummary.objects.values_list("meeting_id", flat=True)
    )
    qs = qs.filter(pk__in=meeting_pks_with_summaries)
    return qs


def distill_meetings():
    qs = _meetings_qs()
    for meeting in qs:
        for style in STYLES:
            yield {"meeting_id": meeting.legistar_id, "style": style}


@require_GET
def meeting(request, meeting_id: int, style: str):
    meeting_ = get_object_or_404(Meeting, legistar_id=meeting_id)
    meeting_description = _make_meeting_description(meeting_, style)
    return render(
        request,
        "meeting.dhtml",
        {
            "style": style,
            "meeting_id": meeting_id,
            "meeting_description": meeting_description,
        },
    )


def distill_legislations():
    qs = _meetings_qs()
    for meeting in qs:
        for legislation in meeting.legislations:
            if not legislation.summaries.exists():
                continue
            for style in STYLES:
                yield {
                    "meeting_id": meeting.legistar_id,
                    "legislation_id": legislation.legistar_id,
                    "style": style,
                }


@require_GET
def legislation(request, meeting_id: int, legislation_id: int, style: str):
    legislation_ = get_object_or_404(Legislation, legistar_id=legislation_id)
    legislation_description = _make_legislation_description(legislation_, style)
    return render(
        request,
        "legislation.dhtml",
        {
            "style": style,
            "meeting_id": meeting_id,
            "legislation_id": legislation_id,
            "legislation_description": legislation_description,
        },
    )


def distill_documents():
    qs = _meetings_qs()
    for meeting in qs:
        for legislation in meeting.legislations:
            if not legislation.summaries.exists():
                continue
            for document in legislation.documents_qs:
                if not document.summaries.exists():
                    continue
                for style in STYLES:
                    yield {
                        "meeting_id": meeting.legistar_id,
                        "legislation_id": legislation.legistar_id,
                        "document_pk": document.pk,
                        "style": style,
                    }


@require_GET
def document(
    request, meeting_id: int, legislation_id: int, document_pk: int, style: str
):
    document_ = get_object_or_404(Document, pk=document_pk)
    document_description = _make_document_description(document_, style)
    return render(
        request,
        "document.dhtml",
        {
            "style": style,
            "meeting_id": meeting_id,
            "legislation_id": legislation_id,
            "document_pk": document_pk,
            "document_description": document_description,
        },
    )


@require_GET
def index(request):
    return render(request, "index.dhtml")
