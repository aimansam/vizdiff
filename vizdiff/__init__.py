"""vizdiff -- Spot-the-difference visual regression CLI.

Compares two images or two directories of screenshots and produces
side-by-side diffs, highlighted difference regions, and similarity scores.
"""

__version__ = "1.0.0"
__all__ = ["compute_diff", "DiffResult", "terminal_report", "html_report"]

from .differ import compute_diff, DiffResult
from .report import terminal_report, html_report
