import csv
import os
# test edit for Git
def get_csv_export_path(default_name, interactive=True):
    export_dir = os.path.join(os.path.dirname(__file__), "exports", "csv")
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, default_name)

    if not interactive:
        # auto-rename if needed (for web)
        base, ext = os.path.splitext(filepath)
        i = 1
        while os.path.exists(filepath):
            filepath = f"{base} ({i}){ext}"
            i += 1

    return filepath

def export_statement_csv(selected_name, start_s, end_s, export_rows, totals, interactive=True, user_selected_path=None):
    # ---------- Filename ----------
    safe_name = selected_name.replace(" ", "_")
    default_name = f"statement_{safe_name}_{(start_s or 'start')}_to_{(end_s or 'end')}.csv"

    # ---------- Output Path ----------
    filepath = user_selected_path or get_csv_export_path(default_name, interactive)

    # ---------- Write CSV ----------
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Invoice #", "PO #", "Nickname", "Amount", "Status"])
        w.writerows(export_rows)
        w.writerow([])
        w.writerow(["", "", "Total Billed", f"{float(totals.get('billed', 0) or 0):.2f}", ""])
        w.writerow(["", "", "Total Paid",   f"{float(totals.get('paid',   0) or 0):.2f}", ""])
        bal = float(totals.get('balance', (totals.get('billed',0) or 0) - (totals.get('paid',0) or 0)) or 0)
        w.writerow(["", "", "Balance",      f"{abs(bal):.2f}", "Credit" if bal < 0 else "Due"])

    return filepath

def export_invoice_csv(selected_name, export_rows, totals, interactive=True, user_selected_path=None):
    safe_name = selected_name.replace(" ", "_")
    default_name = f"invoices_{safe_name}.csv"
    filepath = user_selected_path or get_csv_export_path(default_name, interactive)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Invoice #", "Date", "PO #", "Total", "Paid", "Status"])
        for r in export_rows:
            w.writerow([
                r.get("number", ""),
                r.get("date", ""),
                r.get("po", ""),
                f"{float(r.get('total', 0)):.2f}",
                f"{float(r.get('paid', 0)):.2f}",
                r.get("status", "")
            ])
        w.writerow([])
        w.writerow(["", "", "Total Billed", f"{float(totals.get('billed', 0) or 0):.2f}"])
        w.writerow(["", "", "Total Paid",   f"{float(totals.get('paid',   0) or 0):.2f}"])
        bal = float(totals.get('balance', (totals.get('billed', 0) or 0) - (totals.get('paid', 0) or 0)) or 0)
        w.writerow(["", "", "Balance",      f"{abs(bal):.2f}", "Credit" if bal < 0 else "Due"])

    return filepath
