# Generated by Django 4.2 on 2023-04-15 18:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('summarized_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('extra', models.JSONField(db_index=True, default=dict, help_text='Extra data.')),
                ('summary', models.TextField(help_text='The summary of the document text.')),
                ('document', models.ForeignKey(help_text='The document this summary belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='summaries', to='documents.document')),
                ('document_text', models.ForeignKey(help_text='The document text this summary belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='summaries', to='documents.documenttext')),
            ],
            options={
                'ordering': ['-summarized_at'],
            },
        ),
    ]