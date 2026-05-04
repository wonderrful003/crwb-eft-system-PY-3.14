Here is your updated Markdown with the correct RBM OBDX Payment File fields documented:

---

# 🏦 CRWB EFT Payment Processing System

**Electronic Funds Transfer System for Central Region Water Board, Malawi**

---

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features) 
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Database Flush & Reset](#database-flush--reset)
- [Loading Reference Data](#loading-reference-data)
- [Sample Data Contents](#sample-data-contents)
- [Project Structure](#project-structure)
- [RBM Compliance](#rbm-compliance)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

---

## 📖 Overview

The CRWB EFT System is a web-based payment processing application designed specifically for Central Region Water Board, Malawi. It facilitates electronic funds transfer operations while ensuring full compliance with Reserve Bank of Malawi (RBM) OBDX Payment File specifications.

---

## ✨ Features

### 🏢 Master Data Management
- **Banks**: 12+ financial institutions with SWIFT codes
- **Zones**: 5 CRWB operational zones
- **Schemes**: 25+ water schemes with auto-cost center assignment
- **Suppliers**: 5+ beneficiary/vendor management
- **Debit Accounts**: 5 CRWB bank accounts

### 👥 User Management
- **System Administrators**: Full system access and configuration
- **Accounts Personnel**: Batch creation and transaction management
- **Finance Manager**: Stage 1 approval (review)
- **Director of Finance**: Final approval

### 🔄 Workflow Management
- Batch creation and editing
- Transaction addition/removal
- Two-stage approval workflow
- Complete audit trail

### 📊 RBM Compliance
- Automatic RBM OBDX Payment File format generation
- Validation of all 17 required body fields
- Text file export in RBM-compatible format
- Real-time compliance checking
- OBDXPMN naming convention: `OBDXPMN_PARTYID_28JUN2025XXXXXXXXXXX.txt`

---

## 🛠 Tech Stack

### Backend
- **Python 3.14+**
- **Django 5.0.6**
- **MySQL 8.0+** (Production)
- **SQLite** (Development - optional)

### Frontend
- **Bootstrap 5**
- **jQuery 3.6**
- **Font Awesome 6**

### Key Dependencies
- `mysqlclient`: MySQL database connector
- `django-crispy-forms`: Form rendering
- `crispy-bootstrap5`: Bootstrap 5 integration
- `Pillow`: Image processing
- `python-dotenv`: Environment variable management
- `openpyxl`: Excel file generation
- `xlwt`: Excel export functionality
- `reportlab`: PDF generation

---

## 📋 Prerequisites

### Software Requirements
- Python 3.14 or higher
- MySQL 8.0 or higher
- Git
- pip (Python package manager)

### Windows Specific
- MySQL Installer for Windows
- Visual C++ Redistributable (for mysqlclient)

---

## 🚀 Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/wonderrful003/crwb-eft-system-PY-3.14.git
cd crwb-eft-system
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

**Requirements.txt:**
```
Django==5.0.6
mysqlclient==2.2.4
django-crispy-forms==2.1
crispy-bootstrap5==2024.1
Pillow==10.3.0
python-dotenv==1.0.0
openpyxl==3.1.2
xlwt==1.3.0
reportlab==4.1.0
asgiref==3.7.2
sqlparse==0.4.4
tzdata==2024.1
```

---

## 🗄️ Database Setup

### MySQL Installation (Windows)

1. Download MySQL Installer: https://dev.mysql.com/downloads/installer/
2. Run installer and choose "Developer Default"
3. Set root password during installation
4. Complete installation and start MySQL service

### Create Database

```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create database (MUST match settings.py)
CREATE DATABASE crwb_eft_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create database user (MUST match settings.py)
CREATE USER 'root'@'localhost' IDENTIFIED BY 'your_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON crwb_eft_system.* TO 'root'@'localhost';
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;
EXIT;
```

**IMPORTANT**: Database name must exactly match your `settings.py` configuration.

---

## ⚙️ Configuration

### Step 1: Copy Environment Template
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### Step 2: Edit .env File

Open `.env` and configure:

```env
# Django Settings
SECRET_KEY=django-insecure-your-secret-key-here-change-this
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# MySQL Configuration (MUST match your MySQL setup)
DB_NAME=crwb_eft_system
DB_USER=root
DB_PASSWORD=your_password_here  # Change this
DB_HOST=localhost
DB_PORT=3306

# Optional: Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Step 3: Verify Database Configuration

Ensure `eft_system/settings.py` matches:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'crwb_eft_system'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```

---

## 🏃 Running the Application

### Step 1: Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 2: Create Superuser
```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

### Step 3: Load Reference Data
```bash
# Navigate to backup folder and load reference data
python manage.py loaddata backup/reference_data.json
```

### Step 4: Start Development Server
```bash
python manage.py runserver
```

### Step 5: Access Application
1. Open browser: http://localhost:8000
2. Login with superuser credentials
3. Navigate to different modules

---

## 💾 Database Flush & Reset

When making significant changes to the database structure or when you need a clean slate, use these commands to flush and reset your database.

### ⚠️ **WARNING: These commands will DELETE ALL DATA in your database!**

### Option 1: Complete Database Reset with Reference Data (Recommended)

```bash
# Step 1: Drop and recreate the database
mysql -u root -p -e "DROP DATABASE IF EXISTS crwb_eft_system; CREATE DATABASE crwb_eft_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Step 2: Remove all migration files (except __init__.py)
# Windows PowerShell
Remove-Item eft_app/migrations/0*.py
Remove-Item eft_app/migrations/__pycache__/* -Recurse -Force

# Linux/Mac
rm -f eft_app/migrations/0*.py
rm -rf eft_app/migrations/__pycache__

# Step 3: Create fresh migrations
python manage.py makemigrations eft_app

# Step 4: Apply migrations
python manage.py migrate

# Step 5: Create new superuser
python manage.py createsuperuser

# Step 6: Load reference data from backup folder
python manage.py loaddata backup/reference_data.json
```

### Option 2: Quick Reset with Flush Command

```bash
# This clears all data but keeps table structure
python manage.py flush

# Then reload reference data
python manage.py loaddata backup/reference_data.json
```

### Option 3: Full Reset Script (Windows PowerShell)

Create a file named `reset_db.ps1` in the project root:

```powershell
# reset_db.ps1
Write-Host "⚠️  WARNING: This will DELETE ALL DATA in the database!" -ForegroundColor Red
$confirmation = Read-Host "Are you sure you want to continue? (y/N)"

if ($confirmation -eq 'y') {
    Write-Host "🔄 Dropping and recreating database..." -ForegroundColor Yellow
    mysql -u root -p -e "DROP DATABASE IF EXISTS crwb_eft_system; CREATE DATABASE crwb_eft_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    
    Write-Host "🔄 Removing migration files..." -ForegroundColor Yellow
    Remove-Item eft_app/migrations/0*.py -ErrorAction SilentlyContinue
    Remove-Item eft_app/migrations/__pycache__/* -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Host "🔄 Creating fresh migrations..." -ForegroundColor Yellow
    python manage.py makemigrations eft_app
    
    Write-Host "🔄 Applying migrations..." -ForegroundColor Yellow
    python manage.py migrate
    
    Write-Host "🔄 Creating superuser..." -ForegroundColor Yellow
    python manage.py createsuperuser
    
    Write-Host "🔄 Loading reference data..." -ForegroundColor Yellow
    python manage.py loaddata backup/reference_data.json
    
    Write-Host "✅ Database reset and data load complete!" -ForegroundColor Green
} else {
    Write-Host "❌ Operation cancelled" -ForegroundColor Red
}
```

Run with:
```powershell
.\reset_db.ps1
```

### Option 4: Full Reset Script (Linux/Mac Bash)

Create a file named `reset_db.sh` in the project root:

```bash
#!/bin/bash
# reset_db.sh

echo -e "\e[31m⚠️  WARNING: This will DELETE ALL DATA in the database!\e[0m"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "\e[33m🔄 Dropping and recreating database...\e[0m"
    mysql -u root -p -e "DROP DATABASE IF EXISTS crwb_eft_system; CREATE DATABASE crwb_eft_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    
    echo -e "\e[33m🔄 Removing migration files...\e[0m"
    rm -f eft_app/migrations/0*.py
    rm -rf eft_app/migrations/__pycache__
    
    echo -e "\e[33m🔄 Creating fresh migrations...\e[0m"
    python manage.py makemigrations eft_app
    
    echo -e "\e[33m🔄 Applying migrations...\e[0m"
    python manage.py migrate
    
    echo -e "\e[33m🔄 Creating superuser...\e[0m"
    python manage.py createsuperuser
    
    echo -e "\e[33m🔄 Loading reference data...\e[0m"
    python manage.py loaddata backup/reference_data.json
    
    echo -e "\e[32m✅ Database reset and data load complete!\e[0m"
else
    echo -e "\e[31m❌ Operation cancelled\e[0m"
fi
```

Make the script executable:
```bash
chmod +x reset_db.sh
./reset_db.sh
```

---

## 📥 Loading Reference Data

### Method 1: Using Django Loaddata Command

```bash
# Navigate to project root and load the reference data
python manage.py loaddata backup/reference_data.json
```

### Method 2: If You Get Integrity Errors

If you encounter foreign key or integrity errors when loading data:

```bash
# Load in specific order to respect dependencies
python manage.py loaddata backup/reference_data.json --ignorenonexistent
```

### Method 3: Load Data After Fresh Migration

```bash
# Complete fresh start
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata backup/reference_data.json
```

### Method 4: Using Python Shell to Load Data

Create a script `load_reference_data.py`:

```python
# load_reference_data.py
from django.core.management import call_command
import os

def load_reference_data():
    """Load reference data from backup folder"""
    data_file = os.path.join('backup', 'reference_data.json')
    
    if os.path.exists(data_file):
        print(f"Loading data from {data_file}...")
        call_command('loaddata', data_file)
        print("✅ Reference data loaded successfully!")
    else:
        print(f"❌ Data file not found: {data_file}")

if __name__ == "__main__":
    load_reference_data()
```

Run with:
```bash
python manage.py shell < load_reference_data.py
```

---

## 📊 Sample Data Contents

The `reference_data.json` file contains the following master data:

### Banks (12)
| ID | Bank Name | SWIFT Code | Status |
|----|-----------|------------|--------|
| 1 | National Bank of Malawi | NBMAMWMW | Active |
| 2 | Standard Bank PLC | SBICMWMX | Active |
| 3 | Reserve Bank of Malawi | RBMAMWMW | Active |
| 4 | FDH Bank PLC | FDHFMWMW | Active |
| 5 | NBS Bank PLC | NBSTMWMW | Active |
| 6 | wonder | WNTMWM12344 | Inactive |
| 7 | Centenary Bank Limited | MBBCMWMW | Active |
| 8 | First Capital Bank PLC | FRCGMWMW | Active |
| 9 | Ecobank Malawi Limited | ECOCMWMW | Active |
| 10 | CDH Investment Bank | CDHIMWMW | Active |
| 11 | MyBucks Banking Corporation | NFBMMWMW | Active |
| 12 | First Discount House Limited | FDHDMWMW | Active |

### Zones (5)
| ID | Zone Code | Zone Name |
|----|-----------|-----------|
| 1 | HQ_ADMIN | Headquarters (Lilongwe) |
| 2 | KS_ZONE | Kasungu Zone |
| 3 | MP_ZONE | Mponela Zone |
| 4 | SL_ZONE | Salima Zone |
| 5 | DZ_ZONE | Dedza Zone |

### Schemes (25+)
| ID | Scheme Code | Scheme Name | Zone |
|----|-------------|-------------|------|
| 1 | 03000101 | HQ Administration | HQ_ADMIN |
| 2 | 10019525 | Mponela Main Scheme | MP_ZONE |
| 3 | 10019524 | Salima Town Scheme | SL_ZONE |
| 4 | 10019523 | Dedza Boma Scheme | DZ_ZONE |
| 5 | 10019530 | Kasungu Boma Scheme | KS_ZONE |
| 6-10 | SALIMA_01 to SALIMA_05 | Various Salima schemes | SL_ZONE |
| 11-14 | DEDZA_01 to DEDZA_04 | Various Dedza schemes | DZ_ZONE |
| 15-21 | KASUNGU_01 to KASUNGU_07 | Various Kasungu schemes | KS_ZONE |
| 22-25 | MPONELA_01 to MPONELA_04 | Various Mponela schemes | MP_ZONE |

### Suppliers (5)
| ID | Supplier Code | Supplier Name | Bank |
|----|--------------|---------------|------|
| 1 | 57819 | Bella Enterprise Pvt Ltd | National Bank |
| 2 | 3 | Anderson Trading | Standard Bank |
| 3 | 408 | City Center Security | Standard Bank |
| 4 | 391 | Jibs Security Services | Standard Bank |
| 5 | 392 | Easy Access Solutions | Standard Bank |

### Debit Accounts (5)
| ID | Account Number | Account Name |
|----|---------------|--------------|
| 1 | 13006161244 | (ORT) MG Other Recurrent Expenditure A/C |
| 2 | 13006161245 | (ORT) MG Capital Expenditure A/C |
| 3 | 13006161246 | (ORT) MG Salaries A/C |
| 4 | 13006161247 | (ORT) MG Project Funds A/C |
| 5 | 34456699805 | TEST Account |

---

## 📁 Project Structure

```
crwb-eft-system/
├── eft_app/                    # Main Django application
│   ├── migrations/            # Database migrations
│   ├── templates/             # HTML templates
│   │   ├── admin/             # System admin templates
│   │   ├── accounts/          # Accounts personnel templates
│   │   ├── finance_manager/   # Finance manager templates
│   │   ├── director/          # Director of finance templates
│   │   └── registration/      # Authentication templates
│   ├── models.py              # Database models
│   ├── views.py               # View logic
│   ├── urls.py                # URL routing
│   ├── forms.py               # Django forms
│   ├── admin.py               # Django admin interface
│   ├── eft_generator.py       # RBM OBDX Payment File generator
│   └── apps.py                # App configuration
├── eft_system/                # Django project
│   ├── settings.py            # Project settings
│   ├── urls.py                # Root URL configuration
│   └── wsgi.py                # WSGI configuration
├── backup/                    # Backup folder
│   └── reference_data.json    # Master reference data
├── requirements.txt           # Python dependencies
├── manage.py                  # Django management script
├── reset_db.ps1               # Windows reset script
├── reset_db.sh                # Linux/Mac reset script
├── load_reference_data.py     # Data loading script
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
└── README.md                  # This documentation
```

---

## 🏦 RBM Compliance

### File Naming Convention (OBDX Payment File)

```
Format: OBDXPMN_PARTYID_28JUN2025XXXXXXXXXXX.txt

Example: OBDXPMN_001300616_28JUN2025BATCH001.txt
```

- **OBDXPMN**: Payment file identifier (domestic payments to suppliers)
- **PARTY ID**: First 9 digits of CRWB's debit account number (e.g., 001300616)
- **DATE**: Format `DDMMMYYYY` (e.g., 28JUN2025)
- **Unique ID**: Batch reference or unique identifier (max 50 characters total)

### Header Record (5 fields) - Semicolon Delimited

| Field | Description | Format | Example |
|-------|-------------|--------|---------|
| 0 | Header Line Identifier | Fixed "0" | `0` |
| 1 | File Reference | Max 16 chars | `REF2025123001` |
| 2 | Currency Code | 3 chars | `MWK` |
| 3 | File Total | 2 decimal places | `1000000.00` |
| 4 | Total Count | Zero-padded to 4 digits | `0042` |

### Body Record (17 fields) - Semicolon Delimited

| Field | Description | Max Length | Required | Example |
|-------|-------------|------------|----------|---------|
| 0 | Line Items Identifier | Fixed "1" | Yes | `1` |
| 1 | Transaction Serial | 4 digits (zero-padded) | Yes | `0001` |
| 2 | Currency Code | 3 chars | Yes | `MWK` |
| 3 | Debit Account Number | 20 chars | Yes | `0013006161228` |
| 4 | Debit Account Name | 55 chars | Yes | `CRWB LTD` |
| 5 | Payment Amount | 2 decimals | Yes | `5000.25` |
| 6 | Payee Details | 55 chars | Yes | `Bella Enterprise Pvt Ltd` |
| 7 | Vendor Code | 7 chars | Yes | `57819` |
| 8 | Employee Number | 6 chars | No | `` |
| 9 | National ID | 8 chars | No | `` |
| 10 | Invoice Number | 16 chars | Yes | `INV-2025-001` |
| 11 | Payee BIC | 11 chars | Yes | `NBMAMWMW` |
| 12 | Credit Account Number | 20 chars | Yes | `1234567890` |
| 13 | Cost Center | 50 chars | Yes | `03000101` |
| 14 | DATE | EMPTY (produces ;;) | No | `` |
| 15 | Source Reference | 18 chars | Yes | `IFMIS-REF-001` |
| 16 | Description | 200 chars | Yes | `Payment for water treatment chemicals` |

### Sample Output File

```
0;REF2025123001;MWK;10000.50;0002
1;0001;MWK;0013006161228;CRWB LTD;5000.25;Bella Enterprise Pvt Ltd;57819;;;INV-2025-001;NBMAMWMW;1234567890;03000101;;IFMIS-REF-001;Payment for water treatment chemicals
1;0002;MWK;0013006161228;CRWB LTD;5000.25;Anderson Trading;0003;;;INV-2025-002;SBICMWMX;9876543210;03000101;;IFMIS-REF-002;Payment for office supplies
```

### Field Validation Rules

1. **Record Type** must be `0` for header, `1` for body
2. **Sequence Numbers** must be zero-padded to 4 digits (0001, 0002, etc.)
3. **Currency** must be consistent across all transactions in a batch
4. **Payment Amount** must have exactly 2 decimal places
5. **Payee BIC** must be valid SWIFT code (8 or 11 characters)
6. **Total Count** in header must match number of body records
7. **File Total** in header must match sum of all Payment Amounts
8. **DATE field (Field 14)** must be EMPTY (produces `;;` in output)

---

## 🐛 Troubleshooting

### Common Issues

#### 1. MySQL Connection Error
**Error**: `django.db.utils.OperationalError: (2003, "Can't connect to MySQL server")`

**Solution**:
```bash
# Check MySQL service is running
# Windows: Open Services (services.msc) → Find MySQL80 → Start

# Verify MySQL installation
mysql --version

# Test connection manually
mysql -u root -p
```

#### 2. Database Access Denied
**Error**: `Access denied for user 'root'@'localhost'`

**Solution**:
```sql
-- Grant privileges again
GRANT ALL PRIVILEGES ON crwb_eft_system.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

#### 3. Missing mysqlclient
**Error**: `mysqlclient 2.0.3 or newer is required`

**Solution**:
```bash
# Windows: Download appropriate wheel
pip install mysqlclient-2.2.4-cp314-cp314-win_amd64.whl

# Or install using pip
pip install mysqlclient
```

#### 4. Reference Data Loading Errors
**Error**: `IntegrityError: Foreign key constraint failed`

**Solution**:
```bash
# Load data with --ignorenonexistent flag
python manage.py loaddata backup/reference_data.json --ignorenonexistent

# Or load in correct order:
python manage.py loaddata backup/reference_data.json --natural-foreign
```

#### 5. "backup/reference_data.json" File Not Found
**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'backup/reference_data.json'`

**Solution**:
```bash
# Check if backup folder exists
dir backup  # Windows
ls -la backup/  # Linux/Mac

# Create backup folder if it doesn't exist
mkdir backup

# Move reference_data.json to backup folder
move reference_data.json backup/  # Windows
mv reference_data.json backup/    # Linux/Mac
```

#### 6. User Delete 405 Error Fix
If you encounter "Method Not Allowed (GET)" when trying to delete users, ensure:
- Delete links point to `/system-admin/users/[id]/delete/confirm/`
- The actual delete URL uses POST method
- You have the `user_delete_confirm` view defined

---

## 🆘 Support

### Contact Information
- **Developer**: CRWB ICT Department
- **Email**: support@crwb.mw
- **Phone**: +265 (0) 1 234 567

### Documentation
- Django Documentation: https://docs.djangoproject.com/
- MySQL Documentation: https://dev.mysql.com/doc/
- Bootstrap Documentation: https://getbootstrap.com/docs/

### Issue Reporting
1. Check existing issues on GitHub
2. Create new issue with detailed description
3. Include error messages and steps to reproduce

---

## 📄 License

This software is proprietary and developed exclusively for Central Region Water Board, Malawi. Unauthorized distribution or use is prohibited.

---

## 📅 Version Information

- **Version**: 2.0.0
- **Release Date**: March 2026
- **Compatibility**: Python 3.14+, Django 5.0.6, MySQL 8.0+
- **Key Updates**: 
  - Two-stage approval workflow (Finance Manager + Director)
  - User delete confirmation page
  - Enhanced audit logging
  - RBM OBDX Payment File compliance
  - Reference data in backup folder
- **Last Updated**: March 2026

---

## 🔄 Quick Reset Commands Summary

For quick reference, here are all reset commands in one place:

### Windows PowerShell
```powershell
# Complete reset with data load
mysql -u root -p -e "DROP DATABASE IF EXISTS crwb_eft_system; CREATE DATABASE crwb_eft_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
Remove-Item eft_app/migrations/0*.py -ErrorAction SilentlyContinue
python manage.py makemigrations eft_app
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata backup/reference_data.json
```

### Linux/Mac
```bash
# Complete reset with data load
mysql -u root -p -e "DROP DATABASE IF EXISTS crwb_eft_system; CREATE DATABASE crwb_eft_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
rm -f eft_app/migrations/0*.py
python manage.py makemigrations eft_app
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata backup/reference_data.json
```

### One-Liner for Quick Reset (after migrations)
```bash
python manage.py flush --noinput && python manage.py loaddata backup/reference_data.json
```
---

**Developed for**: Central Region Water Board, Malawi  
**Purpose**: Electronic Funds Transfer Processing System  
**File Format**: RBM OBDX Payment File (OBDXPMN)  
**Compliance**: Reserve Bank of Malawi (RBM) Standards