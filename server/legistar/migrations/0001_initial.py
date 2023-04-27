# Generated by Django 4.2 on 2023-04-27 19:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('documents', '0001_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legistar_id', models.IntegerField(help_text='The ID of the action on the Legistar site.')),
                ('legistar_guid', models.CharField(help_text='The GUID of the action on the Legistar site.', max_length=36)),
                ('record_no', models.CharField(db_index=True, help_text='The legislative record number of the action.', max_length=255)),
                ('schema_data', models.JSONField(default=dict, help_text='The raw schema data.')),
            ],
            options={
                'verbose_name': 'Action',
                'verbose_name_plural': 'Actions',
            },
        ),
        migrations.CreateModel(
            name='Legislation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legistar_id', models.IntegerField(help_text='The ID of the legislation on the Legistar site.')),
                ('legistar_guid', models.CharField(help_text='The GUID of the legislation on the Legistar site.', max_length=36)),
                ('record_no', models.CharField(db_index=True, help_text='The record number of the legislation.', max_length=255)),
                ('type', models.CharField(help_text='The type of legislation.', max_length=255)),
                ('status', models.CharField(blank=True, help_text='The status of the legislation.', max_length=255)),
                ('title', models.TextField(help_text='The title of the legislation.')),
                ('schema_data', models.JSONField(default=dict, help_text='The raw schema data.')),
                ('documents', models.ManyToManyField(help_text='The documents associated with the legislation.', related_name='legislations', to='documents.document')),
            ],
            options={
                'verbose_name': 'Legislation',
                'verbose_name_plural': 'Legislation',
            },
        ),
        migrations.CreateModel(
            name='Meeting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legistar_id', models.IntegerField(help_text='The ID of the meeting on the Legistar site.')),
                ('legistar_guid', models.CharField(help_text='The GUID of the meeting on the Legistar site.', max_length=36)),
                ('date', models.DateField(db_index=True, help_text='The date of the meeting.')),
                ('time', models.TimeField(blank=True, db_index=True, help_text='The time of the meeting.', null=True)),
                ('location', models.CharField(help_text='The location of the meeting.', max_length=255)),
                ('schema_data', models.JSONField(default=dict, help_text='The raw schema data.')),
                ('documents', models.ManyToManyField(related_name='meetings', to='documents.document')),
            ],
            options={
                'verbose_name': 'Meeting',
                'verbose_name_plural': 'Meetings',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='MeetingSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('summary', models.TextField(help_text='The summary of the meeting.')),
                ('summarizer_name', models.CharField(help_text='The name of the MeetingSummarizerCallable.', max_length=255)),
                ('meeting', models.ForeignKey(help_text='The summarized meeting.', on_delete=django.db.models.deletion.CASCADE, related_name='summaries', to='legistar.meeting')),
            ],
            options={
                'verbose_name': 'Meeting Summary',
                'verbose_name_plural': 'Meeting Summaries',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LegislationSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('summary', models.TextField(help_text='The summary of the legislation.')),
                ('summarizer_name', models.CharField(help_text='The name of the summarizer.', max_length=255)),
                ('legislation', models.ForeignKey(help_text='The legislation that the summary is for.', on_delete=django.db.models.deletion.CASCADE, related_name='summaries', to='legistar.legislation')),
            ],
            options={
                'verbose_name': 'Legislation Summary',
                'verbose_name_plural': 'Legislation Summaries',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='action',
            constraint=models.UniqueConstraint(fields=('legistar_id', 'legistar_guid'), name='unique_action_legistar_id_guid'),
        ),
        migrations.AddConstraint(
            model_name='meetingsummary',
            constraint=models.UniqueConstraint(fields=('meeting', 'summarizer_name'), name='unique_meeting_summary_meeting_summarizer_name'),
        ),
        migrations.AddConstraint(
            model_name='meeting',
            constraint=models.UniqueConstraint(fields=('legistar_id', 'legistar_guid'), name='unique_meeting_legistar_id_guid'),
        ),
        migrations.AddConstraint(
            model_name='legislationsummary',
            constraint=models.UniqueConstraint(fields=('legislation', 'summarizer_name'), name='unique_legislation_summary_legislation_summarizer'),
        ),
        migrations.AddConstraint(
            model_name='legislation',
            constraint=models.UniqueConstraint(fields=('legistar_id', 'legistar_guid'), name='unique_legislation_legistar_id_guid'),
        ),
    ]
