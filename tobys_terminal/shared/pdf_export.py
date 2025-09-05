import sqlite3
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.pdfgen import canvas as _canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
)
from reportlab.lib.units import inch
from tkinter import messagebox
from datetime import datetime
from copy import deepcopy
from collections import defaultdict
import os, re
import importlib.resources as pkg_resources

from reportlab.pdfbase.pdfmetrics import stringWidth
from flask import send_file, request
from config import ASSETS_DIR, EXPORTS_DIR
# Define paths using package resources
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



def wrap_po_if_needed(po_number, font="Helvetica", font_size=10, max_width=1.2 * inch):
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




def generate_pdf(customer_name, rows, totals, start_date, end_date, statement_number, nickname=None, output_path=None, interactive=True):
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
        from tkinter import messagebox
        if os.path.exists(filepath):
            overwrite = messagebox.askyesno(
                "Replace File?",
                f"The file already exists:\n\n{filename}\n\n"
                "Do you want to replace it?"
            )
            if not overwrite:
                #print("❌ Export cancelled by user.")
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
        topMargin=40,    # ↓ was 80
        bottomMargin=50
    )

    # top of generate_pdf() add this tiny helper
    def _num(x):
        try:
            return float(x or 0)
        except Exception:
            return 0.0


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
    from collections import defaultdict

    pay_index: dict[str, list[str]] = defaultdict(list)
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


    # Build data rows WITHOUT bottom totals for now; we’ll decide after pass 1
    header_row = ["Date", "Inv. #", "PO #", "Nickname", "Amount", "Status"]

    base_rows = [header_row] + unpaid_rows + paid_rows


    # ---------- compute totals once ----------
    totals = _normalize_totals(rows, totals)

    # ---------- masthead (tight grid that matches the table width = 6.4")
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image

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
    # title_style.fontSize = 18
    # title_style.leading = 20
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


    # Assemble a 2-row masthead grid. Row 1: left + right meta. Row 2 (we’ll fill right with totals on pass 2 if multi-page)
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
    #print(f"✅ PDF saved to: {filepath}")
    return filepath


def generate_imm_status_report(status, rows, output_path=None):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from datetime import datetime

    filename = f"IMM_Status_{status}_{datetime.now():%Y%m%d}.pdf"
    EXPORTS_DIR = os.path.join(EXPORTS_BASE_DIR, "imm_reports")
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
    from tobys_terminal.shared.db import get_connection
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
    # Connect to your terminal.db database
    from tobys_terminal.shared.db import get_connection
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # ... rest of the function ...


    # Query the imm_orders table
    cur.execute("""
        SELECT po_number, nickname, in_hand_date, firm_date, invoice_number, process, status, notes
        FROM imm_orders
        WHERE LOWER(status) NOT IN ('done', 'complete', 'cancelled', 'archived', 'done done')
        AND LOWER(IFNULL(p_status, '')) NOT IN ('picked up')
        ORDER BY in_hand_date ASC
    """)
    orders = cur.fetchall()
    conn.close()

    # Prepare export folder
    EXPORTS_DIR = os.path.join(EXPORTS_BASE_DIR, "imm_reports")
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")
    filename = f"IMM_Production_{mode}_{today_str}.pdf"
    filepath = os.path.join(EXPORTS_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=landscape(pagesize=LETTER), leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    normal_style.wordWrap = 'CJK'

    # Define table headers and widths
    if mode == "full":
        headers = ["PO", "Project Name", "In Hands", "Firm", "Invoice #", "Process", "Status", "Notes"]
        col_widths = [0.7*inch, 1.8*inch, 1.0*inch, 0.7*inch, 1.0*inch, 1.0*inch, 1.6*inch, 3.3*inch]
    else:
        headers = ["PO", "Project Name", "In Hands", "Firm", "Invoice #", "Status", ""]  # blank column at end
        col_widths = [0.7*inch, 1.8*inch, 1.0*inch, 0.7*inch, 1.0*inch, 1.6*inch, 2.5*inch]

    # Prepare filtered data rows
    rows = []
    for order in orders:
        status = order["status"]
        if mode == "emb" and status != "Inline-EMB":
            continue
        if mode == "dtf" and status != "Inline-DTF":
            continue

        in_hand_fmt = ""
        try:
            in_hand_fmt = datetime.strptime(order["in_hand_date"], "%Y-%m-%d").strftime("%m/%d/%Y")
        except:
            in_hand_fmt = order["in_hand_date"] or ""

        firm_display = "Yes" if str(order["firm_date"]).lower().startswith("y") else "No"

        if mode == "full":
            rows.append([
                order["po_number"],
                order["nickname"],
                in_hand_fmt,
                firm_display,
                order["invoice_number"],
                order["process"],
                order["status"],
                Paragraph(order["notes"] or "", normal_style)
            ])
        else:
            rows.append([
                order["po_number"],
                order["nickname"],
                in_hand_fmt,
                firm_display,
                order["invoice_number"],
                order["status"],
                ""  # blank column
            ])

    # Build table
    table_data = [headers] + rows
    table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightcyan]),
    ]))

    title_text = f"IMM Production – {'FULL' if mode == 'full' else mode.upper()} – {datetime.now().strftime('%B %d, %Y')}"
    story = [Paragraph(title_text, styles["Title"]), Spacer(1, 12), table]

    doc.build(story)
    return filepath


if __name__ == "__main__":
    # Run all three versions now to confirm they're working
    full_path = generate_imm_production_pdf(mode="full")
    emb_path = generate_imm_production_pdf(mode="emb")
    dtf_path = generate_imm_production_pdf(mode="dtf")
    print(full_path, emb_path, dtf_path)

