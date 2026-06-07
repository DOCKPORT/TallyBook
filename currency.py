"""
Pure currency formatting and conversion utilities for TallyBook.

Provides formatting functions with no Qt dependencies.
Extracted from TallyBookWindow._format_number_as_currency,
_format_percentage, _to_internal, and _from_internal.
"""

from decimal import Decimal, ROUND_HALF_UP


def format_number_as_currency(
    value: float, symbol: str, decimals: int, include_symbol: bool = True
) -> str:
    """Formats a numeric value as a currency string, handling negative zero.

    Args:
        value: The numeric value to format.
        symbol: The currency symbol to prepend (e.g. "$", "€").
        decimals: Number of decimal places to display.
        include_symbol: Whether to include the currency symbol.

    Returns:
        Formatted currency string.
    """
    if abs(value) < 1e-9:  # Treat very small numbers as zero
        formatted_value = f"{0.0:,.{decimals}f}"
    else:
        formatted_value = f"{value:,.{decimals}f}"

    if include_symbol:
        return f"{symbol} {formatted_value}"
    return formatted_value


def format_percentage(value: float) -> str:
    """Formats a numeric value as a percentage string, handling negative zero.

    Args:
        value: The numeric value (e.g. 12.5 for 12.50%).

    Returns:
        Formatted percentage string with two decimal places.
    """
    if abs(value) < 1e-6:
        return "0.00%"
    return f"{value:.2f}%"


def to_internal(amount_float: float) -> int:
    """Converts a UI float to a database integer (cents).

    Args:
        amount_float: The float value from the UI.

    Returns:
        The value as integer cents.
    """
    if amount_float is None:
        return 0
    return int(
        Decimal(str(round(amount_float, 2)))
        .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        * 100
    )


def from_internal(amount_int: int) -> float:
    """Converts a database integer (cents) to a UI float.

    Args:
        amount_int: The integer value from the database (cents).

    Returns:
        The value as a float.
    """
    if amount_int is None:
        return 0.0
    return float(Decimal(amount_int) / 100)