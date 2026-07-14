from celery import shared_task


@shared_task(name="tasks.send_otp_email_task")
def send_otp_email_task(email, otp, first_name=""):
    from utils.Email import send_otp_email

    send_otp_email(email=email, otp=otp, first_name=first_name)


@shared_task(name="tasks.send_welcome_email_task")
def send_welcome_email_task(email, first_name=""):
    from utils.Email import send_welcome_email

    send_welcome_email(email=email, first_name=first_name)


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
