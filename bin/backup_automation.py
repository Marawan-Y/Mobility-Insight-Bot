#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime
import schedule
import time

class BackupManager:
    def __init__(self):
        self.backup_dir = "backups"
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def backup_database(self):
        """Create automated backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"mobility_backup_{timestamp}.sql")
        
        cmd = [
            "mysqldump",
            "-hlocalhost",
            "-umobility_user",
            "-pSecure_Pass123!",
            "--single-transaction",
            "--routines",
            "--triggers",
            "mobility_bot_server"
        ]
        
        try:
            with open(backup_file, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                # Compress backup
                subprocess.run(['gzip', backup_file])
                print(f"✓ Backup created: {backup_file}.gz")
                
                # Clean old backups (keep last 7 days)
                self.cleanup_old_backups()
                return True
            else:
                print(f"✗ Backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"✗ Backup error: {e}")
            return False
    
    def cleanup_old_backups(self, keep_days=7):
        """Remove backups older than keep_days"""
        import glob
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=keep_days)
        
        for backup in glob.glob(os.path.join(self.backup_dir, "*.gz")):
            file_time = datetime.fromtimestamp(os.path.getmtime(backup))
            if file_time < cutoff:
                os.remove(backup)
                print(f"  Removed old backup: {os.path.basename(backup)}")
    
    def schedule_backups(self):
        """Schedule daily backups"""
        schedule.every().day.at("02:00").do(self.backup_database)
        
        print("Backup scheduler started (daily at 2 AM)")
        print("Press Ctrl+C to stop")
        
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    manager = BackupManager()
    
    # Run immediate backup
    print("Running immediate backup...")
    manager.backup_database()
    
    # Start scheduler
    try:
        manager.schedule_backups()
    except KeyboardInterrupt:
        print("\nScheduler stopped")