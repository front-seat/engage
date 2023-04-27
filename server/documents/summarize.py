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
# Full summary prompts
# ---------------------------------------------------------------------

CONCISE_SUMMARY_PROMPT = """Write a concise summary of the following text. Include all the important details:

"{text}"

CONCISE_SUMMARY:"""  # noqa: E501


EDUCATED_LAYPERSON_PROMPT = """Write a charming, concise, and engaging summary of the following text. Target your summary at a highly educated layperson:


"{text}"


ENGAGING_SUMMARY:"""  # noqa: E501


HIGH_SCHOOL_PROMPT = """Write an engaging summary of the following text that's perfect for a high school student's reading level and attention span:

"{text}"

HIGH_SCHOOL_SUMMARY:"""  # noqa: E501


ENTERTAINING_BLOG_POST_PROMPT = """Write an entertaining summary of the following text. Make it perfect for a blog post that we hope goes viral and gets lots of clicks:

"{text}"

ENTERTAINING_BLOG_POST_SUMMARY:"""  # noqa: E501


# ---------------------------------------------------------------------
# Headline prompts
# ---------------------------------------------------------------------

NEWSPAPER_HEADLINE_PROMPT = """Write an engaging one-sentence newspaper headline for the following text. Assume your reader is a highly educated layperson:

"{text}"

ENGAGING_HEADLINE:"""  # noqa: E501


CATCHY_CONTROVERSIAL_HEADLINE_PROMPT = """Write a catchy, controversial one-sentence headline for the following text. Try and write something that will go viral and get of clicks:

"{text}"

CATCHY_HEADLINE:"""  # noqa: E501


# ---------------------------------------------------------------------
# Summarizers
# ---------------------------------------------------------------------


def summarize_gpt35_educated_layperson(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    assert substitutions is None, "substitutions not supported by this summarizer"
    summary = summarize_openai_langchain(
        text,
        map_prompt=EDUCATED_LAYPERSON_PROMPT,
        combine_prompt=EDUCATED_LAYPERSON_PROMPT,
        substitutions=substitutions,
    )
    return summary


def summarize_gpt35_high_school(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    assert substitutions is None, "substitutions not supported by this summarizer"
    summary = summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=HIGH_SCHOOL_PROMPT,
        substitutions=substitutions,
    )
    return summary


def summarize_gpt35_entertaining_blog_post(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    assert substitutions is None, "substitutions not supported by this summarizer"
    summary = summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=ENTERTAINING_BLOG_POST_PROMPT,
        substitutions=substitutions,
    )
    return summary


def summarize_gpt35_newspaper_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    assert substitutions is None, "substitutions not supported by this summarizer"
    summary = summarize_openai_langchain(
        text,
        map_prompt=EDUCATED_LAYPERSON_PROMPT,
        combine_prompt=NEWSPAPER_HEADLINE_PROMPT,
        substitutions=substitutions,
    )
    return summary


def summarize_gpt35_catchy_controversial_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    assert substitutions is None, "substitutions not supported by this summarizer"
    summary = summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=CATCHY_CONTROVERSIAL_HEADLINE_PROMPT,
        substitutions=substitutions,
    )
    return summary


# ---------------------------------------------------------------------
# External utilities
# ---------------------------------------------------------------------


class SummarizerCallable(t.Protocol):
    __name__: str

    def __call__(self, text: str, substitutions: dict[str, str] | None = None) -> str:
        ...


SUMMARIZERS: list[SummarizerCallable] = [
    summarize_gpt35_educated_layperson,
    summarize_gpt35_high_school,
    summarize_gpt35_entertaining_blog_post,
    summarize_gpt35_newspaper_headline,
    summarize_gpt35_catchy_controversial_headline,
]


SUMMARIZERS_BY_NAME: dict[str, SummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in SUMMARIZERS
}
