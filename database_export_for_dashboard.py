#!/usr/bin/env python3
"""
Database Export Script for Enhanced Variance Assessment Dashboard
================================================================

This script exports data from the MySQL database in a format compatible with
the dashboard's upload functionality. It creates a structured JSON file that
contains all necessary data for analysis.

Usage:
    python database_export_for_dashboard.py [--output filename.json] [--date-range YYYY-MM-DD YYYY-MM-DD]
"""

import os
import json
import argparse
import pymysql
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class DatabaseExporter:
    """Export database data for dashboard analysis"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv("DB_HOST", "localhost"),
            'port': int(os.getenv("DB_PORT", 3306)),
            'user': os.getenv("DB_USER", ""),
            'password': os.getenv("DB_PASSWORD", ""),
            'database': os.getenv("DB_NAME", ""),
            'charset': 'utf8mb4'
        }
    
    def export_full_dataset(self, 
                           output_file: str = None, 
                           date_range: Optional[tuple] = None,
                           include_metadata: bool = True) -> Dict:
        """
        Export complete dataset compatible with dashboard
        
        Args:
            output_file: Output JSON filename
            date_range: Tuple of (start_date, end_date) as strings
            include_metadata: Whether to include export metadata
            
        Returns:
            Dictionary containing exported data
        """
        
        print("🔄 Starting database export for dashboard analysis...")
        
        # Generate filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"mobility_dashboard_export_{timestamp}.json"
        
        # Export data
        export_data = {
            'export_metadata': self._generate_metadata(date_range) if include_metadata else {},
            'trend_queries': self._export_trend_queries(date_range),
            'assessment_trials': self._export_assessment_trials(date_range),
            'assessment_metrics': self._export_assessment_metrics(date_range),
            'schema_info': self._get_schema_info()
        }
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)
        
        # Generate summary
        self._print_export_summary(export_data, output_file)
        
        return export_data
    
    def _generate_metadata(self, date_range: Optional[tuple]) -> Dict:
        """Generate export metadata"""
        return {
            'export_timestamp': datetime.now().isoformat(),
            'exporter_version': '1.0.0',
            'source_database': {
                'host': self.db_config['host'],
                'database': self.db_config['database'],
                'export_date_range': {
                    'start': date_range[0] if date_range else None,
                    'end': date_range[1] if date_range else None,
                    'full_export': date_range is None
                }
            },
            'compatibility': {
                'dashboard_version': '1.0.0',
                'required_columns': [
                    'id', 'use_case', 'sector', 'demand', 'selected_trend',
                    'trend_solutions', 'confidence_score', 'session_id', 'created_at'
                ]
            }
        }
    
    def _export_trend_queries(self, date_range: Optional[tuple]) -> List[Dict]:
        """Export trend_queries table data"""
        print("📊 Exporting trend queries...")
        
        query = """
            SELECT 
                id,
                use_case,
                sector,
                demand,
                selected_trend,
                trend_solutions,
                trend_assessment,
                radar_positioning,
                pestel_tag,
                market_solution,
                partners,
                confidence_score,
                session_id,
                created_at
            FROM trend_queries
        """
        
        if date_range:
            query += " WHERE created_at BETWEEN %s AND %s"
            query += " ORDER BY created_at DESC"
            params = date_range
        else:
            query += " ORDER BY created_at DESC"
            params = None
        
        try:
            conn = pymysql.connect(**self.db_config)
            df = pd.read_sql(query, conn, params=params)
            conn.close()
            
            # Convert to list of dictionaries
            return df.to_dict('records')
            
        except Exception as e:
            print(f"❌ Error exporting trend queries: {e}")
            return []
    
    def _export_assessment_trials(self, date_range: Optional[tuple]) -> List[Dict]:
        """Export llm_assessment_trials table data"""
        print("🧪 Exporting assessment trials...")
        
        query = """
            SELECT 
                id,
                trial_id,
                use_case,
                sector,
                demand,
                timestamp,
                raw_output,
                latency_ms,
                token_count,
                api_calls,
                metadata,
                created_at
            FROM llm_assessment_trials
        """
        
        if date_range:
            query += " WHERE created_at BETWEEN %s AND %s"
            query += " ORDER BY created_at DESC"
            params = date_range
        else:
            query += " ORDER BY created_at DESC"
            params = None
        
        try:
            conn = pymysql.connect(**self.db_config)
            df = pd.read_sql(query, conn, params=params)
            conn.close()
            
            return df.to_dict('records')
            
        except Exception as e:
            print(f"⚠️  Assessment trials table not found or error: {e}")
            return []
    
    def _export_assessment_metrics(self, date_range: Optional[tuple]) -> List[Dict]:
        """Export llm_assessment_metrics table data"""
        print("📈 Exporting assessment metrics...")
        
        query = """
            SELECT 
                id,
                assessment_id,
                metric_type,
                metric_name,
                metric_value,
                details,
                created_at
            FROM llm_assessment_metrics
        """
        
        if date_range:
            query += " WHERE created_at BETWEEN %s AND %s"
            query += " ORDER BY created_at DESC"
            params = date_range
        else:
            query += " ORDER BY created_at DESC"
            params = None
        
        try:
            conn = pymysql.connect(**self.db_config)
            df = pd.read_sql(query, conn, params=params)
            conn.close()
            
            return df.to_dict('records')
            
        except Exception as e:
            print(f"⚠️  Assessment metrics table not found or error: {e}")
            return []
    
    def _get_schema_info(self) -> Dict:
        """Get database schema information"""
        schema_info = {
            'tables': {},
            'relationships': []
        }
        
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Get table info
            tables = ['trend_queries', 'llm_assessment_trials', 'llm_assessment_metrics']
            
            for table in tables:
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                
                schema_info['tables'][table] = [
                    {
                        'field': col[0],
                        'type': col[1],
                        'null': col[2],
                        'key': col[3],
                        'default': col[4],
                        'extra': col[5]
                    }
                    for col in columns
                ]
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️  Could not retrieve schema info: {e}")
        
        return schema_info
    
    def _print_export_summary(self, export_data: Dict, filename: str):
        """Print export summary"""
        print("\n" + "="*60)
        print("📋 EXPORT SUMMARY")
        print("="*60)
        
        print(f"✅ Export file: {filename}")
        print(f"📊 Trend queries: {len(export_data['trend_queries']):,} records")
        print(f"🧪 Assessment trials: {len(export_data['assessment_trials']):,} records")  
        print(f"📈 Assessment metrics: {len(export_data['assessment_metrics']):,} records")
        
        if export_data['trend_queries']:
            dates = [r['created_at'] for r in export_data['trend_queries'] if r.get('created_at')]
            if dates:
                print(f"📅 Date range: {min(dates)} → {max(dates)}")
        
        # File size
        file_size = os.path.getsize(filename) / (1024 * 1024)  # MB
        print(f"💾 File size: {file_size:.2f} MB")
        
        # Unique queries info
        unique_queries = set()
        for record in export_data['trend_queries']:
            query_key = f"{record.get('use_case', '')}-{record.get('sector', '')}-{record.get('demand', '')}"
            unique_queries.add(query_key)
        
        print(f"🔍 Unique query combinations: {len(unique_queries)}")
        
        print(f"\n✅ Export completed successfully!")
        print(f"📁 Upload this file to the Enhanced Variance Assessment Dashboard")
        print("="*60)
    
    def export_sample_dataset(self, sample_size: int = 100) -> str:
        """Export a sample dataset for testing"""
        print(f"🔬 Exporting sample dataset ({sample_size} records)...")
        
        query = f"""
            SELECT * FROM trend_queries 
            ORDER BY created_at DESC 
            LIMIT {sample_size}
        """
        
        try:
            conn = pymysql.connect(**self.db_config)
            df = pd.read_sql(query, conn)
            conn.close()
            
            sample_data = {
                'export_metadata': {
                    'export_type': 'sample',
                    'sample_size': len(df),
                    'export_timestamp': datetime.now().isoformat()
                },
                'trend_queries': df.to_dict('records'),
                'assessment_trials': [],
                'assessment_metrics': [],
                'schema_info': self._get_schema_info()
            }
            
            filename = f"sample_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(sample_data, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"✅ Sample export saved: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error creating sample export: {e}")
            return ""


def main():
    parser = argparse.ArgumentParser(description='Export database for Enhanced Variance Assessment Dashboard')
    
    parser.add_argument('--output', '-o', 
                       help='Output filename (default: auto-generated)')
    
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'),
                       help='Date range for export (YYYY-MM-DD YYYY-MM-DD)')
    
    parser.add_argument('--sample', type=int,
                       help='Export sample dataset with specified number of records')
    
    parser.add_argument('--no-metadata', action='store_true',
                       help='Skip metadata generation')
    
    args = parser.parse_args()
    
    exporter = DatabaseExporter()
    
    # Sample export
    if args.sample:
        exporter.export_sample_dataset(args.sample)
        return
    
    # Full export
    date_range = None
    if args.date_range:
        try:
            date_range = (
                datetime.strptime(args.date_range[0], '%Y-%m-%d'),
                datetime.strptime(args.date_range[1], '%Y-%m-%d')
            )
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            return
    
    exporter.export_full_dataset(
        output_file=args.output,
        date_range=date_range,
        include_metadata=not args.no_metadata
    )


if __name__ == "__main__":
    main()