from __future__ import annotations

import datetime
import json
import typing as t
import urllib.parse

import requests
from django.db import models, transaction

from server.documents.models import Document, DocumentSummary
from server.documents.summarize import SummarizationSuccess
from server.lib.style import SummarizationStyle
from server.lib.summary_model import SummaryBaseModel
from server.lib.truncate import truncate_str

from .lib.web_schema import (
    LegislationCrawlData,
    LegislationRowCrawlData,
    Link,
    MeetingCrawlData,
    MeetingRowCrawlData,
)
from .summarize.legislation import LEGISLATION_SUMMARIZERS_BY_STYLE
from .summarize.meetings import MEETING_SUMMARIZERS_BY_STYLE


def _load_link(link: Link) -> tuple[bytes, str]:
    """Load a document from a Legistar URL."""
    response = requests.get(link.url)
    response.raise_for_status()
    return response.content, response.headers["Content-Type"]


class LegistarDocumentKind:
    """The kind of attached document."""

    AGENDA = "agenda"
    AGENDA_PACKET = "agenda_packet"
    MINUTES = "minutes"
    ATTACHMENT = "attachment"
    SUPPORTING_DOCUMENT = "supporting_document"
    FULL_TEXT = "full_text"


class MeetingManager(models.Manager):
    """Custom manager for the Meeting model."""

    def cancelled(self):
        """Return all meetings that have been canceled."""
        return self.filter(time=None)

    def active(self):
        """Return all meetings that have not been canceled."""
        return self.exclude(time=None)

    def future(self, relative_to: datetime.date | None = None, inclusive: bool = True):
        """Return all meetings that have not yet occurred."""
        when = relative_to or datetime.date.today()
        filter_params = {"date__gte": when} if inclusive else {"date__gt": when}
        return self.filter(**filter_params)

    def past(self, include_today: bool = False):
        """Return all meetings that have already occurred."""
        filter_params = (
            {"date__lte": datetime.date.today()}
            if include_today
            else {"date__lt": datetime.date.today()}
        )
        return self.filter(**filter_params)

    def update_or_create_from_crawl_data(
        self, crawl_data: MeetingCrawlData
    ) -> tuple[Meeting, bool]:
        """Update or create a meeting from crawl data."""
        meeting, created = self.update_or_create(
            legistar_id=crawl_data.id,
            legistar_guid=crawl_data.guid,
            defaults={
                "date": crawl_data.date,
                "time": crawl_data.time,
                "location": crawl_data.location,
                "crawl_data": json.loads(crawl_data.json()),
            },
        )
        assert isinstance(meeting, Meeting)
        # Load all the documents, if needed; update the meeting's
        # documents to match the crawl_data.
        documents = []
        agenda_document, _ = Document.objects.get_or_create_from_url(
            url=crawl_data.agenda.url,
            kind=LegistarDocumentKind.AGENDA,
            title=f"meeting-{crawl_data.id}-agenda",
        )
        documents.append(agenda_document)
        if crawl_data.agenda_packet:
            agenda_packet_document, _ = Document.objects.get_or_create_from_url(
                url=crawl_data.agenda_packet.url,
                kind=LegistarDocumentKind.AGENDA_PACKET,
                title=f"meeting-{crawl_data.id}-agenda_packet",
            )
            documents.append(agenda_packet_document)
        if crawl_data.minutes:
            minutes_document, _ = Document.objects.get_or_create_from_url(
                url=crawl_data.minutes.url,
                kind=LegistarDocumentKind.MINUTES,
                title=f"meeting-{crawl_data.id}-minutes",
            )
            documents.append(minutes_document)
        for attachment in crawl_data.attachments:
            attachment_document, _ = Document.objects.get_or_create_from_url(
                url=attachment.url,
                kind=LegistarDocumentKind.ATTACHMENT,
                title=f"meeting-{crawl_data.id}-attachment-{attachment.name}",
            )
            documents.append(attachment_document)
        meeting.documents.set(documents)
        return meeting, created


class Meeting(models.Model):
    """A single meeting as found on the Legistar website."""

    objects = MeetingManager()

    legistar_id = models.IntegerField(
        help_text="The ID of the meeting on the Legistar site."
    )
    legistar_guid = models.CharField(
        max_length=36, help_text="The GUID of the meeting on the Legistar site."
    )
    date = models.DateField(db_index=True, help_text="The date of the meeting.")
    time = models.TimeField(
        db_index=True, null=True, blank=True, help_text="The time of the meeting."
    )
    location = models.CharField(
        max_length=255, help_text="The location of the meeting."
    )
    raw_crawl_data = models.JSONField(default=dict, help_text="The raw crawl data.")

    documents = models.ManyToManyField(
        Document,
        related_name="meetings",
    )

    @property
    def is_canceled(self) -> bool:
        """Whether the meeting has been canceled."""
        return self.time is None

    @property
    def is_active(self) -> bool:
        """Whether the meeting has not been canceled."""
        return not self.is_canceled

    @property
    def agenda(self) -> Document:
        """Return the agenda document, if it exists."""
        return self.documents.get(kind=LegistarDocumentKind.AGENDA)

    @property
    def agenda_packet(self) -> Document | None:
        """Return the agenda packet document, if it exists."""
        return self.documents.filter(kind=LegistarDocumentKind.AGENDA_PACKET).first()

    @property
    def minutes(self) -> Document | None:
        """Return the minutes document, if it exists."""
        return self.documents.filter(kind=LegistarDocumentKind.MINUTES).first()

    @property
    def attachments(self) -> t.Iterable[Document]:
        """Return the attachments documents, if they exist."""
        return self.documents.filter(kind=LegistarDocumentKind.ATTACHMENT)

    @property
    def crawl_data(self) -> MeetingCrawlData:
        """Return the underlying crawled data for the meeting."""
        return MeetingCrawlData.parse_obj(self.raw_crawl_data)

    @crawl_data.setter
    def crawl_data(self, value: MeetingCrawlData):
        """Set the crawl data data for the meeting."""
        self.raw_crawl_data = json.loads(value.json())

    @property
    def crawl_data_rows(self) -> list[MeetingRowCrawlData]:
        """Return the rows of the meeting."""
        return self.crawl_data.rows

    @property
    def url(self) -> str:
        """Return the URL for the meeting."""
        return self.crawl_data.url

    @property
    def record_nos(self) -> t.Iterable[str]:
        """Return the record numbers for the meeting."""
        return {row.legislation.name for row in self.crawl_data_rows}

    @property
    def legislations(self) -> t.Iterable[Legislation]:
        """Return the legislations associated with the meeting."""
        # CONSIDER: we don't explicitly link Legislation to Meeting in the database
        # with a foreign key. This is flexible; when I first started, I wasn't sure
        # whether the linkage was exclusive or not. Now I know better, and we should
        # revisit this. -Dave
        return Legislation.objects.filter(record_no__in=self.record_nos)

    def legislation_summaries(
        self, style: SummarizationStyle, require: bool = True
    ) -> t.Iterable[LegislationSummary]:
        """
        Return the legislation summaries for the meeting for a given style.

        If `require` is True (the default), we raise an exception if we can't find
        a summary for each existing legislation. If `require` is False, we return
        whatever we can find.
        """
        legislation_objs = list(self.legislations)
        legislation_summary_objs = LegislationSummary.objects.filter(
            legislation__in=legislation_objs,
            style=style,
        )
        if require and legislation_summary_objs.count() != len(legislation_objs):
            raise ValueError(f"Missing legislation summaries for {self} ({style}).")
        return legislation_summary_objs

    def document_summaries(
        self,
        style: SummarizationStyle,
        excludes: frozenset[str]
        | None = frozenset(
            [LegistarDocumentKind.AGENDA, LegistarDocumentKind.AGENDA_PACKET]
        ),
        require: bool = True,
    ) -> t.Iterable[DocumentSummary]:
        """
        Return the document summaries for the meeting that match the specific
        pipeline configuration.

        If `require` is True (the default), we raise an exception if we can't find
        a summary for each existing document. If `require` is False, we return
        whatever we can find.
        """
        document_objs = (
            list(self.documents.exclude(kind__in=excludes))
            if excludes
            else list(self.documents.all())
        )
        document_summary_objs = DocumentSummary.objects.filter(
            document__in=document_objs,
            style=style,
        )
        if require and document_summary_objs.count() != len(document_objs):
            raise ValueError(f"Missing document summaries for {self} ({style}).")
        return document_summary_objs

    def __str__(self):
        time_or_cancel = self.time or "canceled"
        return (
            f"Meeting: {self.crawl_data.department.name} {self.date} @ {time_or_cancel}"
        )

    class Meta:
        verbose_name = "Meeting"
        verbose_name_plural = "Meetings"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["legistar_id", "legistar_guid"],
                name="unique_meeting_legistar_id_guid",
            ),
        ]


class MeetingSummaryManager(models.Manager):
    """A manager for meeting summaries."""

    def get_or_create_from_meeting(
        self,
        meeting: Meeting,
        style: SummarizationStyle,
    ) -> tuple[MeetingSummary, bool]:
        """
        Get or create a meeting summary from the meeting.

        Summaries for all affiliated documents *and* legislations must already exist,
        or we raise an exception.
        """
        with transaction.atomic():
            # If we already have a summary, return it.
            summary = self.filter(meeting=meeting, style=style).first()
            if summary is not None:
                return summary, False

            # Get legislation body summary objects for each legislation.
            # Raise an exception if we can't find them.
            legislation_summaries = meeting.legislation_summaries(style)
            legislation_summary_texts = [ls.body for ls in legislation_summaries]

            # Likewise for all documents, skipping the ones we normally ignore.
            document_summaries = meeting.document_summaries(style)
            document_summary_texts = [ds.body for ds in document_summaries]

            # Invoke the summarizer.
            summarizer = MEETING_SUMMARIZERS_BY_STYLE[style]
            result = summarizer(
                meeting.crawl_data.department.name,
                legislation_summary_texts=legislation_summary_texts,
                document_summary_texts=document_summary_texts,
            )
            # XXX TODO DAVE
            assert isinstance(result, SummarizationSuccess)
            summary = self.create(
                meeting=meeting,
                style=style,
                body=result.body,
                headline=result.headline,
                original_text=result.original_text,
                chunks=result.chunks,
                chunk_summaries=result.chunk_summaries,
            )
            return summary, True


class MeetingSummary(SummaryBaseModel):
    """A summary of a meeting."""

    objects = MeetingSummaryManager()

    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="summaries",
        help_text="The summarized meeting.",
    )

    class Meta:
        verbose_name = "Meeting summary"
        verbose_name_plural = "Meeting summaries"

        constraints = [
            models.UniqueConstraint(
                fields=["meeting", "style"],
                name="unique_meeting_summmary_for_config",
            ),
        ]


class LegislationManager(models.Manager):
    """A custom manager for Legislation objects."""

    def update_or_create_from_crawl_data(
        self, crawl_data: LegislationCrawlData
    ) -> tuple[Legislation, bool]:
        """Update or create a legislation from crawl data."""
        legislation, created = self.update_or_create(
            legistar_id=crawl_data.id,
            legistar_guid=crawl_data.guid,
            defaults={
                "record_no": crawl_data.record_no,
                "type": crawl_data.type,
                "status": crawl_data.status,
                "title": crawl_data.title,
                "crawl_data": json.loads(crawl_data.json()),
            },
        )
        assert isinstance(legislation, Legislation)
        # Load all the documents, if needed; update the legislation's
        # documents to match the crawl data.
        documents = []
        for attachment in crawl_data.attachments:
            attachment_document, _ = Document.objects.get_or_create_from_url(
                url=attachment.url,
                kind=LegistarDocumentKind.ATTACHMENT,
                title=f"legislation-{crawl_data.id}-attachment-{attachment.name}",
            )
            documents.append(attachment_document)
        for supporting_document in crawl_data.supporting_documents:
            supporting_document_document, _ = Document.objects.get_or_create_from_url(
                url=supporting_document.url,
                kind=LegistarDocumentKind.SUPPORTING_DOCUMENT,
                title=f"legislation-{crawl_data.id}-supporting-{supporting_document.name}",
            )
            documents.append(supporting_document_document)
        if crawl_data.full_text is not None:
            full_text_document, _ = Document.objects.get_or_create_from_url(
                url=urllib.parse.urljoin(crawl_data.url, "#FullTextDiv"),
                kind=LegistarDocumentKind.FULL_TEXT,
                title=f"legislation-{crawl_data.id}-full",
                raw_content=crawl_data.full_text.encode("utf-8"),
                _get_mime_type=lambda url: "text/plain",
            )
            documents.append(full_text_document)
        legislation.documents.set(documents)

        return legislation, created


class Legislation(models.Model):
    """A single piece of legislation as found on the Legistar website."""

    objects = LegislationManager()

    legistar_id = models.IntegerField(
        help_text="The ID of the legislation on the Legistar site."
    )
    legistar_guid = models.CharField(
        max_length=36, help_text="The GUID of the legislation on the Legistar site."
    )

    record_no = models.CharField(
        db_index=True, max_length=255, help_text="The record number of the legislation."
    )
    type = models.CharField(max_length=255, help_text="The type of legislation.")
    status = models.CharField(
        max_length=255, blank=True, help_text="The status of the legislation."
    )
    title = models.TextField(help_text="The title of the legislation.")
    raw_crawl_data = models.JSONField(default=dict, help_text="The raw crawl data.")

    documents = models.ManyToManyField(
        Document,
        related_name="legislations",
        help_text="The documents associated with the legislation.",
    )

    @property
    def crawl_data(self) -> LegislationCrawlData:
        """Return the crawl data for the legislation."""
        return LegislationCrawlData.parse_obj(self.raw_crawl_data)

    @crawl_data.setter
    def crawl_data(self, value: LegislationCrawlData):
        """Set the crawl data for the legislation."""
        self.raw_crawl_data = json.loads(value.json())

    @property
    def crawl_data_rows(self) -> list[LegislationRowCrawlData]:
        """Return the rows of the legislation."""
        return self.crawl_data.rows

    @property
    def attachments(self) -> t.Iterable[Document]:
        """Return the attachments for the legislation."""
        return self.documents.filter(kind=LegistarDocumentKind.ATTACHMENT)

    @property
    def supporting_documents(self) -> t.Iterable[Document]:
        """Return the supporting documents for the legislation."""
        return self.documents.filter(kind=LegistarDocumentKind.SUPPORTING_DOCUMENT)

    @property
    def url(self) -> str:
        """Return the URL for the legislation."""
        return self.crawl_data.url

    @property
    def truncated_title(self) -> str:
        """Return the truncated title for the legislation."""
        return truncate_str(self.title, 48)

    @property
    def kind(self) -> str:
        """Return the kind of legislation."""
        return self.type.split("(")[0].strip()

    def document_summaries(
        self,
        style: SummarizationStyle,
        excludes: frozenset[str] | None = None,
        require: bool = True,
    ) -> t.Iterable[DocumentSummary]:
        """Return the document summaries for the legislation."""
        document_objs = (
            list(self.documents.exclude(kind__in=excludes))
            if excludes
            else list(self.documents.all())
        )
        document_summary_objs = DocumentSummary.objects.filter(
            document__in=document_objs,
            style=style,
        )
        if require and document_summary_objs.count() != len(document_objs):
            raise ValueError(f"Missing document summaries for {self} ({style})")
        return document_summary_objs

    def __str__(self):
        return f"Legislation: {self.record_no} - {self.truncated_title}"

    class Meta:
        verbose_name = "Legislation"
        verbose_name_plural = "Legislation"
        constraints = [
            models.UniqueConstraint(
                fields=["legistar_id", "legistar_guid"],
                name="unique_legislation_legistar_id_guid",
            ),
        ]


class LegislationSummaryManager(models.Manager):
    def get_or_create_from_legislation(
        self,
        legislation: Legislation,
        style: SummarizationStyle,
    ) -> tuple[LegislationSummary, bool]:
        """
        Get or create a legislation summary from the legislation.

        Summaries for all affiliated documents must already exist, or we raise
        an exception.
        """
        with transaction.atomic():
            # If we already have a summary, return it
            summary = self.filter(
                legislation=legislation,
                style=style,
            ).first()
            if summary is not None:
                return summary, False

            # Get document body summary objects. Raise an exception if we can't
            # find them.
            document_summaries = legislation.document_summaries(style)
            document_summary_texts = [ds.body for ds in document_summaries]

            # Invoke the summarizer.
            summarizer = LEGISLATION_SUMMARIZERS_BY_STYLE[style]
            result = summarizer(
                legislation.title, document_summary_texts=document_summary_texts
            )
            # XXX TODO DAVE
            assert isinstance(result, SummarizationSuccess)
            summary = self.create(
                legislation=legislation,
                style=style,
                body=result.body,
                headline=result.headline,
                original_text=result.original_text,
                chunks=result.chunks,
                chunk_summaries=result.chunk_summaries,
            )
            return summary, True


class LegislationSummary(SummaryBaseModel):
    """A summary of legislation as found on the Legistar website."""

    objects = LegislationSummaryManager()

    legislation = models.ForeignKey(
        Legislation,
        on_delete=models.CASCADE,
        related_name="summaries",
        help_text="The legislation that the summary is for.",
    )

    class Meta:
        verbose_name = "Legislation summary"
        verbose_name_plural = "Legislation summaries"

        constraints = [
            models.UniqueConstraint(
                fields=["legislation", "style"],
                name="unique_legislation_summary_for_config",
            ),
        ]
