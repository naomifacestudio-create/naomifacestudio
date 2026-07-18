from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("treatments", "0005_visual_builder_with_legacy_conversion"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="treatment",
            name="legacy_full_description_sr",
        ),
        migrations.RemoveField(
            model_name="treatment",
            name="legacy_full_description_en",
        ),
    ]
