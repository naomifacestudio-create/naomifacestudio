from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0002_blog_meta_description_en_blog_meta_description_hr'),
    ]

    operations = [
        migrations.RenameField(model_name='blog', old_name='title_hr', new_name='title_sr'),
        migrations.RenameField(model_name='blog', old_name='slug_hr', new_name='slug_sr'),
        migrations.RenameField(model_name='blog', old_name='short_description_hr', new_name='short_description_sr'),
        migrations.RenameField(model_name='blog', old_name='full_description_hr', new_name='full_description_sr'),
        migrations.RenameField(model_name='blog', old_name='meta_description_hr', new_name='meta_description_sr'),
    ]
