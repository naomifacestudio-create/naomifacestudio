from django.db import migrations, models


def restore_croatian_locale(apps, schema_editor):
    SeoMetadata = apps.get_model("seo", "SeoMetadata")
    database = schema_editor.connection.alias
    SeoMetadata.objects.using(database).filter(locale="sr").update(locale="hr")
    for metadata in SeoMetadata.objects.using(database).all().iterator():
        updates = {}
        for field_name in ("canonical_url", "og_url"):
            value = getattr(metadata, field_name, "") or ""
            rewritten = value.replace("/sr-latn/", "/hr/")
            if rewritten != value:
                updates[field_name] = rewritten
        if updates:
            SeoMetadata.objects.using(database).filter(pk=metadata.pk).update(**updates)


def restore_serbian_locale(apps, schema_editor):
    SeoMetadata = apps.get_model("seo", "SeoMetadata")
    database = schema_editor.connection.alias
    SeoMetadata.objects.using(database).filter(locale="hr").update(locale="sr")
    for metadata in SeoMetadata.objects.using(database).all().iterator():
        updates = {}
        for field_name in ("canonical_url", "og_url"):
            value = getattr(metadata, field_name, "") or ""
            rewritten = value.replace("/hr/", "/sr-latn/")
            if rewritten != value:
                updates[field_name] = rewritten
        if updates:
            SeoMetadata.objects.using(database).filter(pk=metadata.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ("seo", "0002_migrate_legacy_meta_descriptions"),
        ("blogs", "0007_restore_croatian_fields"),
        ("education", "0006_restore_croatian_fields"),
        ("treatments", "0008_restore_croatian_fields"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="seometadata",
            name="seo_locale_sr_or_en",
        ),
        migrations.RunPython(restore_croatian_locale, restore_serbian_locale),
        migrations.AlterField(
            model_name="seometadata",
            name="locale",
            field=models.CharField(
                choices=[("hr", "Croatian"), ("en", "English")],
                max_length=12,
                verbose_name="language",
            ),
        ),
        migrations.AddConstraint(
            model_name="seometadata",
            constraint=models.CheckConstraint(
                check=models.Q(locale__in=("hr", "en")),
                name="seo_locale_hr_or_en",
            ),
        ),
    ]
