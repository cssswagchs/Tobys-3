# utils/theme.py
from tkinter import ttk
import tkinter as tk

# Pull in your brand colors
try:
    from tobys_terminal.shared.css_swag_colors import (
        FOREST_GREEN, PALM_GREEN, CORAL_ORANGE,
        COCONUT_CREAM, TAN_SAND, PALM_BARK
    )
except Exception:
    # Sensible fallbacks if the palette module isn't found
    FOREST_GREEN = "#0d5744"
    PALM_GREEN = "#127b5f"
    CORAL_ORANGE = "#da674e"
    COCONUT_CREAM = "#fefaf2"
    TAN_SAND = "#e4c193"
    PALM_BARK = "#a45f2b"

def apply_theme(root: tk.Misc, *, large=False, base_bg="auto"):
    """
    Apply brand-aware ttk styling + widget defaults.
    - large=True bumps font sizes a bit.
    - base_bg: 'coconut', 'sand', 'auto' (auto picks coconut).
    """
    style = ttk.Style(root)
    # Reliable base theme to style over
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Base fonts
    import tkinter.font as tkfont
    base = tkfont.nametofont("TkDefaultFont")
    size = 11 if large else 10
    base.configure(size=size)
    root.option_add("*Font", base)

    heading = tkfont.Font(family=base.cget("family"), size=size+2, weight="bold")

    # Choose a subtle paper-like background
    if base_bg == "sand":
        paper = TAN_SAND
    else:
        paper = COCONUT_CREAM  # auto/coconut default

    # Window background
    root.configure(bg=paper)
    style.configure(".", background=paper)

    # Buttons
    style.configure(
        "Swag.TButton",
        padding=(10, 6),
        foreground="white",
        background=FOREST_GREEN,
        borderwidth=0,
        focuscolor=paper
    )
    style.map(
        "Swag.TButton",
        background=[("active", PALM_GREEN), ("pressed", PALM_GREEN)],
        relief=[("pressed", "sunken"), ("!pressed", "flat")]
    )

    # Secondary buttons (accent)
    style.configure(
        "Accent.Swag.TButton",
        padding=(10, 6),
        foreground="white",
        background=CORAL_ORANGE,
        borderwidth=0
    )
    style.map("Accent.Swag.TButton", background=[("active", CORAL_ORANGE)])

    # Labels
    style.configure("Swag.TLabel", background=paper)
    style.configure("Title.Swag.TLabel", background=paper, font=heading, foreground=FOREST_GREEN)

    # Frames / Labelframes
    style.configure("Swag.TFrame", background=paper)
    style.configure("Swag.TLabelframe", background=paper)
    style.configure("Swag.TLabelframe.Label", background=paper, foreground=PALM_BARK)

    # Entry / Combobox
    style.configure("Swag.TEntry", padding=(6, 4))
    style.configure("Swag.TCombobox", padding=(4, 2))

    # Treeview (zebra + selection)
    style.configure(
        "Swag.Treeview",
        rowheight=26,
        borderwidth=0,
        background="white",
        fieldbackground="white"
    )
    style.configure("Swag.Treeview.Heading", font=(base.cget("family"), size, "bold"))

    # Selection colors: light mint on brand green outline
    style.map(
        "Swag.Treeview",
        background=[("selected", "#e8f6f1")],
        foreground=[("selected", "black")]
    )

    # Tiny helpers on the root for easy reuse
    if not hasattr(root, "_swag"):
        root._swag = {}
    root._swag["paper"] = paper

def zebra_tree(tree: ttk.Treeview):
    """Apply zebra striping to an existing Treeview after inserts."""
    tree.tag_configure("odd", background="#f7f7fb")
    tree.tag_configure("even", background="#ffffff")
    # re-tag current rows
    for i, iid in enumerate(tree.get_children(""), start=1):
        tree.item(iid, tags=("even",) if i % 2 == 0 else ("odd",))

def style_tree_columns(tree: ttk.Treeview, widths: dict | None = None):
    """Set sensible widths and anchors."""
    for col in tree["columns"]:
        w = 140
        if widths and col in widths:
            w = widths[col]
        tree.heading(col, text=col)
        tree.column(col, width=w, anchor="w")
