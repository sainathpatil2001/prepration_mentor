from django.db import migrations, models
import django.db.models.deletion


def populate_test_categories(apps, schema_editor):
    Test = apps.get_model('accounts', 'Test')
    TestCategory = apps.get_model('accounts', 'TestCategory')
    try:
        from django.utils.text import slugify
    except ImportError:
        def slugify(value):
            return value.lower().replace(' ', '-') if value else ''

    for test in Test.objects.all():
        category_label = getattr(test, 'category', None)
        if not category_label:
            continue
        name = category_label.strip()
        if not name:
            continue

        base_slug = slugify(name)[:110] or 'category'
        slug_candidate = base_slug
        suffix = 1
        while TestCategory.objects.filter(slug=slug_candidate).exclude(name=name).exists():
            suffix += 1
            slug_candidate = f"{base_slug}-{suffix}"

        category_obj, created = TestCategory.objects.get_or_create(
            name=name,
            defaults={'slug': slug_candidate}
        )
        if not category_obj.slug:
            category_obj.slug = slug_candidate
            category_obj.save(update_fields=['slug'])

        setattr(test, 'category_fk', category_obj)
        test.save(update_fields=['category_fk'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_test_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(help_text='URL friendly identifier', max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
                ('display_order', models.PositiveIntegerField(default=0, help_text='Lower numbers appear first')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='test',
            name='category_fk',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tests', to='accounts.testcategory'),
        ),
        migrations.RunPython(populate_test_categories, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='test',
            name='category',
        ),
        migrations.RenameField(
            model_name='test',
            old_name='category_fk',
            new_name='category',
        ),
    ]

