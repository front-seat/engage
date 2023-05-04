# class LegislationSummarizationPipeline
import sys
import typing as t

from django.conf import settings

from server.documents.extract import ExtractorCallable, extract_pipeline_v1
from server.documents.models import Document, DocumentSummary, DocumentText
from server.documents.summarize import (
    CONCISE_SUMMARY_PROMPT,
    EDUCATED_LAYPERSON_PROMPT,
    HIGH_SCHOOL_PROMPT,
    SummarizerCallable,
    summarize_gpt35_concise,
    summarize_gpt35_educated_layperson,
    summarize_gpt35_entertaining_blog_post,
    summarize_gpt35_high_school,
    summarize_openai_langchain,
)
from server.lib.truncate import truncate_str

# TODO: circular nonsense here, since .models imports this module.
from .models import Legislation, LegislationSummary, LegistarDocumentKind, Meeting

# CONSIDER: this is obviously not the final boss form. What do we really
# want to do here? How can we easily allow outside parties to create new
# prompt combinations, particularly from the command line?


# ---------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------


def _extract_and_summarize_document(
    document: Document,
    summarizer: SummarizerCallable,
    extractor: ExtractorCallable = extract_pipeline_v1,
) -> DocumentSummary:
    """
    Extract the text from a document, then summarize it using the given
    summarizer.
    """
    document_text, _ = DocumentText.objects.get_or_create_from_document(
        document, extractor=extractor
    )
    document_summary, _ = DocumentSummary.objects.get_or_create_from_document_text(
        document_text, summarizer=summarizer
    )
    return document_summary


# ---------------------------------------------------------------------
# Legislation prompts
# ---------------------------------------------------------------------

LEGISLATION_CONCISE_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a concise summary of the following text, which is titled "<<title>>". Include the most important details:

"{text}"

CONCISE_CITY_COUNCIL_LEGISLATIVE_ACTION_SUMMARY:"""  # noqa: E501


LEGISLATION_EDUCATED_LAYPERSON_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a charming, concise, and engaging summary of the legislative effort, which is titled "<<title>>". Target your summary at a highly educated layperson. Try to highlight the most impactful agenda items; it's okay to drop less important ones (like, for example, appointments to minor commissions) if there isn't enough space to include them all.

"{text}"

ENGAGING_CITY_COUNCIL_LEGISLATIVE_ACTION_SUMMARY:"""  # noqa: E501


LEGISLATION_HIGH_SCHOOL_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Pretend you're a high school student writing a summary of the legislative effort, which is called "<<title>>". Write a summary that's clear and easy to understand:

"{text}"

HIGH_SCHOOL_CITY_COUNCIL_LEGISLATIVE_ACTION_SUMMARY:"""  # noqa: E501


LEGISLATION_ENTERTAINING_BLOG_POST_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write an entertaining summary of the legislative effort, which is titled "<<title>>". Make it perfect for a blog post that we hope goes viral and gets lots of clicks.

"{text}"

CLICKBAIT_BLOG_POST_CITY_COUNCIL_LEGISLATIVE_ACTION_SUMMARY:"""  # noqa: E501


LEGISLATION_ELEMENTARY_SCHOOL_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. The overall action is titled "<<title>>". Summarize, but make it easy for an elementary school kid to understand:

"{text}"

ELEMENTARY_SCHOOL_CITY_COUNCIL_LEGISLATIVE_ACTION_SUMMARY:"""  # noqa: E501


LEGISLATION_CONCISE_HEADLINE_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a concise and extremely compact headline (one sentence or less) for the action, which is titled "<<title>>". Capture only the most salient detail or two:

"{text}"

CONCISE_COMPACT_HEADLINE:"""  # noqa: E501


LEGISLATION_NEWSPAPER_HEADLINE_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write an engaging one-sentence newspaper headline for the legislative effort, which is titled "<<title>>". Make it perfect for a newspaper read by highly educated laypeople.

"{text}"

NEWSPAPER_HEADLINE:"""  # noqa: E501


LEGISLATION_HIGH_SCHOOL_ESSAY_TITLE_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a short title for an essay written by a high-school student about the legislative effort, which is called "<<title>>".

"{text}"

HIGH_SCHOOL_ESSAY_TITLE:"""  # noqa: E501


LEGISLATION_CATCHY_CONTROVERSIAL_HEADLINE_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a catchy one-sentence headline for the legislative effort, which is titled "<<title>>". Try and write something that will go viral and get lots of clicks:

"{text}"

CLICKBAIT_HEADLINE:"""  # noqa: E501


LEGISLATION_ELEMENTARY_SCHOOL_HEADLINE_PROMPT = """The following is a set of descriptions of documents related to a single legislative action taken a city council body. Write a headline that's easy for an elementary school kid to understand:

"{text}"

ELEMENTARY_SCHOOL_HEADLINE:"""  # noqa: E501


# ---------------------------------------------------------------------
# Legislation internal utilties
# ---------------------------------------------------------------------


def _summarize_legislation(
    legislation: Legislation,
    document_summarizer: SummarizerCallable,
    join_summarizer: SummarizerCallable,
    verbose_name: str,
) -> str:
    """
    Summarize a piece of legislation by summarizing all of its documents
    using the `document_summarizer`, then combining the resulting summaries
    using the given `combine_prompt`.
    """
    if settings.VERBOSE:
        print(
            f">>>> SUMMARIZE: legislation docs {verbose_name}({legislation})",
            file=sys.stderr,
        )

    # Summarize every document associated with this legislation.
    document_summaries: list[DocumentSummary] = [
        _extract_and_summarize_document(document, document_summarizer)
        for document in legislation.documents.all()
    ]

    if settings.VERBOSE:
        print(
            f">>>> SUMMARIZE: legislation join {verbose_name}({legislation})",
            file=sys.stderr,
        )

    # Join the summaries together.
    substitutions = {
        "<<title>>": truncate_str(legislation.title, 100).replace('"', "'"),
    }
    texts = "\n\n".join([d_summ.summary for d_summ in document_summaries])
    return join_summarizer(texts, substitutions=substitutions)


# ---------------------------------------------------------------------
# Legislation joiners
# ---------------------------------------------------------------------


def _join_legislation_summaries_gpt35_concise(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_CONCISE_PROMPT,
        substitutions=substitutions,
    )


def _join_legislation_summaries_gpt35_educated_layperson(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=EDUCATED_LAYPERSON_PROMPT,
        combine_prompt=LEGISLATION_EDUCATED_LAYPERSON_PROMPT,
        substitutions=substitutions,
    )


def _join_legislation_summaries_gpt35_high_school(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=HIGH_SCHOOL_PROMPT,
        combine_prompt=LEGISLATION_HIGH_SCHOOL_PROMPT,
        substitutions=substitutions,
    )


def _join_legislation_summaries_gpt35_entertaining_blog_post(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_ENTERTAINING_BLOG_POST_PROMPT,
        substitutions=substitutions,
    )


def _join_legislation_summaries_gpt35_elementary_school(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_ELEMENTARY_SCHOOL_PROMPT,
        substitutions=substitutions,
    )


def _join_legislation_summaries_gpt35_concise_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_CONCISE_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


def _join_legislation_summaries_gpt35_newspaper_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_NEWSPAPER_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


def _join_legislation_summaries_gpt35_high_school_essay_title(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_HIGH_SCHOOL_ESSAY_TITLE_PROMPT,
        substitutions=substitutions,
    )


def _join_legislation_summaries_gpt35_catchy_controversial_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_CATCHY_CONTROVERSIAL_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


def _join_legislation_summaries_gpt35_elementary_school_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=LEGISLATION_ELEMENTARY_SCHOOL_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


# ---------------------------------------------------------------------
# Legislation summarizers
# ---------------------------------------------------------------------


def summarize_legislation_gpt35_concise(legislation: Legislation) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_concise,
        join_summarizer=_join_legislation_summaries_gpt35_concise,
        verbose_name="gpt35_concise",
    )


def summarize_legislation_gpt35_educated_layperson(legislation: Legislation) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_educated_layperson,
        join_summarizer=_join_legislation_summaries_gpt35_educated_layperson,
        verbose_name="gpt35_educated_layperson",
    )


def summarize_legislation_gpt35_high_school(legislation: Legislation) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_high_school,
        join_summarizer=_join_legislation_summaries_gpt35_high_school,
        verbose_name="gpt35_high_school",
    )


def summarize_legislation_gpt35_entertaining_blog_post(legislation: Legislation) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_concise,
        join_summarizer=_join_legislation_summaries_gpt35_entertaining_blog_post,
        verbose_name="gpt35_entertaining_blog_post",
    )


def summarize_legislation_gpt35_elementary_school(legislation: Legislation) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_concise,
        join_summarizer=_join_legislation_summaries_gpt35_elementary_school,
        verbose_name="gpt35_elementary_school",
    )


def summarize_legislation_gpt35_concise_headline(legislation: Legislation) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_concise,
        join_summarizer=_join_legislation_summaries_gpt35_concise_headline,
        verbose_name="gpt35_concise_headline",
    )


def summarize_legislation_gpt35_high_school_essay_title(
    legislation: Legislation,
) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_concise,
        join_summarizer=_join_legislation_summaries_gpt35_high_school_essay_title,
        verbose_name="gpt35_high_school_essay_title",
    )


def summarize_legislation_gpt35_newspaper_headline(legislation: Legislation) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_concise,
        join_summarizer=_join_legislation_summaries_gpt35_newspaper_headline,
        verbose_name="gpt35_newspaper_headline",
    )


def summarize_legislation_gpt35_catchy_controversial_headline(
    legislation: Legislation,
) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_concise,
        join_summarizer=_join_legislation_summaries_gpt35_catchy_controversial_headline,
        verbose_name="gpt35_catchy_controversial_headline",
    )


def summarize_legislation_gpt35_elementary_school_headline(
    legislation: Legislation,
) -> str:
    return _summarize_legislation(
        legislation,
        document_summarizer=summarize_gpt35_concise,
        join_summarizer=_join_legislation_summaries_gpt35_elementary_school_headline,
        verbose_name="gpt35_elementary_school_headline",
    )


# ---------------------------------------------------------------------
# Legislation external utilties
# ---------------------------------------------------------------------


@t.runtime_checkable
class LegislationSummarizerCallable(t.Protocol):
    __name__: str

    def __call__(self, legislation: Legislation) -> str:
        ...


LEGISLATION_SUMMARIZERS: list[LegislationSummarizerCallable] = [
    summarize_legislation_gpt35_concise,
    # summarize_legislation_gpt35_educated_layperson,
    # summarize_legislation_gpt35_high_school,
    # summarize_legislation_gpt35_entertaining_blog_post,
    # summarize_legislation_gpt35_elementary_school,
    summarize_legislation_gpt35_concise_headline,
    # summarize_legislation_gpt35_newspaper_headline,
    # summarize_legislation_gpt35_high_school_essay_title,
    # summarize_legislation_gpt35_catchy_controversial_headline,
    # summarize_legislation_gpt35_elementary_school_headline,
]

LEGISLATION_SUMMARIZERS_BY_NAME: dict[str, LegislationSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in LEGISLATION_SUMMARIZERS
}


# ---------------------------------------------------------------------
# Meeting prompts
# ---------------------------------------------------------------------


MEETING_CONCISE_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write a concise summary of the following text. Include the most important details:

"{text}"

CONCISE_AGENDA_SUMMARY:"""  # noqa: E501


MEETING_EDUCATED_LAYPERSON_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write a charming, concise, and engaging summary of the agenda. Target your summary at a highly educated layperson. Try to highlight the most impactful agenda items; it's okay to drop less important ones (like, for example, appointments to minor commissions) if there isn't enough space to include them all. Please try not to repeat yourself.

"{text}"

ENGAGING_AGENDA_SUMMARY:"""  # noqa: E501


MEETING_HIGH_SCHOOL_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Pretend you're a high school student writing a summary for a school assignment. Write a summary that's clear and easy to understand:

"{text}"

HIGH_SCHOOL_AGENDA_SUMMARY:"""  # noqa: E501


MEETING_ENTERTAINING_BLOG_POST_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write an entertaining summary of the agenda. Make it perfect for a blog post that we hope goes viral and gets lots of clicks.

"{text}"

CLICKBAIT_BLOG_POST_AGENDA_SUMMARY:"""  # noqa: E501


MEETING_ELEMENTARY_SCHOOL_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Summarize, but make it easy for an elementary school kid to understand:

"{text}"

ELEMENTARY_SCHOOL_AGENDA_SUMMARY:"""  # noqa: E501


MEETING_CONCISE_HEADLINE_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write a concise and extremely compact headline (one sentence or less) for the following text. Capture the most salient detail or two:

"{text}"

CONCISE_COMPACT_HEADLINE_FOR_AGENDA:"""  # noqa: E501


MEETING_NEWSPAPER_HEADLINE_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write an engaging one-sentence newspaper headline for the agenda. Make it perfect for a newspaper read by highly educated laypeople.

"{text}"

NEWSPAPER_HEADLINE_FOR_AGENDA:"""  # noqa: E501


MEETING_HIGH_SCHOOL_ESSAY_TITLE_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write a short title for an essay written by a high school student about the agenda.

"{text}"

HIGH_SCHOOL_ESSAY_TITLE_FOR_AGENDA:"""  # noqa: E501


MEETING_CATCHY_CONTROVERSIAL_HEADLINE_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write a catchy one-sentence headline for the agenda. Try and write something that will go viral and get lots of clicks.

"{text}"

CLICKBAIT_HEADLINE_FOR_AGENDA:"""  # noqa: E501


MEETING_ELEMENTARY_SCHOOL_HEADLINE_PROMPT = """The following is a set of descriptions of items on the agenda for an upcoming <<department>> meeting. Write a headline that's easy for an elementary school kid to understand:

"{text}"

ELEMENTARY_SCHOOL_HEADLINE_FOR_AGENDA:"""  # noqa: E501


# ---------------------------------------------------------------------
# Meeting internal utilities
# ---------------------------------------------------------------------


def _summarize_meeting(
    meeting: Meeting,
    document_summarizer: SummarizerCallable,
    legislation_summarizer: LegislationSummarizerCallable,
    join_summarizer: SummarizerCallable,
    verbose_name: str,
) -> str:
    if settings.VERBOSE:
        print(
            f">>>> SUMMARIZE: meeting docs {verbose_name}({meeting})",
            file=sys.stderr,
        )

    # Summarize every document associated with this meeting, EXCEPT
    # those of type LegistarDocumentKind.AGENDA and LegistarDocumentKind.AGENDA_PACKET.
    # "Agenda" duplicates meeting.schema.rows but is not as nicely formatted.
    # "Agenda Packet" is a PDF of the agenda + attachments, which we are going
    # to summarize separately.
    document_summaries: list[DocumentSummary] = []
    qs = meeting.documents.exclude(
        kind__in=[LegistarDocumentKind.AGENDA, LegistarDocumentKind.AGENDA_PACKET]
    )
    document_summaries = [
        _extract_and_summarize_document(document, document_summarizer)
        for document in qs
    ]

    # Make sure we've summarized each piece of associated legislation.
    # XXX TODO: compare _extract_and_summarize_document(...), which creates
    # stuff in the database, with _summarize_legislation(...), which doesn't,
    # and which is why we call get_or_create(...) directly. This is all very
    # silly and non-parallel and clearly we need to do better. -Dave
    legislation_summaries = []
    for legislation in meeting.legislations:
        l_summ, _ = LegislationSummary.objects.get_or_create_from_legislation(
            legislation, legislation_summarizer
        )
        legislation_summaries.append(l_summ)

    # Now summarize that in totality + add the extra meeting document_summaries.
    document_summary_texts = [ds.summary for ds in document_summaries]
    summary_texts = [ls.summary for ls in legislation_summaries]
    all_texts = summary_texts + document_summary_texts

    # Run a summarizer over the text of all the document summaries.
    if settings.VERBOSE:
        print(
            f">>>> SUMMARIZE: meeting join {verbose_name}({meeting})",
            file=sys.stderr,
        )
    joined_summaries = "\n\n".join(all_texts)
    substitutions = {"<<department>>": meeting.schema.department.name}
    return join_summarizer(joined_summaries, substitutions)


# ---------------------------------------------------------------------
# Meeting joiners
# ---------------------------------------------------------------------


def _join_meeting_summaries_gpt35_concise(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_educated_layperson(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=EDUCATED_LAYPERSON_PROMPT,
        combine_prompt=MEETING_EDUCATED_LAYPERSON_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_high_school(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=HIGH_SCHOOL_PROMPT,
        combine_prompt=MEETING_HIGH_SCHOOL_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_entertaining_blog_post(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_ENTERTAINING_BLOG_POST_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_elementary_school(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_ELEMENTARY_SCHOOL_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_concise_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CONCISE_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_newspaper_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_NEWSPAPER_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_high_school_essay_title(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_HIGH_SCHOOL_ESSAY_TITLE_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_catchy_controversial_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_CATCHY_CONTROVERSIAL_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


def _join_meeting_summaries_gpt35_elementary_school_headline(
    text: str, substitutions: dict[str, str] | None = None
) -> str:
    return summarize_openai_langchain(
        text,
        map_prompt=CONCISE_SUMMARY_PROMPT,
        combine_prompt=MEETING_ELEMENTARY_SCHOOL_HEADLINE_PROMPT,
        substitutions=substitutions,
    )


# ---------------------------------------------------------------------
# Meeting summarizers
# ---------------------------------------------------------------------


def summarize_meeting_gpt35_concise(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_concise,
        legislation_summarizer=summarize_legislation_gpt35_concise,
        join_summarizer=_join_meeting_summaries_gpt35_concise,
        verbose_name="gpt35_concise",
    )


def summarize_meeting_gpt35_educated_layperson(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_educated_layperson,
        legislation_summarizer=summarize_legislation_gpt35_educated_layperson,
        join_summarizer=_join_meeting_summaries_gpt35_educated_layperson,
        verbose_name="gpt35_educated_layperson",
    )


def summarize_meeting_gpt35_high_school(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_high_school,
        legislation_summarizer=summarize_legislation_gpt35_high_school,
        join_summarizer=_join_meeting_summaries_gpt35_high_school,
        verbose_name="gpt35_high_school",
    )


def summarize_meeting_gpt35_entertaining_blog_post(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_entertaining_blog_post,
        legislation_summarizer=summarize_legislation_gpt35_educated_layperson,
        join_summarizer=_join_meeting_summaries_gpt35_entertaining_blog_post,
        verbose_name="gpt35_entertaining_blog_post",
    )


def summarize_meeting_gpt35_elementary_school(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_concise,
        legislation_summarizer=summarize_legislation_gpt35_concise,
        join_summarizer=_join_meeting_summaries_gpt35_elementary_school,
        verbose_name="gpt35_elementary_school",
    )


def summarize_meeting_gpt35_concise_headline(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_concise,
        legislation_summarizer=summarize_legislation_gpt35_concise,
        join_summarizer=_join_meeting_summaries_gpt35_concise_headline,
        verbose_name="gpt35_concise_headline",
    )


def summarize_meeting_gpt35_newspaper_headline(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_educated_layperson,
        legislation_summarizer=summarize_legislation_gpt35_educated_layperson,
        join_summarizer=_join_meeting_summaries_gpt35_newspaper_headline,
        verbose_name="gpt35_newspaper_headline",
    )


def summarize_meeting_gpt35_high_school_essay_title(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_educated_layperson,
        legislation_summarizer=summarize_legislation_gpt35_educated_layperson,
        join_summarizer=_join_meeting_summaries_gpt35_high_school_essay_title,
        verbose_name="gpt35_high_school_essay_title",
    )


def summarize_meeting_gpt35_catchy_controversial_headline(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_educated_layperson,
        legislation_summarizer=summarize_legislation_gpt35_educated_layperson,
        join_summarizer=_join_meeting_summaries_gpt35_catchy_controversial_headline,
        verbose_name="gpt35_catchy_controversial_headline",
    )


def summarize_meeting_gpt35_elementary_school_headline(meeting: Meeting) -> str:
    return _summarize_meeting(
        meeting,
        document_summarizer=summarize_gpt35_concise,
        legislation_summarizer=summarize_legislation_gpt35_concise,
        join_summarizer=_join_meeting_summaries_gpt35_elementary_school_headline,
        verbose_name="gpt35_elementary_school_headline",
    )


# ---------------------------------------------------------------------
# Meeting external utilties
# ---------------------------------------------------------------------


@t.runtime_checkable
class MeetingSummarizerCallable(t.Protocol):
    __name__: str

    def __call__(self, meeting: Meeting) -> str:
        ...


MEETING_SUMMARIZERS: list[MeetingSummarizerCallable] = [
    summarize_meeting_gpt35_concise,
    # summarize_meeting_gpt35_educated_layperson,
    # summarize_meeting_gpt35_high_school,
    # summarize_meeting_gpt35_entertaining_blog_post,
    # summarize_meeting_gpt35_elementary_school,
    summarize_meeting_gpt35_concise_headline,
    # summarize_meeting_gpt35_newspaper_headline,
    # summarize_meeting_gpt35_high_school_essay_title,
    # summarize_meeting_gpt35_catchy_controversial_headline,
    # summarize_meeting_gpt35_elementary_school_headline,
]

MEETING_SUMMARIZERS_BY_NAME: dict[str, MeetingSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in MEETING_SUMMARIZERS
}
MEETING_SUMMARIZERS_BY_NAME: dict[str, MeetingSummarizerCallable] = {
    summarizer.__name__: summarizer for summarizer in MEETING_SUMMARIZERS
}
