from django import template

from utils.Currency import format_amount

register = template.Library()


@register.filter(name="currency")
def currency(amount, currency_code):
    """Renders `amount` with the owner's currency symbol — see #40."""
    return format_amount(amount, currency_code)
