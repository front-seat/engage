import typing as t

from django.conf import settings
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter

default_v1_prompt = """Write a charming, concise, and engaging summary of the following text. Target your summary at a highly educated layperson:


"{text}"


ENGAGING_SUMMARY:"""  # noqa: E501
default_v1_prompt_template = PromptTemplate(
    template=default_v1_prompt, input_variables=["text"]
)


def summarize_langchain_v1(
    text: str,
    temperature: float = 0.4,
    model_name: str = "gpt-3.5-turbo",
    chain_type: str = "map_reduce",
    chunk_size: int = 3584,
    map_prompt: str | None = None,
    combine_prompt: str | None = None,
    **kwargs: t.Any,
) -> str:
    """Summarize text using langchain and openAI. v1."""
    if settings.OPENAI_API_KEY is None:
        raise ValueError("OPENAI_API_KEY is not set.")
    llm = ChatOpenAI(
        client=None,  # XXX langchain type hints are busted; shouldn't be needed
        temperature=temperature,
        model_name=model_name,
        openai_organization=settings.OPENAI_ORGANIZATION,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    text_splitter = CharacterTextSplitter(chunk_size=chunk_size)
    texts = text_splitter.split_text(text)
    documents = [Document(page_content=text) for text in texts]
    map_prompt_template = (
        PromptTemplate(template=map_prompt, input_variables=["text"])
        if map_prompt
        else default_v1_prompt_template
    )
    combine_prompt_template = (
        PromptTemplate(template=combine_prompt, input_variables=["text"])
        if combine_prompt
        else default_v1_prompt_template
    )
    chain = load_summarize_chain(
        llm,
        chain_type=chain_type,
        map_prompt=map_prompt_template,
        combine_prompt=combine_prompt_template,
    )
    summary = chain.run(documents)
    return summary


def summarize_pipeline_v1(text: str, **kwargs: t.Any) -> str:
    """Summarize text using a pipeline of summarizers. v1."""
    summary = summarize_langchain_v1(text, **kwargs)
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
