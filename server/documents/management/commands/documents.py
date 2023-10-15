import sys

import djclick as click
from django.conf import settings

from server.documents.models import Document, DocumentSummary
from server.lib.style import SUMMARIZATION_STYLES


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
def extract_single(pk: int):
    """Grab extracted text from a document in the DB; extract it if needed."""
    document = Document.objects.get(pk=pk)
    text = document.extract_text()
    click.echo(text)


@extract.command(name="all")
@click.option("--ignore-kinds", type=str, default="agenda,agenda_packet")
def extract_all(ignore_kinds: str = "agenda,agenda_packet"):
    """
    Get the extracted text of a Document from the database, or extract it
    if it hasn't been extracted yet.
    """
    ignore_kinds_set = set(ik.strip() for ik in ignore_kinds.split(","))
    documents = Document.objects.all().exclude(kind__in=ignore_kinds_set)
    documents_without = documents.filter(extracted_text="")
    for document in documents_without:
        text = document.extract_text()
        click.echo(text)


@main.group(invoke_without_command=True)
def summarize():
    """Summarize extracted document text."""
    context = click.get_current_context()
    if context.invoked_subcommand is None:
        click.echo(context.get_help())


@summarize.command(name="single")
@click.argument("pk", type=int, required=True)
@click.argument("style", type=str, default=SUMMARIZATION_STYLES[0])
@click.argument("kind", type=str, default="body")
def summarize_single(
    pk: int,
    style: str,
    kind: str,
):
    """
    Get a previously summarized document from the database, or summarize it
    if it hasn't been summarized yet.
    """
    assert style in SUMMARIZATION_STYLES, f"Invalid style: {style}"
    document = Document.objects.get(pk=pk)
    if not document.extracted_text:
        raise click.ClickException(
            "No extracted text found for document. Run extract first."
        )
    document_summary, _ = DocumentSummary.manager.get_or_create_from_document(
        document, style
    )
    click.echo(document_summary.headline)
    click.echo(document_summary.body)


@summarize.command(name="all")
@click.option("--ignore-kinds", type=str, default="agenda,agenda_packet")
def summarize_all(ignore_kinds: str = "agenda,agenda_packet"):
    """Summarize text from all documents using all summarizers."""
    ignore_kinds_set = set(ik.strip() for ik in ignore_kinds.split(","))
    documents = Document.objects.all().exclude(kind__in=ignore_kinds_set)
    documents_with = documents.exclude(extracted_text="")
    for style in SUMMARIZATION_STYLES:
        if settings.VERBOSE:
            print(f">>>> ALL-DOCS: Using {style}", file=sys.stderr)
        for document in documents_with:
            (
                document_summary,
                _,
            ) = DocumentSummary.manager.get_or_create_from_document(document, style)
            if settings.VERBOSE:
                print(
                    f">>>> ALL-DOCS: Sum {document} w/ {style}",
                    file=sys.stderr,
                )
            click.echo(document_summary.headline)
            click.echo(document_summary.body)
            if settings.VERBOSE:
                print("\n\n", file=sys.stderr)
