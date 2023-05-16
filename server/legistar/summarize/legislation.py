import typing as t

from server.documents.summarize import CONCISE_SUMMARY_PROMPT, summarize_openai
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
    document_summary_texts: list[str],
) -> str:
    result = summarize_openai(
        "\n\n".join(document_summary_texts),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_CONCISE_PROMPT,
        substitutions=_get_legislation_substitutions(title),
    )
    return result.summary


def summarize_legislation_gpt35_concise_headline(
    title: str, document_summary_texts: list[str]
) -> str:
    result = summarize_openai(
        "\n\n".join(document_summary_texts),
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_CONCISE_HEADLINE_PROMPT,
        substitutions=_get_legislation_substitutions(title),
    )
    return result.summary


# ---------------------------------------------------------------------
# Legislation external utilties
# ---------------------------------------------------------------------


@t.runtime_checkable
class LegislationSummarizerCallable(t.Protocol):
    __name__: str

    def __call__(self, title: str, document_summary_texts: list[str]) -> str:
        ...


LEGISLATION_SUMMARIZERS: list[LegislationSummarizerCallable] = [
    summarize_legislation_gpt35_concise,
    summarize_legislation_gpt35_concise_headline,
]

LEGISLATION_SUMMARIZERS_BY_NAME: dict[str, LegislationSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in LEGISLATION_SUMMARIZERS
}
