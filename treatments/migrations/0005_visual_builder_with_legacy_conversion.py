from django.db import migrations, models


def convert_ckeditor_content(apps, schema_editor):
    Treatment = apps.get_model("treatments", "Treatment")
    from page.legacy_html import convert_ckeditor_html

    for treatment in Treatment.objects.all().iterator(chunk_size=100):
        updates = {}
        for suffix in ("sr", "en"):
            legacy_html = getattr(treatment, f"legacy_full_description_{suffix}", "") or ""
            # Conversion is intentionally strict. Migrations are atomic on
            # PostgreSQL, so any failure aborts and leaves all original fields
            # and media untouched instead of accepting partial conversion.
            try:
                page, plaintext = convert_ckeditor_html(legacy_html)
            except Exception as exc:
                title = getattr(treatment, "title_sr", None) or getattr(treatment, "title_en", "")
                raise ValueError(
                    f"Failed converting Treatment pk={treatment.pk} "
                    f"title={title!r} locale={suffix}: {exc}"
                ) from exc
            updates[f"body_page_{suffix}"] = page
            updates[f"body_plaintext_{suffix}"] = plaintext
            updates[f"page_version_{suffix}"] = 1 if page.get("sections") else 0
        Treatment.objects.filter(pk=treatment.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ("treatments", "0004_update_serbian_verbose_names"),
    ]

    operations = [
        migrations.RenameField(
            model_name="treatment",
            old_name="full_description_sr",
            new_name="legacy_full_description_sr",
        ),
        migrations.RenameField(
            model_name="treatment",
            old_name="full_description_en",
            new_name="legacy_full_description_en",
        ),
        migrations.AddField(
            model_name="treatment",
            name="body_page_sr",
            field=models.JSONField(
                blank=True,
                null=True,
                verbose_name="Visual content (Serbian)",
            ),
        ),
        migrations.AddField(
            model_name="treatment",
            name="body_page_en",
            field=models.JSONField(
                blank=True,
                null=True,
                verbose_name="Visual content (English)",
            ),
        ),
        migrations.AddField(
            model_name="treatment",
            name="body_plaintext_sr",
            field=models.TextField(
                blank=True,
                editable=False,
                verbose_name="Plaintext content (Serbian)",
            ),
        ),
        migrations.AddField(
            model_name="treatment",
            name="body_plaintext_en",
            field=models.TextField(
                blank=True,
                editable=False,
                verbose_name="Plaintext content (English)",
            ),
        ),
        migrations.AddField(
            model_name="treatment",
            name="page_version_sr",
            field=models.PositiveIntegerField(
                default=0,
                verbose_name="Content version (Serbian)",
            ),
        ),
        migrations.AddField(
            model_name="treatment",
            name="page_version_en",
            field=models.PositiveIntegerField(
                default=0,
                verbose_name="Content version (English)",
            ),
        ),
        migrations.AlterField(
            model_name="treatment",
            name="legacy_full_description_sr",
            field=models.TextField(
                blank=True,
                editable=False,
                verbose_name="Legacy CKEditor content (Serbian)",
            ),
        ),
        migrations.AlterField(
            model_name="treatment",
            name="legacy_full_description_en",
            field=models.TextField(
                blank=True,
                editable=False,
                verbose_name="Legacy CKEditor content (English)",
            ),
        ),
        migrations.AlterField(
            model_name="treatment",
            name="short_description_sr",
            field=models.TextField(
                blank=True,
                max_length=500,
                verbose_name="Short Description (Serbian)",
            ),
        ),
        migrations.AlterField(
            model_name="treatment",
            name="short_description_en",
            field=models.TextField(
                blank=True,
                max_length=500,
                verbose_name="Short Description (English)",
            ),
        ),
        migrations.AlterField(
            model_name="treatment",
            name="thumbnail",
            field=models.ImageField(
                blank=True,
                help_text="Supports WebP format",
                upload_to="content/featured/%Y/%m/",
                verbose_name="Thumbnail Image",
            ),
        ),
        migrations.AlterModelOptions(
            name="treatment",
            options={
                "ordering": ("-created_at",),
                "verbose_name": "Treatment",
                "verbose_name_plural": "Treatments",
            },
        ),
        migrations.RunPython(convert_ckeditor_content, migrations.RunPython.noop),
    ]
