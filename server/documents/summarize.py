import typing as t

from django.conf import settings
from langchain import OpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter


def summarize_langchain_v1(
    text: str,
    temperature: float = 0.2,
    model_name: str = "gpt-3.5-turbo",
    chain_type: str = "map_reduce",
    **kwargs: t.Any,
) -> str:
    """Summarize text using langchain and openAI. v1."""
    if settings.OPENAI_API_KEY is None:
        raise ValueError("OPENAI_API_KEY is not set.")
    llm = OpenAI(
        client=None,  # XXX langchain type hints are busted; shouldn't be needed
        temperature=temperature,
        model_name=model_name,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    text_splitter = CharacterTextSplitter(text)
    texts = text_splitter.split_text(text)
    documents = [Document(page_content=text) for text in texts]
    chain = load_summarize_chain(llm, chain_type=chain_type)
    summary = chain.run(documents)
    return summary


def summarize_pipeline_v1(text: str, **kwargs: t.Any) -> str:
    """Summarize text using a pipeline of summarizers. v1."""
    summary = summarize_langchain_v1(text)
    return summary


class SummarizerCallable(t.Protocol):
    def __call__(self, text: str, **kwargs: t.Any) -> str:
        ...


SUMMARIZE_PIPELINE_V1 = "summarize-pipeline-v1"


SUMMARIZERS: dict[str, SummarizerCallable] = {
    SUMMARIZE_PIPELINE_V1: summarize_pipeline_v1,
}


def get_summarizer(name: str) -> SummarizerCallable:
    """Get a summarizer for a given MIME type and version."""
    return SUMMARIZERS[name]


def run_summarizer(name: str, text: str, **kwargs: t.Any) -> str:
    """Run the summarizer for a given MIME type and version."""
    return SUMMARIZERS[name](text, **kwargs)
