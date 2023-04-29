from __future__ import annotations

import io
import mimetypes
import sys
import typing as t

import requests
from django.conf import settings
from django.db import models, transaction
from django.utils.text import slugify

from server.lib.truncate import truncate_str

from .extract import EXTRACTORS_BY_NAME, ExtractorCallable
from .summarize import SUMMARIZERS_BY_NAME, SummarizerCallable

OPENAI_ADA_EMBEDDING_DIMENSIONS = 1536


def _load_url_mime_type(url: str) -> str:
    """Load the content type of a URL."""
    response = requests.head(url)
    response.raise_for_status()
    raw_content_type = response.headers["Content-Type"]
    mime_type, *_ = raw_content_type.split(";")
    return mime_type


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
        raw_content: bytes | None = None,
        _get_mime_type: t.Callable[[str], str] = _load_url_mime_type,
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
            mime_type = _get_mime_type(url)
            if settings.VERBOSE:
                extension = mimetypes.guess_extension(mime_type)
                if extension is None:
                    raise ValueError(f"Unknown MIME type: {mime_type}")
                file_name = f"{slugify(title)}{extension}"
                print(
                    f"         : {file_name} (HEAD)",
                    file=sys.stderr,
                )
            document = self.create(
                url=url,
                kind=kind,
                title=title,
                mime_type=mime_type,
                raw_content=raw_content,
            )
            return document, True


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
    raw_content = models.BinaryField(
        blank=True,
        null=True,
        default=None,
        help_text="""If the content was obtained via means other than the URL, 
(for instance, was obtained by grabbing a piece of the HTML content at the URL)
, then this field contains the raw text of the document.""",
    )

    @property
    def is_pdf(self) -> bool:
        return self.mime_type == "application/pdf"

    @property
    def is_text(self) -> bool:
        return self.mime_type == "text/plain"

    @property
    def has_raw_content(self) -> bool:
        return self.raw_content is not None

    @property
    def extension(self) -> str:
        maybe_extension = mimetypes.guess_extension(self.mime_type)
        if maybe_extension is None:
            raise ValueError(f"Unknown MIME type: {self.mime_type}")
        return maybe_extension

    @property
    def file_name(self) -> str:
        return f"{slugify(self.title)}{self.extension}"

    @property
    def truncated_title(self) -> str:
        return truncate_str(self.title, 48)

    @property
    def short_title(self) -> str:
        return self.title.split("-")[-1].strip()

    def read(
        self, _loader: t.Callable[[str], tuple[bytes, str]] = _load_url
    ) -> io.BytesIO:
        """Read the document from the raw_content, or the URL."""
        if self.raw_content is not None:
            return io.BytesIO(self.raw_content)
        content, _ = _loader(self.url)
        return io.BytesIO(content)

    def __str__(self):
        return f"{self.kind}: {self.title}"


class DocumentTextManager(models.Manager):
    def get_or_create_from_document(
        self,
        document: Document,
        extractor: ExtractorCallable,
        _reader: t.Callable[[Document], io.BytesIO] = lambda document: document.read(),
    ) -> tuple[DocumentText, bool]:
        """Get or create a document text from a document."""
        # Don't use the default get_or_create() because we want to
        # use the document and extractor as the unique identifier.
        with transaction.atomic():
            document_text = self.filter(
                document=document, extractor_name=extractor.__name__
            ).first()
            if document_text is not None:
                return document_text, False
            if settings.VERBOSE:
                print(
                    f">>>> EXTRACT: document({document}, {extractor.__name__})",
                    file=sys.stderr,
                )
            text = extractor(
                io=_reader(document),
                mime_type=document.mime_type,
            )
            document_text = self.create(
                document=document,
                text=text,
                extractor_name=extractor.__name__,
            )
            return document_text, True


class DocumentText(models.Model):
    """The extracted content of a document."""

    objects = DocumentTextManager()

    extracted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    extractor_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="The name of the extractor used to extract the text.",
    )
    text = models.TextField(help_text="The text content of the document.")

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="texts",
        help_text="The document this text belongs to.",
    )

    @property
    def extractor(self) -> ExtractorCallable:
        return EXTRACTORS_BY_NAME[self.extractor_name]

    def __str__(self):
        return f"Extracted text of: {self.document}"

    class Meta:
        ordering = ["-extracted_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["document", "extractor_name"],
                name="unique_document_extractor_name",
            )
        ]

        verbose_name_plural = "Document text contents"


class DocumentSummaryManager(models.Manager):
    def get_or_create_from_document_text(
        self,
        document_text: DocumentText,
        summarizer: SummarizerCallable,
    ) -> tuple[DocumentSummary, bool]:
        with transaction.atomic():
            document_summary = self.filter(
                document_text=document_text, summarizer_name=summarizer.__name__
            ).first()
            if document_summary is not None:
                return document_summary, False
            if settings.VERBOSE:
                print(
                    f">>>> SUMMARIZE: doc_text({document_text}, {summarizer.__name__})",
                    file=sys.stderr,
                )
            summary = summarizer(
                text=document_text.text,
            )
            document_summary = self.create(
                document=document_text.document,
                document_text=document_text,
                summary=summary,
                summarizer_name=summarizer.__name__,
            )
            return document_summary, True


class DocumentSummary(models.Model):
    """The extracted summary of a document text."""

    objects = DocumentSummaryManager()

    summarized_at = models.DateTimeField(auto_now_add=True, db_index=True)
    summarizer_name = models.CharField(max_length=255, db_index=True)
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
    def summarizer(self) -> SummarizerCallable:
        return SUMMARIZERS_BY_NAME[self.summarizer_name]

    class Meta:
        ordering = ["-summarized_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["document_text", "summarizer_name"],
                name="unique_document_text_summarizer_name",
            )
        ]

        verbose_name_plural = "Document summaries"
