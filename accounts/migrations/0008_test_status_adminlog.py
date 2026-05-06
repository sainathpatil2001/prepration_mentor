from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def set_existing_tests_published(apps, schema_editor):
    Test = apps.get_model('accounts', 'Test')
    Test.objects.all().update(status='published', is_hidden=False, published_at=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_test_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='is_hidden',
            field=models.BooleanField(default=False, help_text='Hidden tests are not visible to students'),
        ),
        migrations.AddField(
            model_name='test',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='test',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='draft', max_length=20),
        ),
        migrations.CreateModel(
            name='AdminLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('publish', 'Publish'), ('draft', 'Save Draft'), ('hide', 'Hide'), ('unhide', 'Unhide'), ('delete', 'Delete')], max_length=20)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('metadata', models.TextField(blank=True, null=True, help_text='Additional context stored as JSON string')),
                ('admin_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_logs', to='auth.user')),
                ('test', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_logs', to='accounts.test')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='adminlog',
            index=models.Index(fields=['action', 'created_at'], name='accounts_ad_action_a6f2e1_idx'),
        ),
        migrations.RunPython(set_existing_tests_published, migrations.RunPython.noop),
    ]

