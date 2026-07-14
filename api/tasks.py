from celery import shared_task


@shared_task(name="tasks.send_otp_email_task")
def send_otp_email_task(email, otp, first_name=""):
    from utils.Email import send_otp_email

    send_otp_email(email=email, otp=otp, first_name=first_name)


@shared_task(name="tasks.send_welcome_email_task")
def send_welcome_email_task(email, first_name=""):
    from utils.Email import send_welcome_email

    send_welcome_email(email=email, first_name=first_name)


@shared_task(name="tasks.send_mileage_reminders_task")
def send_mileage_reminders_task():
    """
    Daily sweep: emails owners whose chosen mileage-reminder cadence
    (daily/weekly/monthly) has elapsed since the last nudge, asking them to
    update their cars' odometer readings.
    """
    from django.utils import timezone
    from django.utils.timesince import timesince

    from accounts.models import User
    from utils import Constants
    from utils.Email import send_mileage_reminder_email

    now = timezone.now()
    sent = 0

    queryset = (
        User.objects
        .filter(is_active=True)
        .exclude(mileage_reminder_frequency=Constants.MILEAGE_REMINDER_OFF)
        .prefetch_related("cars")
    )

    for user in queryset:
        interval_days = Constants.MILEAGE_REMINDER_INTERVAL_DAYS.get(user.mileage_reminder_frequency)
        if not interval_days:
            continue

        if user.last_mileage_reminder_at and (now - user.last_mileage_reminder_at).days < interval_days:
            continue

        cars = []
        for car in user.cars.filter(is_active=True):
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

        send_mileage_reminder_email(email=user.email, first_name=user.first_name, cars=cars)
        user.last_mileage_reminder_at = now
        user.save(update_fields=["last_mileage_reminder_at", "updated_at"])
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
