from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="mileage_reminder_frequency",
            field=models.CharField(
                choices=[("off", "Off"), ("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")],
                default="off",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_mileage_reminder_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
