Printavo Synchronization System

Overview

The Printavo Synchronization System is a unified solution for importing and managing data from Printavo. It replaces the previous separate import processes with a more streamlined approach.


Features
• **Unified Synchronization**: Sync all data types (customers, orders, payments) in one operation
• **Targeted Syncing**: Selectively sync only IMM or Harlestons orders
• **Database Verification**: Built-in tools to check database integrity
• **Status Filtering**: Automatically filters out completed/archived orders
• **Due Date Management**: Properly handles customer due dates across systems


How to Use

From the Desktop Application
1. Open Toby's Terminal desktop application
2. Use the new "Printavo Sync" section in the sidebar
3. Choose from:
- **Sync All Data**: Updates all data from Printavo
- **Sync IMM Orders**: Updates only IMM orders
- **Sync Harlestons Orders**: Updates only Harlestons orders


From the Command Line

You can also run the sync process directly from the command line:


# Sync everything
python -m tobys_terminal.shared.printavo_sync

# Import specific functions for custom scripts
from tobys_terminal.shared.printavo_sync import sync_all, sync_imm_orders, sync_harlestons_orders


Technical Details

Data Flow
1. The system first checks and creates necessary database tables
2. It then identifies customer IDs associated with IMM and Harlestons
3. For each company, it retrieves invoices from the main invoices table
4. It updates existing orders or creates new ones in the respective tables
5. Status filters are applied to hide completed/archived orders
6. Customer due dates are synchronized across tables


Configuration

The system uses status filters defined in `config.py`:

• `EXCLUDED_STATUSES`: General statuses to exclude (e.g., 'done', 'cancelled')
• `EXCLUDED_P_STATUSES`: Production statuses to exclude
• `HARLESTONS_EXCLUDED_STATUSES`: Harlestons-specific exclusions
• `IMM_EXCLUDED_STATUSES`: IMM-specific exclusions


CSV Import

The system can also import data from CSV files:

1. Place CSV files in the `data_imports` directory
2. Files should be named:
- `harlestons_orders.csv` for Harlestons orders


Logs

Logs are stored in the `logs` directory with filenames like `printavo_sync_YYYYMMDD.log`.


Troubleshooting

If you encounter issues:

1. Use the "Check Database" function to verify database integrity
2. Check the log files for detailed error messages
3. Ensure your database connection is properly configured in `.env`