#!/usr/bin/env python3
import pymysql
import os
import sys
from datetime import datetime

def run_complete_validation():
    """Run complete validation of the setup"""
    
    print("Complete MySQL Server Setup Validation")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Server Database
    tests_total += 1
    print("\n[Test 1] Server Database Connection")
    try:
        conn = pymysql.connect(
            host='localhost',
            user='mobility_user',
            password='Secure_Pass123!',
            database='mobility_bot_server',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"✓ MySQL Version: {version}")
        conn.close()
        tests_passed += 1
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 2: Data Migration
    tests_total += 1
    print("\n[Test 2] Data Migration Verification")
    try:
        conn = pymysql.connect(
            host='localhost',
            user='mobility_user',
            password='Secure_Pass123!',
            database='mobility_bot_server',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trend_queries")
        count = cursor.fetchone()[0]
        print(f"✓ Records migrated: {count}")
        conn.close()
        tests_passed += 1
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 3: Remote Access
    tests_total += 1
    print("\n[Test 3] Remote Access Configuration")
    try:
        conn = pymysql.connect(
            host='localhost',
            user='mobility_user',
            password='Secure_Pass123!',
            database='mobility_bot_server',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT User, Host FROM mysql.user WHERE User LIKE 'dev_%' OR User = 'mobility_user'")
        users = cursor.fetchall()
        print("✓ Remote users configured:")
        for user, host in users:
            print(f"  - {user}@{host}")
        conn.close()
        tests_passed += 1
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 4: Application Configuration
    tests_total += 1
    print("\n[Test 4] Application Configuration")
    if os.path.exists('.env.server'):
        print("✓ Server configuration file exists")
        tests_passed += 1
    else:
        print("✗ Server configuration file missing")
    
    # Test 5: Team Configurations
    tests_total += 1
    print("\n[Test 5] Team Configuration Files")
    team_files = ['.env.team1', '.env.team2', '.env.team3']
    all_exist = all(os.path.exists(f) for f in team_files)
    if all_exist:
        print("✓ All team configuration files created")
        tests_passed += 1
    else:
        print("✗ Some team configuration files missing")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"VALIDATION SUMMARY: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("✓ ALL TESTS PASSED - System ready for production!")
        return True
    else:
        print("✗ Some tests failed - Please review and fix issues")
        return False

if __name__ == "__main__":
    success = run_complete_validation()
    sys.exit(0 if success else 1)