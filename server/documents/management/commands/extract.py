import sys

import djclick as click
from django.conf import settings

from server.documents.extract import EXTRACT_PIPELINE_V1, run_extractor
from server.documents.models import Document, DocumentText


@click.group(invoke_without_command=True)
def main():
    """Extract text from documents."""
    context = click.get_current_context()
    if context.invoked_subcommand is None:
        click.echo(context.get_help())


@main.command()
@click.argument("pk", type=int, required=True)
@click.argument("extractor", type=str, default=EXTRACT_PIPELINE_V1)
@click.option("--db", is_flag=True, default=False)
def single(pk: int, extractor: str, db: bool):
    """Extract text from a single document."""
    document = Document.objects.get(pk=pk)
    if db:
        document_text, _ = DocumentText.objects.get_or_create_from_document(
            document, extractor
        )
        click.echo(document_text.text)
        return
    with document.file.open("rb") as file:
        text = run_extractor(extractor, document.mime_type, file)
    click.echo(text)


@main.command()
@click.argument("extractor", type=str, default=EXTRACT_PIPELINE_V1)
@click.option("--db", is_flag=True, default=False)
def all(extractor: str, db: bool):
    """Extract text from all documents that don't yet have it."""
    documents_with = DocumentText.objects.filter(extractor=extractor).values_list(
        "document_id", flat=True
    )
    documents_without = Document.objects.exclude(pk__in=documents_with)
    for document in documents_without:
        if db:
            document_text, _ = DocumentText.objects.get_or_create_from_document(
                document, extractor_name=extractor
            )
            click.echo(document_text.text)
            continue

        if settings.VERBOSE:
            print(f">>>> EXTRACT [nodb]: doc({document}, {extractor})", file=sys.stderr)

        with document.file.open("rb") as file:
            text = run_extractor(name=extractor, io=file, mime_type=document.mime_type)
        click.echo(text)
