# Generated by Django 4.2 on 2023-04-28 16:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(help_text='The original URL where the document was found.', unique=True)),
                ('kind', models.CharField(db_index=True, help_text='The kind of document.', max_length=255)),
                ('title', models.CharField(help_text='The title of the document.', max_length=255)),
                ('mime_type', models.CharField(help_text='The MIME type of the document.', max_length=255)),
                ('raw_content', models.BinaryField(blank=True, default=None, help_text='If the content was obtained via means other than the URL, \n(for instance, was obtained by grabbing a piece of the HTML content at the URL)\n, then this field contains the raw text of the document.', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DocumentText',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('extracted_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('extractor_name', models.CharField(db_index=True, help_text='The name of the extractor used to extract the text.', max_length=255)),
                ('text', models.TextField(help_text='The text content of the document.')),
                ('document', models.ForeignKey(help_text='The document this text belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='texts', to='documents.document')),
            ],
            options={
                'verbose_name_plural': 'Document text contents',
                'ordering': ['-extracted_at'],
            },
        ),
        migrations.CreateModel(
            name='DocumentSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('summarized_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('summarizer_name', models.CharField(db_index=True, max_length=255)),
                ('summary', models.TextField(help_text='The summary of the document text.')),
                ('document', models.ForeignKey(help_text='The document this summary belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='summaries', to='documents.document')),
                ('document_text', models.ForeignKey(help_text='The document text this summary belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='summaries', to='documents.documenttext')),
            ],
            options={
                'verbose_name_plural': 'Document summaries',
                'ordering': ['-summarized_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='documenttext',
            constraint=models.UniqueConstraint(fields=('document', 'extractor_name'), name='unique_document_extractor_name'),
        ),
        migrations.AddConstraint(
            model_name='documentsummary',
            constraint=models.UniqueConstraint(fields=('document_text', 'summarizer_name'), name='unique_document_text_summarizer_name'),
        ),
    ]
