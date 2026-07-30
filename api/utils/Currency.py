CURRENCY_SYMBOLS = {
    "UGX": "USh", "KES": "KSh", "TZS": "TSh", "RWF": "RF", "NGN": "₦",
    "GHS": "GH₵", "ZAR": "R", "EGP": "E£", "USD": "$", "GBP": "£",
    "EUR": "€", "INR": "₹", "AED": "AED", "CAD": "CA$", "AUD": "A$",
}

# Currencies whose minor unit isn't used in everyday display.
ZERO_DECIMAL_CURRENCIES = {"UGX", "RWF"}


def format_amount(amount, currency_code):
    """
    Renders a money amount for server-rendered surfaces (the monthly report
    email/PDF — see #40) where there's no Intl.NumberFormat to lean on like
    the frontend has. Falls back to a bare, symbol-less number when
    currency_code is unset or unrecognized — same as the pre-#40 behavior,
    which pre-existing accounts and records keep until they get a currency.
    """
    decimals = 0 if currency_code in ZERO_DECIMAL_CURRENCIES else 2
    formatted_number = f"{float(amount):,.{decimals}f}"
    symbol = CURRENCY_SYMBOLS.get(currency_code)
    if not symbol:
        return formatted_number
    return f"{symbol} {formatted_number}"


def load_latest_rates():
    """
    {currency: Decimal rate_to_usd}, one entry per currency using its most
    recently fetched ExchangeRate row (see #40's refresh_exchange_rates_task,
    which runs daily). A currency that's never been fetched yet (task
    hasn't run, or the API dropped it that day) is simply absent —
    convert_amount() treats that as "can't convert" and returns the amount
    unchanged, same as an unset currency.

    Filters to the latest row per currency at the DB layer (rather than
    loading and sorting the whole audit table in Python) since this runs on
    essentially every expense/service request.
    """
    from django.db.models import OuterRef, Subquery

    from expenses.models import ExchangeRate

    latest_id_per_currency = (
        ExchangeRate.objects.filter(currency=OuterRef("currency")).order_by("-date").values("pk")[:1]
    )
    rows = ExchangeRate.objects.filter(pk=Subquery(latest_id_per_currency))
    return {row.currency: row.rate_to_usd for row in rows}


def convert_amount(amount, from_currency, to_currency, rates):
    """
    Converts `amount` from `from_currency` to `to_currency` through USD as
    the common pivot, always using the *latest* known rate for each — not
    the rate in effect on the transaction's own date. That's a deliberate
    simplification (see #40): it matches how most personal-finance apps
    show "what this is worth in my currency today" rather than tracking
    historical FX drift per transaction, and avoids needing a rate lookup
    keyed on every expense's individual date.

    Falls back to returning `amount` completely unconverted whenever either
    currency is blank (unset) or has no known rate yet — the same
    "no currency, show a bare number" fallback #40 established for
    formatting in general.
    """
    if not from_currency or not to_currency or from_currency == to_currency:
        return amount
    from_rate = rates.get(from_currency)
    to_rate = rates.get(to_currency)
    if not from_rate or not to_rate:
        return amount
    return amount * from_rate / to_rate
