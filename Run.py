#!/usr/bin/env python3
"""
Schaeffler Mobility Insight Platform - Enhanced Application Runner
================================================================

This script handles the complete startup sequence with health checks,
performance monitoring, and error recovery.

Features:
- Pre-flight health checks
- Database structure validation
- Session management initialization
- Error handling setup
- Performance monitoring
- Graceful shutdown handling
"""

import os
import sys
import time
import signal
import subprocess
from datetime import datetime
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# Import application modules
try:
    from fix_database import fix_database
    from health_check import run_health_check
    from session_manager import session_manager
    from logger_config import setup_logger
    from error_handler import handle_application_error
    from config import config
except ImportError as e:
    print(f"Error importing application modules: {e}")
    print("Please ensure all required files are present in the application directory")
    sys.exit(1)

# Global variables
logger = None
app_process = None

def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ███████╗ ██████╗██╗  ██╗ █████╗ ███████╗███████╗███████╗██╗     ███████╗  ║
║   ██╔════╝██╔════╝██║  ██║██╔══██╗██╔════╝██╔════╝██╔════╝██║     ██╔════╝  ║
║   ███████╗██║     ███████║███████║█████╗  █████╗  █████╗  ██║     █████╗    ║
║   ╚════██║██║     ██╔══██║██╔══██║██╔══╝  ██╔══╝  ██╔══╝  ██║     ██╔══╝    ║
║   ███████║╚██████╗██║  ██║██║  ██║███████╗██║     ██║     ███████╗███████╗  ║
║   ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝     ╚══════╝╚══════╝  ║
║                                                                              ║
║                    MOBILITY INSIGHT PLATFORM                                ║
║                   Advanced Application Runner                               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)
    print(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

def check_environment():
    """Check environment variables and configuration"""
    global logger
    logger.info("Checking environment configuration...")
    
    required_env_vars = [
        'SECRET_KEY',
        'DB_HOST',
        'DB_USER', 
        'DB_PASSWORD',
        'DB_NAME'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file configuration")
        return False
    
    # Check API keys
    llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    if llm_provider == 'openai':
        if not os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY') == 'your-openai-api-key-here':
            logger.warning("OpenAI API key not configured")
            print("⚠️  OpenAI API key not configured")
            print("Please update OPENAI_API_KEY in your .env file")
            return False
    elif llm_provider == 'vertex':
        if not os.getenv('VERTEX_PROJECT'):
            logger.warning("Vertex AI project not configured")
            print("⚠️  Vertex AI project not configured")
            print("Please update VERTEX_PROJECT in your .env file")
            return False
    
    logger.info("Environment configuration validated")
    print("✅ Environment configuration valid")
    return True

def run_pre_flight_checks():
    """Run comprehensive pre-flight checks"""
    global logger
    print("\n🔍 Running Pre-flight Checks...")
    print("-" * 40)
    
    checks_passed = 0
    total_checks = 5
    
    # 1. Environment check
    logger.info("Starting pre-flight checks")
    if check_environment():
        checks_passed += 1
        print("✅ Environment configuration")
    else:
        print("❌ Environment configuration")
    
    # 2. Database fix and validation
    print("🔧 Fixing database structure...")
    try:
        fix_database()
        checks_passed += 1
        print("✅ Database structure")
        logger.info("Database structure validated and fixed")
    except Exception as e:
        print(f"❌ Database structure: {e}")
        logger.error(f"Database fix failed: {e}")
    
    # 3. Health check
    print("🏥 Running health check...")
    try:
        if run_health_check():
            checks_passed += 1
            print("✅ System health check")
            logger.info("Health check passed")
        else:
            print("❌ System health check")
            logger.error("Health check failed")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        logger.error(f"Health check error: {e}")
    
    # 4. Session manager initialization
    print("📂 Initializing session management...")
    try:
        session_manager.cleanup_old_sessions()
        checks_passed += 1
        print("✅ Session management")
        logger.info("Session manager initialized")
    except Exception as e:
        print(f"❌ Session management: {e}")
        logger.error(f"Session manager error: {e}")
    
    # 5. Check for required files
    print("📁 Checking application files...")
    required_files = [
        'Final_Structured_app.py',
        'templates/index.html',
        'templates/base.html',
        'static/style.css',
        'assessment_write.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if not missing_files:
        checks_passed += 1
        print("✅ Application files")
        logger.info("All required files present")
    else:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        logger.error(f"Missing required files: {missing_files}")
    
    print("-" * 40)
    print(f"Pre-flight Summary: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("🚀 All checks passed! Ready to launch!")
        logger.info("All pre-flight checks passed")
        return True
    elif checks_passed >= 3:
        print("⚠️  Some issues detected, but application may still work")
        logger.warning(f"Pre-flight checks: {checks_passed}/{total_checks} passed")
        response = input("Continue anyway? (y/n): ").lower().strip()
        return response in ['y', 'yes']
    else:
        print("❌ Critical issues detected. Cannot start application.")
        logger.error("Critical pre-flight check failures")
        return False

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        global app_process, logger
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        print(f"\n🛑 Received shutdown signal. Stopping application gracefully...")
        
        if app_process:
            try:
                app_process.terminate()
                app_process.wait(timeout=10)
                print("✅ Application stopped gracefully")
                logger.info("Application stopped gracefully")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing application...")
                app_process.kill()
                logger.warning("Application force killed")
            except Exception as e:
                print(f"Error stopping application: {e}")
                logger.error(f"Error stopping application: {e}")
        
        # Cleanup
        session_manager.cleanup_old_sessions()
        print("👋 Goodbye!")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def start_application():
    """Start the main Flask application"""
    global app_process, logger
    
    print("\n🚀 Starting Schaeffler Mobility Insight Platform...")
    print("-" * 50)
    
    try:
        # Start the Flask application
        app_process = subprocess.Popen([
            sys.executable, 'Final_Structured_app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        logger.info("Flask application started")
        print("✅ Application server started")
        print("🌐 Access the application at: http://127.0.0.1:5000")
        print("📊 Health monitoring enabled")
        
        # Monitor the application
        monitor_application()
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        print(f"❌ Failed to start application: {e}")
        return False

def monitor_application():
    """Monitor the running application"""
    global app_process, logger
    
    print("\n📊 Application Monitoring Active")
    print("Press Ctrl+C to stop the application")
    print("-" * 50)
    
    start_time = time.time()
    last_health_check = 0
    health_check_interval = 300  # 5 minutes
    
    while True:
        try:
            # Check if process is still running
            if app_process.poll() is not None:
                # Process has terminated
                return_code = app_process.returncode
                if return_code == 0:
                    print("✅ Application exited normally")
                    logger.info("Application exited normally")
                else:
                    print(f"❌ Application exited with error code: {return_code}")
                    logger.error(f"Application exited with code: {return_code}")
                    
                    # Show stderr if available
                    stderr_output = app_process.stderr.read()
                    if stderr_output:
                        print("Error output:")
                        print(stderr_output)
                        logger.error(f"Application stderr: {stderr_output}")
                break
            
            # Periodic health checks
            current_time = time.time()
            if current_time - last_health_check > health_check_interval:
                print(f"🏥 Running periodic health check... (Runtime: {format_uptime(current_time - start_time)})")
                try:
                    if run_health_check():
                        print("✅ Health check passed")
                        logger.info("Periodic health check passed")
                    else:
                        print("⚠️  Health check issues detected")
                        logger.warning("Periodic health check failed")
                except Exception as e:
                    print(f"⚠️  Health check error: {e}")
                    logger.error(f"Periodic health check error: {e}")
                
                last_health_check = current_time
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user")
            logger.info("Shutdown requested by user")
            break
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            logger.error(f"Monitoring error: {e}")
            break

def format_uptime(seconds):
    """Format uptime in human-readable format"""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def show_startup_info():
    """Show important startup information"""
    print("\n📋 Startup Information")
    print("-" * 30)
    print(f"📁 Working Directory: {os.getcwd()}")
    print(f"🐍 Python Version: {sys.version.split()[0]}")
    print(f"🌐 LLM Provider: {os.getenv('LLM_PROVIDER', 'openai')}")
    print(f"🗄️  Database: {os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}")
    print(f"📝 Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    print(f"🔧 Environment: {os.getenv('FLASK_ENV', 'development')}")

def check_port_availability():
    """Check if the required ports are available"""
    import socket
    
    ports_to_check = [5000]  # Flask default port
    unavailable_ports = []
    
    for port in ports_to_check:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            if result == 0:
                unavailable_ports.append(port)
    
    if unavailable_ports:
        print(f"⚠️  Ports {unavailable_ports} are already in use")
        print("Please stop other applications using these ports or change the configuration")
        return False
    
    return True

def main():
    """Main application runner"""
    global logger
    
    # Print banner
    print_banner()
    
    # Setup logging
    logger = setup_logger()
    logger.info("Application runner started")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Show startup info
    show_startup_info()
    
    # Check port availability
    if not check_port_availability():
        logger.error("Port availability check failed")
        sys.exit(1)
    
    # Run pre-flight checks
    if not run_pre_flight_checks():
        logger.error("Pre-flight checks failed")
        print("\n❌ Cannot start application due to failed checks")
        print("Please resolve the issues above and try again")
        sys.exit(1)
    
    # Start application
    print("\n" + "=" * 80)
    start_application()
    
    # Cleanup on exit
    print("\n🧹 Performing cleanup...")
    session_manager.cleanup_old_sessions()
    logger.info("Application runner finished")
    print("✅ Cleanup completed")

if __name__ == "__main__":
    main()