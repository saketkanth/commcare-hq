# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import corehq.form_processor.track_related
import corehq.form_processor.models
import dimagi.utils.couch
import corehq.form_processor.abstract_models


class Migration(migrations.Migration):

    dependencies = [
        ('form_processor', '0046_add_not_null_constraint_to_owner_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncLogSQL',
            fields=[
                ('sync_log_id', models.CharField(max_length=255, unique=True, serialize=False, primary_key=True, db_index=True)),
                ('date', models.DateTimeField()),
                ('user_id', models.CharField(max_length=255)),
                ('previous_log_id', models.CharField(max_length=255, null=True)),
                ('duration', models.IntegerField(null=True)),
                ('case_ids_on_phone', corehq.form_processor.models.SetField(default='null', help_text='Enter a valid JSON object')),
                ('dependent_case_ids_on_phone', corehq.form_processor.models.SetField(default='null', help_text='Enter a valid JSON object')),
                ('owner_ids_on_phone', corehq.form_processor.models.SetField(default='null', help_text='Enter a valid JSON object')),
                ('index_tree', corehq.form_processor.models.IndexTreeField(default='null', help_text='Enter a valid JSON object')),
                ('extension_index_tree', corehq.form_processor.models.IndexTreeField(default='null', help_text='Enter a valid JSON object')),
                ('closed_cases', corehq.form_processor.models.SetField(default='null', help_text='Enter a valid JSON object')),
                ('extensions_checked', models.BooleanField(default=False)),
                ('last_submitted', models.DateTimeField(null=True)),
                ('last_cached', models.DateTimeField(null=True)),
                ('hash_at_last_cached', models.TextField(null=True)),
                ('had_state_error', models.BooleanField(default=False)),
                ('error_date', models.DateTimeField(null=True)),
                ('error_hash', models.TextField(null=True)),
            ],
            options={
                'db_table': 'form_processor_synclogsql',
            },
            bases=(models.Model, dimagi.utils.couch.RedisLockableMixIn, corehq.form_processor.abstract_models.AbstractSyncLog, corehq.form_processor.track_related.TrackRelatedChanges),
        ),
    ]
