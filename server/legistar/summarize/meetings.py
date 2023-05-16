import typing as t

from server.documents.summarize import CONCISE_SUMMARY_TEMPLATE, summarize_openai

# ---------------------------------------------------------------------
# Django templates for our LLM prompts
# ---------------------------------------------------------------------

# Django template syntax uses {{ variable_name }}; this does not conflict
# with the LangChain variable substitution syntax, which uses {variable_name}.
# But it *does* read a little confusingly. Sorry about that.

MEETING_CONCISE_TEMPLATE = """The following is a set of descriptions of items on the agenda for an upcoming {{ department }} meeting. Write a concise summary of the following text. Include the most important details:

"{text}"

CONCISE_AGENDA_SUMMARY:"""  # noqa: E501


MEETING_CONCISE_HEADLINE_TEMPLATE = """The following is a set of descriptions of items on the agenda for an upcoming {{ department }} meeting. Write a concise and extremely compact headline (one sentence or less) for the following text. Capture the most salient detail or two:

"{text}"

CONCISE_COMPACT_HEADLINE_FOR_AGENDA:"""  # noqa: E501


# ---------------------------------------------------------------------
# Meeting summarizers
# ---------------------------------------------------------------------


def _meeting_template_context(department_name: str) -> dict[str, t.Any]:
    """Return a context dictionary for our Django meeting templates."""
    return {"department": department_name}


def summarize_meeting_gpt35_concise(
    department_name: str,
    document_summary_texts: list[str],
    legislation_summary_texts: list[str],
) -> str:
    result = summarize_openai(
        "\n\n".join(document_summary_texts + legislation_summary_texts),
        map_template=CONCISE_SUMMARY_TEMPLATE,
        combine_template=MEETING_CONCISE_TEMPLATE,
        context=_meeting_template_context(department_name),
    )
    return result.summary


def summarize_meeting_gpt35_concise_headline(
    department_name: str,
    document_summary_texts: list[str],
    legislation_summary_texts: list[str],
) -> str:
    result = summarize_openai(
        "\n\n".join(document_summary_texts + legislation_summary_texts),
        map_template=CONCISE_SUMMARY_TEMPLATE,
        combine_template=MEETING_CONCISE_HEADLINE_TEMPLATE,
        context=_meeting_template_context(department_name),
    )
    return result.summary


# ---------------------------------------------------------------------
# Meeting external utilties
# ---------------------------------------------------------------------


@t.runtime_checkable
class MeetingSummarizerCallable(t.Protocol):
    __name__: str

    def __call__(
        self,
        department_name: str,
        document_summary_texts: list[str],
        legislation_summary_texts: list[str],
    ) -> str:
        ...


MEETING_SUMMARIZERS: list[MeetingSummarizerCallable] = [
    summarize_meeting_gpt35_concise,
    summarize_meeting_gpt35_concise_headline,
]

MEETING_SUMMARIZERS_BY_NAME: dict[str, MeetingSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in MEETING_SUMMARIZERS
}
MEETING_SUMMARIZERS_BY_NAME: dict[str, MeetingSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in MEETING_SUMMARIZERS
}
