from tobys_terminal.shared.customer_utils import get_grouped_customers

def open_production_roster(company_label):
    if not company_label:
        print("⚠️ No company label provided to open_production_roster.")
        return

    label = company_label.strip().lower()

    if label.startswith("imm"):
        from .imm_roster_view import open_imm_roster_view
        open_imm_roster_view(company_label)

    elif label.startswith("harleston"):
        from .harlestons_roster_view import open_harlestons_roster_view
        open_harlestons_roster_view(company_label)

    else:
        from .default_roster_view import open_default_roster_view
        open_default_roster_view(company_label)
