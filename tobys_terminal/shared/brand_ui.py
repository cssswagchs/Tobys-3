# utils/brand_ui.py
from tkinter import ttk
import tkinter as tk

# Your brand colors
from tobys_terminal.shared.css_swag_colors import (
    FOREST_GREEN, PALM_GREEN, CORAL_ORANGE,
    COCONUT_CREAM, TAN_SAND, PALM_BARK
)

def apply_brand(root: tk.Misc, *, sand_bg=False, large_title=False):
    """Apply Sage-style ttk theme to a window."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    import tkinter.font as tkfont
    base = tkfont.nametofont("TkDefaultFont")
    base.configure(size=11)
    root.option_add("*Font", base)

    title_font = tkfont.Font(
        family=base.cget("family"),
        size=18 if large_title else 16,
        weight="bold"
    )

    # DEFAULT: coconut cream, unless sand_bg=True
    paper = TAN_SAND if sand_bg else COCONUT_CREAM
    root.configure(bg=paper)
    style.configure(".", background=paper)

    if not hasattr(root, "_swag"):
        root._swag = {}
    root._swag["paper"] = paper

    # Primary button (green)
    style.configure("Primary.TButton", padding=(12, 7),
                    background=FOREST_GREEN, foreground="white",
                    borderwidth=0)
    style.map("Primary.TButton",
              background=[("active", PALM_GREEN), ("pressed", PALM_GREEN)])

    # Accent button (coral)
    style.configure("Accent.TButton", padding=(12, 7),
                    background=CORAL_ORANGE, foreground="white",
                    borderwidth=0)
    style.map("Accent.TButton", background=[("active", CORAL_ORANGE)])

    # Cards / group boxes
    style.configure("Card.TFrame", background=paper)
    style.configure("Card.TLabelframe", background=paper)
    style.configure("Card.TLabelframe.Label", background=paper, foreground=PALM_BARK)

    # Header labels
    style.configure("Header.TLabel", background=paper,
                    foreground=FOREST_GREEN, font=title_font)
    style.configure("Subheader.TLabel", background=paper,
                    foreground=PALM_BARK)

    # Table
    style.configure("Sage.Treeview", rowheight=26,
                    background="white", fieldbackground="white", borderwidth=0)
    style.configure("Sage.Treeview.Heading", font=(base.cget("family"), 11, "bold"))
    style.map("Sage.Treeview",
              background=[("selected", "#e8f6f1")],  # gentle mint
              foreground=[("selected", "black")])

def make_header(parent, title, subtitle=None, icon_text="🐢"):
    """A Sage-like header bar with title + optional subtitle."""
    f = ttk.Frame(parent, style="Card.TFrame", padding=(6, 10, 6, 6))
    # icon + title row
    row = ttk.Frame(f, style="Card.TFrame")
    row.pack(fill="x")
    ttk.Label(row, text=icon_text, style="Header.TLabel").pack(side="left", padx=(0, 6))
    ttk.Label(row, text=title, style="Header.TLabel").pack(side="left")
    if subtitle:
        ttk.Label(f, text=subtitle, style="Subheader.TLabel").pack(anchor="w", pady=(2, 0))
    return f

def zebra_tree(tree: ttk.Treeview):
    """Apply zebra striping to a populated Treeview."""
    tree.tag_configure("odd", background="#f7f2ea")  # sandy tint
    tree.tag_configure("even", background="#ffffff")
    for i, iid in enumerate(tree.get_children(""), start=1):
        tree.item(iid, tags=("even",) if i % 2 == 0 else ("odd",))
