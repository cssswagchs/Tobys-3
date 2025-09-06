# Deployment Guide for Toby's Terminal

This guide provides instructions for deploying the Toby's Terminal application to GitHub and setting up the application in production environments.

## GitHub Deployment

### 1. Create a GitHub Repository

1. Go to [GitHub](https://github.com/) and sign in to your account
2. Click on the "+" icon in the top-right corner and select "New repository"
3. Enter a repository name (e.g., "tobys-terminal")
4. Add a description (optional)
5. Choose whether the repository should be public or private
6. Do not initialize the repository with a README, .gitignore, or license
7. Click "Create repository"

### 2. Push Your Code to GitHub

After creating the repository, you'll see instructions for pushing an existing repository. Follow these steps:

```bash
# Navigate to your project directory
cd path/to/tobys_terminal_clean

# Add the remote repository
git remote add origin https://github.com/yourusername/tobys-terminal.git

# Rename the default branch to main (optional but recommended)
git branch -M main

# Push your code to GitHub
git push -u origin main
```

### 3. Verify Your Repository

1. Refresh your GitHub repository page
2. Ensure all files have been uploaded correctly
3. Check that the README.md is displayed on the repository homepage

## Production Deployment

### 1. Server Requirements

- Python 3.8 or higher
- SQLite 3
- Required Python packages (see requirements.txt)

### 2. Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tobys-terminal.git
   cd tobys-terminal
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration:
   ```
   TOBYS_TERMINAL_DB=path/to/your/terminal.db
   ```

4. Create necessary directories:
   ```bash
   mkdir -p data_imports
   mkdir -p logs
   ```

5. Install the package:
   ```bash
   pip install -e .
   ```

### 3. Running the Desktop Application

```bash
python -m tobys_terminal.desktop.main
```

### 4. Running the Web Application

For development:
```bash
python -m tobys_terminal.web.app
```

For production, consider using a WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 tobys_terminal.web.app:app
```

### 5. Setting Up as a Service (Linux)

Create a systemd service file for the web application:

```bash
sudo nano /etc/systemd/system/tobys-terminal-web.service
```

Add the following content:

```
[Unit]
Description=Toby's Terminal Web Application
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/tobys-terminal
Environment="PATH=/path/to/venv/bin"
Environment="PYTHONPATH=/path/to/tobys-terminal"
Environment="TOBYS_TERMINAL_DB=/path/to/terminal.db"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 tobys_terminal.web.app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable tobys-terminal-web
sudo systemctl start tobys-terminal-web
```

## Updating the Application

To update the application with new changes:

```bash
# Navigate to your project directory
cd path/to/tobys-terminal

# Pull the latest changes
git pull

# Install any new dependencies
pip install -r requirements.txt

# Restart the service if running as a systemd service
sudo systemctl restart tobys-terminal-web
```

## Backup and Restore

### Creating Backups

Regularly back up your database file:

```bash
# Create a backup directory
mkdir -p backups

# Create a timestamped backup
cp path/to/terminal.db backups/terminal_$(date +%Y%m%d_%H%M%S).db
```

### Restoring from Backup

To restore from a backup:

```bash
# Stop the application if it's running
sudo systemctl stop tobys-terminal-web  # If using systemd

# Restore the database
cp backups/terminal_YYYYMMDD_HHMMSS.db path/to/terminal.db

# Restart the application
sudo systemctl start tobys-terminal-web  # If using systemd
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify the database path in your `.env` file
   - Check file permissions on the database file
   - Ensure the directory exists and is writable

2. **Module Not Found Errors**
   - Ensure the package is installed: `pip install -e .`
   - Check your PYTHONPATH environment variable

3. **Web Application Not Accessible**
   - Check if the service is running: `sudo systemctl status tobys-terminal-web`
   - Verify firewall settings allow access to port 5000
   - Check the application logs for errors