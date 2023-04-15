# Generated by Django 4.2 on 2023-04-15 18:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('documents', '0001_initial'),
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
                ('file', models.FileField(help_text='The downloaded document.', upload_to='documents')),
            ],
        ),
        migrations.CreateModel(
            name='DocumentText',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('extracted_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('extra', models.JSONField(db_index=True, default=dict, help_text='Extra data.')),
                ('text', models.TextField(help_text='The text content of the document.')),
                ('document', models.ForeignKey(help_text='The document this text belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='texts', to='documents.document')),
            ],
            options={
                'ordering': ['-extracted_at'],
            },
        ),
    ]
