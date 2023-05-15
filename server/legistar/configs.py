from dataclasses import dataclass


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
