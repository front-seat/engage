import typing as t

from server.documents.summarize import (
    CONCISE_SUMMARY_PROMPT,
    summarize_openai,
    summarize_vic13b_repdep,
)

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
# Meeting summarizers
# ---------------------------------------------------------------------


def _get_meeting_substitutions(department_name: str) -> dict[str, str]:
    return {"<<department>>": department_name}


def summarize_meeting_gpt35_concise(
    department_name: str,
    document_summaries: list[str],
    legislation_summaries: list[str],
) -> str:
    return summarize_openai(
        "\n\n".join(document_summaries + legislation_summaries),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_PROMPT,
        substitutions=_get_meeting_substitutions(department_name),
    )


def summarize_meeting_vic13b_repdep_concise(
    department_name: str,
    document_summaries: list[str],
    legislation_summaries: list[str],
) -> str:
    return summarize_vic13b_repdep(
        "\n\n".join(document_summaries + legislation_summaries),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_PROMPT,
        substitutions=_get_meeting_substitutions(department_name),
    )


def summarize_meeting_gpt35_concise_headline(
    department_name: str,
    document_summaries: list[str],
    legislation_summaries: list[str],
) -> str:
    return summarize_openai(
        "\n\n".join(document_summaries + legislation_summaries),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_HEADLINE_PROMPT,
        substitutions=_get_meeting_substitutions(department_name),
    )


def summarize_meeting_vic13b_repdep_concise_headline(
    department_name: str,
    document_summaries: list[str],
    legislation_summaries: list[str],
) -> str:
    return summarize_vic13b_repdep(
        "\n\n".join(document_summaries + legislation_summaries),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_HEADLINE_PROMPT,
        substitutions=_get_meeting_substitutions(department_name),
    )


# ---------------------------------------------------------------------
# Meeting external utilties
# ---------------------------------------------------------------------


@t.runtime_checkable
class MeetingSummarizerCallable(t.Protocol):
    __name__: str

    def __call__(
        self,
        department_name: str,
        document_summaries: list[str],
        legislation_summaries: list[str],
    ) -> str:
        ...


MEETING_SUMMARIZERS: list[MeetingSummarizerCallable] = [
    summarize_meeting_gpt35_concise,
    summarize_meeting_gpt35_concise_headline,
    # summarize_meeting_vic13b_repdep_concise,
    # summarize_meeting_vic13b_repdep_concise_headline,
]

MEETING_SUMMARIZERS_BY_NAME: dict[str, MeetingSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in MEETING_SUMMARIZERS
}
MEETING_SUMMARIZERS_BY_NAME: dict[str, MeetingSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in MEETING_SUMMARIZERS
}
