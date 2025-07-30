import os
import json
import tempfile
from datetime import datetime, timedelta

class FileSessionManager:
    def __init__(self, session_dir=None):
        self.session_dir = session_dir or os.path.join(tempfile.gettempdir(), 'mobility_sessions')
        os.makedirs(self.session_dir, exist_ok=True)
        self.cleanup_old_sessions()
    
    def save_session_data(self, session_id, data):
        """Save session data to file"""
        filepath = os.path.join(self.session_dir, f"{session_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    
    def load_session_data(self, session_id):
        """Load session data from file"""
        filepath = os.path.join(self.session_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def delete_session_data(self, session_id):
        """Delete session data file"""
        filepath = os.path.join(self.session_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
    
    def cleanup_old_sessions(self, days=7):
        """Clean up sessions older than specified days"""
        cutoff_time = datetime.now() - timedelta(days=days)
        for filename in os.listdir(self.session_dir):
            filepath = os.path.join(self.session_dir, filename)
            if os.path.getmtime(filepath) < cutoff_time.timestamp():
                os.remove(filepath)

# Initialize session manager
session_manager = FileSessionManager()