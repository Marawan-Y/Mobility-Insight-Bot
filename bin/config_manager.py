#!/usr/bin/env python3
import os
import shutil
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self):
        self.current_config = self.get_current_config()
    
    def get_current_config(self):
        """Determine current configuration"""
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                content = f.read()
                if 'mobility_bot_server' in content:
                    return 'server'
                else:
                    return 'local'
        return 'none'
    
    def switch_to_server(self):
        """Switch to server configuration"""
        print("Switching to server database configuration...")
        
        # Backup current .env
        if os.path.exists('.env'):
            shutil.copy('.env', '.env.local.backup')
            print("✓ Backed up current config to .env.local.backup")
        
        # Copy server config
        if os.path.exists('.env.server'):
            shutil.copy('.env.server', '.env')
            print("✓ Switched to server configuration")
            return True
        else:
            print("✗ .env.server not found!")
            return False
    
    def switch_to_local(self):
        """Switch to local configuration"""
        print("Switching to local database configuration...")
        
        # Restore local backup
        if os.path.exists('.env.local.backup'):
            shutil.copy('.env.local.backup', '.env')
            print("✓ Switched to local configuration")
            return True
        else:
            print("✗ Local backup not found!")
            return False
    
    def test_connection(self):
        """Test current database connection"""
        load_dotenv(override=True)
        
        import pymysql
        
        try:
            conn = pymysql.connect(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", 3306)),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                charset='utf8mb4'
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) FROM trend_queries")
            count = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"✓ Connected to: {os.getenv('DB_HOST')}")
            print(f"✓ Database: {os.getenv('DB_NAME')}")
            print(f"✓ Records: {count}")
            return True
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

def main():
    """Interactive configuration manager"""
    manager = ConfigManager()
    
    while True:
        print("\nDatabase Configuration Manager")
        print("=" * 40)
        print(f"Current config: {manager.current_config}")
        print("\n1. Switch to server database")
        print("2. Switch to local database")
        print("3. Test current connection")
        print("4. Exit")
        
        choice = input("\nSelect option: ")
        
        if choice == '1':
            manager.switch_to_server()
            manager.test_connection()
        elif choice == '2':
            manager.switch_to_local()
            manager.test_connection()
        elif choice == '3':
            manager.test_connection()
        elif choice == '4':
            break
        else:
            print("Invalid option!")

if __name__ == "__main__":
    main()