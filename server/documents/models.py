from __future__ import annotations

import io
import mimetypes
import sys
import typing as t

import humanize
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils.text import slugify

from .extract import run_extractor
from .summarize import run_summarizer

OPENAI_ADA_EMBEDDING_DIMENSIONS = 1536


def _load_url(url: str) -> tuple[bytes, str]:
    """Load a document from a URL."""
    response = requests.get(url)
    response.raise_for_status()
    return response.content, response.headers["Content-Type"]


class DocumentManager(models.Manager):
    def get_or_create_from_url(
        self,
        url: str,
        kind: str,
        title: str,
        loader: t.Callable[[str], tuple[bytes, str]] = _load_url,
    ) -> tuple[Document, bool]:
        """Get or create a document from a URL."""
        # Don't use the default get_or_create() because we want to
        # use the URL as the unique identifier and prevent loading the
        # document from the URL if it already exists.
        with transaction.atomic():
            document = self.filter(url=url).first()
            if document is not None:
                return document, False
            if settings.VERBOSE:
                print(f">>>> CRAWL: get_document({url})", file=sys.stderr)
            content, mime_type = loader(url)
            extension = mimetypes.guess_extension(mime_type)
            if extension is None:
                raise ValueError(f"Unknown MIME type: {mime_type}")
            file_name = f"{slugify(title)}{extension}"
            content_file = ContentFile(content, name=file_name)
            if settings.VERBOSE:
                natural_size = humanize.naturalsize(len(content), format="%.0f")
                print(
                    f"         : {file_name} ({natural_size})",
                    file=sys.stderr,
                )

            document = self.create(
                url=url,
                title=title,
                mime_type=mime_type,
                kind=kind,
                file=content_file,
            )
            return document, True

    def get_or_create_from_content(
        self,
        url: str,
        kind: str,
        title: str,
        content: bytes,
        mime_type: str,
    ) -> tuple[Document, bool]:
        """Get or create a document from a URL."""

        def _loader(_: str) -> tuple[bytes, str]:
            return content, mime_type

        return self.get_or_create_from_url(url, kind, title, _loader)


class Document(models.Model):
    """
    A single document downloaded from a source URL.
    """

    objects = DocumentManager()

    url = models.URLField(
        unique=True, help_text="The original URL where the document was found."
    )
    kind = models.CharField(
        max_length=255,
        db_index=True,
        help_text="The kind of document.",
    )
    title = models.CharField(max_length=255, help_text="The title of the document.")
    mime_type = models.CharField(
        max_length=255, help_text="The MIME type of the document."
    )
    file = models.FileField(
        upload_to="documents",
        help_text="The downloaded document.",
    )

    def __str__(self):
        return f"{self.kind}: {self.title}"


class DocumentTextManager(models.Manager):
    def filter_by_extractor(self, extractor_name: str):
        return self.filter(extra__extractor__name=extractor_name)

    def filter_by_document(self, document: Document):
        return self.filter(document=document)

    def filter_by_document_and_extractor(self, document: Document, extractor_name: str):
        return self.filter(document=document, extra__extractor__name=extractor_name)

    def get_or_create_from_document(
        self,
        document: Document,
        extractor_name: str,
        extractor_kwargs: dict[str, t.Any] | None = None,
    ) -> tuple[DocumentText, bool]:
        """Get or create a document text from a document."""
        # Don't use the default get_or_create() because we want to
        # use the document and extractor as the unique identifier.
        with transaction.atomic():
            document_text = self.filter_by_document_and_extractor(
                document, extractor_name
            ).first()
            if document_text is not None:
                return document_text, False
            if settings.VERBOSE:
                print(
                    f">>>> EXTRACT: document({document}, {extractor_name})",
                    file=sys.stderr,
                )
            with document.file.open("rb") as file:
                text = run_extractor(
                    name=extractor_name,
                    io=t.cast(io.BytesIO, file),
                    mime_type=document.mime_type,
                    **(extractor_kwargs or {}),
                )
            document_text = self.create(
                document=document,
                extra={
                    "extractor": {
                        "name": extractor_name,
                        "kwargs": extractor_kwargs or {},
                    }
                },
                text=text,
            )
            return document_text, True


class DocumentText(models.Model):
    """The extracted content of a document."""

    objects = DocumentTextManager()

    extracted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    extra = models.JSONField(default=dict, db_index=True, help_text="Extra data.")

    @property
    def extractor_name(self) -> str:
        return self.extra["extractor"]["name"]

    @extractor_name.setter
    def extractor_name(self, value: str):
        self.extra["extractor"] = {**self.extra.get("extractor", {}), "name": value}

    @property
    def extractor_kwargs(self) -> dict[str, t.Any]:
        return self.extra["extractor"].get("kwargs", {})

    @extractor_kwargs.setter
    def extractor_kwargs(self, value: dict[str, t.Any]):
        self.extra["extractor"] = {
            **self.extra.get("extractor", {}),
            "kwargs": value,
        }

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="texts",
        help_text="The document this text belongs to.",
    )
    text = models.TextField(help_text="The text content of the document.")

    def __str__(self):
        return f"Extracted text of: {self.document}"

    class Meta:
        ordering = ["-extracted_at"]


class DocumentSummaryManager(models.Manager):
    def filter_by_summarizer(self, summarizer_name: str):
        return self.filter(extra__summarizer__name=summarizer_name)

    def filter_by_document_text(self, document_text: DocumentText):
        return self.filter(document_text=document_text)

    def filter_by_document_text_and_summarizer(
        self, document_text: DocumentText, summarizer_name: str
    ):
        return self.filter(
            document_text=document_text, extra__summarizer__name=summarizer_name
        )

    def get_or_create_from_document_text(
        self,
        document_text: DocumentText,
        summarizer_name: str,
        summarizer_kwargs: dict[str, t.Any] | None = None,
    ) -> tuple[DocumentSummary, bool]:
        with transaction.atomic():
            document_summary = self.filter_by_document_text_and_summarizer(
                document_text, summarizer_name
            ).first()
            if document_summary is not None:
                return document_summary, False
            if settings.VERBOSE:
                print(
                    f">>>> SUMMARIZE: doc_text({document_text}, {summarizer_name})",
                    file=sys.stderr,
                )
            summary = run_summarizer(
                name=summarizer_name,
                text=document_text.text,
                **(summarizer_kwargs or {}),
            )
            document_summary = self.create(
                document=document_text.document,
                document_text=document_text,
                extra={
                    "summarizer": {
                        "name": summarizer_name,
                        "kwargs": summarizer_kwargs or {},
                    }
                },
                summary=summary,
            )
            return document_summary, True


class DocumentSummary(models.Model):
    """The extracted summary of a document text."""

    objects = DocumentSummaryManager()

    summarized_at = models.DateTimeField(auto_now_add=True, db_index=True)

    extra = models.JSONField(default=dict, db_index=True, help_text="Extra data.")

    summary = models.TextField(help_text="The summary of the document text.")

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="summaries",
        help_text="The document this summary belongs to.",
    )

    document_text = models.ForeignKey(
        DocumentText,
        on_delete=models.CASCADE,
        related_name="summaries",
        help_text="The document text this summary belongs to.",
    )

    @property
    def summarizer_name(self) -> str:
        return self.extra["summarizer"]["name"]

    @summarizer_name.setter
    def summarizer_name(self, value: str):
        self.extra["summarizer"] = {**self.extra.get("summarizer", {}), "name": value}

    @property
    def summarizer_kwargs(self) -> dict[str, t.Any]:
        return self.extra["summarizer"].get("kwargs", {})

    @summarizer_kwargs.setter
    def summarizer_kwargs(self, value: dict[str, t.Any]):
        self.extra["summarizer"] = {
            **self.extra.get("summarizer", {}),
            "kwargs": value,
        }

    class Meta:
        ordering = ["-summarized_at"]
        verbose_name_plural = "Document summaries"
