from __future__ import annotations

import io
import mimetypes
import sys
import typing as t

import requests
from django.conf import settings
from django.db import models, transaction
from django.utils.text import slugify

from server.lib.pipeline_config import PipelineConfig
from server.lib.summary_model import SummaryBaseModel
from server.lib.truncate import truncate_str

from .extract import extract_text_from_bytes
from .summarize import SUMMARIZERS_BY_NAME, SummarizationSuccess


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
    Represents a single document (like a PDF file, Word doc, or plain text) that
    we found on Legistar.

    Documents are always created from a URL which contains the original content.

    Typically, the URL *only* contains the original content. That is, it's
    the PDF file in question!

    However, sometimes the URL is a web page that contains the document in
    question plus some other stuff (like a header, footer, etc.). In that case,
    we can use the `raw_content` field to store the raw bytes of the document
    itself. This is useful with Legistar, since *sometimes* ordinances and
    resolutions have their full text in separate PDF files, but *sometimes*
    the full text is *only* available on a web page that has lots of other
    UI elements and content on it. Annoying.

    Finally, all `Document` instances have an `extracted_text` field. This
    starts off blank, but you can call `extract_text()` to attempt to extract
    the full text of the document. For instance, if the document is a PDF, we'll
    crack it open and try to find its useful content. Calling `extract_text()`
    both returns the extracted text *and* saves it to the database. Calling
    `extract_text()` multiple times is safe, and will only extract the text
    once; after that, it will just return the text that was already extracted.
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

    extracted_text = models.TextField(
        blank=True,
        null=False,
        default="",
        help_text="""The extracted full text of the document. Since extraction
        happens asynchronously, this field may be empty until the extraction
        process has completed.""",
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

    def extract_text(self) -> str:
        # Don't re-extract, of course.
        if self.extracted_text:
            return self.extracted_text

        # Run the extraction pipeline.
        text = extract_text_from_bytes(self.read(), self.mime_type)
        self.extracted_text = text
        self.save()
        return text

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


class DocumentSummaryManager(models.Manager):
    def get_or_create_from_document(
        self,
        document: Document,
        config: PipelineConfig,
    ) -> tuple[DocumentSummary, bool]:
        with transaction.atomic():
            # If we already have a summary for this document, return it.
            document_summary = self.filter(
                document=document,
                config_name=config.name,
            ).first()
            if document_summary is not None:
                return document_summary, False

            # If the document has no extracted text, it's not ready to be summarized.
            if not document.extracted_text:
                raise ValueError(
                    f"Document {document} has no extracted text; can't be summarized."
                )

            # Otherwise, create a new summary.
            if settings.VERBOSE:
                print(
                    f">>>> SUMMARIZE: doc({document}, {config.name})",
                    file=sys.stderr,
                )

            summarizer = SUMMARIZERS_BY_NAME[config.document]
            result = summarizer(text=document.extracted_text)
            # XXX TODO DAVE
            assert isinstance(result, SummarizationSuccess)
            document_summary = self.create(
                document=document,
                config_name=config.name,
                body=result.body,
                headline=result.headline,
                original_text=result.original_text,
                chunks=result.chunks,
                chunk_summaries=result.chunk_summaries,
            )
            return document_summary, True


class DocumentSummary(SummaryBaseModel):
    """A summary of a document."""

    objects = DocumentSummaryManager()

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="summaries",
        help_text="The summarized document.",
    )

    class Meta:
        verbose_name = "Document summary"
        verbose_name_plural = "Document summaries"

        constraints = [
            models.UniqueConstraint(
                fields=["document", "config_name"],
                name="unique_document_summary_for_config",
            )
        ]
