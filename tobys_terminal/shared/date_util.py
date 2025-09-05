# shared/date_util.py

from tkcalendar import DateEntry
from datetime import datetime
import sys
import os
from tobys_terminal.shared.css_swag_colors import FOREST_GREEN, PALM_GREEN, CORAL_ORANGE, COCONUT_CREAM, TAN_SAND


def create_date_picker(parent, width=12):
    return DateEntry(
        parent,
        width=width,
        background=FOREST_GREEN,         # Header background
        foreground="white",              # Text color
        borderwidth=2,
        headersbackground=COCONUT_CREAM, # Header row (days of week)
        normalbackground=COCONUT_CREAM,  # Default cell background
        weekendbackground=TAN_SAND,      # Slightly different weekend bg
        selectbackground=CORAL_ORANGE,   # Selected date highlight
        selectforeground="white",        # Selected text
        date_pattern='yyyy-mm-dd',
        disabledbackground="#ddd",       # Optional: for future use
    )


def parse_date_input(date_str):
    # Tries multiple formats and returns a formatted date or None
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

def safe_set_date(date_entry, raw_val):
    """Safely set a parsed date in a DateEntry field. Leaves blank if invalid or empty."""
    from tkinter import END

    try:
        parsed = parse_date_input(raw_val)
        if parsed:
            date_entry.set_date(parsed)
        else:
            date_entry.delete(0, END)
    except:
        date_entry.delete(0, END)

from tkcalendar import DateEntry

def create_calendar_entry(parent, default=None):
    try:
        # If a valid date is provided, use it
        entry = DateEntry(parent, width=14, date_pattern="yyyy-mm-dd")
        if default:
            entry.set_date(default)
    except Exception:
        # If the default can't be parsed or is empty, do nothing
        pass
    return entry
