# Toby's Terminal Upgrade Guide

## Overview of Changes

This upgrade introduces a new unified Printavo synchronization system that replaces the old separate import buttons. The main changes are:

1. **New Printavo Sync Module**: A comprehensive system for synchronizing data from Printavo
2. **Updated Main Interface**: The main application now has a "Printavo Sync" section instead of separate import buttons
3. **Enhanced Database Management**: Better handling of customer due dates and status filtering

## Files Changed/Added

- **`tobys_terminal/shared/printavo_sync.py`** (NEW): The core synchronization functionality
- **`tobys_terminal/desktop/main.py`** (UPDATED): Updated main application with new sync UI
- **`docs/printavo_sync.md`** (NEW): Documentation for the new sync system
- **`docs/installation_guide.md`** (NEW): Guide for installing the updates
- **`test_printavo_sync.py`** (NEW): Script to test the new functionality
- **`update_main.py`** (NEW): Helper script to update the main application file

## Installation Steps

### Step 1: Backup Your Current System

Before making any changes, create a backup of your current system:

```bash
# Create a backup directory
mkdir -p backups/$(date +%Y%m%d)

# Copy important files
cp -r tobys_terminal/desktop/main.py backups/$(date +%Y%m%d)/
```

### Step 2: Copy New Files

1. Copy the new `printavo_sync.py` to the shared directory:

```bash
cp tobys_terminal/shared/printavo_sync.py /path/to/your/installation/tobys_terminal/shared/
```

2. Create the documentation directory if it doesn't exist:

```bash
mkdir -p /path/to/your/installation/docs
```

3. Copy the documentation files:

```bash
cp docs/printavo_sync.md /path/to/your/installation/docs/
cp docs/installation_guide.md /path/to/your/installation/docs/
```

4. Copy the test and update scripts:

```bash
cp test_printavo_sync.py /path/to/your/installation/
cp update_main.py /path/to/your/installation/
```

### Step 3: Update the Main Application

Run the update script to replace the old main.py with the new version:

```bash
cd /path/to/your/installation
python update_main.py
```

### Step 4: Create Required Directories

```bash
mkdir -p data_imports
mkdir -p logs
```

### Step 5: Test the Installation

1. First, test the sync functionality without affecting your database:

```bash
python test_printavo_sync.py --mode check
```

2. If that works, try running the application:

```bash
python -m tobys_terminal.desktop.main
```

## Troubleshooting

### Module Not Found Errors

If you see errors like `ModuleNotFoundError: No module named 'tobys_terminal'`:

```bash
# Install the package in development mode
pip install -e .

# Or set the PYTHONPATH
export PYTHONPATH=/path/to/your/installation  # Linux/Mac
# OR
set PYTHONPATH=C:\path\to\your\installation  # Windows
```

### Database Connection Issues

1. Make sure your `.env` file has the correct database path:

```
TOBYS_TERMINAL_DB=H:/My Drive/Sage Projects/tobys-terminal-3-0/tobys_terminal-3/terminal.db
```

2. Check that the database file exists and is accessible.

## Reverting Changes

If you need to revert to the original version:

```bash
# Restore the original main.py
cp backups/YYYYMMDD/main.py tobys_terminal/desktop/main.py
```

## Getting Help

If you encounter any issues during the upgrade process, please refer to the documentation in the `docs` directory or contact the developer for assistance.