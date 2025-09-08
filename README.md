# Toby's Terminal - CSS Billing System

A comprehensive billing and management system for CSS with both desktop and web interfaces.

## Overview

Toby's Terminal is a specialized application designed to manage invoices, customers, payments, and production tracking for CSS Billing. It consists of two main components:

1. **Desktop Application**: A tkinter-based GUI application for local use
2. **Web Application**: A Flask-based web interface for remote access

## Features

- **Customer Management**: Track customer information and profiles
- **Invoice Tracking**: Manage invoices and their statuses
- **Payment Reconciliation**: Track and reconcile payments
- **Statement Generation**: Generate customer statements for specific date ranges
- **Production Tracking**: Monitor production status for different companies (IMM, Harlestons)
- **A/R Reports**: Generate accounts receivable reports
- **Data Import/Export**: Import data from CSV files and export to various formats

## Installation

### Prerequisites

- Python 3.8 or higher
- SQLite3

### Setup

1. Clone this repository:
   ```
   git clone https://github.com/cssswagchs/Tobys-3.git
   cd tobys-terminal
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the desktop application:
   ```
   python -m tobys_terminal.desktop.main
   ```

4. Run the web application:
   ```
   python -m tobys_terminal.web.app
   ```

## Configuration

The application uses a configuration file (`config.py`) to set various parameters:

- **Database Path**: Set via the `TOBYS_TERMINAL_DB` environment variable or defaults to `terminal.db` in the project root
- **Export Directories**: Configured for statements, reports, and other exports
- **UI Settings**: Theme and font configurations
- **Status Options**: Predefined status options for production tracking

## Usage

### Desktop Application

The desktop application provides a GUI interface with the following main sections:

- **Import**: Import customers, orders, and payments from CSV files
- **Views**: Access various views like customer statements, A/R reports, and reconciliation
- **Utilities**: Additional tools like production tracking and oldest invoice finder

### Web Application

The web application provides similar functionality through a browser interface, with additional features:

- **Authentication**: User login and access control
- **Customer Portal**: Allow customers to view their invoices and statements
- **Admin Dashboard**: Manage users and system settings

## Development

### Project Structure

```
tobys_terminal/
├── desktop/           # Desktop application code
│   ├── gui/           # GUI components
│   ├── importers/     # Data import functionality
│   └── main.py        # Desktop application entry point
├── shared/            # Shared code between desktop and web
│   ├── assets/        # Images and other assets
│   ├── data/          # Data files
│   ├── exports/       # Export directories
│   └── utils/         # Utility functions
└── web/               # Web application code
    ├── routes/        # Flask routes
    ├── static/        # Static files
    ├── templates/     # HTML templates
    └── app.py         # Web application entry point
```

### Database Schema

The application uses SQLite with the following main tables:

- **customers**: Customer information
- **invoices**: Invoice details
- **payments**: Payment records
- **customer_profiles**: Additional customer metadata
- **statement_tracking**: Statement generation tracking

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

## Author

Developed by Leslie for Toby's Terminal.


cd tobys_terminal-3
git remote add origin https://github.com/cssswagchs/Tobys-3.git

When you make changes to the code:

```bash
git add .
git commit -m "Description of changes"
git push
```


pip install -e .