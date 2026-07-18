from django.db import migrations


CONTENT_MODELS = (
    ("blogs", "Blog"),
    ("education", "Education"),
    ("treatments", "Treatment"),
)


def migrate_legacy_descriptions(apps, schema_editor):
    SeoMetadata = apps.get_model("seo", "SeoMetadata")
    ContentType = apps.get_model("contenttypes", "ContentType")
    database = schema_editor.connection.alias

    for app_label, model_name in CONTENT_MODELS:
        Model = apps.get_model(app_label, model_name)
        content_type, _ = ContentType.objects.using(database).get_or_create(
            app_label=app_label,
            model=model_name.lower(),
        )
        for item in Model.objects.using(database).all().iterator():
            for locale, field_name in (
                ("sr", "meta_description_sr"),
                ("en", "meta_description_en"),
            ):
                description = (getattr(item, field_name, "") or "").strip()
                if description:
                    SeoMetadata.objects.using(database).update_or_create(
                        content_type_id=content_type.pk,
                        object_id=item.pk,
                        locale=locale,
                        defaults={"meta_description": description},
                    )


def restore_legacy_descriptions(apps, schema_editor):
    SeoMetadata = apps.get_model("seo", "SeoMetadata")
    ContentType = apps.get_model("contenttypes", "ContentType")
    database = schema_editor.connection.alias

    for app_label, model_name in CONTENT_MODELS:
        Model = apps.get_model(app_label, model_name)
        content_type = ContentType.objects.using(database).filter(
            app_label=app_label,
            model=model_name.lower(),
        ).first()
        if not content_type:
            continue
        for item in Model.objects.using(database).all().iterator():
            updates = {}
            for locale, field_name in (
                ("sr", "meta_description_sr"),
                ("en", "meta_description_en"),
            ):
                metadata = SeoMetadata.objects.using(database).filter(
                    content_type_id=content_type.pk,
                    object_id=item.pk,
                    locale=locale,
                ).first()
                if metadata:
                    updates[field_name] = metadata.meta_description
            if updates:
                Model.objects.using(database).filter(pk=item.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ("seo", "0001_initial"),
        ("blogs", "0005_visual_builder_fields"),
        ("education", "0004_visual_builder_fields"),
        ("treatments", "0006_remove_converted_ckeditor_fields"),
    ]

    operations = [
        migrations.RunPython(
            migrate_legacy_descriptions,
            restore_legacy_descriptions,
        ),
    ]
