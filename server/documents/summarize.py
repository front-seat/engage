import typing as t

from django.conf import settings
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter

# ---------------------------------------------------------------------
# Base utilities
# ---------------------------------------------------------------------


def _substitute(s: str, substitutions: dict[str, str] | None) -> str:
    if substitutions is None:
        return s
    for key, value in substitutions.items():
        s = s.replace(key, value)
    return s


def summarize_openai_langchain(
    text: str,
    map_prompt: str,
    combine_prompt: str,
    substitutions: dict[str, str] | None = None,
    model_name: str = "gpt-3.5-turbo",
    temperature: float = 0.4,
    chain_type: str = "map_reduce",
    chunk_size: int = 3584,
) -> str:
    """Summarize text using langchain and openAI. Low-level."""
    if settings.OPENAI_API_KEY is None:
        raise ValueError("OPENAI_API_KEY is not set.")
    # XXX figure out how to handle this more gracefully
    if not text.strip():
        return "(no summary available)"
    llm = ChatOpenAI(
        client=None,  # XXX langchain type hints are busted; shouldn't be needed
        temperature=temperature,
        model_name=model_name,
        openai_organization=settings.OPENAI_ORGANIZATION,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    text_splitter = CharacterTextSplitter(chunk_size=chunk_size)
    texts = text_splitter.split_text(text)
    text_lengths = [len(text) for text in texts]
    if any(text_length > chunk_size for text_length in text_lengths):
        text_splitter = CharacterTextSplitter("\n", chunk_size=chunk_size)
        texts = text_splitter.split_text(text)
        text_lengths = [len(text) for text in texts]
        if any(text_length > chunk_size for text_length in text_lengths):
            raise ValueError("Unable to split text into small enough chunks.")

    documents = [Document(page_content=text) for text in texts]
    final_map_prompt = _substitute(map_prompt, substitutions)
    map_prompt_template = PromptTemplate(
        template=final_map_prompt, input_variables=["text"]
    )
    final_combine_prompt = _substitute(combine_prompt, substitutions)
    combine_prompt_template = PromptTemplate(
        template=final_combine_prompt, input_variables=["text"]
    )
    chain = load_summarize_chain(
        llm,
        chain_type=chain_type,
        map_prompt=map_prompt_template,
        combine_prompt=combine_prompt_template,
    )
    summary = chain.run(documents)
    return summary


# ---------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------

CONCISE_SUMMARY_PROMPT = """Write a concise summary of the following text. Include the most important details:

"{text}"

CONCISE_SUMMARY:"""  # noqa: E501


CONCISE_HEADLINE_PROMPT = """Write a concise and extremely compact headline (one sentence or less) for the following text. Capture only the most salient detail or two:

"{text}"

CONCISE_COMPACT_HEADLINE:"""  # noqa: E501


# ---------------------------------------------------------------------
# Summarizers
# ---------------------------------------------------------------------


def summarize_gpt35_concise(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    assert substitutions is None, "substitutions not supported by this summarizer"
    summary = summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=CONCISE_SUMMARY_PROMPT,
        substitutions=substitutions,
    )
    return summary


def summarize_gpt35_concise_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    assert substitutions is None, "substitutions not supported by this summarizer"
    summary = summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=CONCISE_HEADLINE_PROMPT,
        substitutions=substitutions,
    )
    return summary


# ---------------------------------------------------------------------
# External utilities
# ---------------------------------------------------------------------


@t.runtime_checkable
class SummarizerCallable(t.Protocol):
    __name__: str

    def __call__(self, text: str, substitutions: dict[str, str] | None = None) -> str:
        ...


SUMMARIZERS: list[SummarizerCallable] = [
    summarize_gpt35_concise,
    summarize_gpt35_concise_headline,
]


SUMMARIZERS_BY_NAME: dict[str, SummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in SUMMARIZERS
}
