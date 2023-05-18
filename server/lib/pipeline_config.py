import typing as t
from dataclasses import dataclass

# CONSIDER: This file lives in the server.lib package, but it "knows"
# about the summarization methods in the server.documents.* and server.legistar.*
# packages. This is a bit of a violation of the dependency graph.
# It's possible that choosing to make two separate packages on day one (aka
# server.documents and server.legistar) was a bit of a mistake. Perhaps they should
# be combined into a single package called server.data or something like that. Then
# this file would have a more natural home in server.data. -Dave


SummarizationClass: t.TypeAlias = t.Literal["meeting", "legislation", "document"]

SUMMARIZATION_CLASSES: frozenset[SummarizationClass] = frozenset(
    ["meeting", "legislation", "document"]
)


@dataclass(frozen=True)
class PipelineConfig:
    """
    Defines all the summarization & extraction parameters needed to go from
    raw documents to a final meeting summary.
    """

    name: str
    """The name of this pipeline configuration."""

    meeting: str
    """The name of the meeting summarization method."""

    legislation: str
    """The name of the legislation summarization method."""

    document: str
    """The name of the individual document summarization method."""

    extractor: str
    """The name of the text extraction method to use for this pipeline."""

    def for_class(self, klass: SummarizationClass) -> str:
        """
        Returns the summarization configuration for the given class of
        summarization.
        """
        if klass == "meeting":
            return self.meeting
        elif klass == "legislation":
            return self.legislation
        elif klass == "document":
            return self.document
        else:
            raise ValueError(f"Unknown summarization class: {klass}")


CONCISE_PIPELINE_CONFIG = PipelineConfig(
    name="concise",
    meeting="summarize_meeting_gpt35_concise",
    legislation="summarize_legislation_gpt35_concise",
    document="summarize_gpt35_concise",
    extractor="extract_pipeline_v1",
)


PIPELINE_CONFIGS: list[PipelineConfig] = [
    CONCISE_PIPELINE_CONFIG,
]


PIPELINE_CONFIGS_BY_NAME: dict[str, PipelineConfig] = {
    config.name: config for config in PIPELINE_CONFIGS
}
