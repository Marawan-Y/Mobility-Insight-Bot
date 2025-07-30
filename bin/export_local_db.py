#!/usr/bin/env python3
import os
import subprocess
import pymysql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def export_local_database():
    """Export local database to SQL file"""
    
    print("Exporting Local Database")
    print("=" * 50)
    
    # Configuration
    local_host = os.getenv("DB_HOST", "localhost")
    local_user = os.getenv("DB_USER", "your_user")
    local_pass = os.getenv("DB_PASSWORD", "your_pass")
    local_db = os.getenv("DB_NAME", "mobility_bot")
    
    # Create backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"mobility_bot_backup_{timestamp}.sql"
    
    # Export command
    cmd = [
        "mysqldump",
        f"-h{local_host}",
        f"-u{local_user}",
        f"-p{local_pass}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--add-drop-table",
        local_db
    ]
    
    try:
        print(f"Exporting database '{local_db}' to '{backup_file}'...")
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            file_size = os.path.getsize(backup_file) / 1024 / 1024  # MB
            print(f"✓ Export successful! File: {backup_file} ({file_size:.2f} MB)")
            return backup_file
        else:
            print(f"✗ Export failed: {result.stderr}")
            return None
            
    except FileNotFoundError:
        print("✗ mysqldump not found. Please install MySQL client tools.")
        return None
    except Exception as e:
        print(f"✗ Export error: {e}")
        return None

def verify_export(backup_file):
    """Verify the export file"""
    
    print("\nVerifying Export")
    print("-" * 30)
    
    if not os.path.exists(backup_file):
        print("✗ Backup file not found")
        return False
    
    # Check file size
    file_size = os.path.getsize(backup_file)
    if file_size == 0:
        print("✗ Backup file is empty")
        return False
    
    # Check for essential tables
    with open(backup_file, 'r', encoding='utf8') as f:
        content = f.read()
        
    required_tables = ['trend_queries']
    for table in required_tables:
        if f"CREATE TABLE `{table}`" in content:
            print(f"✓ Table '{table}' found in export")
        else:
            print(f"✗ Table '{table}' missing from export")
            return False
    
    print(f"✓ Export verified successfully")
    return True

if __name__ == "__main__":
    backup_file = export_local_database()
    if backup_file and verify_export(backup_file):
        print(f"\n✓ Ready to import: {backup_file}")
    else:
        print("\n✗ Export validation failed")