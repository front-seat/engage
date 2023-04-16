# class LegislationSummarizationPipeline
import sys
import typing as t

from django.conf import settings

from server.documents.extract import EXTRACT_PIPELINE_V1
from server.documents.models import Document, DocumentSummary, DocumentText
from server.documents.summarize import SUMMARIZE_PIPELINE_V1, run_summarizer

# CONSIDER: circular nonsense here, since .models imports this module.
from .models import Legislation, LegistarDocumentKind, Meeting

# CONSIDER: this is obviously not the final boss form. What do we really
# want to do here? -Dave

# CONSIDER: one thing to consider is that the server.document pipelines
# (extract & summarize) ARE NOT tied to the database whatsoever. That
# seems harder to do here, but it's worth thinking about. -Dave


# ---------------------------------------------------------------------
# Meeting pipelines
# ---------------------------------------------------------------------


MEETING_UNIFIED_SUMMARY_PROMPT_V1 = """The following is a set of descriptions of legislative actions on the agenda for an upcoming city councile meeting. Write a charming, concise, and engaging summary of the agenda. Target your summary at a highly educated layperson. Try to highlight the most impactful agenda items; it's okay to drop less important ones (like, for example, appointments to the local film commission) if there isn't enough space to include them all.

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
    leg_pipeline = get_legislation_pipeline(LEGISLATION_PIPELINE_V1)
    leg_summaries = []
    for legislation in meeting.legislations:
        leg_summaries.append(leg_pipeline(legislation))

    # Now summarize that in totality + add the extra meeting document_summaries.
    document_summaries.extend(leg_summaries)

    # Run a summarizer over the text of all the document summaries.
    if settings.VERBOSE:
        print(
            f">>>> SUMMARIZE: meeting({meeting}) - joining leg + meeting summaries",
            file=sys.stderr,
        )
    joined_summaries = "\n\n".join([ds.summary for ds in document_summaries])
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
    unified_summary = run_summarizer(SUMMARIZE_PIPELINE_V1, joined_summaries)
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
