import datetime

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html_join
from django.views.decorators.http import require_GET

from server.documents.models import Document, DocumentSummary
from server.lib.pipeline_config import (
    PIPELINE_CONFIGS,
    PIPELINE_CONFIGS_BY_NAME,
    PipelineConfig,
)
from server.lib.truncate import truncate_str

from .models import Legislation, LegislationSummary, Meeting, MeetingSummary


def distill_calendars():
    for config in PIPELINE_CONFIGS:
        yield {"config_name": config.name}


def _summary_as_html(summary: str):
    splits = [s.strip() for s in summary.split("\n")]
    return format_html_join("\n", "<p>{}</p>", ((s,) for s in splits if s))


def _clean_headline(headline: str):
    # XXX this belongs elsehwere -- maybe as part of our summarization pipeline?
    headline = headline.strip()
    if headline.startswith("“") or headline.startswith('"'):
        headline = headline[1:]
    if headline.endswith("”") or headline.endswith('"'):
        headline = headline[:-1]
    return headline


def _make_legislation_mini_description(
    legislation: Legislation, config: PipelineConfig
) -> dict:
    headline = get_object_or_404(
        LegislationSummary,
        legislation=legislation,
        summarizer_name=config.legislation.headline,
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


def _make_meeting_description(meeting: Meeting, config: PipelineConfig) -> dict:
    if meeting.is_active:
        summary = get_object_or_404(
            MeetingSummary, meeting=meeting, summarizer_name=config.meeting.body
        )
        headline = get_object_or_404(
            MeetingSummary, meeting=meeting, summarizer_name=config.meeting.headline
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
                _make_legislation_mini_description(legislation, config)
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


def _make_document_mini_description(document: Document, config: PipelineConfig) -> dict:
    headline = get_object_or_404(
        DocumentSummary, document=document, summarizer_name=config.document.headline
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


def _make_legislation_description(
    legislation: Legislation, config: PipelineConfig
) -> dict:
    summary = get_object_or_404(
        LegislationSummary,
        legislation=legislation,
        summarizer_name=config.legislation.body,
    )
    headline = get_object_or_404(
        LegislationSummary,
        legislation=legislation,
        summarizer_name=config.legislation.headline,
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
            _make_document_mini_description(document, config)
            for document in legislation.documents.all()
        ],
    }


def _make_document_description(document: Document, config: PipelineConfig) -> dict:
    summary = get_object_or_404(
        DocumentSummary, document=document, summarizer_name=config.document.body
    )
    headline = get_object_or_404(
        DocumentSummary, document=document, summarizer_name=config.document.headline
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
def calendar(request, config_name: str):
    config = PIPELINE_CONFIGS_BY_NAME.get(config_name)
    if config is None:
        raise Http404(f"Unknown config name: {config_name}")
    meetings = Meeting.objects.future(relative_to=_get_relative_to()).order_by("-date")
    meeting_descriptions = [_make_meeting_description(m, config) for m in meetings]
    return render(
        request,
        "calendar.dhtml",
        {"config_name": config_name, "meeting_descriptions": meeting_descriptions},
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
        for config in PIPELINE_CONFIGS:
            yield {"meeting_id": meeting.legistar_id, "config_name": config.name}


@require_GET
def meeting(request, meeting_id: int, config_name: str):
    config = PIPELINE_CONFIGS_BY_NAME.get(config_name)
    if config is None:
        raise Http404(f"Unknown config name: {config_name}")
    meeting_ = get_object_or_404(Meeting, legistar_id=meeting_id)
    meeting_description = _make_meeting_description(meeting_, config)
    return render(
        request,
        "meeting.dhtml",
        {
            "config_name": config_name,
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
            for config in PIPELINE_CONFIGS:
                yield {
                    "meeting_id": meeting.legistar_id,
                    "legislation_id": legislation.legistar_id,
                    "config_name": config.name,
                }


@require_GET
def legislation(request, meeting_id: int, legislation_id: int, config_name: str):
    config = PIPELINE_CONFIGS_BY_NAME.get(config_name)
    if config is None:
        raise Http404(f"Unknown config name: {config_name}")
    legislation_ = get_object_or_404(Legislation, legistar_id=legislation_id)
    legislation_description = _make_legislation_description(legislation_, config)
    return render(
        request,
        "legislation.dhtml",
        {
            "config_name": config_name,
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
            for document in legislation.documents.all():
                if not document.summaries.exists():
                    continue
                for config in PIPELINE_CONFIGS:
                    yield {
                        "meeting_id": meeting.legistar_id,
                        "legislation_id": legislation.legistar_id,
                        "document_pk": document.pk,
                        "config_name": config.name,
                    }


@require_GET
def document(
    request, meeting_id: int, legislation_id: int, document_pk: int, config_name: str
):
    config = PIPELINE_CONFIGS_BY_NAME.get(config_name)
    if config is None:
        raise Http404(f"Unknown config name: {config_name}")
    document_ = get_object_or_404(Document, pk=document_pk)
    document_description = _make_document_description(document_, config)
    return render(
        request,
        "document.dhtml",
        {
            "config_name": config_name,
            "meeting_id": meeting_id,
            "legislation_id": legislation_id,
            "document_pk": document_pk,
            "document_description": document_description,
        },
    )


@require_GET
def index(request):
    return render(request, "index.dhtml")
