import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="tasks.send_otp_email_task")
def send_otp_email_task(email, otp, first_name=""):
    from utils.Email import send_otp_email

    send_otp_email(email=email, otp=otp, first_name=first_name)


@shared_task(name="tasks.send_password_reset_email_task")
def send_password_reset_email_task(email, otp, first_name=""):
    from utils.Email import send_password_reset_email

    send_password_reset_email(email=email, otp=otp, first_name=first_name)


@shared_task(name="tasks.send_welcome_email_task")
def send_welcome_email_task(email, first_name=""):
    from utils.Email import send_welcome_email

    send_welcome_email(email=email, first_name=first_name)


@shared_task(name="tasks.send_account_deactivated_email_task")
def send_account_deactivated_email_task(email, first_name=""):
    from utils.Email import send_account_deactivated_email

    send_account_deactivated_email(email=email, first_name=first_name)


@shared_task(name="tasks.send_support_request_email_task")
def send_support_request_email_task(support_request_id, attachments=None):
    """
    `attachments` is a list of {"name", "content_type", "content_b64"} carried
    in the task payload. They are deliberately not read from storage: this task
    runs in the worker pod, which does not share a filesystem with the API pod
    that handled the upload.
    """
    from base64 import b64decode

    from support.models import SupportRequest
    from utils.Email import send_support_request_email

    support_request = SupportRequest.objects.get(pk=support_request_id)
    decoded = [
        (item["name"], b64decode(item["content_b64"]), item.get("content_type"))
        for item in (attachments or [])
    ]
    send_support_request_email(support_request, attachments=decoded)


@shared_task(name="tasks.send_mileage_reminder_email_task")
def send_mileage_reminder_email_task(user_id, cars):
    """
    Sends one user's mileage reminder and, only on success, confirms it by
    setting last_mileage_reminder_at. Dispatched (never called inline) by
    send_mileage_reminders_task so one user's failure can't crash the rest of
    that day's batch — see #27. A failure here is logged and simply left for
    the next sweep to notice the still-stale claim and retry; there's no
    other cost to a reminder landing a day late.
    """
    from django.utils import timezone

    from accounts.models import User
    from utils import Constants
    from utils.Email import send_mileage_reminder_email

    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return

    # Re-asserts eligibility at send time, not just at claim time: Celery
    # delivers at-least-once, so a redelivered message (or a stale-lease
    # reclaim racing a slow-but-eventually-successful send) must not
    # double-send, and a user who turned reminders off after being claimed
    # shouldn't get mailed anyway.
    interval_days = Constants.MILEAGE_REMINDER_INTERVAL_DAYS.get(user.mileage_reminder_frequency)
    if not interval_days:
        return
    if user.last_mileage_reminder_at and (timezone.now() - user.last_mileage_reminder_at).days < interval_days:
        return

    try:
        send_mileage_reminder_email(email=user.email, first_name=user.first_name, cars=cars)
    except Exception:
        logger.error(
            "Failed to send mileage reminder to user_id=%s; will retry on a later sweep", user_id, exc_info=True
        )
        return

    User.objects.filter(pk=user_id).update(
        last_mileage_reminder_at=timezone.now(),
        mileage_reminder_queued_at=None,
        updated_at=timezone.now(),
    )


@shared_task(name="tasks.send_mileage_reminders_task")
def send_mileage_reminders_task():
    """
    Daily sweep: emails owners whose chosen mileage-reminder cadence
    (daily/weekly/monthly) has elapsed since the last nudge, asking them to
    update their cars' odometer readings.

    Claims each eligible user via mileage_reminder_queued_at — a lease, not a
    delivery confirmation — then dispatches the actual send as its own task
    (send_mileage_reminder_email_task). last_mileage_reminder_at, which the
    cadence check above reads, is only set by that task once the send
    actually succeeds. A claim whose send never confirms (crash, lost task,
    a raised exception) goes stale after Constants.REMINDER_CLAIM_LEASE_HOURS
    and gets reclaimed by a later sweep. See #27.
    """
    from django.db.models import Prefetch, Q
    from django.utils import timezone
    from django.utils.timesince import timesince

    from accounts.models import User
    from cars.models import Car
    from utils import Constants

    now = timezone.now()
    lease_cutoff = now - timezone.timedelta(hours=Constants.REMINDER_CLAIM_LEASE_HOURS)
    queued = 0

    queryset = (
        User.objects
        .filter(is_active=True)
        .exclude(mileage_reminder_frequency=Constants.MILEAGE_REMINDER_OFF)
        .filter(Q(mileage_reminder_queued_at__isnull=True) | Q(mileage_reminder_queued_at__lt=lease_cutoff))
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

        # Atomically claim (conditioned on the queued_at value read above,
        # which is None for a never-claimed user or a since-gone-stale one)
        # so two concurrent workers that both pass the eligibility check
        # can't both dispatch a send.
        claimed = User.objects.filter(
            pk=user.pk,
            mileage_reminder_queued_at=user.mileage_reminder_queued_at,
        ).update(mileage_reminder_queued_at=now, updated_at=now)
        if not claimed:
            continue

        send_mileage_reminder_email_task.delay(user_id=user.pk, cars=cars)
        queued += 1

    return f"Queued {queued} mileage reminder email(s)"


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


@shared_task(name="tasks.send_deletion_reminder_email_task")
def send_deletion_reminder_email_task(user_id, days_remaining):
    """
    Sends one account's deletion reminder and, only on success, confirms it
    by setting deletion_reminder_sent_at. Dispatched (never called inline) by
    send_account_deletion_reminder_task so one account's failure can't crash
    the rest of that day's batch — see #27. A failure here is logged and
    simply left for the next sweep to notice the still-stale claim and
    retry.
    """
    from django.utils import timezone

    from accounts.models import User
    from utils.Email import send_deletion_reminder_email

    # Re-checks is_active/deletion_reminder_sent_at at send time, not just at
    # claim time: the account may have been reactivated (deactivate() clears
    # both) since this task was queued.
    user = User.objects.filter(pk=user_id, is_active=False, deletion_reminder_sent_at__isnull=True).first()
    if user is None:
        return

    try:
        send_deletion_reminder_email(email=user.email, first_name=user.first_name, days_remaining=days_remaining)
    except Exception:
        logger.error(
            "Failed to send deletion reminder to user_id=%s; will retry on a later sweep", user_id, exc_info=True
        )
        return

    User.objects.filter(pk=user_id).update(deletion_reminder_sent_at=timezone.now(), updated_at=timezone.now())


@shared_task(name="tasks.send_account_deletion_reminder_task")
def send_account_deletion_reminder_task():
    """
    Daily sweep: emails owners whose deactivated account has passed
    Constants.ACCOUNT_DELETION_REMINDER_DAYS since deactivation, warning that
    permanent deletion is coming.

    Claims each account via deletion_reminder_queued_at — a lease, not a
    delivery confirmation — then dispatches the actual send as its own task
    (send_deletion_reminder_email_task), which alone sets
    deletion_reminder_sent_at once the send actually succeeds. A claim whose
    send never confirms goes stale after Constants.REMINDER_CLAIM_LEASE_HOURS
    and gets reclaimed by a later sweep. See #27.
    """
    from django.db.models import Q
    from django.utils import timezone

    from accounts.models import User
    from utils import Constants

    now = timezone.now()
    cutoff = now - timezone.timedelta(days=Constants.ACCOUNT_DELETION_REMINDER_DAYS)
    # Excludes accounts already eligible for the purge sweep: this task and
    # purge_deactivated_accounts_task both run daily with no ordering
    # guarantee, so without this an account sitting past the 30-day cutoff
    # (e.g. a previous run of this task never claimed it) could get a
    # misleading "15 days left" email right as, or after, it's deleted.
    purge_cutoff = now - timezone.timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS)
    lease_cutoff = now - timezone.timedelta(hours=Constants.REMINDER_CLAIM_LEASE_HOURS)
    days_remaining = Constants.ACCOUNT_DELETION_GRACE_DAYS - Constants.ACCOUNT_DELETION_REMINDER_DAYS

    queryset = User.objects.filter(
        is_active=False,
        is_email_verified=True,
        deactivated_at__isnull=False,
        deactivated_at__lte=cutoff,
        deactivated_at__gt=purge_cutoff,
        deletion_reminder_sent_at__isnull=True,
    ).filter(Q(deletion_reminder_queued_at__isnull=True) | Q(deletion_reminder_queued_at__lt=lease_cutoff))

    queued = 0
    for user in queryset:
        claimed = User.objects.filter(
            pk=user.pk,
            deletion_reminder_sent_at__isnull=True,
            deletion_reminder_queued_at=user.deletion_reminder_queued_at,
        ).update(deletion_reminder_queued_at=now, updated_at=now)
        if not claimed:
            continue
        send_deletion_reminder_email_task.delay(user_id=user.pk, days_remaining=days_remaining)
        queued += 1

    return f"Queued {queued} deletion reminder email(s)"


@shared_task(name="tasks.purge_deactivated_accounts_task")
def purge_deactivated_accounts_task():
    """
    Daily sweep: permanently deletes accounts that have been deactivated for
    longer than Constants.ACCOUNT_DELETION_GRACE_DAYS. Support can reactivate
    a deactivated account any time before this runs; past the grace period
    the deletion is final and cascades to the owner's cars, service history,
    expenses, reminders and inspections. Each owner's Cloudinary-hosted car
    photos are removed too (the cascade only touches DB rows, not the actual
    hosted images), and a final "your data is gone" email goes out first —
    there's no address left to send to once the row is deleted.
    """
    from django.utils import timezone

    from accounts.models import User
    from utils import Constants
    from utils.Cloudinary import delete_photos
    from utils.Email import send_account_deleted_email

    cutoff = timezone.now() - timezone.timedelta(days=Constants.ACCOUNT_DELETION_GRACE_DAYS)
    queryset = User.objects.filter(
        is_active=False,
        is_email_verified=True,
        deactivated_at__isnull=False,
        deactivated_at__lte=cutoff,
    ).prefetch_related("cars")

    count = 0
    for user in queryset:
        delete_photos([car.photo_url for car in user.cars.all() if car.photo_url])
        send_account_deleted_email(email=user.email, first_name=user.first_name)
        user.delete()
        count += 1

    return f"Purged {count} deactivated account(s) and their data"


@shared_task(name="tasks.send_duplicate_signup_email_task")
def send_duplicate_signup_email_task(email, first_name=""):
    from utils.Email import send_duplicate_signup_email

    send_duplicate_signup_email(email=email, first_name=first_name)


@shared_task(name="tasks.send_verify_reminder_email_task")
def send_verify_reminder_email_task(user_id, days_remaining):
    """
    Sends one account's email-verification reminder — with a fresh OTP,
    since the original issued at signup has long since expired — and, only on
    success, confirms it by setting verify_reminder_sent_at. Dispatched
    (never called inline) by send_email_verification_reminder_task so one
    account's failure can't crash the rest of that day's batch, same as the
    mileage and deletion reminders (see #27). A failure here is logged and
    left for the next sweep to notice the still-stale claim and retry.
    """
    from django.utils import timezone

    from accounts.models import User, EmailVerificationOTP
    from utils.Email import send_verify_email_reminder_email

    # Re-checks is_email_verified/verify_reminder_sent_at at send time, not
    # just at claim time: the account may have verified (or already been sent
    # this reminder by a reclaim of a stale lease) since this task was queued.
    user = User.objects.filter(pk=user_id, is_email_verified=False, verify_reminder_sent_at__isnull=True).first()
    if user is None:
        return

    _, raw_otp = EmailVerificationOTP.create_for_user(user)

    try:
        send_verify_email_reminder_email(
            email=user.email, otp=raw_otp, first_name=user.first_name, days_remaining=days_remaining
        )
    except Exception:
        logger.error(
            "Failed to send verify reminder to user_id=%s; will retry on a later sweep", user_id, exc_info=True
        )
        return

    User.objects.filter(pk=user_id).update(
        verify_reminder_sent_at=timezone.now(),
        verify_reminder_queued_at=None,
        updated_at=timezone.now(),
    )


@shared_task(name="tasks.send_email_verification_reminder_task")
def send_email_verification_reminder_task():
    """
    Daily sweep: emails signups whose account is still unverified
    Constants.EMAIL_VERIFY_REMINDER_DAYS after they registered, nudging them
    to finish verifying before the account is removed.

    Claims each eligible account via verify_reminder_queued_at — a lease, not
    a delivery confirmation — then dispatches the actual send as its own task
    (send_verify_reminder_email_task), which alone sets verify_reminder_sent_at
    once the send actually succeeds. A claim whose send never confirms goes
    stale after Constants.REMINDER_CLAIM_LEASE_HOURS and gets reclaimed by a
    later sweep. See #27, #23.
    """
    from django.db.models import Q
    from django.utils import timezone

    from accounts.models import User
    from utils import Constants

    now = timezone.now()
    cutoff = now - timezone.timedelta(days=Constants.EMAIL_VERIFY_REMINDER_DAYS)
    # Excludes accounts already eligible for the purge sweep: this task and
    # purge_unverified_accounts_task both run daily with no ordering
    # guarantee, so without this an account past the 15-day cutoff could get
    # a misleading "N days left" nudge right as, or after, it's deleted.
    purge_cutoff = now - timezone.timedelta(days=Constants.EMAIL_VERIFY_PURGE_DAYS)
    lease_cutoff = now - timezone.timedelta(hours=Constants.REMINDER_CLAIM_LEASE_HOURS)
    days_remaining = Constants.EMAIL_VERIFY_PURGE_DAYS - Constants.EMAIL_VERIFY_REMINDER_DAYS

    queryset = User.objects.filter(
        is_email_verified=False,
        date_joined__lte=cutoff,
        date_joined__gt=purge_cutoff,
        verify_reminder_sent_at__isnull=True,
    ).filter(Q(verify_reminder_queued_at__isnull=True) | Q(verify_reminder_queued_at__lt=lease_cutoff))

    queued = 0
    for user in queryset:
        claimed = User.objects.filter(
            pk=user.pk,
            verify_reminder_sent_at__isnull=True,
            verify_reminder_queued_at=user.verify_reminder_queued_at,
        ).update(verify_reminder_queued_at=now, updated_at=now)
        if not claimed:
            continue
        send_verify_reminder_email_task.delay(user_id=user.pk, days_remaining=days_remaining)
        queued += 1

    return f"Queued {queued} verification reminder email(s)"


@shared_task(name="tasks.send_monthly_expense_report_email_task")
def send_monthly_expense_report_email_task(user_id, year, month):
    """
    Builds and sends one user's monthly expense digest for `year`/`month`,
    dispatched (never called inline) by send_monthly_expense_reports_task so
    one user's failure can't crash the rest of that sweep — see #27.

    Claims a MonthlyExpenseReportDelivery row before sending (atomically,
    via its unique constraint) and only confirms it (sent_at) once the send
    actually succeeds — same claim-then-confirm shape as the mileage/
    deletion/verify reminder tasks (see #27), just per period instead of per
    mutable column. This is what stops two concurrent or redelivered
    executions for the same (user, year, month) from both proceeding to
    send: whichever loses the race to claim (or finds an unexpired claim
    already held) returns immediately rather than sending a duplicate.
    """
    from django.db import IntegrityError, transaction
    from django.utils import timezone

    from accounts.models import User
    from expenses.models import MonthlyExpenseReportDelivery
    from expenses.reports import build_monthly_report
    from utils import Constants
    from utils.Email import send_monthly_expense_report_email

    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return

    report = build_monthly_report(user, year, month)
    # Re-checked here rather than trusted from the sweep's queryset: cheap
    # insurance against a stale/incorrect caller, and the sweep already did
    # the real filtering to avoid queuing this task for zero-expense users.
    if report["count"] == 0:
        return

    now = timezone.now()
    lease_cutoff = now - timezone.timedelta(hours=Constants.REMINDER_CLAIM_LEASE_HOURS)

    try:
        # Wrapped in its own savepoint: an IntegrityError otherwise leaves
        # the connection unusable for the queries in the except branch below.
        with transaction.atomic():
            delivery = MonthlyExpenseReportDelivery.objects.create(
                user_id=user_id, year=year, month=month, queued_at=now
            )
    except IntegrityError:
        # A row for this period already exists — either already sent, or
        # another execution's claim on it is still live. Only a stale
        # (unsent, lease-expired) claim is worth reclaiming.
        claimed = MonthlyExpenseReportDelivery.objects.filter(
            user_id=user_id,
            year=year,
            month=month,
            sent_at__isnull=True,
            queued_at__lt=lease_cutoff,
        ).update(queued_at=now)
        if not claimed:
            return
        delivery = MonthlyExpenseReportDelivery.objects.get(user_id=user_id, year=year, month=month)

    try:
        send_monthly_expense_report_email(email=user.email, first_name=user.first_name, report=report)
    except Exception:
        logger.error(
            "Failed to send monthly expense report to user_id=%s for %s-%s", user_id, year, month, exc_info=True
        )
        return

    MonthlyExpenseReportDelivery.objects.filter(pk=delivery.pk).update(sent_at=timezone.now())


@shared_task(name="tasks.send_monthly_expense_reports_task")
def send_monthly_expense_reports_task():
    """
    Runs on the 1st of each month (CELERY_BEAT_SCHEDULE): finds every active
    user who logged at least one expense last calendar month — and doesn't
    already have a *confirmed* MonthlyExpenseReportDelivery for it — and
    queues them a digest email. Users with nothing spent are skipped
    entirely — no "nothing spent" email, see #21. Excluding only confirmed
    (sent_at is set) deliveries, rather than any row at all, is what makes
    this sweep safe to re-run for the same period: anyone whose earlier
    claim never got confirmed (a crash, a still-failing send) gets
    re-queued instead of being mistaken for already delivered.
    """
    from django.utils import timezone

    from accounts.models import User
    from expenses.models import MonthlyExpenseReportDelivery

    today = timezone.localdate()
    prev_year, prev_month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)

    # Deliberately not `.exclude(monthly_expense_report_deliveries__year=...,
    # ...__month=..., ...__sent_at__isnull=False)`: exclude() with multiple
    # conditions on a multi-valued (reverse-FK) relation does NOT require
    # them to hold on the same related row — it can match year on one
    # delivery and month on an entirely different one — so a user with any
    # confirmed delivery in the same year, in a different month, would be
    # wrongly excluded here. The subquery below pins all three conditions to
    # one row, same as Django's documented workaround for this gotcha.
    already_delivered = MonthlyExpenseReportDelivery.objects.filter(
        year=prev_year, month=prev_month, sent_at__isnull=False
    ).values("user_id")

    user_ids = (
        User.objects.filter(
            is_active=True,
            cars__expenses__expense_date__year=prev_year,
            cars__expenses__expense_date__month=prev_month,
        )
        .exclude(pk__in=already_delivered)
        .distinct()
        .values_list("pk", flat=True)
    )

    queued = 0
    for user_id in user_ids:
        send_monthly_expense_report_email_task.delay(user_id=user_id, year=prev_year, month=prev_month)
        queued += 1

    return f"Queued {queued} monthly expense report email(s)"


@shared_task(name="tasks.purge_unverified_accounts_task")
def purge_unverified_accounts_task():
    """
    Daily sweep: permanently deletes accounts that are still unverified
    Constants.EMAIL_VERIFY_PURGE_DAYS after they registered. Unlike
    purge_deactivated_accounts_task, there's no reactivate window and no
    goodbye email — the account was never confirmed as real to begin with.
    Login rejects unverified accounts (accounts.serializers.LoginSerializer),
    so an unverified account can never have reached the dashboard to add a
    car, meaning there's no Cloudinary cleanup needed here either.
    """
    from django.utils import timezone

    from accounts.models import User
    from utils import Constants

    cutoff = timezone.now() - timezone.timedelta(days=Constants.EMAIL_VERIFY_PURGE_DAYS)
    # Deleted one row at a time (re-checking is_email_verified=False on each
    # delete) rather than a single bulk queryset.delete(): the bulk form
    # collects matching rows up front and deletes them by pk afterward, so a
    # user who verifies in the gap between collection and the delete
    # statement would still get purged. This shrinks that race to the delete
    # of a single already-stale row instead of the whole day's batch.
    candidate_ids = list(
        User.objects.filter(is_email_verified=False, date_joined__lte=cutoff).values_list("pk", flat=True)
    )
    count = 0
    for user_id in candidate_ids:
        deleted, _ = User.objects.filter(pk=user_id, is_email_verified=False).delete()
        if deleted:
            count += 1

    return f"Purged {count} never-verified account(s)"
