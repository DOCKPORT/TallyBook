"""
DPI-aware scaling utilities for TallyBook.

Provides pure functions to calculate screen-based scale factors
and scale pixel values, extracted from TallyBookWindow and widgets.
"""

def calculate_scale_factor(screen_width: int, screen_height: int) -> float:
    """Calculate DPI scale factor based on a 1920x1080 reference resolution.

    Uses the smaller dimension ratio to ensure the UI fits entirely on screen.
    Clamps to a minimum of 0.8 to prevent unreadably small UI elements.

    Args:
        screen_width: Screen resolution width in pixels.
        screen_height: Screen resolution height in pixels.

    Returns:
        Scale factor clamped to [0.8, ∞).
    """
    factor = min(screen_width / 1920, screen_height / 1080)
    return max(0.8, factor)


def scaled(scale_factor: float, value: int) -> int:
    """Scale a base pixel value by the given factor.

    Args:
        scale_factor: The DPI scale factor to apply.
        value: The base pixel value (typically from a 1920x1080 reference).

    Returns:
        The scaled pixel value as an integer.
    """
    return int(value * scale_factor)