from django.db import models


class Body(models.Model):
    """
    A legislative body, such as Seattle City Council.
    """


class DocumentKind(models.TextChoices):
    """Known document types as seen on seattle.legistar.com."""

    # Overall document types
    AGENDA = "Agenda", "Agenda"
    AGENDA_PACKET = "Agenda Packet", "Agenda Packet"
    ORDINANCE_SUMMARY = "Ord Summary", "Ordinance Summary"
    TRANSCRIPT = "Transcript", "Transcript"

    # Legislative document types
    APPOINTMENT = "Appt", "Appointment"
    CLERK_FILE = "CF", "Clerk File"
    COUNCIL_BILL = "CB", "Council Bill"
    COUNCIL_BUDGET_ACTION = "CBA", "Council Budget Action"
    INFORMATION_ITEM = "Inf", "Information Item"
    INTRODUCTION_AND_REFERRAL_CALENDAR = "IRC", "Introduction and Referral Calendar"
    MINUTES = "Min", "Minutes"
    ORDINANCE = "Ord", "Ordinance"
    RESOLUTION = "Res", "Resolution"
    STATEMENT_OF_LEGISLATIVE_INTENT = "SLI", "Statement of Legislative Intent"


class Document(models.Model):
    """
    A single document downloaded from a source URL.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        help_text="The date and time this document was scraped.",
    )
    source_url = models.URLField(
        help_text="The original URL where the document was found."
    )
    event_date = models.DateField(
        help_text="The date of the event the document is about, if known.",
        null=True,
        blank=True,
        db_index=True,
    )
    kind = models.CharField(
        max_length=100,
        choices=DocumentKind.choices,
        help_text="The kind of document.",
        db_index=True,
    )

    file = models.FileField(
        upload_to="documents",
        help_text="The downloaded document, if any.",
        null=True,
        blank=True,
        default=None,
    )

    text = models.TextField(
        help_text="The extracted text of the document.",
        blank=True,
    )

    def __str__(self):
        return f"{self.kind} ({self.event_date})"
