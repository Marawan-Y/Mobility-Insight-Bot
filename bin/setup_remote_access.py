#!/usr/bin/env python3
import os
import socket
import pymysql

def get_server_ip():
    """Get server's IP address"""
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    
    # Get all IPs
    print(f"Hostname: {hostname}")
    print(f"Primary IP: {ip_address}")
    
    # Get all network interfaces (Linux/Mac)
    if os.name != 'nt':
        import subprocess
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if result.returncode == 0:
            all_ips = result.stdout.strip().split()
            print(f"All IPs: {', '.join(all_ips)}")
    
    return ip_address

def create_remote_user(admin_password):
    """Create users for remote team access"""
    
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password=admin_password,
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # Create developer users
        developers = [
            ('dev_user1', 'Dev_Pass123!', 'Developer 1'),
            ('dev_user2', 'Dev_Pass456!', 'Developer 2'),
            ('dev_user3', 'Dev_Pass789!', 'Developer 3')
        ]
        
        for username, password, comment in developers:
            try:
                cursor.execute(f"""
                    CREATE USER '{username}'@'%' IDENTIFIED BY '{password}'
                """)
                cursor.execute(f"""
                    GRANT SELECT, INSERT, UPDATE, DELETE ON mobility_bot_server.* TO '{username}'@'%'
                """)
                print(f"✓ Created user: {username} ({comment})")
            except Exception as e:
                print(f"! User {username} might already exist: {e}")
        
        cursor.execute("FLUSH PRIVILEGES")
        conn.commit()
        conn.close()
        
        print("\n✓ Remote users created successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error creating users: {e}")
        return False

def generate_team_configs(server_ip):
    """Generate .env files for team members"""
    
    print("\nGenerating team configuration files...")
    
    template = """# Schaeffler Mobility Insight Bot - Team Configuration
# Server Database Configuration
DB_HOST={server_ip}
DB_PORT=3306
DB_USER={username}
DB_PASSWORD={password}
DB_NAME=mobility_bot_server

# OpenAI Configuration (Add your own key)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo

# Flask Configuration
SECRET_KEY=team-secret-key-2024
FLASK_ENV=development

# Feedback Form
FEEDBACK_FORM_URL=https://docs.google.com/forms/d/e/your-form-id/viewform
"""
    
    configs = [
        ('dev_user1', 'Dev_Pass123!', '.env.team1'),
        ('dev_user2', 'Dev_Pass456!', '.env.team2'),
        ('dev_user3', 'Dev_Pass789!', '.env.team3')
    ]
    
    for username, password, filename in configs:
        content = template.format(
            server_ip=server_ip,
            username=username,
            password=password
        )
        
        with open(filename, 'w') as f:
            f.write(content)
        
        print(f"✓ Created {filename}")
    
    # Create connection test script
    test_script = f"""#!/usr/bin/env python3
import pymysql
import sys

def test_connection(username, password):
    try:
        conn = pymysql.connect(
            host='{server_ip}',
            port=3306,
            user=username,
            password=password,
            database='mobility_bot_server',
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trend_queries")
        count = cursor.fetchone()[0]
        
        print(f"✓ Connected successfully!")
        print(f"✓ Database has {{count}} records")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {{e}}")
        return False

if __name__ == "__main__":
    username = input("Username: ")
    password = input("Password: ")
    test_connection(username, password)
"""
    
    with open('test_remote_connection.py', 'w') as f:
        f.write(test_script)
    
    print("✓ Created test_remote_connection.py")

def main():
    print("Remote Database Access Setup")
    print("=" * 50)
    
    # Get server IP
    server_ip = get_server_ip()
    
    # Create remote users
    admin_pass = input("\nEnter MySQL root password: ")
    if create_remote_user(admin_pass):
        generate_team_configs(server_ip)
        
        print("\n" + "=" * 50)
        print("Setup Complete!")
        print(f"Server IP: {server_ip}")
        print("\nShare these files with team members:")
        print("- .env.team1 → Developer 1")
        print("- .env.team2 → Developer 2")
        print("- .env.team3 → Developer 3")
        print("\nEach developer should:")
        print("1. Rename their .env.teamX to .env")
        print("2. Add their OpenAI API key")
        print("3. Run: python test_remote_connection.py")

if __name__ == "__main__":
    main()