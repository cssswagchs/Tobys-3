# Testing Guide for Toby's Terminal

This guide provides instructions for testing the Toby's Terminal application, including the new Printavo sync functionality and enhanced roster views.

## Prerequisites

Before testing, ensure you have:

1. Installed all required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Installed the package in development mode:
   ```bash
   pip install -e .
   ```

3. Set up your environment variables in a `.env` file (see `.env.example` for reference)

4. Created the necessary directories:
   ```bash
   mkdir -p data_imports
   mkdir -p logs
   ```

## Testing the Basic Application

### 1. Running the Desktop Application

```bash
python -m tobys_terminal.desktop.main
```

Verify that:
- The application launches without errors
- All tabs are accessible
- The database connection works properly

### 2. Running the Web Application

```bash
python -m tobys_terminal.web.app
```

Verify that:
- The web server starts without errors
- You can access the web interface at http://localhost:5000
- The database connection works properly

## Testing the New Printavo Sync Functionality

### 1. Using the Test Script

The `test_printavo_sync.py` script allows you to test the new Printavo sync functionality without modifying your database:

```bash
# Check database configuration
python test_printavo_sync.py --mode check

# Test IMM orders sync
python test_printavo_sync.py --mode imm

# Test Harlestons orders sync
python test_printavo_sync.py --mode harlestons

# Test full sync
python test_printavo_sync.py --mode all
```

### 2. Testing in the Desktop Application

1. Launch the desktop application with the updated main.py:
   ```bash
   python -m tobys_terminal.desktop.main
   ```

2. Navigate to the "Printavo Sync" section
3. Test each sync option:
   - Check Database
   - Sync IMM Orders
   - Sync Harlestons Orders
   - Sync All

### 3. Testing the Enhanced Roster Views

1. Launch the desktop application
2. Navigate to the IMM and Harlestons roster views
3. Test the new features:
   - Inline editing for all fields
   - Calendar widgets on date fields
   - Order entry that matches imported orders with existing ones using PO numbers
   - Integration with the new printavo_sync.py system

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
   TOBYS_TERMINAL_DB=path/to/your/terminal.db
   ```

2. Check that the database file exists and is accessible.

### Log Files

Check the log files in the `logs` directory for detailed error information:

```bash
ls -la logs/
cat logs/latest_log_file.log
```

## Reporting Issues

If you encounter any issues during testing, please document:

1. The specific feature or functionality being tested
2. The steps to reproduce the issue
3. Any error messages or unexpected behavior
4. Your environment details (OS, Python version, etc.)