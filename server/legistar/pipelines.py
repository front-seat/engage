# class LegislationSummarizationPipeline
import sys
import typing as t

from django.conf import settings

from server.documents.extract import EXTRACT_PIPELINE_V1
from server.documents.models import Document, DocumentSummary, DocumentText
from server.documents.summarize import SUMMARIZE_PIPELINE_V1, run_summarizer

# CONSIDER: circular nonsense here, since .models imports this module.
from .models import Legislation, LegislationSummary, LegistarDocumentKind, Meeting

# CONSIDER: this is obviously not the final boss form. What do we really
# want to do here? -Dave

# CONSIDER: one thing to consider is that the server.document pipelines
# (extract & summarize) ARE NOT tied to the database whatsoever. That
# seems harder to do here, but it's worth thinking about. -Dave


# ---------------------------------------------------------------------
# Meeting pipelines
# ---------------------------------------------------------------------


MEETING_UNIFIED_SUMMARY_PROMPT_V1 = """The following is a set of descriptions of legislative actions on the agenda for an upcoming city council meeting. Write a charming, concise, and engaging summary of the agenda. Target your summary at a highly educated layperson. Try to highlight the most impactful agenda items; it's okay to drop less important ones (like, for example, appointments to the local film commission) if there isn't enough space to include them all.

"{text}"

ENGAGING_CITY_COUNCIL_AGENDA_SUMMARY:"""  # noqa: E501


def summarize_meeting_document_v1(
    meeting: Meeting, document: Document
) -> DocumentSummary:
    document_text, _ = DocumentText.objects.get_or_create_from_document(
        document, extractor_name=EXTRACT_PIPELINE_V1
    )
    document_summary, _ = DocumentSummary.objects.get_or_create_from_document_text(
        document_text, summarizer_name=SUMMARIZE_PIPELINE_V1
    )
    return document_summary


def summarize_meeting_v1(meeting: Meeting, **kwargs: t.Any) -> str:
    if settings.VERBOSE:
        print(f">>>> SUMMARIZE: meeting({meeting})", file=sys.stderr)

    # Summarize every document associated with this meeting, EXCEPT
    # those of type LegistarDocumentKind.AGENDA and LegistarDocumentKind.AGENDA_PACKET.
    # "Agenda" duplicates meeting.schema.rows but is not as nicely formatted.
    # "Agenda Packet" is a PDF of the agenda + attachments, which we are going
    # to summarize separately.
    document_summaries: list[DocumentSummary] = []
    qs = meeting.documents.exclude(
        kind__in=[LegistarDocumentKind.AGENDA, LegistarDocumentKind.AGENDA_PACKET]
    )
    for document in qs:
        document_summaries.append(summarize_meeting_document_v1(meeting, document))

    # Make sure we've summarized each piece of associated legislation.
    legislation_summaries = []
    for legislation in meeting.legislations:
        (
            legislation_summary,
            _,
        ) = LegislationSummary.objects.get_or_create_from_legislation(
            legislation, LEGISLATION_PIPELINE_V1
        )
        legislation_summaries.append(legislation_summary)

    # Now summarize that in totality + add the extra meeting document_summaries.
    document_summary_texts = [ds.summary for ds in document_summaries]
    summary_texts = [ls.summary for ls in legislation_summaries]
    all_texts = summary_texts + document_summary_texts

    # Run a summarizer over the text of all the document summaries.
    if settings.VERBOSE:
        print(
            f">>>> SUMMARIZE: meeting({meeting}) - joining leg + meeting summaries",
            file=sys.stderr,
        )
    joined_summaries = "\n\n".join(all_texts)
    unified_summary = run_summarizer(
        SUMMARIZE_PIPELINE_V1,
        joined_summaries,
        map_prompt=MEETING_UNIFIED_SUMMARY_PROMPT_V1,
        combine_prompt=MEETING_UNIFIED_SUMMARY_PROMPT_V1,
    )
    return unified_summary


class MeetingPipelineCallable(t.Protocol):
    def __call__(self, meeting: Meeting, **kwargs: t.Any) -> str:
        ...


MEETING_PIPELINE_V1 = "meeting-pipeline-v1"


MEETING_PIPELINES: dict[str, MeetingPipelineCallable] = {
    MEETING_PIPELINE_V1: summarize_meeting_v1,
}


def get_meeting_pipeline(name: str) -> MeetingPipelineCallable:
    return MEETING_PIPELINES[name]


def run_meeting_pipeline(name: str, meeting: Meeting, **kwargs: t.Any) -> str:
    return get_meeting_pipeline(name)(meeting, **kwargs)


# ---------------------------------------------------------------------
# Legislation pipelines
# ---------------------------------------------------------------------


LEGISLATION_UNIFIED_SUMMARY_PROMPT_V1 = """The following is a set of descriptions of documents related to a single legislation action taken by a large city council. Write a charming, concise, and engaging summary of the legislative effort, which is titled "<<title>>". Target your summary at a highly educated layperson. Try to highlight the most impactful agenda items; it's okay to drop less important ones (like, for example, appointments to the local film commission) if there isn't enough space to include them all.

"{text}"

ENGAGING_CITY_COUNCIL_LEGISLATIVE_ACTION_SUMMARY:"""  # noqa: E501


def summarize_legislation_document_v1(
    legislation: Legislation, document: Document
) -> DocumentSummary:
    document_text, _ = DocumentText.objects.get_or_create_from_document(
        document, extractor_name=EXTRACT_PIPELINE_V1
    )
    document_summary, _ = DocumentSummary.objects.get_or_create_from_document_text(
        document_text, summarizer_name=SUMMARIZE_PIPELINE_V1
    )
    return document_summary


def summarize_legislation_v1(legislation: Legislation, **kwargs: t.Any) -> str:
    if settings.VERBOSE:
        print(f">>>> SUMMARIZE: legislation({legislation})", file=sys.stderr)

    # Summarize every document associated with this legislation.
    document_summaries: list[DocumentSummary] = []
    for document in legislation.documents.all():
        document_summaries.append(
            summarize_legislation_document_v1(legislation, document)
        )

    # Run a summarizer over the text of all the document summaries.
    if settings.VERBOSE:
        print(
            f">>>> SUMMARIZE: legislation({legislation}) - joining summaries",
            file=sys.stderr,
        )
    joined_summaries = "\n\n".join([ds.summary for ds in document_summaries])
    # XXX do something smarter here!
    mid_length_title = (
        legislation.title[:100] + "..."
        if len(legislation.title) > 100
        else legislation.title
    )
    mid_length_title = mid_length_title.replace('"', "'")
    prompt = LEGISLATION_UNIFIED_SUMMARY_PROMPT_V1.replace(
        "<<title>>", mid_length_title
    )
    # XXX figure out how to send multiple variables through a chain
    unified_summary = run_summarizer(
        SUMMARIZE_PIPELINE_V1,
        joined_summaries,
        map_prompt=prompt,
        combine_prompt=prompt,
    )
    return unified_summary


class LegislationPipelineCallable(t.Protocol):
    def __call__(self, legislation: Legislation, **kwargs: t.Any) -> str:
        ...


LEGISLATION_PIPELINE_V1 = "legislation-pipeline-v1"

LEGISLATION_PIPELINES: dict[str, LegislationPipelineCallable] = {
    LEGISLATION_PIPELINE_V1: summarize_legislation_v1,
}


def get_legislation_pipeline(name: str) -> LegislationPipelineCallable:
    return LEGISLATION_PIPELINES[name]


def run_legislation_pipeline(
    name: str, legislation: Legislation, **kwargs: t.Any
) -> str:
    return get_legislation_pipeline(name)(legislation, **kwargs)
