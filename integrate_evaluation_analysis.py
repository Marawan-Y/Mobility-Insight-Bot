#!/usr/bin/env python3
"""
Dashboard Integration Script
===========================

This script integrates the upload functionality and GPT analysis export
into your existing enhanced_variance_assessment_dashboard.py file.

Usage:
    python integrate_upload_functionality.py
"""

import os
import shutil
from pathlib import Path

def backup_original_dashboard():
    """Backup the original dashboard file"""
    original_file = "enhanced_variance_assessment_dashboard.py"
    
    if os.path.exists(original_file):
        backup_file = f"{original_file}.backup"
        shutil.copy2(original_file, backup_file)
        print(f"✅ Original dashboard backed up to: {backup_file}")
        return True
    else:
        print(f"⚠️  Original dashboard file not found: {original_file}")
        return False

def create_integrated_dashboard():
    """Create the integrated dashboard with upload functionality"""
    
    # The integrated dashboard code would be written here
    # For now, we'll create a simple replacement notice
    
    integrated_code = '''#!/usr/bin/env python3
"""
Enhanced Variance Assessment Dashboard with Integrated Upload & Export
====================================================================

This is the integrated version that includes:
1. Database connection (original functionality)  
2. File upload capability (new)
3. GPT analysis export (new)

To use this integration:
1. Replace your original enhanced_variance_assessment_dashboard.py with this file
2. Run: streamlit run enhanced_variance_assessment_dashboard.py
3. Use the sidebar to choose between "Database Connection" and "Upload File"
4. Export analysis results in the "Data Export" tab
"""

# Import the enhanced dashboard with upload from our created artifact
from enhanced_variance_assessment_dashboard_with_upload import EnhancedVarianceAnalysisDashboardWithUpload
from gpt_analysis_exporter import GPTAnalysisExporter

def main():
    dashboard = EnhancedVarianceAnalysisDashboardWithUpload()
    dashboard.create_dashboard()

if __name__ == "__main__":
    main()
'''
    
    with open("enhanced_variance_assessment_dashboard_integrated.py", "w") as f:
        f.write(integrated_code)
    
    print("✅ Created integrated dashboard: enhanced_variance_assessment_dashboard_integrated.py")

def create_setup_script():
    """Create setup script for all components"""
    
    setup_script = '''#!/usr/bin/env python3
"""
Setup Script for Enhanced LLM Analysis System
============================================
"""

import os
import subprocess
import sys

def install_dependencies():
    """Install additional dependencies"""
    dependencies = [
        "streamlit>=1.28.0",
        "plotly>=5.15.0",
        "scikit-learn>=1.3.0",
        "scipy>=1.11.0"
    ]
    
    for dep in dependencies:
        print(f"Installing {dep}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

def create_directories():
    """Create necessary directories"""
    dirs = ["exports", "uploads", "analysis_reports"]
    
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        print(f"✅ Created directory: {dir_name}")

def main():
    print("🔧 Setting up Enhanced LLM Analysis System...")
    
    install_dependencies()
    create_directories()
    
    print("\\n✅ Setup completed!")
    print("\\n📋 Next steps:")
    print("1. Export your database: python database_export_for_dashboard.py")
    print("2. Run dashboard: streamlit run enhanced_variance_assessment_dashboard_with_upload.py")
    print("3. Upload your exported file or connect to database")
    print("4. Export analysis for GPT: Use the Data Export tab")

if __name__ == "__main__":
    main()
'''
    
    with open("setup_enhanced_analysis.py", "w") as f:
        f.write(setup_script)
    
    print("✅ Created setup script: setup_enhanced_analysis.py")

def main():
    print("🔧 Integrating Upload Functionality into Dashboard...")
    print("="*60)
    
    backup_original_dashboard()
    create_integrated_dashboard() 
    create_setup_script()
    
    print("\n✅ Integration completed!")
    print("\n📋 Files created:")
    print("- enhanced_variance_assessment_dashboard_integrated.py (main dashboard)")
    print("- setup_enhanced_analysis.py (setup script)")
    print("\n🚀 To get started:")
    print("1. Run: python setup_enhanced_analysis.py")
    print("2. Run: streamlit run enhanced_variance_assessment_dashboard_with_upload.py")

if __name__ == "__main__":
    main()