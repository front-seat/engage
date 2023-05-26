# Generated by Django 4.2.1 on 2023-05-26 05:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("documents", "0001_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="Legislation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "legistar_id",
                    models.IntegerField(
                        help_text="The ID of the legislation on the Legistar site."
                    ),
                ),
                (
                    "legistar_guid",
                    models.CharField(
                        help_text="The GUID of the legislation on the Legistar site.",
                        max_length=36,
                    ),
                ),
                (
                    "record_no",
                    models.CharField(
                        db_index=True,
                        help_text="The record number of the legislation.",
                        max_length=255,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        help_text="The type of legislation.", max_length=255
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        blank=True,
                        help_text="The status of the legislation.",
                        max_length=255,
                    ),
                ),
                ("title", models.TextField(help_text="The title of the legislation.")),
                (
                    "raw_crawl_data",
                    models.JSONField(default=dict, help_text="The raw crawl data."),
                ),
                (
                    "documents",
                    models.ManyToManyField(
                        help_text="The documents associated with the legislation.",
                        related_name="legislations",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "verbose_name": "Legislation",
                "verbose_name_plural": "Legislation",
            },
        ),
        migrations.CreateModel(
            name="Meeting",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "legistar_id",
                    models.IntegerField(
                        help_text="The ID of the meeting on the Legistar site."
                    ),
                ),
                (
                    "legistar_guid",
                    models.CharField(
                        help_text="The GUID of the meeting on the Legistar site.",
                        max_length=36,
                    ),
                ),
                (
                    "date",
                    models.DateField(
                        db_index=True, help_text="The date of the meeting."
                    ),
                ),
                (
                    "time",
                    models.TimeField(
                        blank=True,
                        db_index=True,
                        help_text="The time of the meeting.",
                        null=True,
                    ),
                ),
                (
                    "location",
                    models.CharField(
                        help_text="The location of the meeting.", max_length=255
                    ),
                ),
                (
                    "raw_crawl_data",
                    models.JSONField(default=dict, help_text="The raw crawl data."),
                ),
                (
                    "documents",
                    models.ManyToManyField(
                        related_name="meetings", to="documents.document"
                    ),
                ),
            ],
            options={
                "verbose_name": "Meeting",
                "verbose_name_plural": "Meetings",
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="MeetingSummary",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("body", models.TextField(help_text="A detailed summary of a text.")),
                ("headline", models.TextField(help_text="A brief summary of a text.")),
                (
                    "original_text",
                    models.TextField(help_text="The original summarized text."),
                ),
                (
                    "chunks",
                    models.JSONField(
                        default=list,
                        help_text="Text chunks sent to the LLM for summarization.",
                    ),
                ),
                (
                    "chunk_summaries",
                    models.JSONField(
                        default=list, help_text="LLM outputs for each text chunk."
                    ),
                ),
                (
                    "style",
                    models.CharField(
                        db_index=True,
                        help_text="The SummarizationStyle used to generate this summary.",
                        max_length=255,
                    ),
                ),
                (
                    "meeting",
                    models.ForeignKey(
                        help_text="The summarized meeting.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="summaries",
                        to="legistar.meeting",
                    ),
                ),
            ],
            options={
                "verbose_name": "Meeting summary",
                "verbose_name_plural": "Meeting summaries",
            },
        ),
        migrations.CreateModel(
            name="LegislationSummary",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("body", models.TextField(help_text="A detailed summary of a text.")),
                ("headline", models.TextField(help_text="A brief summary of a text.")),
                (
                    "original_text",
                    models.TextField(help_text="The original summarized text."),
                ),
                (
                    "chunks",
                    models.JSONField(
                        default=list,
                        help_text="Text chunks sent to the LLM for summarization.",
                    ),
                ),
                (
                    "chunk_summaries",
                    models.JSONField(
                        default=list, help_text="LLM outputs for each text chunk."
                    ),
                ),
                (
                    "style",
                    models.CharField(
                        db_index=True,
                        help_text="The SummarizationStyle used to generate this summary.",
                        max_length=255,
                    ),
                ),
                (
                    "legislation",
                    models.ForeignKey(
                        help_text="The legislation that the summary is for.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="summaries",
                        to="legistar.legislation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Legislation summary",
                "verbose_name_plural": "Legislation summaries",
            },
        ),
        migrations.AddConstraint(
            model_name="meetingsummary",
            constraint=models.UniqueConstraint(
                fields=("meeting", "style"), name="unique_meeting_summmary_for_style"
            ),
        ),
        migrations.AddConstraint(
            model_name="meeting",
            constraint=models.UniqueConstraint(
                fields=("legistar_id", "legistar_guid"),
                name="unique_meeting_legistar_id_guid",
            ),
        ),
        migrations.AddConstraint(
            model_name="legislationsummary",
            constraint=models.UniqueConstraint(
                fields=("legislation", "style"),
                name="unique_legislation_summary_for_style",
            ),
        ),
        migrations.AddConstraint(
            model_name="legislation",
            constraint=models.UniqueConstraint(
                fields=("legistar_id", "legistar_guid"),
                name="unique_legislation_legistar_id_guid",
            ),
        ),
    ]
