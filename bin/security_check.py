#!/usr/bin/env python3
import pymysql
import subprocess
import os

def security_audit():
    """Run security audit on MySQL server"""
    
    print("MySQL Security Audit")
    print("=" * 50)
    
    admin_pass = input("Enter MySQL root password: ")
    
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password=admin_pass,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # Check 1: Anonymous users
        print("\n[1] Checking for anonymous users...")
        cursor.execute("SELECT User, Host FROM mysql.user WHERE User=''")
        anon_users = cursor.fetchall()
        if anon_users:
            print(f"⚠ Found {len(anon_users)} anonymous users - REMOVE THEM!")
        else:
            print("✓ No anonymous users found")
        
        # Check 2: Root access
        print("\n[2] Checking root access...")
        cursor.execute("SELECT User, Host FROM mysql.user WHERE User='root'")
        root_users = cursor.fetchall()
        for user, host in root_users:
            if host == '%':
                print(f"⚠ Root access from any host detected - RESTRICT IT!")
            else:
                print(f"✓ Root access limited to: {host}")
        
        # Check 3: Password validation
        print("\n[3] Checking password policies...")
        cursor.execute("SHOW VARIABLES LIKE 'validate_password%'")
        password_policies = cursor.fetchall()
        if password_policies:
            for var, val in password_policies:
                print(f"  {var}: {val}")
        else:
            print("⚠ Password validation plugin not installed")
        
        # Check 4: SSL/TLS
        print("\n[4] Checking SSL/TLS...")
        cursor.execute("SHOW VARIABLES LIKE '%ssl%'")
        ssl_vars = cursor.fetchall()
        have_ssl = any(var[0] == 'have_ssl' and var[1] == 'YES' for var in ssl_vars)
        if have_ssl:
            print("✓ SSL/TLS is available")
        else:
            print("⚠ SSL/TLS not configured")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ Security audit failed: {e}")

if __name__ == "__main__":
    security_audit()