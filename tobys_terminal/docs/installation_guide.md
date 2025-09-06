# Installation Guide for Updated Toby's Terminal

This guide will help you install and configure the updated version of Toby's Terminal with the new Printavo synchronization system.

## Prerequisites

- Python 3.8 or higher
- Access to your existing Toby's Terminal installation
- Database path (from your previous setup)

## Installation Steps

### 1. Set Up Your Environment

First, make sure you have the correct database path in your `.env` file:

```
# For Windows paths, use either double backslashes or forward slashes
TOBYS_TERMINAL_DB=H:\\My Drive\\Sage Projects\\tobys-terminal-3-0\\tobys_terminal-3\\terminal.db
# OR
TOBYS_TERMINAL_DB=H:/My Drive/Sage Projects/tobys-terminal-3-0/tobys_terminal-3/terminal.db
```

### 2. Update the Main Application

Run the update script to replace the old main.py with the new version:

```bash
python update_main.py
```

This will:
- Create a backup of your original main.py file
- Replace it with the updated version that uses the new Printavo sync system

### 3. Install in Development Mode

To ensure Python can find all the modules correctly:

```bash
# From the project root directory (where setup.py is located)
pip install -e .
```

### 4. Create Required Directories

The Printavo sync system needs these directories:

```bash
mkdir -p data_imports
mkdir -p logs
```

### 5. Test the Installation

Run the desktop application:

```bash
python -m tobys_terminal.desktop.main
```

You should see the new interface with the "Printavo Sync" section replacing the old import buttons.

## Troubleshooting

### Module Not Found Errors

If you see errors like `ModuleNotFoundError: No module named 'tobys_terminal'`:

1. Make sure you've installed the package in development mode (Step 3)
2. Try setting the PYTHONPATH environment variable:
   ```
   # Windows PowerShell
   $env:PYTHONPATH = "path/to/project/root"
   
   # Windows CMD
   set PYTHONPATH=path/to/project/root
   
   # Linux/Mac
   export PYTHONPATH=path/to/project/root
   ```

### Database Connection Issues

If you have database connection problems:

1. Verify the path in your `.env` file is correct
2. Ensure the directory exists and you have write permissions
3. Check that the database file exists or can be created

## Using the New Printavo Sync System

1. Open the desktop application
2. Use the "Printavo Sync" section in the sidebar:
   - "Sync All Data" to update everything
   - "Sync IMM Orders" for just IMM orders
   - "Sync Harlestons Orders" for just Harlestons orders
3. Check the logs directory for detailed information about each sync operation

For more details, see the [Printavo Sync Documentation](./printavo_sync.md).