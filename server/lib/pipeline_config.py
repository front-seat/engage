import typing as t
from dataclasses import dataclass

# CONSIDER: This file lives in the server.lib package, but it "knows"
# about the summarization methods in the server.documents.* and server.legistar.*
# packages. This is a bit of a violation of the dependency graph.
# It's possible that choosing to make two separate packages on day one (aka
# server.documents and server.legistar) was a bit of a mistake. Perhaps they should
# be combined into a single package called server.data or something like that. Then
# this file would have a more natural home in server.data. -Dave


SummarizationKind: t.TypeAlias = t.Literal["body", "headline"]
SummarizationClass: t.TypeAlias = t.Literal["meeting", "legislation", "document"]

SUMMARIZATION_KINDS: frozenset[SummarizationKind] = frozenset(["body", "headline"])
SUMMARIZATION_CLASSES: frozenset[SummarizationClass] = frozenset(
    ["meeting", "legislation", "document"]
)


@dataclass(frozen=True)
class SummarizationConfig:
    body: str
    """The name of the summarization method for the body."""

    headline: str
    """The name of the summarization method for the headline."""

    def for_kind(self, kind: SummarizationKind) -> str:
        """
        Returns the name of the summarizer to use for the given kind of
        summarization.
        """
        if kind == "body":
            return self.body
        elif kind == "headline":
            return self.headline
        else:
            raise ValueError(f"Unknown summarization kind: {kind}")


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

    def for_class(self, klass: SummarizationClass) -> SummarizationConfig:
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
    meeting=SummarizationConfig(
        body="summarize_meeting_gpt35_concise",
        headline="summarize_meeting_gpt35_concise_headline",
    ),
    legislation=SummarizationConfig(
        body="summarize_legislation_gpt35_concise",
        headline="summarize_legislation_gpt35_concise_headline",
    ),
    document=SummarizationConfig(
        body="summarize_gpt35_concise",
        headline="summarize_gpt35_concise_headline",
    ),
    extractor="extract_pipeline_v1",
)


PIPELINE_CONFIGS: list[PipelineConfig] = [
    CONCISE_PIPELINE_CONFIG,
]


PIPELINE_CONFIGS_BY_NAME: dict[str, PipelineConfig] = {
    config.name: config for config in PIPELINE_CONFIGS
}


def filter_pipeline_configs(
    name: str,
    kinds: t.Iterable[SummarizationKind] = SUMMARIZATION_KINDS,
    klasses: t.Iterable[SummarizationClass] = SUMMARIZATION_CLASSES,
) -> t.Iterable[PipelineConfig]:
    """
    Returns all pipeline configurations that use the given summarizer
    for the specified kinds and classes of summarization.
    """
    kinds_set = frozenset(kinds)
    klasses_set = frozenset(klasses)
    for config in PIPELINE_CONFIGS:
        if any(
            config.for_class(klass).for_kind(kind) == name
            for klass in klasses_set
            for kind in kinds_set
        ):
            yield config


def get_pipeline_config(
    name: str,
    kinds: t.Iterable[SummarizationKind] = SUMMARIZATION_KINDS,
    klasses: t.Iterable[SummarizationClass] = SUMMARIZATION_CLASSES,
) -> PipelineConfig:
    """
    Return the single pipeline configuration that uses the given summarizer
    for the specified kinds and classes of summarization.

    If none is found, or if more than one is found, raise an exception.
    """
    configs = list(filter_pipeline_configs(name, kinds, klasses))
    if len(configs) == 0:
        raise ValueError(f"No pipeline config found for {name}")
    elif len(configs) > 1:
        raise ValueError(f"Multiple pipeline configs found for {name}")
    else:
        return configs[0]
