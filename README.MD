
**Electronic Funds Transfer Processing System for Central Region Water Board, Malawi**

## 🚀 Tech Stack
- **Python 3.14+**
- **Django 5.0.6**
- **MySQL 8.0+** (Production) / **SQLite** (Development)
- **Bootstrap 5**
- **RBM EFT Format Compliance**

## 📋 Features
- **RBM-Compliant EFT Processing** - Full compliance with Reserve Bank of Malawi specifications
- **Multi-Role Access Control** - System Admin, Accounts Personnel, Authorizer
- **Batch Processing** - Create, edit, submit, and approve payment batches
- **Master Data Management** - Banks, Zones, Schemes, Suppliers, Debit Accounts
- **Auto-Cost Center Assignment** - Smart cost center mapping from schemes
- **Audit Trail** - Complete transaction history and approval logs
- **Excel Export** - Export batches to RBM-compatible Excel format
- **Real-time Validation** - Form validation with instant feedback

---

## 🚀 INSTALLATION GUIDE

### Step 1: Clone the Repository
```bash
git clone https://github.com/YOUR-USERNAME/crwb-eft-system.git
cd crwb-eft-system
Step 2: Create Virtual Environment
bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
Step 3: Install Python Dependencies
bash
pip install -r requirements.txt
Requirements.txt contents:

txt
Django==5.0.6
mysqlclient==2.2.4
django-crispy-forms==2.1
crispy-bootstrap5==2024.1
Pillow==10.3.0
python-dotenv==1.0.0
openpyxl==3.1.2
reportlab==4.1.0

Step 4: MySQL Database Setup
A. Install MySQL (Windows)
Download MySQL Installer: https://dev.mysql.com/downloads/installer/

Choose "Developer Default"

Set root password (Example: CrwbEft@2025)

Complete installation

Keep MySQL Server running

B. Create Database (MUST MATCH settings.py)
sql
-- Open MySQL Command Line Client or MySQL Workbench
-- Login as root
mysql -u root -p

-- Create database EXACTLY as configured in settings.py
CREATE DATABASE crwbeftdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user EXACTLY as configured in settings.py
CREATE USER 'crwbeftuser'@'localhost' IDENTIFIED BY 'CrwbEft@2025';

-- Grant privileges
GRANT ALL PRIVILEGES ON crwbeftdb.* TO 'crwbeftuser'@'localhost';
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;
EXIT;
Step 5: Configure Environment Variables
bash
# Copy the environment template
copy .env.example .env  # Windows
# or
cp .env.example .env    # Linux/Mac
Edit .env file with your configuration:

env
# Django Secret Key
SECRET_KEY=django-insecure-your-secret-key-here-change-this

# Debug Mode (True for development)
DEBUG=True

# Allowed Hosts
ALLOWED_HOSTS=localhost,127.0.0.1

# MySQL Database Configuration
# MUST MATCH the database you created in Step 4B
DB_NAME=crwbeftdb
DB_USER=crwbeftuser
DB_PASSWORD=CrwbEft@2025
DB_HOST=localhost
DB_PORT=3306
DB_ENGINE=django.db.backends.mysql


Step 6: Database Migration
bash
# Apply database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (admin)
python manage.py createsuperuser
# Follow prompts to create admin account
Step 7: Load Sample Data (Optional)
bash
# Create sample data for testing
python manage.py loaddata sample_data.json
Step 8: Run Development Server
bash
python manage.py runserver
Step 9: Access the Application
Open browser: http://localhost:8000

Login with superuser credentials

Navigate to different modules

📊 DEFAULT LOGIN CREDENTIALS
After loading sample data:

Super Admin: (created)

Accounts User: accounts / test@1234

Authorizer User: authorizer / test@1234

🏗️ PROJECT STRUCTURE
text
crwb-eft-system/
├── eft_app/                 # Main application
│   ├── migrations/          # Database migrations
│   ├── templates/           # HTML templates
│   │   ├── accounts/        # Accounts module
│   │   ├── system_admin/    # Admin module
│   │   └── authorizer/      # Authorizer module
│   ├── models.py            # Database models
│   ├── views.py             # View logic
│   ├── urls.py              # URL routing
│   ├── forms.py             # Forms
│   └── admin.py             # Admin interface
├── eft_system/              # Django project
│   ├── settings.py          # Configuration (CRITICAL)
│   ├── urls.py              # Root URLs
│   └── wsgi.py              # WSGI config
├── requirements.txt         # Python dependencies
├── manage.py               # Django CLI
├── .env.example            # Environment template
├── .gitignore             # Git ignore rules
├── README.md              # This file
└── sample_data.json       # Sample data
⚙️ CRITICAL SETTINGS (settings.py)
Database Configuration MUST Match MySQL Setup:

python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # Must be MySQL
        'NAME': 'crwbeftdb',                   # MUST match created DB
        'USER': 'crwbeftuser',                 # MUST match created user
        'PASSWORD': 'CrwbEft@2025',            # MUST match user password
        'HOST': 'localhost',                   # Local MySQL server
        'PORT': '3306',                        # Default MySQL port
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        }
    }
}
🐛 TROUBLESHOOTING
MySQL Connection Issues:
bash
# 1. Check MySQL service is running
# Windows: Services.msc → MySQL80 → Start

# 2. Verify database exists
mysql -u root -p -e "SHOW DATABASES;"

# 3. Test connection
python manage.py dbshell

# 4. Check MySQL client installation
pip list | grep mysql
Migration Issues:
bash
# Reset migrations (Development only!)
python manage.py migrate --fake eft_app zero
python manage.py makemigrations eft_app
python manage.py migrate
Common Errors:
"Access denied for user": Check DB_USER and DB_PASSWORD in .env

"Unknown database": Database name doesn't match settings.py

MySQL not installed: Install MySQL 8.0+ first

Port 3306 in use: Change MySQL port or stop conflicting service



Address: Central Region Water Board, Lilongwe, Malawi

Version: 1.0.0
Last Updated: February 2025
Compatible with: Python 3.14+, Django 5.0.6, MySQL 8.0+
License: Proprietary - CRWB Malawi