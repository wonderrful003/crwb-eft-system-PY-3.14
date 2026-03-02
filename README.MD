
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
- [Sample Data](#sample-data)
- [Project Structure](#project-structure)
- [RBM Compliance](#rbm-compliance)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

---

## 📖 Overview

The CRWB EFT System is a web-based payment processing application designed specifically for Central Region Water Board, Malawi. It facilitates electronic funds transfer operations while ensuring full compliance with Reserve Bank of Malawi (RBM) specifications.

## ✨ Features

### 🏢 Master Data Management
- **Banks**: Manage financial institutions with SWIFT codes
- **Zones**: CRWB operational zones
- **Schemes**: Water schemes with auto-cost center assignment
- **Suppliers**: Beneficiary/vendor management
- **Debit Accounts**: CRWB bank accounts

### 💼 Role-Based Access Control
- **System Administrators**: Full system access and configuration
- **Accounts Personnel**: Batch creation and transaction management
- **Authorizers**: Approval workflow and compliance verification

### 🔄 Workflow Management
- Batch creation and editing
- Transaction addition/removal
- Submission for approval
- Approval/Rejection workflow
- Complete audit trail

### 📊 RBM Compliance
- Automatic RBM file format generation
- Validation of all required fields
- Excel export in RBM-compatible format
- Real-time compliance checking

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
- **DataTables**
- **Font Awesome 6**

### Key Dependencies
- `mysqlclient`: MySQL database connector
- `django-crispy-forms`: Form rendering
- `openpyxl`: Excel file generation
- `reportlab`: PDF generation
- `Pillow`: Image processing

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
        'NAME': 'crwb_eft_system',        # Must match DB_NAME in .env
        'USER': 'root',                    # Must match DB_USER in .env
        'PASSWORD': '',                    # Change this - Must match DB_PASSWORD in .env
        'HOST': 'localhost',
        'PORT': '3306',
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

### Step 3: Load Sample Data (Optional)
```bash
python manage.py loaddata eft_config_data.json
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

## 📊 Sample Data

The system includes pre-loaded sample data:

### Banks (6)
- National Bank of Malawi (NBMAMWMW)
- Standard Bank PLC (SBICMWMX)
- Reserve Bank of Malawi (RBMAMWMW)
- FDH Bank PLC (FDHFMWMW)
- NBS Bank PLC (NBSTMWMW)

### Zones (5)
- HQ_ADMIN - Headquarters (Lilongwe)
- KS_ZONE - Kasungu Zone
- MP_ZONE - Mponela Zone
- SL_ZONE - Salima Zone
- DZ_ZONE - Dedza Zone

### Schemes (5)
- 03000101 - HQ Administration
- 10019525 - Mponela Main Scheme
- 10019524 - Salima Town Scheme
- 10019523 - Dedza Boma Scheme
- 10019530 - Kasungu Boma Scheme

### Suppliers (5)
- Bella Enterprise Pvt Ltd
- Anderson Trading
- City Center Security
- Jibs Security Services
- Easy Access Solutions

### Debit Accounts (5)
- 13006161244 - (ORT) MG Other Recurrent Expenditure A/C
- 13006161245 - (ORT) MG Capital Expenditure A/C
- 13006161246 - (ORT) MG Salaries A/C
- 13006161247 - (ORT) MG Project Funds A/C

---

## 📁 Project Structure

```
crwb-eft-system/
├── eft_app/                    # Main Django application
│   ├── migrations/            # Database migrations
│   ├── templates/             # HTML templates
│   │   ├── accounts/          # Accounts personnel templates
│   │   ├── system_admin/      # System admin templates
│   │   ├── authorizer/        # Authorizer templates
│   │   └── registration/      # Authentication templates
│   ├── models.py              # Database models
│   ├── views.py               # View logic (5000+ lines)
│   ├── urls.py                # URL routing
│   ├── forms.py               # Django forms
│   ├── admin.py               # Django admin interface
│   └── apps.py                # App configuration
├── eft_system/                # Django project
│   ├── settings.py            # Project settings (CRITICAL)
│   ├── urls.py                # Root URL configuration
│   └── wsgi.py                # WSGI configuration
├── requirements.txt           # Python dependencies
├── manage.py                  # Django management script
├── sample_data.json           # Sample database data
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
└── README.md                  # This documentation
```

---

## 🏦 RBM Compliance

### Transaction Format
The system generates RBM-compliant EFT files with exact format:

```
1;[Sequence];MWK;[Account];[Name];[Amount];[Details1];[Details2];;;;;[BIC];[CreditAcc];;;;[Ref];[Desc]
```

### Required Fields
1. **Record Type** (1=Detail)
2. **Sequence Number** (4 digits, zero-padded)
3. **Currency** (MWK)
4. **Debit Account Number** (20 characters)
5. **Debit Account Name** (55 characters)
6. **Payment Amount** (2 decimal places)
7. **Payee Details 1** (55 characters)
8. **Payee Details 2** (7 characters, vendor code)
9-12. **Payment Details 3-6** (Optional)
13. **Beneficiary Bank BIC** (8 or 11 characters)
14. **Credit Account Number** (20 characters)
15-17. **Mandate Details** (Optional)
18. **Originator's Reference** (18 characters, IFMIS reference)
19. **Transaction Description** (200 characters)

### Validation Rules
- All required fields must be populated
- Amounts must have exactly 2 decimal places
- SWIFT codes must be valid (8 or 11 characters)
- Account numbers must be numeric
- Sequence numbers must be unique per batch

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
pip install mysqlclient-2.2.4-cp311-cp311-win_amd64.whl

# Or install from unofficial binary
pip install mysqlclient
```

#### 4. Migration Errors
```bash
# Reset migrations (development only!)
python manage.py migrate --fake eft_app zero
python manage.py makemigrations eft_app
python manage.py migrate
```

#### 5. Port Already in Use
```bash
# Kill process on port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID [PID] /F

# Linux/Mac:
lsof -ti:8000 | xargs kill -9
```

### Debug Mode
For development, ensure `DEBUG=True` in `.env` file to see detailed error messages.

---



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

- **Version**: 1.0.0
- **Release Date**: February 2025
- **Compatibility**: Python 3.14+, Django 5.0.6, MySQL 8.0+
- **Last Updated**: February 2025

---

**Developed by**: CRWB ICT Department  
**For**: Central Region Water Board, Malawi  
**Purpose**: Electronic Funds Transfer Processing System
```

