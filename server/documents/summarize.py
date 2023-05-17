import typing as t
from dataclasses import dataclass

from django.conf import settings
from django.template import Context, Template
from langchain.base_language import BaseLanguageModel
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter

# ---------------------------------------------------------------------
# Base utilities
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class SummarizationResultBase:
    original_text: str
    """The original text that was summarized."""

    @property
    def success(self) -> bool:
        return isinstance(self, SummarizationSuccess)


@dataclass(frozen=True)
class SummarizationError(SummarizationResultBase):
    """An error that occurred while summarizing a text."""

    message: str
    """A human-readable error message."""


@dataclass(frozen=True)
class SummarizationSuccess(SummarizationResultBase):
    """The result of summarizing a text."""

    body: str
    """A detailed summary of the text."""

    headline: str
    """A brief summary of the text."""

    chunks: tuple[str]
    """Text chunks sent to the LLM for summarization."""

    chunk_summaries: tuple[str]
    """LLM outputs for each text chunk."""


SummarizationResult: t.TypeAlias = SummarizationError | SummarizationSuccess


def _render_django_template(
    django_template: str, context: dict[str, t.Any] | None
) -> str:
    ctx = Context(context or {})
    template = Template(django_template)
    return template.render(ctx)


def _make_langchain_prompt(
    django_template: str,
    context: dict[str, t.Any] | None = None,
    input_variables: tuple[str] = ("text",),
) -> PromptTemplate:
    """
    Given a *Django* template-style prompt string, render the *Django* template
    into a final prompt string. From there, return a LangChain PromptTemplate
    instance.
    """
    rendered_prompt = _render_django_template(django_template, context)
    return PromptTemplate(
        template=rendered_prompt, input_variables=list(input_variables)
    )


def _attempt_to_split_text(text: str, chunk_size: int) -> list[str]:
    """
    Attempt to split text into chunks of at most `chunk_size`.

    If this fails, split on newlines.

    If this fails, raise an exception.
    """
    # Here, we use LangChain's *seemingly* buggy text splitter to attempt to
    # split the text into chunks of size `chunk_size`. If this fails, we try
    # to split the text on newlines. If *that* fails, we return an empty result.
    #
    # I've read LangChain's (paltry) docs; I've also read the underlying code.
    # Frankly, it's entirely unclear to me what the theory of operation of
    # CharacterTextSplitter even *is* here.
    #
    # FUTURE: replace this with something not-langchain.
    text_splitter = CharacterTextSplitter(chunk_size=chunk_size)
    texts = text_splitter.split_text(text)
    text_lengths = [len(text) for text in texts]
    if any(text_length > chunk_size for text_length in text_lengths):
        text_splitter = CharacterTextSplitter("\n", chunk_size=chunk_size)
        texts = text_splitter.split_text(text)
        text_lengths = [len(text) for text in texts]
        if any(text_length > chunk_size for text_length in text_lengths):
            raise RuntimeError("Could not split text into chunks.")
    return texts


def summarize_langchain_llm(
    text: str,
    llm: BaseLanguageModel,
    map_template: str,
    combine_template: str,
    context: dict[str, t.Any] | None = None,
    chain_type: str = "map_reduce",
    chunk_size: int = 3584,
) -> SummarizationResult:
    """Summarize text using an arbitrary langchain LLM. Lowest level."""
    # The first failure mode: if the text is empty, return an empty result.
    if not text.strip():
        return SummarizationError(original_text=text, message="Text was empty.")

    # The second failure mode: splitting text with LangChain blows up. ¯\_(ツ)_/¯
    try:
        texts = _attempt_to_split_text(text, chunk_size)
    except RuntimeError:
        return SummarizationError(original_text=text, message="Could not split text.")

    # You can't just split a string. Oh no, LangChain demands `Document` objects.
    documents = [Document(page_content=text) for text in texts]

    # Build LangChain-style PromptTemplates.
    map_prompt = _make_langchain_prompt(map_template, context)
    combine_prompt = _make_langchain_prompt(combine_template, context)

    # Build the summarization chain.
    chain = load_summarize_chain(
        llm,
        chain_type=chain_type,
        map_prompt=map_prompt,
        combine_prompt=combine_prompt,
        return_intermediate_steps=True,
    )

    # Run the chain.
    outputs = chain(documents)

    # Make sure the expected output keys are available.
    # (We used the `return_intermediate_steps=True` option above, so we expect
    # to see the `intermediate_steps` key.)
    assert "output_text" in outputs
    assert "intermediate_steps" in outputs

    # We did it!
    return SummarizationSuccess(
        original_text=text,
        body=outputs["output_text"],
        # XXX TODO DAVE
        headline=outputs["output_text"].split("\n")[0],
        chunks=tuple(texts),
        chunk_summaries=tuple(outputs["intermediate_steps"]),
    )


def summarize_openai(
    text: str,
    map_template: str,
    combine_template: str,
    context: dict[str, t.Any] | None = None,
    model_name: str = "gpt-3.5-turbo",
    temperature: float = 0.4,
    chain_type: str = "map_reduce",
    chunk_size: int = 3584,
) -> SummarizationResult:
    """Summarize text using langchain and openAI. Low-level."""
    if settings.OPENAI_API_KEY is None:
        raise ValueError("OPENAI_API_KEY is not set.")
    llm = ChatOpenAI(
        client=None,  # XXX langchain type hints are busted; shouldn't be needed
        temperature=temperature,
        model_name=model_name,
        openai_organization=settings.OPENAI_ORGANIZATION,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    return summarize_langchain_llm(
        text=text,
        llm=llm,
        map_template=map_template,
        combine_template=combine_template,
        context=context,
        chain_type=chain_type,
        chunk_size=chunk_size,
    )


# ---------------------------------------------------------------------
# Django templates for our LLM prompts
# ---------------------------------------------------------------------

# Django templates use {{ variable_name }} for variable substitution.
#
# LangChain uses {variable_name}.
#
# The `*_template` parameters to `summarize_openai(...)` are allowed to be
# both Django *and* LangChain templates; we render the Django template ourselves
# and pass that rendered result to LangChain.

CONCISE_SUMMARY_TEMPLATE = """Write a concise summary of the following text. Include the most important details:

TEXT:::
{text}
:::END_TEXT

CONCISE_SUMMARY:"""  # noqa: E501


CONCISE_HEADLINE_TEMPLATE = """Write a concise and extremely compact headline (one sentence or less) for the following text. Capture only the most salient detail or two:

TEXT:::
{text}
:::END_TEXT

CONCISE_COMPACT_HEADLINE:"""  # noqa: E501


# ---------------------------------------------------------------------
# Summarizers
# ---------------------------------------------------------------------


def summarize_gpt35_concise(text: str, context: dict[str, t.Any] | None = None) -> str:
    result = summarize_openai(
        text,
        map_template=CONCISE_SUMMARY_TEMPLATE,
        combine_template=CONCISE_SUMMARY_TEMPLATE,
        context=context,
    )
    return result.summary


def summarize_gpt35_concise_headline(
    text: str, context: dict[str, t.Any] | None = None
) -> str:
    result = summarize_openai(
        text,
        map_template=CONCISE_SUMMARY_TEMPLATE,
        combine_template=CONCISE_HEADLINE_TEMPLATE,
        context=context,
    )
    return result.summary


# ---------------------------------------------------------------------
# External utilities
# ---------------------------------------------------------------------


@t.runtime_checkable
class SummarizerCallable(t.Protocol):
    __name__: str

    def __call__(self, text: str, context: dict[str, t.Any] | None = None) -> str:
        ...


SUMMARIZERS: list[SummarizerCallable] = [
    summarize_gpt35_concise,
    summarize_gpt35_concise_headline,
]


SUMMARIZERS_BY_NAME: dict[str, SummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in SUMMARIZERS
}
