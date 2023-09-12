import datetime

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html_join
from django.views.decorators.http import require_GET

from server.documents.models import Document, DocumentSummary
from server.lib.style import SUMMARIZATION_STYLES, SummarizationStyle
from server.lib.truncate import truncate_str

from .models import Legislation, LegislationSummary, Meeting, MeetingSummary

# ------------------------------------------------------------------------
# Utilities for cleaning up text summaries and generating HTML
# ------------------------------------------------------------------------


# CONSIDER: if we make these (and our `truncate_str`) into Django template
# filters, we could remove most -- maybe all? -- of the `_*_context()`
# functions below and move their functionality directly to the templates.


def _text_to_html_paragraphs(text: str):
    """Convert text, with newlines, to simple runs of HTML paragraphs."""
    splits = [s.strip() for s in text.split("\n")]
    return format_html_join("\n", "<p>{}</p>", ((s,) for s in splits if s))


def _remove_surrounding_quotes(text: str):
    """Remove quotes and other annoying characters in a given text."""
    # Usually, we use this with the headline for a summary; for whatever reason,
    # GPT-3.5 and Vicuna 13B both like putting quotes around the headlines
    # they generate. CONSIDER making this part of the summarization pipeline
    # rather than a view/template concern.
    text = text.strip()
    if text.startswith("“") or text.startswith('"'):
        text = text[1:]
    if text.endswith("”") or text.endswith('"'):
        text = text[:-1]
    return text


# ------------------------------------------------------------------------
# Utilities to generate context data for our Django templates
# ------------------------------------------------------------------------


def _legislation_table_context(
    legislation: Legislation, style: SummarizationStyle
) -> dict:
    """
    Build context data for the given `legislation`; this is used in our
    HTML templates that display a table of legislation instances.
    """
    summary = get_object_or_404(
        LegislationSummary,
        legislation=legislation,
        style=style,
    )
    clean_headline = _remove_surrounding_quotes(summary.headline)
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


def _document_table_context(document: Document, style: SummarizationStyle) -> dict:
    """
    Build context data for a `document`; this is used in our HTML templates
    that display a table of `Document` instances.
    """
    summary = get_object_or_404(DocumentSummary, document=document, style=style)
    clean_headline = _remove_surrounding_quotes(summary.headline)
    return {
        "pk": document.pk,
        "url": document.url,
        "kind": document.kind.replace("_", " ").title(),
        "title": document.short_title,
        "truncated_title": document.truncated_title,
        "headline": clean_headline,
        "truncated_headline": truncate_str(clean_headline, 24),
    }


def _meeting_context(meeting: Meeting, style: SummarizationStyle) -> dict:
    """
    Build context data for a `meeting`; this is used in our HTML templates
    that display detailed information about a single `Meeting` instance.
    """
    if meeting.is_active:
        summary = get_object_or_404(MeetingSummary, meeting=meeting, style=style)
        clean_headline = _remove_surrounding_quotes(summary.headline)
        return {
            "is_active": True,
            "legistar_id": meeting.legistar_id,
            "url": meeting.url,
            "date": meeting.date,
            "time": meeting.time,
            "location": meeting.location,
            "department": meeting.crawl_data.department,
            "headline": clean_headline,
            "truncated_headline": truncate_str(clean_headline, 24),
            "summary": _text_to_html_paragraphs(summary.body),
            "legislation_table_contexts": [
                _legislation_table_context(legislation, style)
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
            "department": meeting.crawl_data.department,
        }


def _legislation_context(legislation: Legislation, style: SummarizationStyle) -> dict:
    """
    Build context data for a `legislation`; this is used in our HTML
    templates that display detailed information about a single `Legislation`
    instance.
    """
    summary = get_object_or_404(
        LegislationSummary, legislation=legislation, style=style
    )
    return {
        "legistar_id": legislation.legistar_id,
        "url": legislation.url,
        "title": legislation.title,
        "truncated_title": legislation.truncated_title,
        "type": legislation.type,
        "kind": legislation.kind,
        "headline": _remove_surrounding_quotes(summary.headline),
        "summary": _text_to_html_paragraphs(summary.body),
        "document_table_contexts": [
            _document_table_context(document, style)
            for document in legislation.documents.all()
        ],
    }


def _document_context(document: Document, style: SummarizationStyle) -> dict:
    """
    Build context data for a `document`; this is used in our HTML templates
    that display detailed information about a single `Document` instance.
    """
    summary = get_object_or_404(DocumentSummary, document=document, style=style)
    clean_headline = _remove_surrounding_quotes(summary.headline)
    return {
        "pk": document.pk,
        "url": document.url,
        "kind": document.kind.replace("_", " ").title(),
        "title": document.short_title,
        "truncated_title": document.truncated_title,
        "headline": clean_headline,
        "truncated_headline": truncate_str(clean_headline, 24),
        "summary": _text_to_html_paragraphs(summary.body),
    }


# ------------------------------------------------------------------------
# Utilities for grabbing the right data from our database
# ------------------------------------------------------------------------

PAST_CUTOFF_DELTA = datetime.timedelta(days=8)
"""How far back in time should we still show meeting summaries?"""


def _get_relative_to(when: datetime.date | None = None) -> datetime.date:
    """Return the date to use as the "relative to" date for meeting queries."""
    final_when = when or datetime.date.today()
    return final_when - PAST_CUTOFF_DELTA


def _meetings_qs():
    """Return a Django QuerySet of all meetings that should show summaries."""
    qs = Meeting.objects.future(relative_to=_get_relative_to())
    qs = qs.exclude(time=None)
    meeting_pks_with_summaries = set(
        MeetingSummary.objects.values_list("meeting_id", flat=True)
    )
    qs = qs.filter(pk__in=meeting_pks_with_summaries)
    return qs


# ------------------------------------------------------------------------
# Django Distill functions; these define the set of static pages to generate
# ------------------------------------------------------------------------


def distill_calendars():
    """
    Provide all possible parameterizations of /calendar/:style/ so that
    Django Distill can generate all the static pages we'd like.
    """
    for style in SUMMARIZATION_STYLES:
        yield {"style": style}


def distill_meetings():
    """
    Provide all possible parameterizations of /meeting/:meeting_id/:style/
    so that Django Distill can generate all the static pages we'd like.
    """
    qs = _meetings_qs()
    for meeting in qs:
        for style in SUMMARIZATION_STYLES:
            yield {"meeting_id": meeting.legistar_id, "style": style}


def distill_legislations():
    """
    Provide all possible parameterizations of
    /legislation/:meeting_id/:legislation_id/:style/
    so that Django Distill can generate all the static pages we'd like.
    """
    qs = _meetings_qs()
    for meeting in qs:
        for legislation in meeting.legislations:
            if not legislation.summaries.exists():
                continue
            for style in SUMMARIZATION_STYLES:
                yield {
                    "meeting_id": meeting.legistar_id,
                    "legislation_id": legislation.legistar_id,
                    "style": style,
                }


def distill_documents():
    """
    Provide all possible parameterizations of
    /document/:meeting_id/:legislation_id/:document_pk/:style/
    so that Django Distill can generate all the static pages we'd like.
    """
    qs = _meetings_qs()
    for meeting in qs:
        for legislation in meeting.legislations:
            if not legislation.summaries.exists():
                continue
            for document in legislation.documents.all():
                if not document.summaries.exists():
                    continue
                for style in SUMMARIZATION_STYLES:
                    yield {
                        "meeting_id": meeting.legistar_id,
                        "legislation_id": legislation.legistar_id,
                        "document_pk": document.pk,
                        "style": style,
                    }


# ------------------------------------------------------------------------
# Django views (our actual HTTP endpoints -- invoked by Django Distill)
# ------------------------------------------------------------------------


@require_GET
def calendar(request, style: str):
    """Render the calendar page for a given `style`."""
    if style not in SUMMARIZATION_STYLES:
        raise Http404(f"Unknown style: {style}")
    meetings = Meeting.objects.future(relative_to=_get_relative_to()).order_by("-date")
    meeting_contexts = [_meeting_context(m, style) for m in meetings]
    return render(
        request,
        "calendar.dhtml",
        {"style": style, "meeting_contexts": meeting_contexts},
    )


@require_GET
def meeting(request, meeting_id: int, style: str):
    """Render the meeting detail page for a given `meeting_id` and `style`."""
    if style not in SUMMARIZATION_STYLES:
        raise Http404(f"Unknown style: {style}")
    meeting_ = get_object_or_404(Meeting, legistar_id=meeting_id)
    meeting_context = _meeting_context(meeting_, style)
    return render(
        request,
        "meeting.dhtml",
        {
            "style": style,
            "meeting_id": meeting_id,
            "meeting_context": meeting_context,
        },
    )


@require_GET
def legislation(request, meeting_id: int, legislation_id: int, style: str):
    """Render the legislation detail page for a given `legislation_id` and `style`."""
    if style not in SUMMARIZATION_STYLES:
        raise Http404(f"Unknown style: {style}")
    legislation_ = get_object_or_404(Legislation, legistar_id=legislation_id)
    legislation_context = _legislation_context(legislation_, style)
    return render(
        request,
        "legislation.dhtml",
        {
            "style": style,
            "meeting_id": meeting_id,
            "legislation_id": legislation_id,
            "legislation_context": legislation_context,
        },
    )


@require_GET
def document(
    request, meeting_id: int, legislation_id: int, document_pk: int, style: str
):
    """Render the document detail page for a given `document_pk` and `style`."""
    if style not in SUMMARIZATION_STYLES:
        raise Http404(f"Unknown style: {style}")
    document_ = get_object_or_404(Document, pk=document_pk)
    document_context = _document_context(document_, style)
    return render(
        request,
        "document.dhtml",
        {
            "style": style,
            "meeting_id": meeting_id,
            "legislation_id": legislation_id,
            "document_pk": document_pk,
            "document_context": document_context,
        },
    )


@require_GET
def index(request):
    """Render the index page, which currently meta-redirects to /calendar/concise/"""
    return render(request, "index.dhtml")
