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


def send_password_reset_email(email: str, otp: str, first_name: str = ""):
    """
    Sends an HTML email containing the password-reset OTP code.
    Called from the Celery task — kept import-safe (no app-startup side effects).
    """
    from django.conf import settings

    name = _display_name(email, first_name)
    expiry_minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 10)

    subject = "Your GlavBox password reset code"
    context = {"otp": otp, "name": name, "expiry_minutes": expiry_minutes}

    text_body = (
        f"Hi {name},\n\n"
        f"Your GlavBox password reset code is: {otp}\n\n"
        f"This code expires in {expiry_minutes} minutes.\n\n"
        f"If you didn't request a password reset, you can safely ignore this email — "
        f"your password hasn't changed."
    )
    html_body = render_to_string("emails/password_reset.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_duplicate_signup_email(email: str, first_name: str = ""):
    """
    Sent when someone submits the signup form with an address that already has
    an account. The signup response itself is identical to a fresh registration
    (so the form can't be used to test whether an address is registered), so
    this email is how the actual account holder finds out.
    """
    from django.conf import settings

    name = _display_name(email, first_name)
    app_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    login_url = f"{app_url}/login"

    subject = "You already have a GlavBox account"
    context = {"name": name, "app_url": app_url, "login_url": login_url}

    text_body = (
        f"Hi {name},\n\n"
        f"Someone just tried to create a GlavBox account with this email address, "
        f"but you already have one — so we didn't create a second.\n\n"
        f"If that was you, just sign in instead: {login_url}\n"
        f"If it wasn't, you can ignore this email. Your account hasn't changed and "
        f"nobody was told whether this address is registered.\n"
    )
    html_body = render_to_string("emails/duplicate_signup.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_verify_email_reminder_email(email: str, otp: str, first_name: str = "", days_remaining: int = 0):
    """
    Sent by the daily sweep once Constants.EMAIL_VERIFY_REMINDER_DAYS have
    passed since signup with the address still unverified. Carries a fresh
    OTP (the old one may be long expired) and warns that the account is
    otherwise removed automatically — never verified in the first place, so
    there's no "reactivate" path once that happens.
    """
    from urllib.parse import urlencode

    from django.conf import settings

    name = _display_name(email, first_name)
    expiry_minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 10)
    app_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    # Lands directly on the OTP-entry step with the address prefilled, rather
    # than the bare login page, so finishing verification from the email
    # doesn't also require retyping the email address.
    verify_url = f"{app_url}/login?{urlencode({'mode': 'verify', 'email': email})}"
    context = {
        "name": name, "otp": otp, "expiry_minutes": expiry_minutes,
        "days_remaining": days_remaining, "verify_url": verify_url,
    }

    subject = "Verify your GlavBox account before it's removed"
    text_body = (
        f"Hi {name},\n\n"
        f"You signed up for GlavBox but never verified your email, so your account isn't active yet.\n\n"
        f"Your verification code is: {otp}\n"
        f"This code expires in {expiry_minutes} minutes.\n\n"
        f"Verify here: {verify_url}\n\n"
        f"If you don't verify within {days_remaining} days, the account will be removed automatically.\n\n"
        f"If you didn't sign up for GlavBox, you can safely ignore this email."
    )
    html_body = render_to_string("emails/verify_reminder.html", context)

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


def send_account_deactivated_email(email: str, first_name: str = ""):
    """
    Sent right after DeactivateAccountView deactivates the account: confirms
    the grace period and how to back out of it before permanent deletion.
    """
    from django.conf import settings

    from utils import Constants

    name = _display_name(email, first_name)
    app_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    grace_days = Constants.ACCOUNT_DELETION_GRACE_DAYS
    context = {"name": name, "grace_days": grace_days, "support_url": f"{app_url}/contact"}

    subject = "Your GlavBox account has been deactivated"
    text_body = (
        f"Hi {name},\n\n"
        f"We're sorry to see you go. Your GlavBox account is now deactivated — you're signed out "
        f"everywhere and can't log back in.\n\n"
        f"Your profile and car data are kept for {grace_days} days. If this was a mistake, contact "
        f"support before then and we can reactivate your account: {context['support_url']}\n\n"
        f"After {grace_days} days, everything is permanently and irreversibly deleted."
    )
    html_body = render_to_string("emails/account_deactivated.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_deletion_reminder_email(email: str, first_name: str = "", days_remaining: int = 0):
    """
    Sent by the daily sweep once ACCOUNT_DELETION_REMINDER_DAYS have passed
    since deactivation — the last nudge before the account is purged.
    """
    from django.conf import settings

    name = _display_name(email, first_name)
    app_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    context = {"name": name, "days_remaining": days_remaining, "support_url": f"{app_url}/contact"}

    subject = f"{days_remaining} days left before your GlavBox account is deleted"
    text_body = (
        f"Hi {name},\n\n"
        f"Your GlavBox account has been deactivated, and in {days_remaining} days your profile and all "
        f"of your car data — service history, expenses, reminders, and photos — will be permanently and "
        f"irreversibly deleted.\n\n"
        f"If you'd like to keep your account, contact support before then and we can reactivate it: "
        f"{context['support_url']}"
    )
    html_body = render_to_string("emails/deletion_reminder.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_account_deleted_email(email: str, first_name: str = ""):
    """
    Sent by the purge sweep right before the account row is deleted (the
    email address won't exist to send to afterward).
    """
    name = _display_name(email, first_name)

    subject = "Your GlavBox account has been deleted"
    context = {"name": name}
    text_body = (
        f"Hi {name},\n\n"
        f"As promised, your GlavBox account and all associated data — profile, cars, service history, "
        f"expenses, reminders, and photos — have now been permanently deleted from our systems.\n\n"
        f"If this was a mistake, you're welcome to sign up again any time — we just won't have your old data."
    )
    html_body = render_to_string("emails/account_deleted.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_monthly_expense_report_email(email: str, first_name: str, report: dict):
    """
    Monthly digest (see #21): summarizes last calendar month's spend and
    links to the in-app report, which is also where the PDF download lives —
    the email itself carries no attachment, to keep the send cheap for users
    who never open it.
    """
    from django.conf import settings

    from utils.Currency import format_amount

    name = _display_name(email, first_name)
    app_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    report_url = f"{app_url}/expenses/reports/{report['year']}-{report['month']:02d}/"
    top_categories = report["by_category"][:3]
    currency_code = report.get("currency", "")

    subject = f"Your {report['month_label']} expense report — {format_amount(report['total'], currency_code)}"
    context = {
        "name": name,
        "report": report,
        "top_categories": top_categories,
        "app_url": app_url,
        "report_url": report_url,
    }

    lines = "\n".join(f"- {c['category_label']}: {format_amount(c['total'], currency_code)}" for c in top_categories)
    text_body = (
        f"Hi {name},\n\n"
        f"You spent {format_amount(report['total'], currency_code)} on your car(s) in {report['month_label']} across "
        f"{report['count']} expense(s).\n\n"
        f"Top categories:\n{lines}\n\n"
        f"View the full breakdown and download the PDF: {report_url}"
    )
    html_body = render_to_string("emails/monthly_expense_report.html", context)

    msg = EmailMultiAlternatives(subject=subject, body=text_body, to=[email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_support_request_email(support_request, attachments=None):
    """
    Notifies the support inbox (DEFAULT_FROM_EMAIL) of a contact-us
    submission. Reply-To is the submitter's own address so support can just
    hit reply.

    `attachments` is a list of (filename, bytes, content_type) handed straight
    through from the request — the files are never written to storage, so this
    email is the only copy.
    """
    from django.conf import settings

    attachments = attachments or []
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

    for filename, content, content_type in attachments:
        msg.attach(filename, content, content_type)

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
