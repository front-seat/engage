# Generated by Django 4.2 on 2023-04-14 05:44

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('documents', '0002_models'),
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
            name='Meeting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legistar_id', models.IntegerField(help_text='The ID of the meeting on the Legistar site.')),
                ('legistar_guid', models.CharField(help_text='The GUID of the meeting on the Legistar site.', max_length=36)),
                ('date', models.DateField(db_index=True, help_text='The date of the meeting.')),
                ('time', models.TimeField(blank=True, db_index=True, help_text='The time of the meeting.', null=True)),
                ('location', models.CharField(help_text='The location of the meeting.', max_length=255)),
                ('schema_data', models.JSONField(default=dict, help_text='The raw schema data.')),
                ('documents', models.ManyToManyField(help_text='The documents associated with the meeting.', related_name='meetings', to='documents.document')),
            ],
            options={
                'verbose_name': 'Meeting',
                'verbose_name_plural': 'Meetings',
                'ordering': ['-date'],
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
                ('title', models.CharField(help_text='The title of the legislation.', max_length=255)),
                ('schema_data', models.JSONField(default=dict, help_text='The raw schema data.')),
                ('documents', models.ManyToManyField(help_text='The documents associated with the legislation.', related_name='legislations', to='documents.document')),
            ],
            options={
                'verbose_name': 'Legislation',
                'verbose_name_plural': 'Legislation',
            },
        ),
        migrations.AddConstraint(
            model_name='action',
            constraint=models.UniqueConstraint(fields=('legistar_id', 'legistar_guid'), name='unique_action_legistar_id_guid'),
        ),
        migrations.AddConstraint(
            model_name='meeting',
            constraint=models.UniqueConstraint(fields=('legistar_id', 'legistar_guid'), name='unique_meeting_legistar_id_guid'),
        ),
        migrations.AddConstraint(
            model_name='legislation',
            constraint=models.UniqueConstraint(fields=('legistar_id', 'legistar_guid'), name='unique_legislation_legistar_id_guid'),
        ),
    ]