import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared')))
from shared.tobys_terminal.shared.customer_utils import get_grouped_customers, get_customer_ids_by_company, get_company_label, get_company_label_from_row
from shared.import_printavo_orders import sync_printavo_orders_from_invoices

sync_printavo_orders_from_invoices("IMM Promotionals")

