import random
import string

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))


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

    subject = "Your My Car verification code"
    context = {"otp": otp, "name": name, "expiry_minutes": expiry_minutes}

    text_body = (
        f"Hi {name},\n\n"
        f"Your My Car verification code is: {otp}\n\n"
        f"This code expires in {expiry_minutes} minutes.\n\n"
        f"If you didn't sign up for My Car, you can safely ignore this email."
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

    subject = "Welcome to My Car!"
    context = {"name": name, "app_url": app_url}

    text_body = (
        f"Hi {name},\n\n"
        f"Welcome to My Car! Your email has been verified and your garage is ready.\n\n"
        f"Head over to {app_url} to add your first car.\n\n"
        f"If you have any questions, just reply to this email — we're always happy to help."
    )
    html_body = render_to_string("emails/welcome.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
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
