#!/usr/bin/env python3
# setup_assessment_db.py

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def setup_assessment_tables():
    """Create assessment tables in database"""
    
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            charset="utf8mb4"
        )
        
        cursor = conn.cursor()
        
        # Create tables (from the framework code)
        print("Creating assessment tables...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_assessment_trials (
                id INT AUTO_INCREMENT PRIMARY KEY,
                trial_id VARCHAR(32) UNIQUE,
                use_case VARCHAR(255),
                sector VARCHAR(255),
                demand TEXT,
                timestamp DATETIME,
                raw_output LONGTEXT,
                latency_ms FLOAT,
                token_count INT,
                api_calls INT,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_input (use_case, sector, demand(255))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_assessment_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                assessment_id VARCHAR(32),
                metric_type VARCHAR(50),
                metric_name VARCHAR(100),
                metric_value FLOAT,
                details JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_assessment (assessment_id),
                INDEX idx_metric (metric_type, metric_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        print("✓ Assessment tables created successfully!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    setup_assessment_tables()