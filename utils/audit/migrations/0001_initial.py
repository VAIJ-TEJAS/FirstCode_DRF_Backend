# Generated migration for AuditLog model

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    """Initial migration for AuditLog model."""

    initial = True

    dependencies = [
        # No dependencies - this is a standalone utility model
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                )),
                ('timestamp', models.DateTimeField(
                    db_index=True,
                )),
                ('action', models.CharField(
                    choices=[
                        ('create', 'CREATE'),
                        ('update', 'UPDATE'),
                        ('delete', 'DELETE'),
                        ('view', 'VIEW'),
                        ('login', 'LOGIN'),
                        ('logout', 'LOGOUT'),
                        ('export', 'EXPORT'),
                        ('import', 'IMPORT'),
                        ('bulk_create', 'BULK_CREATE'),
                        ('bulk_update', 'BULK_UPDATE'),
                        ('bulk_delete', 'BULK_DELETE'),
                    ],
                    db_index=True,
                    max_length=50,
                )),
                ('level', models.CharField(
                    choices=[
                        ('info', 'INFO'),
                        ('warning', 'WARNING'),
                        ('error', 'ERROR'),
                        ('critical', 'CRITICAL'),
                    ],
                    default='info',
                    max_length=20,
                )),
                ('entity_type', models.CharField(
                    db_index=True,
                    max_length=100,
                )),
                ('entity_id', models.CharField(
                    blank=True,
                    db_index=True,
                    max_length=100,
                    null=True,
                )),
                ('entity_repr', models.CharField(
                    blank=True,
                    max_length=255,
                )),
                ('user_id', models.IntegerField(
                    blank=True,
                    db_index=True,
                    null=True,
                )),
                ('user_email', models.EmailField(
                    blank=True,
                    max_length=255,
                )),
                ('user_name', models.CharField(
                    blank=True,
                    max_length=255,
                )),
                ('ip_address', models.GenericIPAddressField(
                    blank=True,
                    null=True,
                )),
                ('user_agent', models.TextField(
                    blank=True,
                )),
                ('request_id', models.CharField(
                    blank=True,
                    db_index=True,
                    max_length=100,
                )),
                ('session_id', models.CharField(
                    blank=True,
                    db_index=True,
                    max_length=100,
                )),
                ('correlation_id', models.CharField(
                    blank=True,
                    db_index=True,
                    max_length=100,
                )),
                ('changes_data', models.JSONField(
                    default=list,
                    blank=True,
                )),
                ('old_state', models.JSONField(
                    blank=True,
                    null=True,
                )),
                ('new_state', models.JSONField(
                    blank=True,
                    null=True,
                )),
                ('metadata', models.JSONField(
                    default=dict,
                    blank=True,
                )),
                ('duration_ms', models.FloatField(
                    blank=True,
                    null=True,
                )),
                ('has_changes', models.BooleanField(
                    db_index=True,
                    default=False,
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                )),
            ],
            options={
                'verbose_name': 'Audit Log Entry',
                'verbose_name_plural': 'Audit Log Entries',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['entity_type', 'entity_id', '-timestamp'],
                name='audit_audit_entity__d6c93c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['user_id', '-timestamp'],
                name='audit_audit_user_id_8f7c2f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['action', '-timestamp'],
                name='audit_audit_action_3b9f8a_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['timestamp', 'level'],
                name='audit_audit_timesta_4a7b9c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['request_id'],
                name='audit_audit_request_e1c5d2_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['correlation_id'],
                name='audit_audit_correla_5d3e8f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['entity_type', 'action', '-timestamp'],
                name='audit_audit_entity__9a2b4c_idx',
            ),
        ),
    ]
