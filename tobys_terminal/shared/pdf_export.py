"""
PDF export functionality for Toby's Terminal application.
Handles statement generation, production reports, and other PDF exports.
"""

# Standard library imports
import os
import re
import sqlite3
from datetime import datetime
from collections import defaultdict
from copy import deepcopy
from  tobys_terminal.shared.css_swag_colors import FOREST_GREEN, PALM_GREEN, CORAL_ORANGE, COCONUT_CREAM, TAN_SAND, PALM_BARK
# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas as _canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, KeepTogether
)
from reportlab.pdfbase.pdfmetrics import stringWidth

from pathlib import Path
    
from tobys_terminal.shared.db import get_connection
from config import PROJECT_ROOT  # Import PROJECT_ROOT from config




# Tkinter imports (for interactive mode)
from tkinter import messagebox

# Package resource handling
try:
    # For Python 3.9+
    from importlib.resources import files
    ASSETS_DIR = str(files('tobys_terminal.shared.assets'))
    EXPORTS_BASE_DIR = str(files('tobys_terminal.shared.exports'))
except (ImportError, AttributeError):
    # Fallback for older Python versions
    import pkg_resources
    ASSETS_DIR = pkg_resources.resource_filename('tobys_terminal.shared', 'assets')
    EXPORTS_BASE_DIR = pkg_resources.resource_filename('tobys_terminal.shared', 'exports')

# Local imports
from tobys_terminal.shared.db import get_connection


# Helper functions for text formatting
def wrap_po_if_needed(po_number, font="Helvetica", font_size=10, max_width=1.2 * inch):
    """Wrap PO numbers that are too long to fit in a cell."""
    if not po_number:
        return ""

    po_number = str(po_number).strip()
    width = stringWidth(po_number, font, font_size)
    if width <= max_width:
        return po_number

    # Try to find a good split point near 2/3 length
    preferred_split = int(len(po_number) * 0.66)

    # Start from preferred_split and walk backward to find a natural break
    for i in range(preferred_split, 0, -1):
        part1 = po_number[:i]
        part2 = po_number[i:]
        if stringWidth(part1, font, font_size) <= max_width and stringWidth(part2, font, font_size) <= max_width:
            return f"{part1}\n{part2}"

    # Fallback if nothing found: just split somewhere safe
    mid = len(po_number) // 2
    return f"{po_number[:mid]}\n{po_number[mid:]}"


def wrap_status_if_needed(status_text, font="Helvetica", font_size=10, max_width=1.0 * inch):
    """Wrap status text that is too long to fit in a cell."""
    if not status_text:
        return ""
    status_text = str(status_text).strip()
    width = stringWidth(status_text, font, font_size)
    if width <= max_width:
        return status_text
    else:
        # Try breaking at the plus sign (for "+x more") if it's there
        if "+ " in status_text or "+1" in status_text:
            parts = status_text.split("+", 1)
            return f"{parts[0].strip()}\n+{parts[1].strip()}"
        elif "-" in status_text:
            parts = status_text.split("-", 1)
            return f"{parts[0].strip()} –\n{parts[1].strip()}"
        # Fallback: split in half
        mid = len(status_text) // 2
        return f"{status_text[:mid]}\n{status_text[mid:]}"


# Main PDF generation functions
def generate_pdf(customer_name, rows, totals, start_date, end_date, statement_number, nickname=None, output_path=None, interactive=True):
    """Generate a customer statement PDF."""
    # Helper function for number conversion
    def _num(x):
        try:
            return float(x or 0)
        except Exception:
            return 0.0
            
    # ---------- filename / path ----------
    safe_name  = re.sub(r'[^a-zA-Z0-9_-]', '_', customer_name)
    safe_start = (start_date or "").replace("/", "-")
    safe_end   = (end_date or "").replace("/", "-")
    date_str   = f"{safe_start}_to_{safe_end}" if safe_start and safe_end else "Full_Range"

    # Use the EXPORTS_BASE_DIR defined at the top
    EXPORTS_DIR = os.path.join(EXPORTS_BASE_DIR, "statements", safe_name)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    filename = f"{statement_number}_statement_{safe_name}_{date_str}.pdf"
    filepath = os.path.join(EXPORTS_DIR, filename)

    if interactive:
        # Prompt before overwriting (Tkinter app)
        if os.path.exists(filepath):
            overwrite = messagebox.askyesno(
                "Replace File?",
                f"The file already exists:\n\n{filename}\n\n"
                "Do you want to replace it?"
            )
            if not overwrite:
                return None
    else:
        # Web/portal mode → move old version to "dnu" folder before overwriting
        if os.path.exists(filepath):
            DNU_DIR = os.path.join(EXPORTS_DIR, "dnu")
            os.makedirs(DNU_DIR, exist_ok=True)
            archived_name = f"{filename.replace('.pdf', '')}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
            archived_path = os.path.join(DNU_DIR, archived_name)
            os.rename(filepath, archived_path)

    # ---------- doc / styles ----------
    doc = SimpleDocTemplate(
        filepath,
        pagesize=LETTER,
        leftMargin=50,
        rightMargin=50,
        topMargin=40,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    unpaid_rows, paid_rows = [], []
    
    # ---------- helper: totals normalize ----------
    def _normalize_totals(_rows, _totals):
        if not _totals:
            billed = sum(_num(r[4]) for r in _rows if r[1] == "Invoice")
            paid   = sum(_num(r[4]) for r in _rows if r[1] == "Payment")
            _totals = {"billed": billed, "paid": paid}
        else:
            _totals["billed"] = _num(_totals.get("billed", 0) or 0)
            _totals["paid"]   = _num(_totals.get("paid",   0) or 0)
        _totals["balance"] = _num(_totals.get("balance", _totals["billed"] - _totals["paid"]))
        return _totals

    # ---------- merge payments into invoice status (keep only unique ref) ----------
    unpaid_rows, paid_rows = [], []
    pay_index = defaultdict(list)
    for r in rows:
        dt, typ, inv = r[0], r[1], r[2]
        if str(typ) == "Payment":
            label = str(r[-1] or "").strip()
            label = re.sub(r'^(?:credit\s*card|bank\s*transfer)\s+', '', label, flags=re.I).strip()
            if label:
                pay_index[inv].append(label)

    # Build invoice display rows
    unpaid_rows, paid_rows = [], []
    for r in rows:
        if str(r[1]) != "Invoice":
            continue
        dt, _, inv, po, nick, amt, paid_flag_or_status = r
        date_str2 = dt.strftime("%m/%d/%Y") if hasattr(dt, "strftime") else str(dt)
        nick_short = (nick[:22] + "...") if nick and len(nick) > 22 else (nick or "")
        amt_str = f"${_num(amt):,.2f}"

        pays = pay_index.get(inv, [])
        if pays:
            first = pays[0]
            more  = f" (+{len(pays)-1} more)" if len(pays) > 1 else ""
            merged_status = f"Paid - {first}{more}"
        else:
            merged_status = "Paid" if str(paid_flag_or_status).lower().startswith("paid") else "Unpaid"

        wrapped_po = wrap_po_if_needed(po or "")
        wrapped_status = wrap_status_if_needed(merged_status)
        row = [date_str2, inv, wrapped_po, nick_short, amt_str, wrapped_status]

        (paid_rows if merged_status.startswith("Paid") else unpaid_rows).append(row)

    # Build data rows WITHOUT bottom totals for now; we'll decide after pass 1
    header_row = ["Date", "Inv. #", "PO #", "Nickname", "Amount", "Status"]
    base_rows = [header_row] + unpaid_rows + paid_rows

    # ---------- compute totals once ----------
    totals = _normalize_totals(rows, totals)

    # ---------- masthead (tight grid that matches the table width = 6.4")
    TABLE_W = 6.4 * inch     # your table colWidths sum: 1 + 1 + 2.2 + 1.2 + 1 = 6.4"
    COL_L  = 3.2 * inch      # split 50/50 so masthead width == table width
    COL_R  = 3.2 * inch

    # Left cell: logo + address (mini-table)
    left_rows = []
    try:
        logo_path = os.path.join(ASSETS_DIR, "logo.png")
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=110, height=55)
            left_rows.append([logo])
        else:
            print(f"⚠️ Logo not found at: {logo_path}")
    except Exception as e:
        print(f"⚠️ Logo load error: {e}")
        pass
    
    addr_style = styles["BodyText"]; addr_style.fontSize = 9
    left_rows += [
        [Paragraph("<b>CSS Embroidery & Print</b>", styles["Heading4"])],
        [Paragraph("1855 Belgrade Avenue", addr_style)],
        [Paragraph("Charleston, SC 29407", addr_style)],
        [Paragraph("Phone: (843) 763-2290", addr_style)],
    ]
    left_col = Table(left_rows, colWidths=[COL_L])
    left_col.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 0),
    ]))

    # Right cell: title + meta as a tidy 2-col table
    title_style = styles["Title"]
    meta_style  = styles["Normal"]; meta_style.spaceAfter = 1

    kv = [
        # First row: title spanning both columns
        [Paragraph("<b>Customer Statement</b>", title_style), ""],
        [Paragraph("<b> </b>", title_style), ""],
        [Paragraph("<b> </b>", title_style), ""],
        [Paragraph("<b>Customer:</b>", meta_style), Paragraph(customer_name, meta_style)],
    ]
    if statement_number:
        kv.append([Paragraph("<b>Statement #:</b>", meta_style), Paragraph(str(statement_number), meta_style)])
    if start_date and end_date:
        kv.append([Paragraph("<b>Date Range:</b>", meta_style), Paragraph(f"{start_date} to {end_date}", meta_style)])
    else:
        kv.append([Paragraph("<b>Statement Date:</b>", meta_style),
                Paragraph(f"{datetime.now():%m/%d/%Y}", meta_style)])

    right_col = Table(kv, colWidths=[1.1*inch, (COL_R - 1.1*inch)])
    right_col.setStyle(TableStyle([
        ("SPAN", (0,0), (1,0)),               # <-- make title span both columns
        ("ALIGN", (0,0), (1,0), "CENTER"),    # <-- center the title text
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,1), (0,-1), "RIGHT"),    # labels right-aligned
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 0),
    ]))

    # Assemble a 2-row masthead grid. Row 1: left + right meta. Row 2 (we'll fill right with totals on pass 2 if multi-page)
    masthead_grid = Table(
        [[left_col, right_col],
        ["",      ""]],                        # placeholder row for totals box (keeps layout stable)
        colWidths=[COL_L, COL_R],
        hAlign="LEFT"
    )
    masthead_grid.setStyle(TableStyle([
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING",   (0,0), (-1,-1), 0),
        ("BOTTOMPADDING",(0,0), (-1,-1), 0),
    ]))

    header_flows = [masthead_grid, Spacer(1, 6)]

    # ---------- table factory (repeat header) ----------
    def _make_table(_data):
        t = Table(_data, colWidths=[1.0*inch, 0.8*inch, 1.2*inch, 2.2*inch, 1.0*inch, 1.0*inch], repeatRows=1)
        t.setStyle(TableStyle([
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,0), 11),
            ("BACKGROUND",  (0,0), (-1,0), colors.lightgrey),
            ("ALIGN",       (4,1), (4,-1), "RIGHT"),
            ("ALIGN",       (0,0), (-1,0), "CENTER"),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("INNERGRID",   (0,0), (-1,-1), 0.25, colors.grey),
            ("BOX",         (0,0), (-1,-1), 0.5, colors.black),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.lightcyan]),
        ]))
        return t

    # ---------- totals box flow ----------
    def _totals_box_flow(_tot):
        box_data = [
            [Paragraph("<b>Totals (this statement)</b>", styles["Normal"])],
            [Paragraph(f"Billed:  ${_tot.get('billed', 0):,.2f}", styles["Normal"])],
            [Paragraph(f"Paid:    ${_tot.get('paid', 0):,.2f}",   styles["Normal"])],
            [Paragraph(f"Balance: ${_tot.get('balance', 0):,.2f}", styles["Normal"])],
        ]
        box = Table(box_data, colWidths=[COL_R], hAlign="RIGHT")  # exactly the width of the right column
        box.setStyle(TableStyle([
            ("BOX",        (0,0), (-1,-1), 0.75, colors.black),
            ("INNERGRID",  (0,0), (-1,-1), 0.25, colors.grey),
            ("BACKGROUND", (0,0), (-1,0),  colors.whitesmoke),
            ("LEFTPADDING",(0,0), (-1,-1), 6),
            ("RIGHTPADDING",(0,0),(-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        return box

    # ---------- footer ----------
    def footer(c, d):
        c.saveState()
        c.setFont("Helvetica", 8)
        c.drawRightString(LETTER[0] - 50, 30, f"Page {c.getPageNumber()}")
        c.restoreState()

    # ---------- PASS 1: count pages ----------
    class _PageCountCanvas(_canvas.Canvas):
        def __init__(self, *args, page_count_sink=None, **kwargs):
            self._sink = page_count_sink
            super().__init__(*args, **kwargs)
        def save(self):
            if self._sink is not None:
                self._sink[:] = [self.getPageNumber()]
            super().save()

    page_count_holder = []
    doc.build(
        [deepcopy(f) for f in header_flows] + [deepcopy(_make_table(base_rows))],
        onFirstPage=footer,
        onLaterPages=footer,
        canvasmaker=lambda *a, **kw: _PageCountCanvas(*a, page_count_sink=page_count_holder, **kw),
    )

    # ---------- decide bottom totals vs top box ----------
    multi_page = bool(page_count_holder and page_count_holder[0] > 1)

    # if single-page, include bottom totals inside the table; else, omit them (we show top box)
    if multi_page:
        final_rows = base_rows[:]  # no bottom totals
    else:
        final_rows = base_rows[:] + [
            ["", "", "", "", ""],
            ["", "", "Total Billed:", f"${totals['billed']:,.2f}", ""],
            ["", "", "Total Paid:",   f"${totals['paid']:,.2f}",   ""],
            ["", "", ("Balance Due:" if totals["balance"] >= 0 else "Credit Balance:")
                     , f"${abs(totals['balance']):,.2f}", ""],
        ]

    # ---------- PASS 2: final build ----------
    if multi_page:
        # clone the masthead and place the totals in row 2, col 2 (0-based)
        mh = deepcopy(masthead_grid)
        mh._cellvalues[1][1] = _totals_box_flow(totals)  # put box in the right cell, row 2
        story_final = [mh, Spacer(1, 6), _make_table(final_rows)]
    else:
        story_final = [deepcopy(masthead_grid), Spacer(1, 6), _make_table(final_rows)]

    doc.build(
        story_final,
        onFirstPage=footer,
        onLaterPages=footer
    )
    return filepath


def generate_imm_status_report(status, rows, output_path=None):
    """Generate a PDF report of IMM orders with a specific status."""
    filename = f"IMM_Status_{status}_{datetime.now():%Y%m%d}.pdf"
    EXPORTS_DIR = EXPORTS_BASE_DIR
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    filepath = os.path.join(EXPORTS_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=LETTER, leftMargin=50, rightMargin=50, topMargin=40, bottomMargin=50)

    header = Paragraph(f"<b>IMM Status Report: {status}</b>", getSampleStyleSheet()["Title"])
    spacer = Spacer(1, 12)

    # Headers for IMM table
    data = [["Date", "PO #", "Reference", "In Hands Date", "Status", "Notes"]] + rows

    t = Table(data, colWidths=[1*inch, 1*inch, 2*inch, 1*inch, 1.5*inch, 2*inch], repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 11),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.lightcyan]),
    ]))

    doc.build([header, spacer, t])
    return filepath


def get_imm_orders_by_status(status):
    """Get all IMM orders with a specific status."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, po_number, nickname, in_hands_date, status, notes
        FROM imm_orders
        WHERE status = ?
        ORDER BY in_hands_date ASC
    """, (status,))
    return cursor.fetchall()


def generate_imm_production_pdf(mode="full"):
    """
    Generate a PDF of IMM production orders.
    
    Args:
        mode (str): "full", "emb", or "dtf" to filter by process type
    
    Returns:
        str: Path to the generated PDF file
    """
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.units import inch
    from datetime import datetime
    import os
    from pathlib import Path
    
    from tobys_terminal.shared.db import get_connection
    from tobys_terminal.shared.pdf_style import create_branded_pdf_elements, truncate_text
    from config import PROJECT_ROOT
    
    # Create reports directory if it doesn't exist
    REPORTS_DIR = PROJECT_ROOT / "imm_reports"
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Set up the PDF document
    today = datetime.now().strftime("%Y%m%d")
    filename = f"IMM_Production_{mode}_{today}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=landscape(letter),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # Get the data
    conn = get_connection()
    cur = conn.cursor()
    
    # Build the query based on mode
    query = """
        SELECT po_number, nickname, in_hand_date, firm_date, 
               invoice_number, process, status, notes
        FROM imm_orders
        WHERE status != 'Hidden'
          AND LOWER(status) NOT IN ('cancelled', 'archived', 'done done')
    """
    
    # Add filter based on mode
    if mode.lower() == "emb":
        query += " AND (process = 'EMB' OR status LIKE '%EMB%')"
    elif mode.lower() == "dtf":
        query += " AND (process = 'DTF' OR status LIKE '%DTF%')"
    
    # Add sorting
    query += """
        ORDER BY
            CASE status
                WHEN 'Inline-EMB' THEN 1
                WHEN 'Inline-DTF' THEN 2
                WHEN 'Inline-PAT' THEN 3
                WHEN 'Need Sewout' THEN 4
                WHEN 'Need Product' THEN 5
                WHEN 'Need File' THEN 6
                WHEN 'Need Approval' THEN 7
                WHEN 'Complete' THEN 8
                ELSE 9
            END,
            COALESCE(customer_due_date, in_hand_date) ASC
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    
    # Format the data
    data = [["PO #", "Project Name", "In Hands", "Firm", "Invoice #", "Process", "Status", "Notes"]]
    
    for row in rows:
        formatted_row = list(row)
        
        # Truncate project name (index 1) to prevent overflow
        if formatted_row[1]:
            formatted_row[1] = truncate_text(formatted_row[1], max_length=25)
        
        # Format date (index 2) from YYYY-MM-DD to MM/DD/YYYY
        if formatted_row[2]:
            try:
                formatted_row[2] = datetime.strptime(formatted_row[2], "%Y-%m-%d").strftime("%m/%d/%Y")
            except ValueError:
                pass  # Leave as is if invalid
        
        # Fix the issue with notes containing the status text
        if formatted_row[7] and formatted_row[6]:
            if formatted_row[7].startswith(formatted_row[6]):
                formatted_row[7] = formatted_row[7][len(formatted_row[6]):].strip()
            
            # Also truncate notes if they're too long
            formatted_row[7] = truncate_text(formatted_row[7], max_length=40)
        
        data.append(formatted_row)
    
    # Set column widths (adjust as needed)
    col_widths = [0.8*inch, 2.5*inch, 0.8*inch, 0.5*inch, 0.8*inch, 0.8*inch, 1.2*inch, 2.3*inch]
    
    # Create PDF elements with branded styling
    title = f"IMM Production – {mode.upper()} – {datetime.now().strftime('%B %d, %Y')}"
    elements, _ = create_branded_pdf_elements(title, data, col_widths)
    
    # Build the PDF
    doc.build(elements)
    
    return filepath







def generate_harlestons_production_pdf():
    """Generate a PDF of the Harlestons production roster."""
    from tobys_terminal.shared.db import get_connection
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Use the same query as in the terminal view to ensure consistency
    query = """
        SELECT po_number, location, club_nickname, process, invoice_number, 
               pcs, priority, in_hand_date, status, notes
        FROM harlestons_orders
        WHERE
            status != 'Hidden'
            AND LOWER(status) NOT IN ('cancelled', 'archived')
        ORDER BY in_hand_date ASC
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    
    # Format the data for the PDF
    data = []
    
    # Add headers
    headers = ["PO #", "Loc", "Club", "Process", "Invoice #", "PCS", "Priority", "Due Date", "Status", "Notes"]
    data.append(headers)
    
    # Add rows
    for row in rows:
        formatted_row = list(row)
        
        # Format date if it exists
        if row[7]:  # in_hand_date
            try:
                formatted_row[7] = datetime.strptime(row[7], "%Y-%m-%d").strftime("%m/%d/%Y")
            except ValueError:
                pass  # Keep as is if invalid
        
        data.append(formatted_row)
    
    # Create the PDF
    today = datetime.now().strftime("%Y%m%d")
    filename = f"Harlestons_Production_{today}.pdf"
    export_dir = os.path.join(EXPORTS_BASE_DIR, "harlestons_reports")
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, filename)
    
    doc = SimpleDocTemplate(filepath, pagesize=landscape(letter))
    elements = []
    
    # Add title
    styles = getSampleStyleSheet()
    title = Paragraph(f"Harlestons Production – {datetime.now().strftime('%B %d, %Y')}", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Create table
    table = Table(data)
    
    # Style the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ])
    
    # Add alternating row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.add('BACKGROUND', (0, i), (-1, i), colors.lightgrey)
    
    table.setStyle(style)
    elements.append(table)
    
    # Build the PDF
    doc.build(elements)
    
    return filepath
