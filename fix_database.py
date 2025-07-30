import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

def fix_database():
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "your_user"),
            password=os.getenv("DB_PASSWORD", "your_pass"),
            database=os.getenv("DB_NAME", "mobility_bot"),
            charset="utf8mb4"
        )
        
        with conn.cursor() as cursor:
            # Check if column exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_schema = %s 
                AND table_name = 'trend_queries' 
                AND column_name = 'session_id'
            """, (os.getenv("DB_NAME", "mobility_bot"),))
            
            if cursor.fetchone()[0] == 0:
                # Add missing column
                cursor.execute("""
                    ALTER TABLE trend_queries 
                    ADD COLUMN session_id VARCHAR(100) 
                    AFTER confidence_score
                """)
                print("Added session_id column successfully")
            else:
                print("session_id column already exists")
                
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error fixing database: {e}")

if __name__ == "__main__":
    fix_database()