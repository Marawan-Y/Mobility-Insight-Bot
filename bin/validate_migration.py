#!/usr/bin/env python3
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def compare_databases():
    """Compare local and server databases"""
    
    print("Database Migration Validation")
    print("=" * 50)
    
    # Local DB config
    local_config = {
        'host': os.getenv("DB_HOST", "localhost"),
        'user': os.getenv("DB_USER", "your_user"),
        'password': os.getenv("DB_PASSWORD", "your_pass"),
        'database': os.getenv("DB_NAME", "mobility_bot"),
        'charset': 'utf8mb4'
    }
    
    # Server DB config
    server_config = {
        'host': 'localhost',  # Change to your server IP
        'user': 'mobility_user',
        'password': 'Secure_Pass123!',
        'database': 'mobility_bot_server',
        'charset': 'utf8mb4'
    }
    
    try:
        # Connect to both databases
        local_conn = pymysql.connect(**local_config)
        server_conn = pymysql.connect(**server_config)
        
        local_cursor = local_conn.cursor()
        server_cursor = server_conn.cursor()
        
        # Compare table counts
        local_cursor.execute("SELECT COUNT(*) FROM trend_queries")
        local_count = local_cursor.fetchone()[0]
        
        server_cursor.execute("SELECT COUNT(*) FROM trend_queries")
        server_count = server_cursor.fetchone()[0]
        
        print(f"Local records:  {local_count}")
        print(f"Server records: {server_count}")
        
        if local_count == server_count:
            print("✓ Record counts match!")
        else:
            print("✗ Record count mismatch!")
        
        # Compare table structure
        local_cursor.execute("DESCRIBE trend_queries")
        local_structure = local_cursor.fetchall()
        
        server_cursor.execute("DESCRIBE trend_queries")
        server_structure = server_cursor.fetchall()
        
        if local_structure == server_structure:
            print("✓ Table structures match!")
        else:
            print("✗ Table structures differ!")
        
        local_conn.close()
        server_conn.close()
        
        print("\n✓ Migration validation complete!")
        return True
        
    except Exception as e:
        print(f"✗ Validation error: {e}")
        return False

if __name__ == "__main__":
    compare_databases()