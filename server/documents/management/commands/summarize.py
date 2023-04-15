import sys

import djclick as click
from django.conf import settings

from server.documents.models import Document, DocumentSummary, DocumentText
from server.documents.summarize import SUMMARIZE_PIPELINE_V1, run_summarizer


@click.group(invoke_without_command=True)
def main():
    """Summarize text from documents."""
    context = click.get_current_context()
    if context.invoked_subcommand is None:
        click.echo(context.get_help())


@main.command()
@click.argument("pk", type=int, required=True)
@click.argument("summarizer", type=str, default=SUMMARIZE_PIPELINE_V1)
@click.option("--temperature", type=float, default=None, required=False)
@click.option("--map-prompt", type=str, default=None, required=False)
@click.option("--combine-prompt", type=str, default=None, required=False)
@click.option("--prompt", type=str, default=None, required=False)
@click.option("--db", is_flag=True, default=False)
def single(
    pk: int,
    summarizer: str,
    db: bool,
    temperature: float | None = None,
    map_prompt: str | None = None,
    combine_prompt: str | None = None,
    prompt: str | None = None,
):
    """Summarize text from a single document."""
    # XXX for now, select the latest text. This should be improved.
    document_text = DocumentText.objects.filter(document_id=pk).first()
    if document_text is None:
        raise click.ClickException(
            "No extracted text found for document. Run extract first."
        )

    if db:
        document_summary, _ = DocumentSummary.objects.get_or_create_from_document_text(
            document_text, summarizer
        )
        click.echo(document_summary.summary)
        return
    summarizer_kwargs = {}
    if temperature is not None:
        summarizer_kwargs["temperature"] = temperature
    if prompt is not None:
        summarizer_kwargs["map_prompt"] = prompt.replace("\\n", "\n")
        summarizer_kwargs["combine_prompt"] = prompt.replace("\\n", "\n")
    else:
        if map_prompt is not None:
            summarizer_kwargs["map_prompt"] = map_prompt.replace("\\n", "\n")
        if combine_prompt is not None:
            summarizer_kwargs["combine_prompt"] = combine_prompt.replace("\\n", "\n")
    summary = run_summarizer(summarizer, document_text.text, **summarizer_kwargs)
    click.echo(summary)


@main.command()
@click.argument("summarizer", type=str, default=SUMMARIZE_PIPELINE_V1)
@click.option("--db", is_flag=True, default=False)
def all(summarizer: str, db: bool):
    """Summarize text from all documents that don't yet have it."""
    documents_with = DocumentSummary.objects.filter(summarizer=summarizer).values_list(
        "document_id", flat=True
    )
    documents_without = Document.objects.exclude(document_id__in=documents_with)
    for document in documents_without:
        document_text = document.texts.first()
        if document_text is None:
            continue
        if db:
            (
                document_summary,
                _,
            ) = DocumentSummary.objects.get_or_create_from_document_text(
                document_text, summarizer_name=summarizer
            )
            click.echo(document_summary.summary)
            continue
        if settings.VERBOSE:
            print(
                f">>>> SUMMARIZE [nodb]: doc_text({document_text}, {summarizer})",
                file=sys.stderr,
            )
        summary = run_summarizer(summarizer, document_text.text)
        click.echo(summary)
