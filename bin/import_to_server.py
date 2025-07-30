#!/usr/bin/env python3
import os
import subprocess
import pymysql
import sys
from datetime import datetime

def import_to_server(backup_file, server_host='localhost'):
    """Import database dump to server"""
    
    print("Importing to Server Database")
    print("=" * 50)
    
    # Server configuration
    server_user = 'mobility_user'
    server_pass = 'Secure_Pass123!'
    server_db = 'mobility_bot_server'
    
    if not os.path.exists(backup_file):
        print(f"✗ Backup file not found: {backup_file}")
        return False
    
    # Import command
    cmd = [
        "mysql",
        f"-h{server_host}",
        f"-u{server_user}",
        f"-p{server_pass}",
        server_db
    ]
    
    try:
        print(f"Importing '{backup_file}' to server database...")
        
        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            print("✓ Import successful!")
            return True
        else:
            print(f"✗ Import failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def verify_import(server_host='localhost'):
    """Verify the imported data"""
    
    print("\nVerifying Import")
    print("-" * 30)
    
    try:
        conn = pymysql.connect(
            host=server_host,
            user='mobility_user',
            password='Secure_Pass123!',
            database='mobility_bot_server',
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")
        
        # Check data
        if 'trend_queries' in tables:
            cursor.execute("SELECT COUNT(*) FROM trend_queries")
            count = cursor.fetchone()[0]
            print(f"✓ Found {count} records in trend_queries")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_to_server.py <backup_file> [server_host]")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    server_host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
    
    if import_to_server(backup_file, server_host):
        verify_import(server_host)