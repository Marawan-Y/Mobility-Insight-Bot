#!/usr/bin/env python3
import pymysql
import sys

def test_mysql_server():
    """Test MySQL server installation and configuration"""
    
    print("MySQL Server Validation")
    print("=" * 50)
    
    # Test 1: Local root connection
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password=input("Enter MySQL root password: "),
            charset='utf8mb4'
        )
        print("✓ Local root connection successful")
        conn.close()
    except Exception as e:
        print(f"✗ Local root connection failed: {e}")
        return False
    
    # Test 2: Database exists
    try:
        conn = pymysql.connect(
            host='localhost',
            user='mobility_user',
            password='Secure_Pass123!',
            database='mobility_bot_server',
            charset='utf8mb4'
        )
        print("✓ Database 'mobility_bot_server' accessible")
        conn.close()
    except Exception as e:
        print(f"✗ Database access failed: {e}")
        return False
    
    # Test 3: User permissions
    try:
        conn = pymysql.connect(
            host='localhost',
            user='mobility_user',
            password='Secure_Pass123!',
            database='mobility_bot_server',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INT PRIMARY KEY)")
        cursor.execute("DROP TABLE test_table")
        conn.close()
        print("✓ User permissions verified")
    except Exception as e:
        print(f"✗ Permission test failed: {e}")
        return False
    
    print("\n✓ MySQL server setup completed successfully!")
    return True

if __name__ == "__main__":
    if not test_mysql_server():
        sys.exit(1)