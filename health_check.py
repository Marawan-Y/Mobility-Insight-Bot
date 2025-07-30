import pymysql
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

def check_database():
    """Check database connectivity"""
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "your_user"),
            password=os.getenv("DB_PASSWORD", "your_pass"),
            database=os.getenv("DB_NAME", "mobility_bot"),
            charset="utf8mb4"
        )
        conn.close()
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database error: {str(e)}"

def check_openai():
    """Check OpenAI API connectivity"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Make a minimal test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        return True, "OpenAI API connection successful"
    except Exception as e:
        return False, f"OpenAI API error: {str(e)}"

def run_health_check():
    """Run all health checks"""
    print("Running health checks...")
    print("-" * 50)
    
    # Check database
    db_ok, db_msg = check_database()
    print(f"Database: {'✓' if db_ok else '✗'} {db_msg}")
    
    # Check OpenAI
    api_ok, api_msg = check_openai()
    print(f"OpenAI API: {'✓' if api_ok else '✗'} {api_msg}")
    
    print("-" * 50)
    
    if db_ok and api_ok:
        print("✓ All systems operational")
        return True
    else:
        print("✗ Some systems have issues")
        return False

if __name__ == "__main__":
    run_health_check()