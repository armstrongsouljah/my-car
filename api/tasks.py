from celery import shared_task


@shared_task(name="tasks.send_otp_email_task")
def send_otp_email_task(email, otp, first_name=""):
    from utils.Email import send_otp_email

    send_otp_email(email=email, otp=otp, first_name=first_name)


@shared_task(name="tasks.send_welcome_email_task")
def send_welcome_email_task(email, first_name=""):
    from utils.Email import send_welcome_email

    send_welcome_email(email=email, first_name=first_name)


@shared_task(name="tasks.send_support_request_email_task")
def send_support_request_email_task(support_request_id):
    from support.models import SupportRequest
    from utils.Email import send_support_request_email

    support_request = SupportRequest.objects.prefetch_related("attachments").get(pk=support_request_id)
    send_support_request_email(support_request)


@shared_task(name="tasks.send_mileage_reminders_task")
def send_mileage_reminders_task():
    """
    Daily sweep: emails owners whose chosen mileage-reminder cadence
    (daily/weekly/monthly) has elapsed since the last nudge, asking them to
    update their cars' odometer readings.
    """
    from django.db.models import Prefetch
    from django.utils import timezone
    from django.utils.timesince import timesince

    from accounts.models import User
    from cars.models import Car
    from utils import Constants
    from utils.Email import send_mileage_reminder_email

    now = timezone.now()
    sent = 0

    queryset = (
        User.objects
        .filter(is_active=True)
        .exclude(mileage_reminder_frequency=Constants.MILEAGE_REMINDER_OFF)
        .prefetch_related(
            Prefetch("cars", queryset=Car.objects.filter(is_active=True), to_attr="active_cars")
        )
    )

    for user in queryset:
        interval_days = Constants.MILEAGE_REMINDER_INTERVAL_DAYS.get(user.mileage_reminder_frequency)
        if not interval_days:
            continue

        if user.last_mileage_reminder_at and (now - user.last_mileage_reminder_at).days < interval_days:
            continue

        cars = []
        for car in user.active_cars:
            updated_ago = (
                f"updated {timesince(car.odometer_updated_at, now)} ago"
                if car.odometer_updated_at else "never updated"
            )
            cars.append({
                "label": str(car),
                "current_odometer_km": car.current_odometer_km,
                "updated_ago": updated_ago,
            })

        if not cars:
            continue

        # Atomically claim this send *before* emailing (conditioned on the
        # last_mileage_reminder_at value read above) so two concurrent
        # workers that both pass the eligibility check can't double-send.
        claimed = User.objects.filter(
            pk=user.pk, last_mileage_reminder_at=user.last_mileage_reminder_at,
        ).update(last_mileage_reminder_at=now, updated_at=now)
        if not claimed:
            continue

        send_mileage_reminder_email(email=user.email, first_name=user.first_name, cars=cars)
        sent += 1

    return f"Sent {sent} mileage reminder email(s)"


@shared_task(name="tasks.send_due_reminders_task")
def send_due_reminders_task():
    """
    Daily sweep (scheduled via CELERY_BEAT_SCHEDULE): finds every active car
    whose next service or general inspection is due/soon due and emails the
    owner one digest per car.
    """
    from utils.Email import send_reminder_email
    from cars.models import Car
    from services.reminders import build_car_reminders

    sent = 0
    queryset = Car.objects.filter(is_active=True, owner__is_active=True).select_related("owner")

    for car in queryset:
        reminders = [r for r in build_car_reminders(car) if r["status"] != "ok"]
        if not reminders:
            continue
        send_reminder_email(
            email=car.owner.email,
            first_name=car.owner.first_name,
            car_label=str(car),
            reminders=reminders,
        )
        sent += 1

    return f"Sent {sent} reminder email(s)"


@shared_task(name="tasks.purge_deactivated_accounts_task")
def purge_deactivated_accounts_task():
    """
    Daily sweep: permanently deletes accounts that have been deactivated for
    longer than Constants.ACCOUNT_DELETION_GRACE_DAYS. Support can reactivate
    a deactivated account any time before this runs; past the grace period
    the deletion is final and cascades to the owner's cars, service history,
    expenses, reminders and inspections.
    """
    from django.utils import timezone

    from accounts.models import User
    from utils import Constants

    cutoff = timezone.now() - timezone.timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS)
    queryset = User.objects.filter(is_active=False, deactivated_at__isnull=False, deactivated_at__lte=cutoff)

    count = queryset.count()
    queryset.delete()
    return f"Purged {count} deactivated account(s) and their data"
