#!/usr/bin/env python3
import os
import time
import requests
import subprocess
from dotenv import load_dotenv
import pymysql

def test_app_with_server_db():
    """Test application with server database"""
    
    print("Application Server DB Connection Test")
    print("=" * 50)
    
    # Load server config
    load_dotenv('.env.server', override=True)
    
    # Test 1: Direct DB connection
    print("\n1. Testing direct database connection...")
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            charset='utf8mb4'
        )
        print("✓ Direct database connection successful")
        conn.close()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    # Test 2: Start application
    print("\n2. Starting application with server database...")
    try:
        # Start app in background
        app_process = subprocess.Popen(
            ['python', 'Final_Structured_app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for app to start
        time.sleep(5)
        
        # Test 3: Check if app is running
        print("\n3. Testing application endpoints...")
        response = requests.get('http://localhost:5000')
        
        if response.status_code == 200:
            print("✓ Application is running")
        else:
            print(f"✗ Application returned status: {response.status_code}")
            
        # Terminate app
        app_process.terminate()
        
        return True
        
    except Exception as e:
        print(f"✗ Application test failed: {e}")
        return False

if __name__ == "__main__":
    test_app_with_server_db()