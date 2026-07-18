from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("education", "0005_remove_education_meta_description_en_and_more"),
    ]

    operations = [
        migrations.RenameField("education", "title_sr", "title_hr"),
        migrations.RenameField("education", "slug_sr", "slug_hr"),
        migrations.RenameField("education", "short_description_sr", "short_description_hr"),
        migrations.RenameField("education", "body_page_sr", "body_page_hr"),
        migrations.RenameField("education", "body_plaintext_sr", "body_plaintext_hr"),
        migrations.RenameField("education", "page_version_sr", "page_version_hr"),
        migrations.AlterField(
            model_name="education",
            name="title_hr",
            field=models.CharField(max_length=200, verbose_name="Title (Croatian)"),
        ),
        migrations.AlterField(
            model_name="education",
            name="slug_hr",
            field=models.SlugField(max_length=200, unique=True, verbose_name="Slug (Croatian)"),
        ),
        migrations.AlterField(
            model_name="education",
            name="short_description_hr",
            field=models.TextField(blank=True, max_length=500, verbose_name="Short Description (Croatian)"),
        ),
        migrations.AlterField(
            model_name="education",
            name="body_page_hr",
            field=models.JSONField(blank=True, null=True, verbose_name="Visual content (Croatian)"),
        ),
        migrations.AlterField(
            model_name="education",
            name="body_plaintext_hr",
            field=models.TextField(blank=True, editable=False, verbose_name="Plaintext content (Croatian)"),
        ),
        migrations.AlterField(
            model_name="education",
            name="page_version_hr",
            field=models.PositiveIntegerField(default=0, verbose_name="Content version (Croatian)"),
        ),
    ]
