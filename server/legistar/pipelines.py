# class LegislationSummarizationPipeline
import sys
import typing as t

from django.conf import settings

from server.documents.summarize import (
    CONCISE_SUMMARY_PROMPT,
    SummarizerCallable,
    summarize_gpt35_concise,
    summarize_openai,
    summarize_vic13b_repdep,
    summarize_vic13b_repdep_concise,
)
from server.lib.truncate import truncate_str

# ---------------------------------------------------------------------
# Legislation prompts
# ---------------------------------------------------------------------

LEGISLATION_CONCISE_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a concise summary of the following text, which is titled "<<title>>". Include the most important details:

"{text}"

CONCISE_CITY_COUNCIL_LEGISLATIVE_ACTION_SUMMARY:"""  # noqa: E501


LEGISLATION_CONCISE_HEADLINE_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a concise and extremely compact headline (one sentence or less) for the action, which is titled "<<title>>". Capture only the most salient detail or two:

"{text}"

CONCISE_COMPACT_HEADLINE:"""  # noqa: E501


# ---------------------------------------------------------------------
# Legislation summarizers
# ---------------------------------------------------------------------


def _get_legislation_substitutions(title: str) -> dict[str, str]:
    return {
        "<<title>>": truncate_str(title, 100).replace('"', "'"),
    }


def summarize_legislation_gpt35_concise(
    title: str,
    document_summaries: list[str],
) -> str:
    return summarize_openai(
        "\n\n".join(document_summaries),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_CONCISE_PROMPT,
        substitutions=_get_legislation_substitutions(title),
    )


def summarize_legislation_vic13b_repdep_concise(
    title: str, document_summaries: list[str]
) -> str:
    return summarize_vic13b_repdep(
        "\n\n".join(document_summaries),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_CONCISE_PROMPT,
        substitutions=_get_legislation_substitutions(title),
    )


def summarize_legislation_gpt35_concise_headline(
    title: str, document_summaries: list[str]
) -> str:
    return summarize_openai(
        "\n\n".join(document_summaries),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_CONCISE_HEADLINE_PROMPT,
        substitutions=_get_legislation_substitutions(title),
    )


def summarize_legislation_vic13b_repdep_concise_headline(
    title: str, document_summaries: list[str]
) -> str:
    return summarize_vic13b_repdep(
        "\n\n".join(document_summaries),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_CONCISE_HEADLINE_PROMPT,
        substitutions=_get_legislation_substitutions(title),
    )


# ---------------------------------------------------------------------
# Legislation external utilties
# ---------------------------------------------------------------------


@t.runtime_checkable
class LegislationSummarizerCallable(t.Protocol):
    __name__: str

    def __call__(self, title: str, document_summaries: list[str]) -> str:
        ...


LEGISLATION_SUMMARIZERS: list[LegislationSummarizerCallable] = [
    summarize_legislation_gpt35_concise,
    summarize_legislation_gpt35_concise_headline,
    summarize_legislation_vic13b_repdep_concise,
    summarize_legislation_vic13b_repdep_concise_headline,
]

LEGISLATION_SUMMARIZERS_BY_NAME: dict[str, LegislationSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in LEGISLATION_SUMMARIZERS
}


# ---------------------------------------------------------------------
# Meeting prompts
# ---------------------------------------------------------------------


MEETING_CONCISE_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write a concise summary of the following text. Include the most important details:

"{text}"

CONCISE_AGENDA_SUMMARY:"""  # noqa: E501


MEETING_CONCISE_HEADLINE_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write a concise and extremely compact headline (one sentence or less) for the following text. Capture the most salient detail or two:

"{text}"

CONCISE_COMPACT_HEADLINE_FOR_AGENDA:"""  # noqa: E501


# ---------------------------------------------------------------------
# Meeting internal utilities
# ---------------------------------------------------------------------


def _summarize_meeting(
    meeting: Meeting,
    document_summarizer: SummarizerCallable,
    legislation_summarizer: LegislationSummarizerCallable,
    join_summarizer: SummarizerCallable,
    verbose_name: str,
) -> str:
    if settings.VERBOSE:
        print(
            f">>>> SUMMARIZE: meeting docs {verbose_name}({meeting})",
            file=sys.stderr,
        )

    # Summarize every document associated with this meeting, EXCEPT
    # those of type LegistarDocumentKind.AGENDA and LegistarDocumentKind.AGENDA_PACKET.
    # "Agenda" duplicates meeting.schema.rows but is not as nicely formatted.
    # "Agenda Packet" is a PDF of the agenda + attachments, which we are going
    # to summarize separately.
    document_summaries: list[DocumentSummary] = []
    qs = meeting.documents.exclude(
        kind__in=[LegistarDocumentKind.AGENDA, LegistarDocumentKind.AGENDA_PACKET]
    )
    document_summaries = [
        _extract_and_summarize_document(document, document_summarizer)
        for document in qs
    ]

    # Make sure we've summarized each piece of associated legislation.
    # XXX TODO: compare _extract_and_summarize_document(...), which creates
    # stuff in the database, with _summarize_legislation(...), which doesn't,
    # and which is why we call get_or_create(...) directly. This is all very
    # silly and non-parallel and clearly we need to do better. -Dave
    legislation_summaries = []
    for legislation in meeting.legislations:
        l_summ, _ = LegislationSummary.objects.get_or_create_from_legislation(
            legislation, legislation_summarizer
        )
        legislation_summaries.append(l_summ)

    # Now summarize that in totality + add the extra meeting document_summaries.
    document_summary_texts = [ds.summary for ds in document_summaries]
    summary_texts = [ls.summary for ls in legislation_summaries]
    all_texts = summary_texts + document_summary_texts

    # Run a summarizer over the text of all the document summaries.
    if settings.VERBOSE:
        print(
            f">>>> SUMMARIZE: meeting join {verbose_name}({meeting})",
            file=sys.stderr,
        )
    joined_summaries = "\n\n".join(all_texts)
    substitutions = {"<<department>>": meeting.schema.department.name}
    return join_summarizer(joined_summaries, substitutions)


# ---------------------------------------------------------------------
# Meeting joiners
# ---------------------------------------------------------------------


def _join_meeting_summaries_gpt35_concise(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_vic13b_repdep_concise(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_vic13b_repdep(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_concise_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_vic13b_repdep_concise_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_vic13b_repdep(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


# ---------------------------------------------------------------------
# Meeting summarizers
# ---------------------------------------------------------------------


def summarize_meeting_gpt35_concise(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_concise,
        legislation_summarizer=summarize_legislation_gpt35_concise,
        join_summarizer=_join_meeting_summaries_gpt35_concise,
        verbose_name="gpt35_concise",
    )


def summarize_meeting_vic13b_repdep_concise(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_vic13b_repdep_concise,
        legislation_summarizer=summarize_legislation_vic13b_repdep_concise,
        join_summarizer=_join_meeting_summaries_vic13b_repdep_concise,
        verbose_name="vic13b_repdep_concise",
    )


def summarize_meeting_gpt35_concise_headline(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_concise,
        legislation_summarizer=summarize_legislation_gpt35_concise,
        join_summarizer=_join_meeting_summaries_gpt35_concise_headline,
        verbose_name="gpt35_concise_headline",
    )


def summarize_meeting_vic13b_repdep_concise_headline(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_vic13b_repdep_concise,
        legislation_summarizer=summarize_legislation_vic13b_repdep_concise,
        join_summarizer=_join_meeting_summaries_vic13b_repdep_concise_headline,
        verbose_name="vic13b_repdep_concise_headline",
    )


# ---------------------------------------------------------------------
# Meeting external utilties
# ---------------------------------------------------------------------


@t.runtime_checkable
class MeetingSummarizerCallable(t.Protocol):
    __name__: str

    def __call__(self, meeting: Meeting) -> str:
        ...


MEETING_SUMMARIZERS: list[MeetingSummarizerCallable] = [
    summarize_meeting_gpt35_concise,
    summarize_meeting_gpt35_concise_headline,
    summarize_meeting_vic13b_repdep_concise,
    summarize_meeting_vic13b_repdep_concise_headline,
]

MEETING_SUMMARIZERS_BY_NAME: dict[str, MeetingSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in MEETING_SUMMARIZERS
}
MEETING_SUMMARIZERS_BY_NAME: dict[str, MeetingSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in MEETING_SUMMARIZERS
}
