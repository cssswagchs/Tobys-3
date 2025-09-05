# gui/ar_view.py
import sys
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta

from tobys_terminal.shared.db import get_connection
from tobys_terminal.shared.brand_ui import apply_brand, zebra_tree

def open_ar_view():
    """Launches the Accounts Receivable Dashboard window."""
    win = tk.Toplevel()
    win.title("Accounts Receivable Dashboard")
    win.geometry("1100x600")
    apply_brand(win)

    ttk.Label(win, text="Accounts Receivable Summary",
              style="Header.TLabel").pack(pady=10)

    columns = ("Company", "0–30 Days", "31–60 Days", "61–90 Days", "90+ Days", "Total Owed")
    tree = ttk.Treeview(win, columns=columns, show="headings", style="Sage.Treeview")

    export_btn = ttk.Button(win, text="📤 Export to CSV", style="Primary.TButton",
                            command=lambda: export_ar_to_csv(ar_summary))
    export_btn.pack(pady=5)

    print_btn = ttk.Button(win, text="🖨️ Print AR Summary", style="Primary.TButton",
                        command=lambda: print_ar_summary(ar_summary))
    print_btn.pack(pady=5)

    save_email_btn = ttk.Button(win, text="💾 Save for Email", style="Primary.TButton",
                            command=lambda: save_ar_for_email(ar_summary))
    save_email_btn.pack(pady=5)


    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=150)
    tree.column("Company", width=250)

    tree.pack(expand=True, fill="both", padx=10, pady=10)
    # Load data
    conn = get_connection()
    cursor = conn.cursor()

    # Get all billable unpaid invoices
    cursor.execute("""
        SELECT
            c.company,
            c.first_name,
            c.last_name,
            i.invoice_number,
            i.total,
            i.invoice_date,
            COALESCE(p.paid, 0) as amount_paid
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        LEFT JOIN (
            SELECT invoice_number, SUM(amount) AS paid
            FROM payments_clean
            GROUP BY invoice_number
        ) p ON p.invoice_number = i.invoice_number
        WHERE LOWER(TRIM(i.invoice_status)) IN (
            'complete and ready for pickup', 'shipped', 'picked up',
            'payment request sent', 'harlestons -- invoiced',
            'past due invoice - followed up', 'on hold - need payment please',
            'done done', 'pickup reminder sent', 'harlestons -- picked up'
        )

          AND COALESCE(i.total, 0) - COALESCE(p.paid, 0) > 0
    """)
    rows = cursor.fetchall()
    
    conn.close()

    today = datetime.today()
    ar_summary = {}

    for company, first, last, inv_num, total, inv_date, paid in rows:

        # Determine balance due
        balance_due = (total or 0.0) - (paid or 0.0)
        if balance_due <= 0:
            continue  # skip fully paid or overpaid invoices


        if isinstance(inv_date, str):
            try:
                inv_date = datetime.strptime(inv_date, "%Y-%m-%d")
            except Exception:
                continue

        days_old = (today - inv_date).days
        company_label = company.strip() if company and company.strip() else f"No Company - {first} {last}"


        # Aging buckets
        if company_label not in ar_summary:
            ar_summary[company_label] = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}

        if days_old <= 30:
            ar_summary[company_label]["0-30"] += balance_due
        elif days_old <= 60:
            ar_summary[company_label]["31-60"] += balance_due
        elif days_old <= 90:
            ar_summary[company_label]["61-90"] += balance_due
        else:
            ar_summary[company_label]["90+"] += balance_due

        # ✅ After bucket is filled, check if balance_due was actually added
        # This isn't necessary now that balance_due <= 0 is checked above,
        # but you can double-guard it with a post-check if you'd like.


    # Populate Treeview
    for company, buckets in sorted(ar_summary.items(), key=lambda x: -sum(x[1].values())):
        total = sum(buckets.values())
        if abs(total) < 0.01:
            continue # filter out zero balances

        if total == 0:
            # print(f"Skipping zero-balance company: {company}")
            continue


        tree.insert("", "end", values=(
            company,
            f"${buckets['0-30']:,.2f}",
            f"${buckets['31-60']:,.2f}",
            f"${buckets['61-90']:,.2f}",
            f"${buckets['90+']:,.2f}",
            f"${total:,.2f}",
        ))


    # Configure style
    tree.tag_configure("totals", background="#e0e0e0", font=("Arial", 12, "bold"))

    # Compute bucket totals
    bucket_totals = {
        "0-30": 0.0,
        "31-60": 0.0,
        "61-90": 0.0,
        "90+": 0.0
    }

    for buckets in ar_summary.values():
        for k in bucket_totals:
            bucket_totals[k] += buckets[k]

    grand_total = sum(bucket_totals.values())

    # Insert totals row
    tree.insert("", "end", values=(
        "💰 TOTALS",
        f"${bucket_totals['0-30']:,.2f}",
        f"${bucket_totals['31-60']:,.2f}",
        f"${bucket_totals['61-90']:,.2f}",
        f"${bucket_totals['90+']:,.2f}",
        f"${grand_total:,.2f}",
    ))
    zebra_tree(tree)
import csv
from tkinter import filedialog, messagebox

def export_ar_to_csv(ar_data: dict):
    """Exports the A/R summary to a CSV file."""
    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")],
        title="Save A/R Report As..."
    )
    if not file_path:
        return

    try:
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Company", "0–30 Days", "31–60 Days", "61–90 Days", "90+ Days", "Total Owed"])

            grand = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
            for company, buckets in sorted(ar_data.items(), key=lambda x: -sum(x[1].values())):
                total = sum(buckets.values())
                if total == 0:
                    continue

                writer.writerow([
                    company,
                    f"{buckets['0-30']:.2f}",
                    f"{buckets['31-60']:.2f}",
                    f"{buckets['61-90']:.2f}",
                    f"{buckets['90+']:.2f}",
                    f"{total:.2f}",
                ])
                for k in grand:
                    grand[k] += buckets[k]

            writer.writerow([
                "TOTAL",
                f"{grand['0-30']:.2f}",
                f"{grand['31-60']:.2f}",
                f"{grand['61-90']:.2f}",
                f"{grand['90+']:.2f}",
                f"{sum(grand.values()):.2f}"
            ])

        messagebox.showinfo("Export Complete", f"A/R report saved to:\n{file_path}")
    except Exception as e:
        messagebox.showerror("Export Failed", f"Error exporting A/R report:\n{str(e)}")

def print_ar_summary(ar_data, output_path=None):
    """Generates a PDF AR summary and opens it for printing or saves to specified path."""
    try:
        # Use the provided path or create a temporary file
        if output_path:
            temp_file_name = output_path
            should_open = False
        else:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file_name = temp_file.name
            should_open = True
            
        # Call helper function to generate the PDF
        generate_ar_pdf(ar_data, temp_file_name)
        
        # Open the file if it's a temporary one for viewing
        if should_open:
            webbrowser.open(f"file://{temp_file_name}")
            
        return temp_file_name
            
    except Exception as e:
        messagebox.showerror("Print Failed", f"Error creating PDF:\n{str(e)}")
        return None

# Extract the PDF generation logic to a separate function
def generate_ar_pdf(ar_data, output_path):
    """Generates the AR PDF at the specified path."""
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Generate today's date string
    today_str = datetime.now().strftime("%B %d, %Y")

    # Load the logo image
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'assets', 'toby-logo.png'))
    img = None
    if os.path.exists(logo_path):
        img = Image(logo_path, width=60, height=60)
        img.hAlign = 'RIGHT'

    # Left side = title and date
    left = [Paragraph("Accounts Receivable Summary", styles['Heading1']),
            Paragraph(f"Generated: {today_str}", styles['Normal'])]

    # Right side = image or blank space
    right = img if img else ""

    # Table to hold both in one row
    header_table = Table([[left, right]], colWidths=[400, 100])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        # Optional spacing tweak
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # Build the table header
    data = [["Company", "0–30 Days", "31–60 Days", "61–90 Days", "90+ Days", "Total Owed"]]
    grand = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}

    for company, buckets in sorted(ar_data.items(), key=lambda x: -sum(x[1].values())):
        total = sum(buckets.values())
        if abs(total) < 0.01:
            continue

        row = [
            company,
            f"${buckets['0-30']:,.2f}",
            f"${buckets['31-60']:,.2f}",
            f"${buckets['61-90']:,.2f}",
            f"${buckets['90+']:,.2f}",
            f"${total:,.2f}",
        ]
        data.append(row)
        for k in grand:
            grand[k] += buckets[k]

    # Add totals row
    data.append([
        "TOTAL",
        f"${grand['0-30']:,.2f}",
        f"${grand['31-60']:,.2f}",
        f"${grand['61-90']:,.2f}",
        f"${grand['90+']:,.2f}",
        f"${sum(grand.values()):,.2f}"
    ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d5744")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.whitesmoke, colors.HexColor("#f0fef7")]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))

    elements.append(table)
    # Add a footer
    footer_style = styles['Normal'].clone('footer')
    footer_style.alignment = 1  # center align
    footer_style.textColor = colors.HexColor("#0d5744")
    elements.append(Paragraph("Powered by Toby's Terminal", footer_style))

    doc.build(elements)
    return output_path

# Add this function to save the AR report for email
def save_ar_for_email(ar_data):
    """Saves the AR summary PDF to a dedicated folder for emailing."""
    try:
        # Create AR reports directory in exports
        from tobys_terminal.shared.pdf_export import EXPORTS_BASE_DIR
        
        # Create AR reports folder if it doesn't exist
        AR_EXPORTS_DIR = os.path.join(EXPORTS_BASE_DIR, "ar_reports")
        os.makedirs(AR_EXPORTS_DIR, exist_ok=True)
        
        # Generate filename with date
        today_str = datetime.now().strftime("%Y%m%d")
        filename = f"AR_Summary_{today_str}.pdf"
        filepath = os.path.join(AR_EXPORTS_DIR, filename)
        
        # Generate the PDF using the existing print function but with a specific path
        generate_ar_pdf(ar_data, filepath)
        
        messagebox.showinfo("Save Complete", 
                           f"AR report saved for email at:\n{filepath}\n\nReady to attach to email.")
        
        # Optionally open the folder containing the file
        import subprocess
        subprocess.Popen(f'explorer /select,"{filepath}"')
        
    except Exception as e:
        messagebox.showerror("Save Failed", f"Error saving AR report:\n{str(e)}")