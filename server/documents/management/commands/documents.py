import sys

import djclick as click
from django.conf import settings

from server.documents.extract import EXTRACTORS, EXTRACTORS_BY_NAME
from server.documents.models import Document, DocumentSummary, DocumentText
from server.lib.pipeline_config import (
    PIPELINE_CONFIGS,
    PIPELINE_CONFIGS_BY_NAME,
    SUMMARIZATION_KINDS,
)


@click.group(invoke_without_command=True)
def main():
    """Manipulate stored documents."""
    context = click.get_current_context()
    if context.invoked_subcommand is None:
        click.echo(context.get_help())


@main.group(invoke_without_command=True)
def extract():
    """Extract text from documents."""
    context = click.get_current_context()
    if context.invoked_subcommand is None:
        click.echo(context.get_help())


@extract.command(name="single")
@click.argument("pk", type=int, required=True)
@click.argument("extractor-name", type=str, default=EXTRACTORS[0])
def extract_single(pk: int, extractor_name: str):
    """Extract text from a single document."""
    extractor = EXTRACTORS_BY_NAME[extractor_name]
    document = Document.objects.get(pk=pk)
    document_text, _ = DocumentText.objects.get_or_create_from_document(
        document, extractor
    )
    click.echo(document_text.text)


@extract.command(name="all")
@click.argument("extractor-name", type=str, default=EXTRACTORS[0])
def extract_all(extractor_name: str):
    """Extract text from all documents that don't yet have it."""
    extractor = EXTRACTORS_BY_NAME[extractor_name]
    documents_with = DocumentText.objects.filter(
        extractor_name=extractor_name
    ).values_list("document_id", flat=True)
    documents_without = Document.objects.exclude(pk__in=documents_with)
    for document in documents_without:
        document_text, _ = DocumentText.objects.get_or_create_from_document(
            document, extractor
        )
        click.echo(document_text.text)


@main.group(invoke_without_command=True)
def summarize():
    """Summarize extracted document text."""
    context = click.get_current_context()
    if context.invoked_subcommand is None:
        click.echo(context.get_help())


@summarize.command(name="single")
@click.argument("pk", type=int, required=True)
@click.argument("config-name", type=str, default=PIPELINE_CONFIGS[0].name)
@click.argument("kind", type=str, default="body")
def summarize_single(
    pk: int,
    config_name: str,
    kind: str,
):
    """
    Get a previously summarized document from the database, or summarize it
    if it hasn't been summarized yet.
    """
    assert kind in SUMMARIZATION_KINDS, f"Invalid kind: {kind}"
    config = PIPELINE_CONFIGS_BY_NAME[config_name]
    # XXX for now, select the latest text. This should be improved, or we
    # should drop the complexity of having different 'extracted texts' for
    # a single document.
    document_text = DocumentText.objects.filter(document_id=pk).first()
    if document_text is None:
        raise click.ClickException(
            "No extracted text found for document. Run extract first."
        )
    document_summary, _ = DocumentSummary.objects.get_or_create_from_document_text(
        document_text, config, kind
    )
    click.echo(document_summary.summary)


@summarize.command(name="all")
@click.option("--ignore-kinds", type=str, default="agenda,agenda_packet")
def summarize_all(ignore_kinds: str = "agenda,agenda_packet"):
    """Extract and summarize text from all documents using all summarizers."""
    extractor = EXTRACTORS[0]
    ignore_kinds_set = set(ik.strip() for ik in ignore_kinds.split(","))
    documents = Document.objects.all().exclude(kind__in=ignore_kinds_set)
    for config in PIPELINE_CONFIGS:
        if settings.VERBOSE:
            print(f">>>> ALL-DOCS: Using {config.name}", file=sys.stderr)
        for document in documents:
            for kind in SUMMARIZATION_KINDS:
                document_text, _ = DocumentText.objects.get_or_create_from_document(
                    document, extractor=extractor
                )
                (
                    document_summary,
                    _,
                ) = DocumentSummary.objects.get_or_create_from_document_text(
                    document_text,
                    config,
                    kind,
                )
                if settings.VERBOSE:
                    print(
                        f">>>> ALL-DOCS: Sum {document} w/ {config.name} '{kind}'",
                        file=sys.stderr,
                    )
                click.echo(document_summary.summary)
                if settings.VERBOSE:
                    print("\n\n", file=sys.stderr)
