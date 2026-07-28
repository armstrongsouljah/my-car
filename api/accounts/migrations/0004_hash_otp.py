from django.db import migrations, models


def burn_plaintext_otps(apps, schema_editor):
    """
    Existing rows hold raw codes, which can no longer be verified against the
    HMAC digests this migration switches to. They are short-lived (10 minutes)
    and re-requestable, so mark them used rather than leaving codes that would
    silently never match.
    """
    apps.get_model("accounts", "EmailVerificationOTP").objects.filter(is_used=False).update(is_used=True)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_emailverificationotp_failed_attempts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emailverificationotp",
            name="otp",
            field=models.CharField(max_length=64),
        ),
        migrations.RunPython(burn_plaintext_otps, migrations.RunPython.noop),
    ]
