"""
Color System - Source of Truth
Provides centralized color definitions for the application's widgets.
"""

# Color tokens
COLOR_EMPTY    = "#555555"  # Grey - 0%
COLOR_LOW      = "#2196f3"  # Blue - 0-10%
COLOR_MEDIUM   = "#ffeb3b"  # Yellow - 10-25%
COLOR_HIGH     = "#ff9800"  # Orange - 25-50%
COLOR_CRITICAL = "#f44336"  # Red - 50%+

def color_for_percentage(pct: float) -> str:
    """Returns the color hex string based on percentage volume."""
    if pct <= 0.0:
        return COLOR_EMPTY
    elif pct <= 10.0:
        return COLOR_LOW
    elif pct <= 25.0:
        return COLOR_MEDIUM
    elif pct <= 50.0:
        return COLOR_HIGH
    else:
        return COLOR_CRITICAL

        
