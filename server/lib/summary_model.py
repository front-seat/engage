from django.db import models

from .pipeline_config import PIPELINE_CONFIGS_BY_NAME, PipelineConfig


class SummaryBaseModel(models.Model):
    """
    An abstract database model that defines the common fields and methods
    expected to be found on *all* summaries in the database, whether they are
    summaries of individual `Document`s, `Legislation`s, or even full council
    `Meeting`s.

    For details on how Django handles abstract base models, see:
    https://docs.djangoproject.com/en/4.2/topics/db/models/#abstract-base-classes
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # We summarize in two ways: a long-form `body` and a short-form `headline`.
    body = models.TextField(help_text="A detailed summary of a text.")
    headline = models.TextField(help_text="A brief summary of a text.")

    # For debugging purposes, we store the original text that was summarized.
    #
    # This is likely to *always* duplicate other content in our database
    # (for instance, if it's a `Document` summary, this will be the same as
    # `Document.extracted_text`), but it's useful to have it here for debugging.
    original_text = models.TextField(help_text="The original summarized text.")

    # When summarizing a large block of text, we often need to split it into
    # chunks and summarize each chunk individually. This allows us to get around
    # the LLM's limited context window size (4k tokens for GPT-3.5-turbo;
    # 2k tokens for Vicuna13B; etc.). To help us debug and just make sense of
    # our final summaries, we store the chunks and per-chunk summaries here.
    chunks = models.JSONField(
        default=list,
        help_text="Text chunks sent to the LLM for summarization.",
    )
    chunk_summaries = models.JSONField(
        default=list,
        help_text="LLM outputs for each text chunk.",
    )

    config_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="The name of the configuration used to generate this summary.",
    )

    @property
    def config(self) -> PipelineConfig:
        """
        Return the configuration that led to this summary. With the configuration,
        we can determine the summarizer that was used, the LLM's parameters,
        and the exact prompts sent to the LLM to generate the summary.
        """
        return PIPELINE_CONFIGS_BY_NAME[self.config_name]

    @config.setter
    def config(self, config: PipelineConfig):
        """Set the configuration that led to this summary."""
        self.config_name = config.name

    class Meta:
        abstract = True
        ordering = ["-created_at"]
