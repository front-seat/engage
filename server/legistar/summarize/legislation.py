import typing as t

from server.documents.summarize import (
    CONCISE_SUMMARY_TEMPLATE,
    SummarizationResult,
    summarize_openai,
)
from server.lib.style import SummarizationStyle
from server.lib.truncate import truncate_str

# ---------------------------------------------------------------------
# Django templates for our LLM prompts
# ---------------------------------------------------------------------

# Django template syntax uses {{ variable_name }}; this does not conflict
# with the LangChain variable substitution syntax, which uses {variable_name}.
# But it *does* read a little confusingly. Sorry about that.

LEGISLATION_CONCISE_TEMPLATE = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a concise summary of the following text, which is titled "{{ title }}". Include the most important details:

"{text}"

CONCISE_CITY_COUNCIL_LEGISLATIVE_ACTION_SUMMARY:"""  # noqa: E501


LEGISLATION_CONCISE_HEADLINE_TEMPLATE = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a concise and extremely compact headline (one sentence or less) for the action, which is titled "{{ title }}". Capture only the most salient detail or two:

"{text}"

CONCISE_COMPACT_HEADLINE:"""  # noqa: E501


# ---------------------------------------------------------------------
# Legislation summarizers
# ---------------------------------------------------------------------


def _legislation_template_context(title: str) -> dict[str, t.Any]:
    """Return a Django template context for legislation prompts."""
    return {
        "title": truncate_str(title, 100).replace('"', "'"),
    }


def summarize_legislation_gpt35_concise(
    title: str,
    document_summary_texts: list[str],
) -> SummarizationResult:
    result = summarize_openai(
        "\n\n".join(document_summary_texts),
        map_template=CONCISE_SUMMARY_TEMPLATE,
        body_combine_template=LEGISLATION_CONCISE_TEMPLATE,
        headline_combine_template=LEGISLATION_CONCISE_HEADLINE_TEMPLATE,
        context=_legislation_template_context(title),
    )
    return result


# ---------------------------------------------------------------------
# Legislation external utilties
# ---------------------------------------------------------------------


@t.runtime_checkable
class LegislationSummarizerCallable(t.Protocol):
    __name__: str

    def __call__(
        self, title: str, document_summary_texts: list[str]
    ) -> SummarizationResult: ...


LEGISLATION_SUMMARIZERS: list[LegislationSummarizerCallable] = [
    summarize_legislation_gpt35_concise,
]

LEGISLATION_SUMMARIZERS_BY_STYLE: dict[
    SummarizationStyle, LegislationSummarizerCallable
] = {
    "concise": summarize_legislation_gpt35_concise,
}
