import secrets
import string

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def generate_otp(length=6):
    # secrets, not random — `random` is a Mersenne Twister, so observing enough
    # issued codes lets an attacker predict the next one.
    return "".join(secrets.choice(string.digits) for _ in range(length))


def _display_name(email: str, first_name: str = "") -> str:
    """Return first_name if provided, otherwise the local part of the email."""
    if first_name and first_name.strip():
        return first_name.strip()
    return email.split("@")[0]


def send_otp_email(email: str, otp: str, first_name: str = ""):
    """
    Sends an HTML verification email containing the OTP code.
    Called from the Celery task — kept import-safe (no app-startup side effects).
    """
    from django.conf import settings

    name = _display_name(email, first_name)
    expiry_minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 10)

    subject = "Your GlavBox verification code"
    context = {"otp": otp, "name": name, "expiry_minutes": expiry_minutes}

    text_body = (
        f"Hi {name},\n\n"
        f"Your GlavBox verification code is: {otp}\n\n"
        f"This code expires in {expiry_minutes} minutes.\n\n"
        f"If you didn't sign up for GlavBox, you can safely ignore this email."
    )
    html_body = render_to_string("emails/otp_verification.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_welcome_email(email: str, first_name: str = ""):
    """Sends a post-verification welcome email."""
    from django.conf import settings

    name = _display_name(email, first_name)
    app_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

    subject = "Welcome to GlavBox!"
    context = {"name": name, "app_url": app_url}

    text_body = (
        f"Hi {name},\n\n"
        f"Welcome to GlavBox! Your email has been verified and your garage is ready.\n\n"
        f"Head over to {app_url} to add your first car.\n\n"
        f"If you have any questions, just reply to this email — we're always happy to help."
    )
    html_body = render_to_string("emails/welcome.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_mileage_reminder_email(email: str, first_name: str, cars: list):
    """
    Nudges the owner to update the odometer readings on their cars.
    `cars` is a list of dicts: {"label", "current_odometer_km", "updated_ago"}.
    """
    from django.conf import settings

    name = _display_name(email, first_name)
    app_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

    subject = "Time to update your mileage"
    context = {"name": name, "cars": cars, "app_url": app_url}

    lines = "\n".join(
        f"- {c['label']}: {c['current_odometer_km']} km ({c['updated_ago']})" for c in cars
    )
    text_body = (
        f"Hi {name},\n\n"
        f"A quick nudge to update the current mileage on your cars so your "
        f"service reminders stay accurate:\n\n"
        f"{lines}\n\n"
        f"Open {app_url} and update each car's odometer reading."
    )
    html_body = render_to_string("emails/mileage_reminder.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_support_request_email(support_request):
    """
    Notifies the support inbox (DEFAULT_FROM_EMAIL) of a contact-us
    submission. Reply-To is the submitter's own address so support can just
    hit reply, and any uploaded files are attached to the email itself.
    """
    from django.conf import settings

    attachments = list(support_request.attachments.all())
    subject = f"[GlavBox Support] {support_request.display_subject}"
    submitted_by = "a registered user" if support_request.user_id else "a visitor"

    text_body = (
        f"New support request from {submitted_by}.\n\n"
        f"Name: {support_request.name}\n"
        f"Email: {support_request.email}\n"
        f"Subject: {support_request.display_subject}\n\n"
        f"Message:\n{support_request.message}\n"
    )
    html_body = render_to_string("emails/support_request.html", {
        "name": support_request.name,
        "email": support_request.email,
        "subject": support_request.display_subject,
        "message": support_request.message,
        "submitted_by": submitted_by,
        "attachment_count": len(attachments),
    })

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        to=[settings.DEFAULT_FROM_EMAIL],
        reply_to=[support_request.email],
    )
    msg.attach_alternative(html_body, "text/html")

    for attachment in attachments:
        attachment.file.open("rb")
        try:
            msg.attach(attachment.file.name.rsplit("/", 1)[-1], attachment.file.read())
        finally:
            attachment.file.close()

    msg.send()


def send_reminder_email(email: str, first_name: str, car_label: str, reminders: list):
    """
    Sends a service/inspection reminder digest for a single car.
    `reminders` is a list of dicts: {"kind", "status", "message"}.
    """
    from django.conf import settings

    name = _display_name(email, first_name)
    app_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

    subject = f"Reminder: {car_label} needs attention"
    context = {"name": name, "car_label": car_label, "reminders": reminders, "app_url": app_url}

    lines = "\n".join(f"- {r['message']}" for r in reminders)
    text_body = (
        f"Hi {name},\n\n"
        f"Your car {car_label} has the following reminders:\n\n"
        f"{lines}\n\n"
        f"Open {app_url} to review your service history and book what's due."
    )
    html_body = render_to_string("emails/service_reminder.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()
