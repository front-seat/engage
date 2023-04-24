import typing as t

from django.conf import settings
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter


def _summarize_openai_langchain(
    text: str,
    map_prompt: str,
    combine_prompt: str,
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
    map_prompt_template = PromptTemplate(template=map_prompt, input_variables=["text"])
    combine_prompt_template = PromptTemplate(
        template=combine_prompt, input_variables=["text"]
    )
    chain = load_summarize_chain(
        llm,
        chain_type=chain_type,
        map_prompt=map_prompt_template,
        combine_prompt=combine_prompt_template,
    )
    summary = chain.run(documents)
    return summary


EDUCATED_LAYPERSON_PROMPT = """Write a charming, concise, and engaging summary of the following text. Target your summary at a highly educated layperson:


"{text}"


ENGAGING_SUMMARY:"""  # noqa: E501


def summarize_gpt35_educated_layperson(text: str) -> str:
    summary = _summarize_openai_langchain(
        text,
        map_prompt=EDUCATED_LAYPERSON_PROMPT,
        combine_prompt=EDUCATED_LAYPERSON_PROMPT,
    )
    return summary


HIGH_SCHOOL_PROMPT = """Write an engaging summary of the following text that's perfect for a high school student's reading level and attention span:

"{text}"

HIGH_SCHOOL_SUMMARY:"""  # noqa: E501


def summarize_gpt35_high_school(text: str) -> str:
    summary = _summarize_openai_langchain(
        text,
        map_prompt=HIGH_SCHOOL_PROMPT,
        combine_prompt=HIGH_SCHOOL_PROMPT,
    )
    return summary


ENTERTAINING_BLOG_POST_PROMPT = """Write an entertaining summary of the following text. Make it perfect for a blog post that we hope gets lots of shares:

"{text}"

ENTERTAINING_BLOG_POST_SUMMARY:"""  # noqa: E501


def summarize_gpt35_entertaining_blog_post(text: str) -> str:
    summary = _summarize_openai_langchain(
        text,
        map_prompt=ENTERTAINING_BLOG_POST_PROMPT,
        combine_prompt=ENTERTAINING_BLOG_POST_PROMPT,
    )
    return summary


NEWSPAPER_HEADLINE_PROMPT = """Write an engaging one-sentence newspaper headline for the following text. Assume your reader is a highly educated layperson:

"{text}"

ENGAGING_HEADLINE:"""  # noqa: E501


def summarize_gpt35_newspaper_headline(text: str) -> str:
    summary = _summarize_openai_langchain(
        text,
        map_prompt=EDUCATED_LAYPERSON_PROMPT,
        combine_prompt=NEWSPAPER_HEADLINE_PROMPT,
    )
    return summary


CATCHY_CONTROVERSIAL_HEADLINE_PROMPT = """Write a catchy, controversial one-sentence headline for the following text. Try and write something that will get lots of clicks:

"{text}"

CATCHY_HEADLINE:"""  # noqa: E501


def summarize_gpt35_catchy_controversial_headline(text: str) -> str:
    summary = _summarize_openai_langchain(
        text,
        map_prompt=EDUCATED_LAYPERSON_PROMPT,
        combine_prompt=CATCHY_CONTROVERSIAL_HEADLINE_PROMPT,
    )
    return summary


class SummarizerCallable(t.Protocol):
    __name__: str

    def __call__(self, text: str) -> str:
        ...
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
