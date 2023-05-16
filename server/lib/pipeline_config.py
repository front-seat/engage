from dataclasses import dataclass

# CONSIDER: This file lives in the server.lib package, but it "knows"
# about the summarization methods in the server.documents.* and server.legistar.*
# packages. This is a bit of a violation of the dependency graph.
# It's possible that choosing to make two separate packages on day one (aka
# server.documents and server.legistar) was a bit of a mistake. Perhaps they should
# be combined into a single package called server.data or something like that. Then
# this file would have a more natural home in server.data. -Dave


@dataclass(frozen=True)
class SummarizationConfig:
    body: str
    """The name of the summarization method for the body."""

    headline: str
    """The name of the summarization method for the headline."""


@dataclass(frozen=True)
class PipelineConfig:
    """
    Defines all the summarization & extraction parameters needed to go from
    raw documents to a final meeting summary.
    """

    name: str
    """The name of this pipeline configuration."""

    meeting: SummarizationConfig
    """The summarization configuration for meetings."""

    legislation: SummarizationConfig
    """The summarization configuration for legislation."""

    document: SummarizationConfig
    """The summarization configuration for individual documents."""

    extractor: str
    """The name of the text extraction method to use for this pipeline."""


CONCISE_PIPELINE_CONFIG = PipelineConfig(
    name="concise",
    meeting=SummarizationConfig(
        body="summarize_meeting_gpt35_concise",
        headline="summarize_meeting_gpt35_concise_headline",
    ),
    legislation=SummarizationConfig(
        body="summarize_legislation_gpt35_concise",
        headline="summarize_legislation_gpt35_concise_headline",
    ),
    document=SummarizationConfig(
        body="summarize_document_gpt35_concise",
        headline="summarize_document_gpt35_concise_headline",
    ),
    extractor="extract_pipeline_v1",
)


PIPELINE_CONFIGS: list[PipelineConfig] = [
    CONCISE_PIPELINE_CONFIG,
]


PIPELINE_CONFIGS_BY_NAME: dict[str, PipelineConfig] = {
    config.name: config for config in PIPELINE_CONFIGS
}


def pipeline_config_for_document_summarizer(
    summarizer_name: str,
) -> PipelineConfig:
    """
    Returns the pipeline configuration that uses the given summarizer for
    document summarization.
    """
    for config in PIPELINE_CONFIGS:
        # Check config.document.body and config.document.headline
        if summarizer_name in (config.document.body, config.document.headline):
            return config
    raise ValueError(f"Unknown summarizer: {summarizer_name}")


def pipeline_config_for_legislation_summarizer(
    summarizer_name: str,
) -> PipelineConfig:
    """
    Returns the pipeline configuration that uses the given summarizer for
    legislation summarization.
    """
    for config in PIPELINE_CONFIGS:
        # Check config.legislation.body and config.legislation.headline
        if summarizer_name in (config.legislation.body, config.legislation.headline):
            return config
    raise ValueError(f"Unknown summarizer: {summarizer_name}")


def pipeline_config_for_meeting_summarizer(
    summarizer_name: str,
) -> PipelineConfig:
    """
    Returns the pipeline configuration that uses the given summarizer for
    meeting summarization.
    """
    for config in PIPELINE_CONFIGS:
        # Check config.meeting.body and config.meeting.headline
        if summarizer_name in (config.meeting.body, config.meeting.headline):
            return config
    raise ValueError(f"Unknown summarizer: {summarizer_name}")
