tobys_terminal-3
├── __init__.py
├── config.py
├── requirements.txt
├── setup.py
├── .gitignore
├── README.md
├── .env
├── tobys_terminal
│   ├── __init__ .py
│   ├── web
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── static
│   │   │   ├── imm-logo.png
│   │   │   ├── harlestons-logo.png
│   │   │   ├── __init__.py
│   │   │   └── cssswag-logo.png
│   │   ├── routes
│   │   │   ├── __init__.py
│   │   │   ├── dataimaging.py
│   │   │   ├── customer_portal.py
│   │   │   ├── admin.py
│   │   │   ├── dashboard.py
│   │   │   ├── auth.py
│   │   │   ├── lori.py
│   │   │   ├── harlestons.py
│   │   │   └── imm.py
│   │   └── templates
│   │       ├── __init__.py
│   │       ├── login.html
│   │       ├── error.html
│   │       ├── dataimaging.html
│   │       ├── 500.html
│   │       ├── 404.html
│   │       ├── customer_invoices.html
│   │       ├── customer_portal.html
│   │       ├── index.html
│   │       ├── lori_dashboard.html
│   │       ├── harlestons_landing.html
│   │       ├── imm_landing.html
│   │       ├── layout.html
│   │       ├── harlestons.html
│   │       ├── imm.html
│   │       └── admin
│   │           ├── __init__.py
│   │           ├── dashboard.html
│   │           ├── users.html
│   │           ├── edit_user.html
│   │           ├── new_user.html
│   │           ├── notes.html
│   │           └── system.html
│   ├── desktop
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── tests
│   │   │   └── __init__.py
│   │   ├── gui
│   │   │   ├── __init__.py
│   │   │   ├── production_roster.py
│   │   │   ├── customer_contact_view.py
│   │   │   ├── customer_statement_creator.py
│   │   │   ├── customer_view.py
│   │   │   ├── default_roster_view.py
│   │   │   ├── statement_history_view.py
│   │   │   ├── reconcile_view.py
│   │   │   ├── payment_checker_view.py
│   │   │   ├── statement_register_view.py
│   │   │   ├── statement_view.py
│   │   │   ├── ar_view.py
│   │   │   ├── harlestons_roster_view.py
│   │   │   ├── imm_roster_view.py
│   │   │   ├── __pycache__
│   │   │   │   ├── __init__.cpython-311.pyc
│   │   │   │   ├── statement_view.cpython-311.pyc
│   │   │   │   ├── reconcile_view.cpython-311.pyc
│   │   │   │   ├── ar_view.cpython-311.pyc
│   │   │   │   ├── payment_checker_view.cpython-311.pyc
│   │   │   │   ├── statement_register_view.cpython-311.pyc
│   │   │   │   ├── customer_view.cpython-311.pyc
│   │   │   │   ├── customer_contact_view.cpython-311.pyc
│   │   │   │   ├── statement_history_view.cpython-311.pyc
│   │   │   │   ├── customer_statement_creator.cpython-311.pyc
│   │   │   │   ├── production_roster.cpython-311.pyc
│   │   │   │   ├── imm_roster_view.cpython-311.pyc
│   │   │   │   └── harlestons_roster_view.cpython-311.pyc
│   │   │   ├── base_view.py
│   │   │   └── test_calendar.py
│   │   └── __pycache__
│   │       └── __init__.cpython-311.pyc
│   ├── shared
│   │   ├── printavo_sync.py
│   │   ├── export_csv.py
│   │   ├── css_swag_colors.py
│   │   ├── __init__.py
│   │   ├── invoice_logic.py
│   │   ├── order_utils.py
│   │   ├── statement_logic.py
│   │   ├── maintenance.py
│   │   ├── misc.py
│   │   ├── company_labels.py
│   │   ├── date_util.py
│   │   ├── theme.py
│   │   ├── reprint.py
│   │   ├── brand_ui.py
│   │   ├── pdf_export.py
│   │   ├── customer_utils.py
│   │   ├── settings.py
│   │   ├── auth_utils.py
│   │   ├── db.py
│   │   ├── data
│   │   │   ├── __init__.py
│   │   │   ├── payments.csv
│   │   │   ├── customers.csv
│   │   │   ├── orders.csv
│   │   │   ├── FULL DATA
│   │   │   │   ├── customers.csv
│   │   │   │   ├── payments.csv
│   │   │   │   └── orders.csv
│   │   │   ├── __pycache__
│   │   │   │   └── __init__.cpython-311.pyc
│   │   │   ├── jaunted.pdf
│   │   │   └── imm_9-6-2025.pdf
│   │   ├── utils
│   │   │   └── __init__.py
│   │   ├── assets
│   │   │   ├── logo.png
│   │   │   ├── __init__.py
│   │   │   ├── toby-logo.png
│   │   │   └── __pycache__
│   │   │       └── __init__.cpython-311.pyc
│   │   ├── exports
│   │   │   ├── __init__.py
│   │   │   ├── csv
│   │   │   │   ├── __init__.py
│   │   │   │   ├── statement_910_Outdoors_start_to_end.csv
│   │   │   │   ├── ARS-Before cleanup 8-16-2025.csv
│   │   │   │   ├── invoices_A_Morgan_Glass.csv
│   │   │   │   ├── AR-8-18-25.csv
│   │   │   │   └── ar 8-.csv
│   │   │   ├── imm_reports
│   │   │   │   ├── __init__.py
│   │   │   │   ├── IMM_Production_emb_20250821.pdf
│   │   │   │   ├── IMM_Production_full_20250821.pdf
│   │   │   │   ├── IMM_Production_dtf_20250821.pdf
│   │   │   │   ├── IMM_Production_full_20250905.pdf
│   │   │   │   ├── IMM_Production_full_20250906.pdf
│   │   │   │   └── IMM_Production_full_20250907.pdf
│   │   │   ├── statements
│   │   │   │   ├── __init__.py
│   │   │   │   ├── S00110_statement_A_Charleston_Bride_Full_Range.pdf
│   │   │   │   ├── S00111_statement_910_Outdoors_Full_Range.pdf
│   │   │   │   ├── S00098_statement_Harlestons_08-04-2025_to_08-10-2025.pdf
│   │   │   │   ├── S00106_statement_IMM_Promotionals_03-01-2025_to_03-31-2025.pdf
│   │   │   │   ├── Bear_the_Palm
│   │   │   │   │   └── S00029_statement_Bear_the_Palm_05-01-2025_to_06-30-2025.pdf
│   │   │   │   ├── IMM_Promotionals
│   │   │   │   │   ├── S00106_statement_IMM_Promotionals_03-01-2025_to_03-31-2025.pdf
│   │   │   │   │   ├── S00105_statement_IMM_Promotionals_02-01-2025_to_02-28-2025.pdf
│   │   │   │   │   ├── S00114_statement_IMM_Promotionals_04-01-2025_to_04-30-2025.pdf
│   │   │   │   │   ├── S00100_statement_IMM_Promotionals_01-01-2021_to_12-31-2021.pdf
│   │   │   │   │   ├── S00101_statement_IMM_Promotionals_01-01-2022_to_12-31-2022.pdf
│   │   │   │   │   ├── S00102_statement_IMM_Promotionals_01-01-2023_to_12-31-2023.pdf
│   │   │   │   │   ├── S00103_statement_IMM_Promotionals_01-01-2024_to_12-31-2024.pdf
│   │   │   │   │   ├── S00104_statement_IMM_Promotionals_01-01-2025_to_01-31-2025.pdf
│   │   │   │   │   ├── S00116_statement_IMM_Promotionals_01-01-2020_to_12-31-2020.pdf
│   │   │   │   │   ├── S00117_statement_IMM_Promotionals_05-01-2025_to_05-31-2025.pdf
│   │   │   │   │   ├── S00118_statement_IMM_Promotionals_05-01-2025_to_05-31-2025.pdf
│   │   │   │   │   ├── S00119_statement_IMM_Promotionals_06-01-2025_to_06-30-2025.pdf
│   │   │   │   │   └── S00120_statement_IMM_Promotionals_07-01-2025_to_07-31-2025.pdf
│   │   │   │   ├── BDVIbez
│   │   │   │   │   └── S00031_statement_BDVIbez_Full_Range.pdf
│   │   │   │   ├── Digital_Graphics
│   │   │   │   │   └── S00032_statement_Digital_Graphics_Full_Range.pdf
│   │   │   │   ├── MMG_-_Marine_Marketing_Group
│   │   │   │   │   ├── S00113_statement_MMG_-_Marine_Marketing_Group_06-01-2025_to_07-15-2025.pdf
│   │   │   │   │   ├── S00113_statement_MMG_-_Marine_Marketing_Group_06-01-2025_to_07-15-2025 (1).pdf
│   │   │   │   │   └── S00113_statement_MMG_-_Marine_Marketing_Group_06-01-2025_to_07-15-2025 (2).pdf
│   │   │   │   ├── AIM_Capital_Solutions_-_PrivateI
│   │   │   │   │   └── S00112_statement_AIM_Capital_Solutions_-_PrivateI_02-18-2025_to_05-10-2025.pdf
│   │   │   │   ├── VKC_Systems
│   │   │   │   │   └── S00123_statement_VKC_Systems_01-01-2016_to_08-20-2025.pdf
│   │   │   │   └── Harlestons
│   │   │   │       ├── S00098_statement_Harlestons_08-04-2025_to_08-10-2025.pdf
│   │   │   │       ├── S00096_statement_Harlestons_07-28-2025_to_08-03-2025.pdf
│   │   │   │       ├── S00095_statement_Harlestons_07-21-2025_to_07-27-2025.pdf
│   │   │   │       ├── S00094_statement_Harlestons_07-14-2025_to_07-20-2025.pdf
│   │   │   │       ├── S00093_statement_Harlestons_07-07-2025_to_07-13-2025.pdf
│   │   │   │       ├── S00092_statement_Harlestons_06-30-2025_to_07-06-2025.pdf
│   │   │   │       ├── S00091_statement_Harlestons_06-23-2025_to_06-29-2025.pdf
│   │   │   │       ├── S00073_statement_Harlestons_01-01-2025_to_01-31-2025.pdf
│   │   │   │       ├── S00072_statement_Harlestons_01-01-2024_to_12-31-2024.pdf
│   │   │   │       ├── S00071_statement_Harlestons_01-01-2023_to_12-31-2023.pdf
│   │   │   │       ├── S00084_statement_Harlestons_05-05-2025_to_05-11-2025.pdf
│   │   │   │       ├── S00082_statement_Harlestons_04-21-2025_to_04-27-2025.pdf
│   │   │   │       ├── S00081_statement_Harlestons_04-14-2025_to_04-20-2025.pdf
│   │   │   │       ├── S00080_statement_Harlestons_04-07-2025_to_04-13-2025.pdf
│   │   │   │       ├── S00090_statement_Harlestons_06-16-2025_to_06-22-2025.pdf
│   │   │   │       ├── S00083_statement_Harlestons_04-28-2025_to_05-04-2025.pdf
│   │   │   │       ├── S00097_statement_Harlestons_01-01-2022_to_12-31-2022.pdf
│   │   │   │       ├── S00074_statement_Harlestons_02-01-2025_to_02-28-2025.pdf
│   │   │   │       ├── S00075_statement_Harlestons_03-03-2025_to_03-07-2025.pdf
│   │   │   │       ├── S00076_statement_Harlestons_03-10-2025_to_03-14-2025.pdf
│   │   │   │       ├── S00077_statement_Harlestons_03-17-2025_to_03-21-2025.pdf
│   │   │   │       ├── S00078_statement_Harlestons_03-24-2025_to_03-31-2025.pdf
│   │   │   │       ├── S00079_statement_Harlestons_04-01-2025_to_04-06-2025.pdf
│   │   │   │       ├── S00069_statement_Harlestons_01-01-2021_to_12-31-2021.pdf
│   │   │   │       ├── S00115_statement_Harlestons_08-11-2025_to_08-17-2025.pdf
│   │   │   │       ├── S00085_statement_Harlestons_05-12-2025_to_05-18-2025.pdf
│   │   │   │       ├── S00086_statement_Harlestons_05-19-2025_to_05-25-2025.pdf
│   │   │   │       ├── S00087_statement_Harlestons_05-26-2025_to_06-01-2025.pdf
│   │   │   │       ├── S00088_statement_Harlestons_06-02-2025_to_06-08-2025.pdf
│   │   │   │       ├── S00089_statement_Harlestons_06-09-2025_to_06-15-2025.pdf
│   │   │   │       ├── S00124_statement_Harlestons_08-18-2025_to_08-24-2025.pdf
│   │   │   │       ├── dnu
│   │   │   │       │   └── S00089_statement_Harlestons_06-09-2025_to_06-15-2025_20250829_100444.pdf
│   │   │   │       └── S00125_statement_Harlestons_08-25-2025_to_08-31-2025.pdf
│   │   │   ├── ar_reports
│   │   │   │   └── AR_Summary_20250831.pdf
│   │   │   ├── __pycache__
│   │   │   │   └── __init__.cpython-311.pyc
│   │   │   └── IMM_Production_full_20250907.pdf
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-311.pyc
│   │   │   ├── db.cpython-311.pyc
│   │   │   ├── pdf_export.cpython-311.pyc
│   │   │   ├── export_csv.cpython-311.pyc
│   │   │   ├── statement_logic.cpython-311.pyc
│   │   │   ├── reprint.cpython-311.pyc
│   │   │   ├── maintenance.cpython-311.pyc
│   │   │   ├── brand_ui.cpython-311.pyc
│   │   │   ├── css_swag_colors.cpython-311.pyc
│   │   │   ├── customer_utils.cpython-311.pyc
│   │   │   ├── order_utils.cpython-311.pyc
│   │   │   ├── date_util.cpython-311.pyc
│   │   │   ├── settings.cpython-311.pyc
│   │   │   ├── import_printavo_orders.cpython-311.pyc
│   │   │   ├── printavo_sync.cpython-311.pyc
│   │   │   ├── imm_import.cpython-311.pyc
│   │   │   └── pdf_style.cpython-311.pyc
│   │   ├── imm_import.py
│   │   └── pdf_style.py
│   └── docs
│       ├── UPGRADE_GUIDE.md
│       ├── todo.md
│       ├── PROJECT_SUMMARY.md
│       ├── GITHUB_INSTRUCTIONS.md
│       ├── deployment_guide.md
│       ├── installation_guide.md
│       ├── printavo_sync.md
│       ├── testing_guide.md
│       └── Folder_File_Structure_tobys_terminal-3.md
├── tobys_terminal.egg-info
│   ├── dependency_links.txt
│   ├── PKG-INFO
│   ├── entry_points.txt
│   ├── SOURCES.txt
│   ├── top_level.txt
│   └── requires.txt
├── terminal.db
├── __pycache__
│   └── config.cpython-311.pyc
├── logs
│   ├── printavo_sync_20250905.log
│   ├── printavo_sync_20250906.log
│   └── printavo_sync_20250907.log
├── Printavo Synchronization System.md
├── data_imports
│   ├── orders.csv
│   ├── payments.csv
│   └── customers.csv
├── optimization_report.py
└── imm_reports
    └── IMM_Production_full_20250907.pdf
