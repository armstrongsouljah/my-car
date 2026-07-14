from django.db import migrations, models

import cars.models


class Migration(migrations.Migration):

    dependencies = [
        ("cars", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="car",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to=cars.models.car_photo_path),
        ),
        migrations.AddField(
            model_name="car",
            name="odometer_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
