from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("layaway", "0005_layaway_status_refunded"),
    ]

    operations = [
        migrations.AddField(
            model_name="layawaypayment",
            name="card_instrument",
            field=models.CharField(blank=True, default="", max_length=12),
        ),
    ]
