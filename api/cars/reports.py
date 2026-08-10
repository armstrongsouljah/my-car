from django.utils import timezone

from utils import Constants

# See #62 — insurance/tax/fuel are ownership cost, not upkeep evidence; only
# these two categories count as "maintenance" for the shareable report.
MAINTENANCE_EXPENSE_CATEGORIES = [
    Constants.EXPENSE_CATEGORY_GARAGE,
    Constants.EXPENSE_CATEGORY_PARTS,
]


def build_service_history_report(car):
    """
    Everything maintenance-relevant logged for one car, for the shareable
    "proof of upkeep" PDF (see #62). Each record shows its own logged
    amount/currency as-is -- unlike the expense reports (expenses/reports.py)
    this never aggregates or FX-converts, so there's no need to reconcile
    records logged in different currencies.
    """
    expenses = car.expenses.filter(
        category__in=MAINTENANCE_EXPENSE_CATEGORIES,
        # A costed ServiceRecord auto-generates a linked Expense (see
        # ServiceRecord._sync_expense) so it shows up in the expense log --
        # already represented below via service_records, so including it
        # here too would double it up on this report.
        service_record__isnull=True,
    )

    return {
        "car": car,
        "service_records": car.service_records.all(),
        "inspections": car.inspections.all(),
        "expenses": expenses,
        "generated_at": timezone.now(),
    }
