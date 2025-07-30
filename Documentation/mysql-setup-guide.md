# Comprehensive Guide: Migrating Local MySQL Database to Server Instance

## Table of Contents

1. [Overview](#1-overview)  
2. [Prerequisites](#2-prerequisites)  
3. [Phase 1: Server Setup](#3-phase-1-server-setup)  
4. [Phase 2: Data Migration](#4-phase-2-data-migration)  
5. [Phase 3: Application Configuration](#5-phase-3-application-configuration)  
6. [Phase 4: Remote Access Setup](#6-phase-4-remote-access-setup)  
7. [Phase 5: Validation & Testing](#7-phase-5-validation--testing)  
8. [Security & Maintenance](#8-security--maintenance)  
9. [Troubleshooting](#9-troubleshooting)  
10. [Quick Reference](#10-quick-reference)  
11. [Conclusion](#conclusion)

---

## 1. Overview

### 1.1 Purpose

This guide provides a complete, step‑by‑step process for migrating a local MySQL database to a server instance, enabling remote access for development teams while maintaining security and data integrity.

### 1.2 Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐
│  Local MySQL    │ ══> │  Server MySQL   │
│    Database     │     │    Database     │
└─────────────────┘     └─────────────────┘
         ↓                       ↑
┌─────────────────┐     ┌─────────────────┐
│   Local App     │     │  Remote Apps    │
│    Instance     │     │  (Team Access)  │
└─────────────────┘     └─────────────────┘
```

### 1.3 Migration Timeline

- **Phase 1:** Server Setup (2–3 hours)  
- **Phase 2:** Data Migration (1–2 hours)  
- **Phase 3:** Application Configuration (1 hour)  
- **Phase 4:** Remote Access Setup (1 hour)  
- **Phase 5:** Validation & Testing (1 hour)  

---

## 2. Prerequisites

### 2.1 Technical Requirements

**Server Requirements**

- **Operating System:** Ubuntu 20.04+, CentOS 8+, or Windows Server 2019+  
- **RAM:** Minimum 4 GB (8 GB recommended)  
- **Storage:** 50 GB+ available  
- **Network:** Static IP or domain name  
- **Ports:** 3306 open for remote access  

**Local Requirements**

- MySQL Client tools installed  
- Python 3.8+ with pip  
- Network access to the server  
- Administrator/root access  

### 2.2 Required Software

Install the following on both the local machine and the server:

```bash
# MySQL Server 8.0+
# MySQL Client tools
# Python 3.8+
# pip packages: pymysql, python-dotenv
```

### 2.3 Information Checklist

- Server IP address or hostname
- Root access credentials
- Current database size
- List of applications using the database
- Team member details for access

---

## 3. Phase 1: Server Setup

### 3.1 Install MySQL Server

#### Ubuntu/Debian

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install MySQL Server
sudo apt install mysql-server -y

# Start and enable MySQL
sudo systemctl start mysql
sudo systemctl enable mysql

# Check status
sudo systemctl status mysql
```

#### CentOS/RHEL

```bash
# Install MySQL repository
sudo yum install https://dev.mysql.com/get/mysql80-community-release-el8-1.noarch.rpm

# Install MySQL Server
sudo yum install mysql-server -y

# Start and enable MySQL
sudo systemctl start mysqld
sudo systemctl enable mysqld

# Get temporary root password
sudo grep 'temporary password' /var/log/mysqld.log
```

#### Windows Server

1. Download MySQL Installer from https://dev.mysql.com/downloads/installer/
2. Run installer and select **Server only**
3. Configure as **Dedicated MySQL Server**
4. Set a root password
5. Configure the MySQL Windows Service

### 3.2 Secure MySQL Installation

```bash
# Run security script
sudo mysql_secure_installation
```

Follow the prompts:
- Set root password: [STRONG_PASSWORD]
- Remove anonymous users: Y
- Disallow root login remotely: N (allowed temporarily)
- Remove test database: Y
- Reload privilege tables: Y

### 3.3 Configure MySQL for Remote Access

#### Edit MySQL Configuration

Locate the configuration file:
- Ubuntu/Debian: `/etc/mysql/mysql.conf.d/mysqld.cnf`
- CentOS/RHEL: `/etc/my.cnf`
- Windows: `C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`

Open and update:

```ini
[mysqld]
# Network settings
bind-address = 0.0.0.0
port = 3306
max_connections = 200

# Performance settings
innodb_buffer_pool_size = 1G
innodb_log_file_size    = 256M
innodb_flush_method     = O_DIRECT

# Security settings
local_infile    = 0
skip-name-resolve = 1

# Character set
character-set-server = utf8mb4
collation-server     = utf8mb4_unicode_ci
```

#### Restart MySQL

```bash
sudo systemctl restart mysql
```

### 3.4 Create Database and Users

```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create production database
CREATE DATABASE mobility_bot_server 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Create application user
CREATE USER 'mobility_app'@'%' 
IDENTIFIED BY 'App_Secure_Pass123!';

GRANT ALL PRIVILEGES ON mobility_bot_server.* 
TO 'mobility_app'@'%';

-- Create backup user (local only)
CREATE USER 'mobility_backup'@'localhost' 
IDENTIFIED BY 'Backup_Pass456!';

GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER 
ON mobility_bot_server.* 
TO 'mobility_backup'@'localhost';

-- Create admin user for remote management
CREATE USER 'mobility_admin'@'%' 
IDENTIFIED BY 'Admin_Pass789!';

GRANT ALL PRIVILEGES ON *.* 
TO 'mobility_admin'@'%' WITH GRANT OPTION;

-- Apply changes
FLUSH PRIVILEGES;

-- Verify users
SELECT User, Host, plugin 
FROM mysql.user 
WHERE User LIKE 'mobility%';
```

### 3.5 Validation Checkpoint 1

Create a script to validate the server setup:

```bash
#!/bin/bash
# validate_server_setup.sh

echo "=== MySQL Server Setup Validation ==="
echo

# Test 1: MySQL service status
echo -n "1. MySQL Service Status: "
if systemctl is-active --quiet mysql; then
    echo "✓ Running"
else
    echo "✗ Not running"
    exit 1
fi

# Test 2: Port 3306 listening
echo -n "2. MySQL Port 3306: "
if netstat -tuln | grep -q ":3306 "; then
    echo "✓ Listening"
else
    echo "✗ Not listening"
    exit 1
fi

# Test 3: Remote binding
echo -n "3. Remote Access Configuration: "
if mysql -u root -p -e "SHOW VARIABLES LIKE 'bind_address';" | grep -q "0.0.0.0"; then
    echo "✓ Configured"
else
    echo "✗ Not configured"
    exit 1
fi

# Test 4: Database exists
echo -n "4. Database Creation: "
if mysql -u root -p -e "SHOW DATABASES;" | grep -q "mobility_bot_server"; then
    echo "✓ Created"
else
    echo "✗ Not created"
    exit 1
fi

echo
echo "✓ All server setup validations passed!"
```

---

## 4. Phase 2: Data Migration

### 4.1 Export Local Database

Create an export script:

```bash
#!/bin/bash
# export_local_database.sh

# Configuration
LOCAL_HOST="localhost"
LOCAL_USER="root"
LOCAL_DB="mobility_bot"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/mobility_bot_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

echo "=== Exporting Local Database ==="
echo "Database: ${LOCAL_DB}"
echo "Output: ${BACKUP_FILE}"
echo

# Export database
mysqldump \
    -h "${LOCAL_HOST}" \
    -u "${LOCAL_USER}" \
    -p \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --add-drop-table \
    --complete-insert \
    --extended-insert \
    --lock-tables=false \
    "${LOCAL_DB}" > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✓ Export successful! Size: ${SIZE}"
    gzip "${BACKUP_FILE}"
    echo "✓ Compressed to ${BACKUP_FILE}.gz"
else
    echo "✗ Export failed!"
    exit 1
fi
```

#### Verify Export Integrity

```python
#!/usr/bin/env python3
# verify_export.py

import gzip
import re
import sys

def verify_sql_export(filename):
    """Verify SQL export file integrity"""
    print(f"Verifying {filename}...")
    
    try:
        # Open file (.sql or .sql.gz)
        f = gzip.open(filename, 'rt', encoding='utf8') if filename.endswith('.gz') \
            else open(filename, 'r', encoding='utf8')
        content = f.read()
        f.close()

        checks = {
            'MySQL Dump header': r'-- MySQL dump',
            'Database creation': r'CREATE DATABASE',
            'Table structures': r'CREATE TABLE',
            'Data inserts': r'INSERT INTO',
            'Completion marker': r'-- Dump completed'
        }

        results = {}
        for check, pattern in checks.items():
            if re.search(pattern, content, re.IGNORECASE):
                results[check] = True
                print(f"✓ {check}: Found")
            else:
                results[check] = False
                print(f"✗ {check}: Not found")

        tables = re.findall(r'CREATE TABLE `([^`]+)`', content)
        print(f"\n✓ Found {len(tables)} tables: {', '.join(tables)}")

        inserts = len(re.findall(r'INSERT INTO', content))
        print(f"✓ Found {inserts} INSERT statements")

        return all(results.values())

    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_export.py <sql_file>")
        sys.exit(1)
    
    if verify_sql_export(sys.argv[1]):
        print("\n✓ Export verification passed!")
    else:
        print("\n✗ Export verification failed!")
        sys.exit(1)
```

### 4.2 Transfer to Server

#### SCP (Secure Copy)

```bash
scp ./backups/mobility_bot_*.sql.gz user@SERVER_IP:/home/user/
```

#### SFTP

```bash
sftp user@SERVER_IP
put ./backups/mobility_bot_*.sql.gz
exit
```

#### Direct Pipe (Advanced)

```bash
mysqldump -h localhost -u root -p mobility_bot | \
ssh user@SERVER_IP "mysql -u mobility_admin -p mobility_bot_server"
```

### 4.3 Import to Server Database

Create an import script:

```bash
#!/bin/bash
# import_to_server.sh

SERVER_HOST="localhost"
SERVER_USER="mobility_admin"
SERVER_DB="mobility_bot_server"
BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "=== Importing to Server Database ==="
echo "Target: ${SERVER_DB}"
echo "File: ${BACKUP_FILE}"
echo

# Decompress if needed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "Decompressing backup..."
    gunzip -k "$BACKUP_FILE"
    SQL_FILE="${BACKUP_FILE%.gz}"
else
    SQL_FILE="$BACKUP_FILE"
fi

# Import database
mysql -h "${SERVER_HOST}" -u "${SERVER_USER}" -p "${SERVER_DB}" < "${SQL_FILE}"

if [ $? -eq 0 ]; then
    echo "✓ Import successful!"
else
    echo "✗ Import failed!"
    exit 1
fi

echo
echo "Verifying import..."
mysql -h "${SERVER_HOST}" -u "${SERVER_USER}" -p "${SERVER_DB}" -e "
SELECT 
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(DATA_LENGTH/1024/1024, 2) AS 'Data_MB'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = '${SERVER_DB}'
ORDER BY TABLE_ROWS DESC;"
```

### 4.4 Validation Checkpoint 2

Create a validation script:

```python
#!/usr/bin/env python3
# validate_migration.py

import pymysql
from datetime import datetime

def compare_databases(local_config, server_config):
    """Compare local and server databases"""
    print("=== Database Migration Validation ===")
    print(f"Time: {datetime.now()}")
    print("=" * 40)
    
    try:
        local_conn  = pymysql.connect(**local_config)
        server_conn = pymysql.connect(**server_config)
        local_cur   = local_conn.cursor()
        server_cur  = server_conn.cursor()

        # Table counts
        local_cur.execute("""
            SELECT COUNT(*) FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s
        """, (local_config['database'],))
        local_tables = local_cur.fetchone()[0]

        server_cur.execute("""
            SELECT COUNT(*) FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s
        """, (server_config['database'],))
        server_tables = server_cur.fetchone()[0]

        print(f"Tables - Local: {local_tables}, Server: {server_tables}")

        # Record counts for each table
        local_cur.execute("""
            SELECT TABLE_NAME FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s
        """, (local_config['database'],))
        
        mismatches = []
        for (table_name,) in local_cur.fetchall():
            local_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            local_count = local_cur.fetchone()[0]
            
            try:
                server_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                server_count = server_cur.fetchone()[0]
                
                if local_count == server_count:
                    print(f"✓ {table_name}: {local_count} records")
                else:
                    print(f"✗ {table_name}: Local={local_count}, Server={server_count}")
                    mismatches.append(table_name)
            except:
                print(f"✗ {table_name}: Missing on server")
                mismatches.append(table_name)

        local_conn.close()
        server_conn.close()

        if not mismatches:
            print("\n✓ Migration validation passed!")
            return True
        else:
            print(f"\n✗ Found {len(mismatches)} mismatches")
            return False

    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False

if __name__ == "__main__":
    local_config = {
        'host': 'localhost',
        'user': 'root',
        'password': input("Local DB password: "),
        'database': 'mobility_bot',
        'charset': 'utf8mb4'
    }
    
    server_config = {
        'host': input("Server IP: "),
        'user': 'mobility_admin',
        'password': input("Server DB password: "),
        'database': 'mobility_bot_server',
        'charset': 'utf8mb4'
    }
    
    compare_databases(local_config, server_config)
```

---

## 5. Phase 3: Application Configuration

### 5.1 Create Environment Configurations

#### Production Configuration (.env.production)

```bash
# Production Server Database Configuration

# Flask Settings
FLASK_ENV=production
SECRET_KEY=your-production-secret-key-change-this
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True

# Database Configuration
DB_HOST=YOUR_SERVER_IP
DB_PORT=3306
DB_USER=mobility_app
DB_PASSWORD=App_Secure_Pass123!
DB_NAME=mobility_bot_server

# Connection Pool Settings
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30

# Application Settings
LOG_LEVEL=INFO
LOG_FILE=/var/log/mobility_bot/app.log

# External Services
OPENAI_API_KEY=your-openai-api-key
FEEDBACK_FORM_URL=https://forms.google.com/your-form-id
```

#### Development Configuration (.env.development)

```bash
# Development Server Database Configuration

# Flask Settings
FLASK_ENV=development
SECRET_KEY=dev-secret-key
DEBUG=True

# Database Configuration
DB_HOST=YOUR_SERVER_IP
DB_PORT=3306
DB_USER=mobility_app
DB_PASSWORD=App_Secure_Pass123!
DB_NAME=mobility_bot_server

# Development Settings
LOG_LEVEL=DEBUG
SHOW_SQL_QUERIES=True
```

### 5.2 Configuration Management System

```python
#!/usr/bin/env python3
# config_manager.py

import os
import shutil
import json
from datetime import datetime
from dotenv import load_dotenv

class ConfigurationManager:
    def __init__(self):
        self.config_dir  = "configs"
        self.backup_dir  = "config_backups"
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

    def list_configurations(self):
        """List all available configurations"""
        return [file for file in os.listdir('.') if file.startswith('.env')]

    def backup_current(self):
        """Backup current configuration"""
        if os.path.exists('.env'):
            timestamp    = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name  = f"{self.backup_dir}/.env.backup.{timestamp}"
            shutil.copy('.env', backup_name)
            print(f"✓ Backed up to {backup_name}")
            return backup_name
        return None

    def switch_config(self, config_name):
        """Switch to specified configuration"""
        if not os.path.exists(config_name):
            print(f"✗ Configuration {config_name} not found")
            return False
        
        self.backup_current()
        shutil.copy(config_name, '.env')
        print(f"✓ Switched to {config_name}")
        return self.test_connection()

    def test_connection(self):
        """Test database connection with current config"""
        load_dotenv(override=True)
        
        try:
            import pymysql
            conn = pymysql.connect(
                host     = os.getenv('DB_HOST'),
                port     = int(os.getenv('DB_PORT', 3306)),
                user     = os.getenv('DB_USER'),
                password = os.getenv('DB_PASSWORD'),
                database = os.getenv('DB_NAME'),
                charset  = 'utf8mb4'
            )
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print(f"✓ Connected to MySQL {version}")
            print(f"  Host: {os.getenv('DB_HOST')}")
            print(f"  Database: {os.getenv('DB_NAME')}")
            conn.close()
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def create_config_report(self):
        """Generate configuration report"""
        report = {
            'timestamp'     : datetime.now().isoformat(),
            'configurations': self.list_configurations(),
            'current_config': {},
            'connection_test': False
        }
        
        if os.path.exists('.env'):
            load_dotenv()
            report['current_config'] = {
                'DB_HOST' : os.getenv('DB_HOST', 'NOT_SET'),
                'DB_NAME' : os.getenv('DB_NAME', 'NOT_SET'),
                'FLASK_ENV': os.getenv('FLASK_ENV', 'NOT_SET')
            }
            report['connection_test'] = self.test_connection()
        
        with open('config_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("✓ Report saved to config_report.json")
        return report

if __name__ == "__main__":
    manager = ConfigurationManager()
    
    while True:
        print("\n=== Configuration Manager ===")
        print("1. List configurations")
        print("2. Switch to production")
        print("3. Switch to development")
        print("4. Test current connection")
        print("5. Generate report")
        print("6. Exit")
        
        choice = input("\nSelect option: ")
        
        if choice == '1':
            configs = manager.list_configurations()
            print("\nAvailable configurations:")
            for config in configs:
                print(f"  - {config}")
        elif choice == '2':
            manager.switch_config('.env.production')
        elif choice == '3':
            manager.switch_config('.env.development')
        elif choice == '4':
            manager.test_connection()
        elif choice == '5':
            manager.create_config_report()
        elif choice == '6':
            break
```

### 5.3 Application Connection Test

```python
#!/usr/bin/env python3
# test_app_connection.py

import os
import sys
import time
import requests
import subprocess
from dotenv import load_dotenv

def test_application_startup():
    """Test if application starts with server database"""
    print("=== Application Startup Test ===")
    load_dotenv('.env.production', override=True)

    # Start the application
    print("Starting application...")
    app_process = subprocess.Popen(
        [sys.executable, 'Final_Structured_app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for startup
    time.sleep(5)

    try:
        # Test basic endpoints
        endpoints = [
            ('/', 'Home page'),
            ('/static/style.css', 'Static files')
        ]
        
        for endpoint, description in endpoints:
            url      = f'http://localhost:5000{endpoint}'
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                print(f"✓ {description}: OK")
            else:
                print(f"✗ {description}: {response.status_code}")

        print("\nTesting database operations...")
        # Additional database operations can be added here

    except Exception as e:
        print(f"✗ Test failed: {e}")
    finally:
        app_process.terminate()
        app_process.wait()
        print("\nApplication stopped")

if __name__ == "__main__":
    test_application_startup()
```

### 5.4 Validation Checkpoint 3

```bash
#!/bin/bash
# validate_app_config.sh

echo "=== Application Configuration Validation ==="
echo

# Test 1: Configuration files exist
echo "1. Configuration Files:"
for config in .env.production .env.development; do
    if [ -f "$config" ]; then
        echo "   ✓ $config exists"
    else
        echo "   ✗ $config missing"
    fi
done

# Test 2: Python dependencies
echo
echo "2. Python Dependencies:"
python -c "import pymysql; print('   ✓ pymysql installed')" 2>/dev/null || echo "   ✗ pymysql missing"
python -c "import dotenv; print('   ✓ python-dotenv installed')" 2>/dev/null || echo "   ✗ python-dotenv missing"

# Test 3: Connection test
echo
echo "3. Database Connection:"
python - <<'PYCODE'
from dotenv import load_dotenv
import os
import pymysql

load_dotenv('.env.production')
try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    print('   ✓ Connected to server database')
    conn.close()
except Exception as e:
    print(f'   ✗ Connection failed: {e}')
PYCODE
```

---

## 6. Phase 4: Remote Access Setup

### 6.1 Configure Firewall

#### UFW (Ubuntu/Debian)

```bash
# Allow MySQL from a specific IP
sudo ufw allow from CLIENT_IP to any port 3306

# Allow MySQL from a subnet
sudo ufw allow from 192.168.1.0/24 to any port 3306

# Allow MySQL from anywhere (less secure)
sudo ufw allow 3306/tcp

# Check firewall status
sudo ufw status numbered
```

#### Firewalld (CentOS/RHEL)

```bash
# Add MySQL service
sudo firewall-cmd --permanent --add-service=mysql

# Or add port directly
sudo firewall-cmd --permanent --add-port=3306/tcp

# Reload firewall
sudo firewall-cmd --reload

# Check status
sudo firewall-cmd --list-all
```

#### Windows Firewall (PowerShell)

```powershell
# Run as Administrator
New-NetFirewallRule `
    -DisplayName "MySQL Server Remote Access" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 3306 `
    -Action Allow `
    -Profile Domain,Private,Public

# Check rule
Get-NetFirewallRule -DisplayName "MySQL Server Remote Access"
```

### 6.2 Create Team User Accounts

```sql
-- Connect as admin
mysql -u mobility_admin -p

-- Create development team users
CREATE USER 'dev_john'@'%' IDENTIFIED BY 'Dev1_Pass123!';
CREATE USER 'dev_sarah'@'%' IDENTIFIED BY 'Dev2_Pass456!';
CREATE USER 'dev_mike'@'%' IDENTIFIED BY 'Dev3_Pass789!';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, 
      CREATE TEMPORARY TABLES, LOCK TABLES, EXECUTE, CREATE VIEW, 
      SHOW VIEW, CREATE ROUTINE, ALTER ROUTINE, EVENT, TRIGGER 
ON mobility_bot_server.* 
TO 'dev_john'@'%', 'dev_sarah'@'%', 'dev_mike'@'%';

-- Create read-only user
CREATE USER 'analyst_team'@'%' IDENTIFIED BY 'Analyst_Pass321!';
GRANT SELECT, SHOW VIEW ON mobility_bot_server.* TO 'analyst_team'@'%';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify users
SELECT User, Host, 
       CASE 
           WHEN User LIKE 'dev_%' THEN 'Developer'
           WHEN User = 'analyst_team' THEN 'Analyst'
           WHEN User = 'mobility_admin' THEN 'Admin'
           WHEN User = 'mobility_app' THEN 'Application'
           ELSE 'Other'
       END AS Role,
       ssl_type, password_expired
FROM mysql.user 
WHERE User NOT IN ('mysql.sys', 'mysql.session', 'mysql.infoschema')
ORDER BY User;
```

### 6.3 Generate Team Configuration Files

```python
#!/usr/bin/env python3
# generate_team_configs.py

import os
import socket
import json
from datetime import datetime

def get_server_info():
    hostname = socket.gethostname()
    ips = []
    for info in socket.getaddrinfo(hostname, None):
        ip = info[4][0]
        if ip not in ips and not ip.startswith('127.'):
            ips.append(ip)
    return {
        'hostname': hostname,
        'ips': ips,
        'primary_ip': ips[0] if ips else 'localhost'
    }

def generate_team_configs():
    server_info = get_server_info()
    
    team_members = [
        {
            'name': 'John Developer',
            'username': 'dev_john',
            'password': 'Dev1_Pass123!',
            'file': '.env.john'
        },
        {
            'name': 'Sarah Developer',
            'username': 'dev_sarah',
            'password': 'Dev2_Pass456!',
            'file': '.env.sarah'
        },
        {
            'name': 'Mike Developer',
            'username': 'dev_mike',
            'password': 'Dev3_Pass789!',
            'file': '.env.mike'
        },
        {
            'name': 'Analytics Team',
            'username': 'analyst_team',
            'password': 'Analyst_Pass321!',
            'file': '.env.analytics'
        }
    ]
    
    template = """# Schaeffler Mobility Bot - Team Member Configuration
# Generated: {timestamp}
# User: {name}

# Database Configuration
DB_HOST={server_ip}
DB_PORT=3306
DB_USER={username}
DB_PASSWORD={password}
DB_NAME=mobility_bot_server

# Application Settings
FLASK_ENV=development
SECRET_KEY=team-dev-secret-2024

# API Keys (Add your personal keys)
OPENAI_API_KEY=your-personal-openai-key

# Features
FEEDBACK_FORM_URL=https://forms.google.com/team-feedback
"""
    
    print("=== Generating Team Configuration Files ===")
    print(f"Server IP: {server_info['primary_ip']}\n")
    
    for member in team_members:
        content = template.format(
            timestamp=datetime.now().isoformat(),
            name=member['name'],
            server_ip=server_info['primary_ip'],
            username=member['username'],
            password=member['password']
        )
        
        with open(member['file'], 'w') as f:
            f.write(content)
        
        print(f"✓ Created {member['file']} for {member['name']}")

    # Create team documentation
    doc_content = f"""# Team Access Documentation
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Server Information
- Primary IP: {server_info['primary_ip']}
- All IPs: {', '.join(server_info['ips'])}
- Database: mobility_bot_server
- Port: 3306

## Team Members
| Name | Username | Config File | Access Level |
|------|----------|-------------|--------------|
| John Developer | dev_john | .env.john | Read/Write |
| Sarah Developer | dev_sarah | .env.sarah | Read/Write |
| Mike Developer | dev_mike | .env.mike | Read/Write |
| Analytics Team | analyst_team | .env.analytics | Read Only |

## Setup Instructions
1. Get your configuration file from the admin
2. Rename it to .env: `mv .env.yourname .env`
3. Add your personal API keys
4. Test connection: `python test_connection.py`
5. Run application: `python app.py`

## Connection Test Command
```python
import pymysql
conn = pymysql.connect(
   host='{server_info['primary_ip']}',
   user='your_username',
   password='your_password',
   database='mobility_bot_server'
)
```
"""
    
    with open('TEAM_ACCESS.md', 'w') as f:
        f.write(doc_content)
    
    print("\n✓ Created TEAM_ACCESS.md documentation")

    # Create test_connection.py
    test_script = f"""#!/usr/bin/env python3
# test_connection.py

import pymysql
import sys
from getpass import getpass

def test_connection():
    print("=== MySQL Remote Connection Test ===")
    username = input("Username: ")
    password = getpass("Password: ")
    
    try:
        conn = pymysql.connect(
            host='{server_info['primary_ip']}',
            port=3306,
            user=username,
            password=password,
            database='mobility_bot_server',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"\\n✓ Connected to MySQL {{version}}")
        
        cursor.execute("SELECT USER()")
        user = cursor.fetchone()[0]
        print(f"✓ Connected as: {{user}}")
        
        cursor.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'mobility_bot_server'")
        tables = cursor.fetchone()[0]
        print(f"✓ Database has {{tables}} tables")
        
        cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
        print("\\n✓ Your permissions:")
        for (grant,) in cursor.fetchall():
            print(f"  {{grant}}")
        
        conn.close()
        print("\\n✓ Connection test passed!")
        return True
        
    except Exception as e:
        print(f"\\n✗ Connection failed: {{e}}")
        return False

if __name__ == "__main__":
    sys.exit(0 if test_connection() else 1)
"""
    
    with open('test_connection.py', 'w') as f:
        f.write(test_script)
    os.chmod('test_connection.py', 0o755)
    print("✓ Created test_connection.py script")

if __name__ == "__main__":
    generate_team_configs()
```

### 6.4 Validation Checkpoint 4

```bash
#!/bin/bash
# validate_remote_access.sh

echo "=== Remote Access Validation ==="
echo

# Test 1: Firewall configuration
echo "1. Firewall Configuration:"
if command -v ufw &> /dev/null; then
    sudo ufw status | grep 3306 && echo "   ✓ MySQL port open" || echo "   ✗ MySQL port not configured"
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --list-ports | grep 3306 && echo "   ✓ MySQL port open" || echo "   ✗ MySQL port not configured"
else
    echo "   ! Firewall status unknown"
fi

# Test 2: MySQL user accounts
echo
echo "2. MySQL User Accounts:"
mysql -u mobility_admin -p -e "
SELECT User, Host, 
       CASE 
           WHEN User LIKE 'dev_%' THEN 'Developer'
           WHEN User = 'analyst_team' THEN 'Analyst'
           WHEN User = 'mobility_admin' THEN 'Admin'
           WHEN User = 'mobility_app' THEN 'Application'
           ELSE 'Other'
       END AS Role
FROM mysql.user 
WHERE User LIKE 'dev_%' OR User IN ('analyst_team', 'mobility_admin', 'mobility_app')
ORDER BY Role, User;
" 2>/dev/null && echo "   ✓ User accounts verified" || echo "   ✗ Cannot verify users"

# Test 3: Remote connectivity
echo
echo "3. Remote Connectivity Test:"
SERVER_IP=$(hostname -I | awk '{print $1}')
nc -zv $SERVER_IP 3306 2>&1 | grep succeeded && echo "   ✓ Port 3306 accessible" || echo "   ✗ Port 3306 not accessible"

# Test 4: Configuration files
echo
echo "4. Team Configuration Files:"
for file in .env.john .env.sarah .env.mike .env.analytics; do
    [ -f "$file" ] && echo "   ✓ $file exists" || echo "   ✗ $file missing"
done
```

---

## 7. Phase 5: Validation & Testing

### 7.1 Comprehensive System Test

```python
#!/usr/bin/env python3
# comprehensive_validation.py

import os
import sys
import pymysql
from datetime import datetime
from dotenv import load_dotenv

class SystemValidator:
    def __init__(self):
        self.results = []
        self.passed  = 0
        self.failed  = 0

    def add_result(self, test_name, passed, details=""):
        self.results.append({
            'test'    : test_name,
            'passed'  : passed,
            'details' : details,
            'timestamp': datetime.now()
        })
        if passed:
            self.passed += 1
            print(f"✓ {test_name}")
        else:
            self.failed += 1
            print(f"✗ {test_name}")
        if details:
            print(f"  {details}")

    def test_server_database(self):
        """Test server database connectivity and structure"""
        try:
            conn = pymysql.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user='mobility_admin',
                password=input("Admin password: "),
                database='mobility_bot_server',
                charset='utf8mb4'
            )
            cursor = conn.cursor()
            
            # Check version
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            self.add_result("MySQL Server Version", True, f"Version {version}")
            
            # Check tables
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = 'mobility_bot_server'
            """)
            table_count = cursor.fetchone()[0]
            self.add_result("Database Tables", table_count > 0, f"{table_count} tables found")
            
            # Check data
            cursor.execute("SELECT COUNT(*) FROM trend_queries")
            record_count = cursor.fetchone()[0]
            self.add_result("Data Migration", record_count > 0, f"{record_count} records")
            
            conn.close()
        except Exception as e:
            self.add_result("Database Connection", False, str(e))

    def test_user_access(self):
        """Test different user access levels"""
        users = [
            ('dev_john', 'Dev1_Pass123!', 'Developer'),
            ('analyst_team', 'Analyst_Pass321!', 'Analyst')
        ]
        
        for username, password, role in users:
            try:
                conn = pymysql.connect(
                    host=os.getenv('DB_HOST', 'localhost'),
                    user=username,
                    password=password,
                    database='mobility_bot_server'
                )
                cursor = conn.cursor()
                
                # Test SELECT
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                # Test INSERT for developers
                if role == 'Developer':
                    try:
                        cursor.execute("""
                            CREATE TEMPORARY TABLE test_access 
                            (id INT PRIMARY KEY)
                        """)
                        cursor.execute("DROP TEMPORARY TABLE test_access")
                        write_access = True
                    except:
                        write_access = False
                    
                    self.add_result(f"{role} Access ({username})", write_access,
                                    "Read/Write access verified" if write_access else "Write access denied")
                else:
                    self.add_result(f"{role} Access ({username})", True, "Read access verified")
                
                conn.close()
            except Exception as e:
                self.add_result(f"{role} Access ({username})", False, str(e))

    def test_application(self):
        """Test application startup and basic functionality"""
        try:
            load_dotenv('.env.production', override=True)
            
            if not os.path.exists('Final_Structured_app.py'):
                self.add_result("Application File", False, "App file not found")
                return
            
            self.add_result("Application File", True, "Found Final_Structured_app.py")
            
            try:
                import flask
                import pymysql
                self.add_result("Python Dependencies", True, "All required packages installed")
            except ImportError as e:
                self.add_result("Python Dependencies", False, f"Missing: {e}")
        except Exception as e:
            self.add_result("Application Test", False, str(e))

    def test_network_connectivity(self):
        """Test network connectivity from different perspectives"""
        import socket
        
        hostname = socket.gethostname()
        ip       = socket.gethostbyname(hostname)
        
        try:
            sock   = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((ip, 3306))
            sock.close()
            
            self.add_result("MySQL Port Accessibility", result == 0,
                             f"Port 3306 on {ip}")
        except Exception as e:
            self.add_result("Network Test", False, str(e))

    def generate_report(self):
        """Generate validation report"""
        report = f"""
# System Validation Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Total Tests: {len(self.results)}
- Passed: {self.passed}
- Failed: {self.failed}
- Success Rate: {(self.passed/len(self.results)*100):.1f}%

## Test Results
"""
        for result in self.results:
            status = "PASS" if result['passed'] else "FAIL"
            report += f"\n### {result['test']} [{status}]\n"
            if result['details']:
                report += f"{result['details']}\n"
        
        report += f"""
## System Information
- Python Version: {sys.version.split()[0]}
- Operating System: {os.name}
- Current Directory: {os.getcwd()}
"""
        
        with open('validation_report.md', 'w') as f:
            f.write(report)
        
        print("\n✓ Report saved to validation_report.md")
        return self.passed == len(self.results)

def main():
    print("=== Comprehensive System Validation ===")
    print("=" * 40)
    
    validator = SystemValidator()
    
    print("\n1. Testing Server Database...")
    validator.test_server_database()
    
    print("\n2. Testing User Access...")
    validator.test_user_access()
    
    print("\n3. Testing Application...")
    validator.test_application()
    
    print("\n4. Testing Network...")
    validator.test_network_connectivity()
    
    print("\n" + "=" * 40)
    
    all_passed = validator.generate_report()
    
    if all_passed:
        print("\n✅ ALL VALIDATION TESTS PASSED!")
        print("System is ready for production use.")
    else:
        print(f"\n⚠️  {validator.failed} tests failed.")
        print("Please review the validation report.")
    
    return all_passed

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
```

### 7.2 Load Testing

```python
#!/usr/bin/env python3
# load_test.py

import concurrent.futures
import time
import pymysql

def test_connection(user_id):
    """Test a single connection"""
    start_time = time.time()
    
    try:
        conn = pymysql.connect(
            host='YOUR_SERVER_IP',
            user='mobility_app',
            password='App_Secure_Pass123!',
            database='mobility_bot_server'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trend_queries")
        cursor.fetchone()
        conn.close()
        
        duration = time.time() - start_time
        return {'user_id': user_id, 'success': True, 'duration': duration}
        
    except Exception as e:
        duration = time.time() - start_time
        return {'user_id': user_id, 'success': False, 'duration': duration, 'error': str(e)}

def run_load_test(num_connections=50):
    """Run a concurrent connection test"""
    print(f"=== Load Test: {num_connections} Concurrent Connections ===")
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_connections) as executor:
        futures = [executor.submit(test_connection, i) for i in range(num_connections)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    total_time = time.time() - start_time

    # Analyze results
    successful     = sum(1 for r in results if r['success'])
    failed         = num_connections - successful
    avg_duration   = sum(r['duration'] for r in results) / len(results)
    
    print("\nResults:")
    print(f"- Total connections: {num_connections}")
    print(f"- Successful: {successful}")
    print(f"- Failed: {failed}")
    print(f"- Average connection time: {avg_duration:.3f}s")
    print(f"- Total test time: {total_time:.3f}s")
    
    if failed > 0:
        print("\nErrors:")
        for r in results:
            if not r['success']:
                print(f"  - Connection {r['user_id']}: {r.get('error', 'Unknown error')}")

if __name__ == "__main__":
    run_load_test(50)
```

---

## 8. Security & Maintenance

### 8.1 Security Hardening

```bash
#!/bin/bash
# security_hardening.sh

echo "=== MySQL Security Hardening ==="

# 1. Remove anonymous users
mysql -u root -p -e "DELETE FROM mysql.user WHERE User='';"

# 2. Remove remote root access
mysql -u root -p -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"

# 3. Remove test database
mysql -u root -p -e "DROP DATABASE IF EXISTS test;"
mysql -u root -p -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"

# 4. Set password validation policy
mysql -u root -p -e "
INSTALL COMPONENT 'file://component_validate_password';
SET GLOBAL validate_password.policy = 'MEDIUM';
SET GLOBAL validate_password.length = 12;
"

# 5. Enable SSL/TLS (example user)
mysql -u root -p -e "
CREATE USER 'ssl_user'@'%' IDENTIFIED BY 'SSL_Pass123!' REQUIRE SSL;
GRANT ALL PRIVILEGES ON mobility_bot_server.* TO 'ssl_user'@'%';
"

# 6. Flush privileges
mysql -u root -p -e "FLUSH PRIVILEGES;"

echo "✓ Security hardening complete"
```

### 8.2 Automated Backup System

```python
#!/usr/bin/env python3
# backup_system.py

import os
import subprocess
import boto3  # Optional: For S3 backup
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

class BackupManager:
    def __init__(self, config):
        self.config     = config
        self.backup_dir = config.get('backup_dir', '/var/backups/mysql')
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self):
        """Create database backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename  = f"mobility_bot_{timestamp}.sql"
        filepath  = os.path.join(self.backup_dir, filename)
        
        cmd = [
            'mysqldump',
            f'-h{self.config["host"]}',
            f'-u{self.config["user"]}',
            f'-p{self.config["password"]}',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--events',
            self.config['database']
        ]
        
        try:
            with open(filepath, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
            
            if result.returncode == 0:
                # Compress
                subprocess.run(['gzip', filepath])
                compressed_file = f"{filepath}.gz"
                
                # Upload to S3
                if self.config.get('s3_bucket'):
                    self.upload_to_s3(compressed_file)
                
                return compressed_file
            else:
                raise Exception(f"Backup failed: {result.stderr}")
        except Exception as e:
            self.send_alert(f"Backup failed: {e}")
            raise

    def cleanup_old_backups(self, keep_days=7):
        """Remove old backups"""
        cutoff = datetime.now() - timedelta(days=keep_days)
        
        for filename in os.listdir(self.backup_dir):
            filepath = os.path.join(self.backup_dir, filename)
            if os.path.getmtime(filepath) < cutoff.timestamp():
                os.remove(filepath)
                print(f"Removed old backup: {filename}")

    def upload_to_s3(self, filepath):
        """Upload backup to S3"""
        s3  = boto3.client('s3')
        key = f"mysql-backups/{os.path.basename(filepath)}"
        
        s3.upload_file(
            filepath,
            self.config['s3_bucket'],
            key
        )
        print(f"Uploaded to S3: {key}")

    def send_alert(self, message):
        """Send email alert"""
        if not self.config.get('smtp_server'):
            return
        
        msg = MIMEText(message)
        msg['Subject'] = 'MySQL Backup Alert'
        msg['From']    = self.config['alert_from']
        msg['To']      = self.config['alert_to']
        
        with smtplib.SMTP(self.config['smtp_server']) as s:
            s.send_message(msg)

# Configuration
backup_config = {
    'host': 'localhost',
    'user': 'mobility_backup',
    'password': 'Backup_Pass456!',
    'database': 'mobility_bot_server',
    'backup_dir': '/var/backups/mysql',
    's3_bucket': 'your-s3-bucket',     # Optional
    'smtp_server': 'smtp.gmail.com',    # Optional
    'alert_from': 'backup@yourdomain.com',
    'alert_to': 'admin@yourdomain.com'
}

if __name__ == "__main__":
    manager = BackupManager(backup_config)
    
    try:
        backup_file = manager.create_backup()
        print(f"✓ Backup created: {backup_file}")
        manager.cleanup_old_backups()
    except Exception as e:
        print(f"✗ Backup error: {e}")
```

### 8.3 Monitoring Setup

```python
#!/usr/bin/env python3
# monitoring.py

import pymysql
import psutil
import time
from datetime import datetime

class DatabaseMonitor:
    def __init__(self, connection_params):
        self.connection_params = connection_params

    def check_health(self):
        """Check database health metrics"""
        metrics = {}
        
        try:
            conn   = pymysql.connect(**self.connection_params)
            cursor = conn.cursor()
            
            # Connections
            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            metrics['connections'] = int(cursor.fetchone()[1])
            
            # Total queries
            cursor.execute("SHOW STATUS LIKE 'Questions'")
            metrics['total_queries'] = int(cursor.fetchone()[1])
            
            # Uptime
            cursor.execute("SHOW STATUS LIKE 'Uptime'")
            metrics['uptime_seconds'] = int(cursor.fetchone()[1])
            
            # Table sizes
            cursor.execute("""
                SELECT TABLE_NAME,
                       ROUND(DATA_LENGTH/1024/1024, 2) AS data_mb,
                       TABLE_ROWS
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                ORDER BY DATA_LENGTH DESC
            """, (self.connection_params['database'],))
            
            metrics['tables'] = []
            for table, size, rows in cursor.fetchall():
                metrics['tables'].append({'name': table, 'size_mb': float(size), 'rows': rows})
            
            conn.close()
            
            # System metrics
            metrics['cpu_percent']    = psutil.cpu_percent(interval=1)
            metrics['memory_percent'] = psutil.virtual_memory().percent
            metrics['disk_usage']     = psutil.disk_usage('/').percent
            
            metrics['status']         = 'healthy'
            metrics['timestamp']      = datetime.now().isoformat()
            
        except Exception as e:
            metrics['status'] = 'error'
            metrics['error']  = str(e)
            metrics['timestamp'] = datetime.now().isoformat()
        
        return metrics

    def continuous_monitoring(self, interval=60):
        """Run continuous monitoring"""
        print("Starting database monitoring...")
        print(f"Checking every {interval} seconds")
        print("Press Ctrl+C to stop")
        
        while True:
            metrics = self.check_health()
            print(f"\n[{metrics['timestamp']}]")
            print(f"Status: {metrics['status']}")
            
            if metrics['status'] == 'healthy':
                print(f"Connections: {metrics['connections']}")
                print(f"CPU: {metrics['cpu_percent']}%")
                print(f"Memory: {metrics['memory_percent']}%")
                print(f"Disk: {metrics['disk_usage']}%")
                
                if metrics['connections'] > 100:
                    print("⚠️  High connection count!")
                if metrics['cpu_percent'] > 80:
                    print("⚠️  High CPU usage!")
                if metrics['memory_percent'] > 80:
                    print("⚠️  High memory usage!")
            else:
                print(f"Error: {metrics.get('error', 'Unknown')}")
            
            time.sleep(interval)

if __name__ == "__main__":
    monitor = DatabaseMonitor({
        'host': 'localhost',
        'user': 'mobility_admin',
        'password': input("Admin password: "),
        'database': 'mobility_bot_server'
    })
    
    try:
        monitor.continuous_monitoring()
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
```

---

## 9. Troubleshooting

### 9.1 Common Issues

#### Cannot Connect Remotely

```bash
# Check MySQL is listening on all interfaces
sudo netstat -tuln | grep 3306

# Check firewall
sudo ufw status
sudo iptables -L | grep 3306

# Check MySQL user hosts
mysql -u root -p -e "SELECT User, Host FROM mysql.user;"

# Test from remote machine
telnet SERVER_IP 3306
```

#### Access Denied Errors

```sql
-- Check user privileges
SHOW GRANTS FOR 'username'@'%';

-- Reset user password
ALTER USER 'username'@'%' IDENTIFIED BY 'NewPassword123!';

-- Check authentication plugin
SELECT User, Host, plugin FROM mysql.user WHERE User = 'username';
```

#### Performance Issues

```sql
-- Check slow query log
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';

-- Enable slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- Check current queries
SHOW PROCESSLIST;

-- Kill a long-running query
KILL QUERY process_id;
```

### 9.2 Recovery Procedures

#### Restore from Backup

```bash
#!/bin/bash
# restore_backup.sh

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Decompress if needed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" > temp_restore.sql
    SQL_FILE="temp_restore.sql"
else
    SQL_FILE="$BACKUP_FILE"
fi

# Restore
mysql -u root -p mobility_bot_server < "$SQL_FILE"

# Cleanup
[ -f "temp_restore.sql" ] && rm temp_restore.sql

echo "✓ Restore complete"
```

---

## 10. Quick Reference

### 10.1 Essential Commands

```bash
# MySQL Service
sudo systemctl status mysql
sudo systemctl restart mysql
sudo systemctl stop mysql
sudo systemctl start mysql

# Connect to MySQL
mysql -u username -p
mysql -h SERVER_IP -u username -p database_name

# Backup
mysqldump -u user -p database > backup.sql
mysqldump -u user -p database | gzip > backup.sql.gz

# Restore
mysql -u user -p database < backup.sql
gunzip < backup.sql.gz | mysql -u user -p database

# User Management
CREATE USER 'user'@'host' IDENTIFIED BY 'password';
GRANT ALL ON database.* TO 'user'@'host';
REVOKE ALL ON database.* FROM 'user'@'host';
DROP USER 'user'@'host';

# Show Information
SHOW DATABASES;
SHOW TABLES;
SHOW PROCESSLIST;
SHOW VARIABLES LIKE '%something%';
SHOW STATUS LIKE '%something%';
```

### 10.2 Connection Strings

```python
# Python (PyMySQL)
import pymysql
conn = pymysql.connect(
    host='SERVER_IP',
    user='username',
    password='password',
    database='mobility_bot_server',
    charset='utf8mb4'
)

# Python (SQLAlchemy)
from sqlalchemy import create_engine
engine = create_engine(
    'mysql+pymysql://username:password@SERVER_IP/mobility_bot_server'
)

# Application .env
DB_HOST=SERVER_IP
DB_PORT=3306
DB_USER=username
DB_PASSWORD=password
DB_NAME=mobility_bot_server
```

### 10.3 Emergency Contacts

#### Support Contacts

**Database Administrator**
- Name: [Your Name]
- Email: admin@company.com
- Phone: +XX XXX XXX XXXX

**Server Access**
- IP: YOUR_SERVER_IP
- SSH: ssh user@YOUR_SERVER_IP
- MySQL: Port 3306

**Backup Location**
- Local: /var/backups/mysql/
- Cloud: s3://your-bucket/mysql-backups/

**Documentation**
- This guide: /docs/mysql_migration_guide.md
- Team access: /docs/TEAM_ACCESS.md
- Troubleshooting: /docs/troubleshooting.md

---

## Conclusion

This comprehensive guide covers all aspects of migrating a local MySQL database to a server instance. Follow each phase sequentially, running validation checkpoints to ensure success before proceeding.

**Key takeaways:**
- Always back up before making changes
- Test each configuration step
- Document all credentials securely
- Monitor the system after deployment
- Keep security as a top priority

For additional support or questions, refer to the troubleshooting section or contact your database administrator.
        