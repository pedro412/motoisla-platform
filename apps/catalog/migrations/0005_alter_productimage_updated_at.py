from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0004_media_assets_v1"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productimage",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
