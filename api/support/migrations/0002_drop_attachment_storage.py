from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Support attachments are no longer written to storage — they ride along on
    the notification email and are dropped afterwards.

    The API pod and the Celery worker have separate filesystems in the cluster,
    so files written during the request were never readable by the task that
    sends the mail. The SupportAttachment rows pointed at files that no longer
    exist on any running pod, so the table goes with the feature; only the
    filenames are kept, on SupportRequest.
    """

    dependencies = [
        ("support", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="supportrequest",
            name="attachment_names",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RemoveField(
            model_name="supportattachment",
            name="support_request",
        ),
        migrations.DeleteModel(
            name="SupportAttachment",
        ),
    ]
