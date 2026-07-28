from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_mileage_reminder"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailverificationotp",
            name="failed_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
