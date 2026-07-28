from django.db import migrations, models

import inspections.models
import utils.Uploads


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inspection",
            name="report",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=inspections.models.inspection_report_path,
                validators=[utils.Uploads.validate_upload_type],
            ),
        ),
    ]
