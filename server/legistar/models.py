from __future__ import annotations

import datetime
import json
import typing as t
import urllib.parse

import requests
from django.db import models, transaction

from server.documents.models import Document, DocumentSummary
from server.lib.pipeline_config import PipelineConfig, SummarizationKind
from server.lib.truncate import truncate_str

from .lib.web_schema import (
    ActionRowSchema,
    ActionSchema,
    LegislationRowSchema,
    LegislationSchema,
    Link,
    MeetingRowSchema,
    MeetingSchema,
)
from .summarize.legislation import LEGISLATION_SUMMARIZERS_BY_NAME
from .summarize.meetings import MEETING_SUMMARIZERS_BY_NAME


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

    def update_or_create_from_schema(
        self, schema: MeetingSchema
    ) -> tuple[Meeting, bool]:
        """Update or create a meeting from a schema."""
        meeting, created = self.update_or_create(
            legistar_id=schema.id,
            legistar_guid=schema.guid,
            defaults={
                "date": schema.date,
                "time": schema.time,
                "location": schema.location,
                "schema_data": json.loads(schema.json()),
            },
        )
        assert isinstance(meeting, Meeting)
        # Load all the documents, if needed; update the meeting's
        # documents to match the schema.
        documents = []
        agenda_document, _ = Document.objects.get_or_create_from_url(
            url=schema.agenda.url,
            kind=LegistarDocumentKind.AGENDA,
            title=f"meeting-{schema.id}-agenda",
        )
        documents.append(agenda_document)
        if schema.agenda_packet:
            agenda_packet_document, _ = Document.objects.get_or_create_from_url(
                url=schema.agenda_packet.url,
                kind=LegistarDocumentKind.AGENDA_PACKET,
                title=f"meeting-{schema.id}-agenda_packet",
            )
            documents.append(agenda_packet_document)
        if schema.minutes:
            minutes_document, _ = Document.objects.get_or_create_from_url(
                url=schema.minutes.url,
                kind=LegistarDocumentKind.MINUTES,
                title=f"meeting-{schema.id}-minutes",
            )
            documents.append(minutes_document)
        for attachment in schema.attachments:
            attachment_document, _ = Document.objects.get_or_create_from_url(
                url=attachment.url,
                kind=LegistarDocumentKind.ATTACHMENT,
                title=f"meeting-{schema.id}-attachment-{attachment.name}",
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
    schema_data = models.JSONField(default=dict, help_text="The raw schema data.")

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
    def schema(self) -> MeetingSchema:
        """Return the schema data for the meeting."""
        return MeetingSchema.parse_obj(self.schema_data)

    @schema.setter
    def schema(self, value: MeetingSchema):
        """Set the schema data for the meeting."""
        self.schema_data = json.loads(value.json())

    @property
    def schema_rows(self) -> list[MeetingRowSchema]:
        """Return the rows of the meeting."""
        return self.schema.rows

    @property
    def url(self) -> str:
        """Return the URL for the meeting."""
        return self.schema.url

    @property
    def record_nos(self) -> t.Iterable[str]:
        """Return the record numbers for the meeting."""
        return {row.legislation.name for row in self.schema_rows}

    @property
    def legislations(self) -> t.Iterable[Legislation]:
        """Return the legislations associated with the meeting."""
        # CONSIDER: we don't explicitly link Legislation to Meeting in the database
        # with a foreign key. This is flexible; when I first started, I wasn't sure
        # whether the linkage was exclusive or not. Now I know better, and we should
        # revisit this. -Dave
        return Legislation.objects.filter(record_no__in=self.record_nos)

    def legislation_summaries(
        self, config: PipelineConfig, kind: SummarizationKind, require: bool = True
    ) -> t.Iterable[LegislationSummary]:
        """
        Return the legislation summaries for the meeting that match the specific
        pipeline configuration.

        If `require` is True (the default), we raise an exception if we can't find
        a summary for each existing legislation. If `require` is False, we return
        whatever we can find.
        """
        legislation_objs = list(self.legislations)
        legislation_summary_objs = LegislationSummary.objects.filter(
            legislation__in=legislation_objs,
            summarizer_name=config.legislation.for_kind(kind),
        )
        if require and legislation_summary_objs.count() != len(legislation_objs):
            raise ValueError(f"Missing legislation summaries for {self} ({kind}).")
        return legislation_summary_objs

    def document_summaries(
        self,
        config: PipelineConfig,
        kind: SummarizationKind,
        excludes: set[str]
        | None = {LegistarDocumentKind.AGENDA, LegistarDocumentKind.AGENDA_PACKET},
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
            summarizer_name=config.document.for_kind(kind),
        )
        if require and document_summary_objs.count() != len(document_objs):
            raise ValueError(f"Missing document summaries for {self} ({kind}).")
        return document_summary_objs

    def __str__(self):
        time_or_cancel = self.time or "canceled"
        return f"Meeting: {self.schema.department.name} {self.date} @ {time_or_cancel}"

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
        config: PipelineConfig,
        kind: SummarizationKind,
    ) -> tuple[MeetingSummary, bool]:
        """
        Get or create a meeting summary from the meeting.

        Summaries for all affiliated documents *and* legislations must already exist,
        or we raise an exception.
        """
        with transaction.atomic():
            # If we already have a summary, return it.
            summary = self.filter(
                meeting=meeting, summarizer_name=config.meeting.for_kind(kind)
            ).first()
            if summary is not None:
                return summary, False

            # Get legislation body summary objects for each legislation.
            # Raise an exception if we can't find them.
            legislation_summaries = meeting.legislation_summaries(config, "body")
            legislation_summary_texts = [ls.summary for ls in legislation_summaries]

            # Likewise for all documents, skipping the ones we normally ignore.
            document_summaries = meeting.document_summaries(config, "body")
            document_summary_texts = [ds.summary for ds in document_summaries]

            # Invoke the summarizer.
            summarizer = MEETING_SUMMARIZERS_BY_NAME[config.meeting.for_kind(kind)]
            summary_text = summarizer(
                meeting.schema.department.name,
                legislation_summary_texts=legislation_summary_texts,
                document_summary_texts=document_summary_texts,
            )
            summary = self.create(
                meeting=meeting,
                summary=summary_text,
                summarizer_name=config.meeting.for_kind(kind),
            )
            return summary, True


class MeetingSummary(models.Model):
    """A summary of a meeting."""

    objects = MeetingSummaryManager()

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name="summaries",
        help_text="The summarized meeting.",
    )

    summary = models.TextField(help_text="The summary of the meeting.")

    summarizer_name = models.CharField(
        max_length=255, help_text="The name of the MeetingSummarizerCallable."
    )

    @property
    def summarizer(self):
        return MEETING_SUMMARIZERS_BY_NAME[self.summarizer_name]

    def __str__(self):
        return f"Meeting Summary: {self.meeting}"

    class Meta:
        verbose_name = "Meeting Summary"
        verbose_name_plural = "Meeting Summaries"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["meeting", "summarizer_name"],
                name="unique_meeting_summary_meeting_summarizer_name",
            ),
        ]


class LegislationManager(models.Manager):
    """A custom manager for Legislation objects."""

    def update_or_create_from_schema(
        self, schema: LegislationSchema
    ) -> tuple[Legislation, bool]:
        """Update or create a legislation from a schema."""
        legislation, created = self.update_or_create(
            legistar_id=schema.id,
            legistar_guid=schema.guid,
            defaults={
                "record_no": schema.record_no,
                "type": schema.type,
                "status": schema.status,
                "title": schema.title,
                "schema_data": json.loads(schema.json()),
            },
        )
        assert isinstance(legislation, Legislation)
        # Load all the documents, if needed; update the legislation's
        # documents to match the schema.
        documents = []
        for attachment in schema.attachments:
            attachment_document, _ = Document.objects.get_or_create_from_url(
                url=attachment.url,
                kind=LegistarDocumentKind.ATTACHMENT,
                title=f"legislation-{schema.id}-attachment-{attachment.name}",
            )
            documents.append(attachment_document)
        for supporting_document in schema.supporting_documents:
            supporting_document_document, _ = Document.objects.get_or_create_from_url(
                url=supporting_document.url,
                kind=LegistarDocumentKind.SUPPORTING_DOCUMENT,
                title=f"legislation-{schema.id}-supporting-{supporting_document.name}",
            )
            documents.append(supporting_document_document)
        if schema.full_text is not None:
            full_text_document, _ = Document.objects.get_or_create_from_url(
                url=urllib.parse.urljoin(schema.url, "#FullTextDiv"),
                kind=LegistarDocumentKind.FULL_TEXT,
                title=f"legislation-{schema.id}-full",
                raw_content=schema.full_text.encode("utf-8"),
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
    schema_data = models.JSONField(default=dict, help_text="The raw schema data.")

    documents = models.ManyToManyField(
        Document,
        related_name="legislations",
        help_text="The documents associated with the legislation.",
    )

    @property
    def schema(self) -> LegislationSchema:
        """Return the schema data for the legislation."""
        return LegislationSchema.parse_obj(self.schema_data)

    @schema.setter
    def schema(self, value: LegislationSchema):
        """Set the schema data for the legislation."""
        self.schema_data = json.loads(value.json())

    @property
    def schema_rows(self) -> list[LegislationRowSchema]:
        """Return the rows of the legislation."""
        return self.schema.rows

    @property
    def attachments(self) -> t.Iterable[Document]:
        """Return the attachments for the legislation."""
        return self.documents.filter(kind=LegistarDocumentKind.ATTACHMENT)

    @property
    def supporting_documents(self) -> t.Iterable[Document]:
        """Return the supporting documents for the legislation."""
        return self.documents.filter(kind=LegistarDocumentKind.SUPPORTING_DOCUMENT)

    @property
    def actions(self):
        """Return the actions for the legislation."""
        return Action.objects.filter(record_no=self.record_no)

    @property
    def url(self) -> str:
        """Return the URL for the legislation."""
        return self.schema.url

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
        config: PipelineConfig,
        kind: SummarizationKind,
        excludes: set[str] | None = None,
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
            summarizer_name=config.document.for_kind(kind),
        )
        if require and document_summary_objs.count() != len(document_objs):
            raise ValueError(f"Missing document summaries for {self} ({kind})")
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
        config: PipelineConfig,
        kind: SummarizationKind,
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
                summarizer_name=config.legislation.for_kind(kind),
            ).first()
            if summary is not None:
                return summary, False

            # Get document body summary objects. Raise an exception if we can't
            # find them.
            document_summaries = legislation.document_summaries(config, "body")
            document_summary_texts = [ds.summary for ds in document_summaries]

            # Invoke the summarizer.
            summarizer = LEGISLATION_SUMMARIZERS_BY_NAME[
                config.legislation.for_kind(kind)
            ]
            summary_text = summarizer(
                legislation.title, document_summary_texts=document_summary_texts
            )
            summary = self.create(
                legislation=legislation,
                summary=summary_text,
                summarizer_name=config.legislation.for_kind(kind),
            )
            return summary, True


class LegislationSummary(models.Model):
    """A summary of legislation as found on the Legistar website."""

    objects = LegislationSummaryManager()

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    legislation = models.ForeignKey(
        Legislation,
        on_delete=models.CASCADE,
        related_name="summaries",
        help_text="The legislation that the summary is for.",
    )

    summary = models.TextField(help_text="The summary of the legislation.")
    summarizer_name = models.CharField(
        max_length=255, help_text="The name of the summarizer."
    )

    @property
    def summarizer(self):
        """Return the summarizer."""
        return LEGISLATION_SUMMARIZERS_BY_NAME[self.summarizer_name]

    class Meta:
        verbose_name = "Legislation Summary"
        verbose_name_plural = "Legislation Summaries"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["legislation", "summarizer_name"],
                name="unique_legislation_summary_legislation_summarizer",
            ),
        ]


class ActionManager(models.Manager):
    def update_or_create_from_schema(self, schema: ActionSchema) -> tuple[Action, bool]:
        """Update or create an action from a schema."""
        action, created = self.update_or_create(
            legistar_id=schema.id,
            legistar_guid=schema.guid,
            defaults={
                "record_no": schema.record_no,
                "schema_data": json.loads(schema.json()),
            },
        )
        return action, created


class Action(models.Model):
    """A single action as found on the Legistar website."""

    objects = ActionManager()

    legistar_id = models.IntegerField(
        help_text="The ID of the action on the Legistar site."
    )
    legistar_guid = models.CharField(
        max_length=36, help_text="The GUID of the action on the Legistar site."
    )

    record_no = models.CharField(
        db_index=True,
        max_length=255,
        help_text="The legislative record number of the action.",
    )

    schema_data = models.JSONField(default=dict, help_text="The raw schema data.")

    @property
    def schema(self) -> ActionSchema:
        """Return the schema data for the action."""
        return ActionSchema.parse_obj(self.schema_data)

    @schema.setter
    def schema(self, value: ActionSchema):
        """Set the schema data for the action."""
        self.schema_data = json.loads(value.json())

    @property
    def schema_rows(self) -> list[ActionRowSchema]:
        """Return the rows of the action."""
        return self.schema.rows

    @property
    def legislation(self) -> Legislation | None:
        """Return the legislation associated with the action."""
        return Legislation.objects.filter(record_no=self.record_no).first()

    @property
    def url(self) -> str:
        """Return the URL for the action."""
        return self.schema.url

    class Meta:
        verbose_name = "Action"
        verbose_name_plural = "Actions"
        constraints = [
            models.UniqueConstraint(
                fields=["legistar_id", "legistar_guid"],
                name="unique_action_legistar_id_guid",
            ),
        ]
