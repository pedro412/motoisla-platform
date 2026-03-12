import django.db.models.deletion
from django.db import migrations, models


def seed_card_instrument_plans(apps, schema_editor):
    CardCommissionPlan = apps.get_model("sales", "CardCommissionPlan")

    # Deactivate legacy NORMAL and MSI_3 plans
    CardCommissionPlan.objects.filter(code__in=["NORMAL", "MSI_3"]).update(is_active=False)

    # Create new instrument-aware plans
    plans = [
        {
            "code": "DEBIT_NORMAL",
            "label": "Tarjeta de débito",
            "installments_months": 0,
            "commission_rate": "0.0200",
            "card_instrument": "DEBIT",
            "sort_order": 0,
        },
        {
            "code": "CREDIT_NORMAL",
            "label": "Tarjeta de crédito",
            "installments_months": 0,
            "commission_rate": "0.0200",
            "card_instrument": "CREDIT",
            "sort_order": 5,
        },
        {
            "code": "CREDIT_MSI_3",
            "label": "Crédito 3 MSI",
            "installments_months": 3,
            "commission_rate": "0.0558",
            "card_instrument": "CREDIT",
            "sort_order": 10,
        },
    ]
    for plan_data in plans:
        CardCommissionPlan.objects.update_or_create(
            code=plan_data["code"],
            defaults=plan_data,
        )


def backfill_card_instrument(apps, schema_editor):
    Payment = apps.get_model("sales", "Payment")
    # All existing CARD payments are CREDIT (confirmed by user)
    Payment.objects.filter(method="CARD", card_instrument__isnull=True).update(card_instrument="CREDIT")

    LayawayPayment = apps.get_model("layaway", "LayawayPayment")
    LayawayPayment.objects.filter(method="CARD", card_instrument="").update(card_instrument="CREDIT")


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0005_sale_profitability_snapshot"),
        ("layaway", "0006_layawaypayment_card_instrument"),
    ]

    operations = [
        migrations.AddField(
            model_name="cardcommissionplan",
            name="card_instrument",
            field=models.CharField(
                blank=True,
                choices=[("DEBIT", "Debit"), ("CREDIT", "Credit")],
                max_length=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="card_instrument",
            field=models.CharField(
                blank=True,
                choices=[("DEBIT", "Debit"), ("CREDIT", "Credit")],
                max_length=12,
                null=True,
            ),
        ),
        migrations.RunPython(seed_card_instrument_plans, migrations.RunPython.noop),
        migrations.RunPython(backfill_card_instrument, migrations.RunPython.noop),
    ]
