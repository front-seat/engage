from __future__ import annotations

import mimetypes
import typing as t

import requests
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils.text import slugify

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
            content, mime_type = loader(url)
            extension = mimetypes.guess_extension(mime_type)
            if extension is None:
                raise ValueError(f"Unknown MIME type: {mime_type}")
            content_file = ContentFile(content, name=f"{slugify(title)}{extension}")
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
