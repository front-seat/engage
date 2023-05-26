import typing as t

SummarizationStyle: t.TypeAlias = t.Literal["concise"]
"""
Define system-wide 'styles' for summarization.

During the development of this project, we had many different styles;
in the end, we settled on a single style, but we keep this class
around in case we want to add more styles in the future.
"""


SUMMARIZATION_STYLES: list[SummarizationStyle] = ["concise"]
