import typing as t
from dataclasses import dataclass

from django.conf import settings
from django.template import Context, Template
from langchain.base_language import BaseLanguageModel
from langchain.chains.combine_documents.map_reduce import MapReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter

from server.lib.style import SummarizationStyle

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

    chunks: tuple[str, ...]
    """Text chunks sent to the LLM for summarization."""

    chunk_summaries: tuple[str, ...]
    """LLM outputs for each text chunk."""


# For the functional programming nerds in the house, here's our Either type. :-)
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
    """
    # We try to split the text in a few different ways. If we're lucky, one
    # of them will yield chunks entirely of size <= `chunk_size`.
    SEPARATORS = ["\n\n", "\n", ". "]

    texts = []
    for separator in SEPARATORS:
        text_splitter = CharacterTextSplitter(separator, chunk_size=chunk_size)
        texts = text_splitter.split_text(text)
        if all(len(text) <= chunk_size for text in texts):
            return texts

    # If we get here, we couldn't find a separator that worked. Just filter
    # out the long chunks.
    filtered_texts = [text for text in texts if len(text) <= chunk_size]
    if not filtered_texts:
        raise RuntimeError("Could not split text.")
    return filtered_texts


def summarize_langchain_llm(
    text: str,
    llm: BaseLanguageModel,
    map_template: str,
    body_combine_template: str,
    headline_combine_template: str,
    context: dict[str, t.Any] | None = None,
    chunk_size: int = 3584,
) -> SummarizationResult:
    """
    Summarize text using an arbitrary langchain LLM. Lowest level.

    We start by splitting the text into chunks of size `chunk_size`. We then
    run each chunk through the LLM using the `map_template` prompt.

    Next, we generate two final summaries: a `headline` (brief) summary and a
    `body` (detailed) summary. These summaries are generated by taking the
    chunk summaries and combining them using the `headline_combine_template`
    and `body_combine_template` prompts, respectively.

    LangChain *almost* makes this easy to do, but unfortunately buries some of
    the key functionality for re-using chunk summaries multiple times. I've
    tried to document our contortions as best I can in the code below.
    """
    # Check for a failure mode: if the text is empty, return an empty result.
    if not text.strip():
        return SummarizationError(original_text=text, message="Text was empty.")

    # Attempt to split our text into chunks of at most `chunk_size`.
    # We use LangChain's `CharacterTextSplitter` for this; it can fail.
    # For now, we consider this a failure mode and return a `SummarizationError`.
    try:
        texts = _attempt_to_split_text(text, chunk_size)
    except RuntimeError:
        return SummarizationError(original_text=text, message="Could not split text.")

    # LangChain documents are tuples of text and arbitrary metadata;
    # we don't use the metadata. It defaults to an empty dict.
    documents = [Document(page_content=text) for text in texts]

    # Build LangChain-style PromptTemplates.
    map_prompt = _make_langchain_prompt(map_template, context)
    body_combine_prompt = _make_langchain_prompt(body_combine_template, context)
    headline_combine_prompt = _make_langchain_prompt(headline_combine_template, context)

    # Build a LangChain summarization chain. This one will produce the body
    # summary.
    chain = load_summarize_chain(
        llm,
        chain_type="map_reduce",
        map_prompt=map_prompt,
        combine_prompt=body_combine_prompt,
        return_intermediate_steps=True,
    )
    # Our hack below depends on this being a MapReduceDocumentsChain.
    assert isinstance(chain, MapReduceDocumentsChain)

    # Run the chain.
    outputs = chain(documents)

    # Make sure the expected output keys are available.
    # (We used the `return_intermediate_steps=True` option above, so we expect
    # to see the `intermediate_steps` key.)
    assert "output_text" in outputs
    assert "intermediate_steps" in outputs

    # Great! We now have the body summary, and the intermediate steps:
    body = outputs["output_text"]
    chunk_summaries = outputs["intermediate_steps"]
    assert len(chunk_summaries) == len(documents)

    # Now we want to generate the headline summary. We want to re-use the
    # chunk summaries we already generated. There's useful code in
    # MapReduceDocumentsChain._process_results() that we want to make use of
    # here; unfortunately, it's buried in a private method. I've opted for a
    # big hack: replace `chain.combine_document_chain` with a new
    # one that uses the `headline` combine prompt, and then manually re-invoke
    # `chain._process_results()`. An alternative I considered: copying
    # langchain's code into our own codebase. That seemed annoying, too. Argh.
    reduce_chain = LLMChain(llm=llm, prompt=headline_combine_prompt)
    combine_document_chain = StuffDocumentsChain(
        llm_chain=reduce_chain,
        document_variable_name="text",
    )
    chain.combine_document_chain = combine_document_chain
    # Massage the chunk summaries into the shape expected by _process_results().
    hack_results = [
        {chain.llm_chain.output_key: chunk_summary} for chunk_summary in chunk_summaries
    ]
    # Call the private method on MapReduceDocumentsChain that we want to use.
    headline, _ = chain._process_results(results=hack_results, docs=documents)

    # We did it!
    return SummarizationSuccess(
        original_text=text,
        body=body,
        headline=headline,
        chunks=tuple(texts),
        chunk_summaries=tuple(outputs["intermediate_steps"]),
    )


def summarize_openai(
    text: str,
    map_template: str,
    body_combine_template: str,
    headline_combine_template: str,
    context: dict[str, t.Any] | None = None,
    model_name: str = "gpt-3.5-turbo",
    temperature: float = 0.4,
    chunk_size: int = 3584,
) -> SummarizationResult:
    """Summarize text using langchain and OpenAI. Low-level."""
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
        body_combine_template=body_combine_template,
        headline_combine_template=headline_combine_template,
        context=context,
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


def summarize_gpt35_concise(
    text: str, context: dict[str, t.Any] | None = None
) -> SummarizationResult:
    result = summarize_openai(
        text,
        map_template=CONCISE_SUMMARY_TEMPLATE,
        # Re-use the chunk summary template for the body summary.
        body_combine_template=CONCISE_SUMMARY_TEMPLATE,
        headline_combine_template=CONCISE_HEADLINE_TEMPLATE,
        context=context,
    )
    return result


# ---------------------------------------------------------------------
# External utilities
# ---------------------------------------------------------------------


@t.runtime_checkable
class SummarizerCallable(t.Protocol):
    __name__: str

    def __call__(
        self, text: str, context: dict[str, t.Any] | None = None
    ) -> SummarizationResult:
        ...


SUMMARIZERS: list[SummarizerCallable] = [
    summarize_gpt35_concise,
]


SUMMARIZERS_BY_STYLE: dict[SummarizationStyle, SummarizerCallable] = {
    "concise": summarize_gpt35_concise,
}
