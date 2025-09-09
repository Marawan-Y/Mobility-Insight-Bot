@echo off
setlocal EnableDelayedExpansion

:: ============================================================================
:: Schaeffler Mobility Insight Platform - Windows Installer
:: ============================================================================

echo.
echo =========================================================================
echo  Schaeffler Mobility Insight Platform - Complete Installation
echo =========================================================================
echo.
echo This script will install all prerequisites and set up your environment
echo Please run this script as Administrator for best results
echo.

:: Color definitions
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

:: Create installation directory
set "INSTALL_DIR=%USERPROFILE%\SchaefflerMobility"
echo %BLUE%Creating installation directory: %INSTALL_DIR%%RESET%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

echo.
echo =========================================================================
echo  PHASE 1: Installing Prerequisites
echo =========================================================================

:: Check and install Git
echo %BLUE%Checking for Git...%RESET%
git --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%Git not found. Installing Git for Windows...%RESET%
    echo Please download and install Git from: https://git-scm.com/download/win
    echo After installation, please restart this script
    pause
    exit /b 1
) else (
    echo %GREEN%Git is already installed%RESET%
)

:: Check and install Python
echo %BLUE%Checking for Python...%RESET%
python --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%Python not found. Installing Python...%RESET%
    echo Please download and install Python 3.9+ from: https://www.python.org/downloads/
    echo IMPORTANT: Check 'Add Python to PATH' during installation
    echo After installation, please restart this script
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo %GREEN%Python !PYTHON_VERSION! is installed%RESET%
)

:: Check and install MySQL
echo %BLUE%Checking for MySQL...%RESET%
mysql --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%MySQL not found. Please install MySQL Server...%RESET%
    echo Download from: https://dev.mysql.com/downloads/mysql/
    echo IMPORTANT: Remember your root password!
    echo After installation, please restart this script
    pause
    exit /b 1
) else (
    echo %GREEN%MySQL is installed%RESET%
)

echo.
echo =========================================================================
echo  PHASE 2: Project Setup
echo =========================================================================

:: Clone or update repository
if exist "schaeffler-mobility-insight" (
    echo %BLUE%Updating existing repository...%RESET%
    cd schaeffler-mobility-insight
    git pull
) else (
    echo %BLUE%Cloning repository...%RESET%
    git clone https://github.com/your-org/schaeffler-mobility-insight.git
    cd schaeffler-mobility-insight
)

:: Create virtual environment
echo %BLUE%Creating Python virtual environment...%RESET%
if exist "venv" (
    echo %YELLOW%Virtual environment already exists, recreating...%RESET%
    rmdir /s /q venv
)
python -m venv venv

:: Activate virtual environment
echo %BLUE%Activating virtual environment...%RESET%
call venv\Scripts\activate.bat

:: Upgrade pip
echo %BLUE%Upgrading pip...%RESET%
python -m pip install --upgrade pip

:: Install Python dependencies
echo %BLUE%Installing Python dependencies...%RESET%
pip install -r requirements.txt
if errorlevel 1 (
    echo %RED%Failed to install dependencies. Trying individual packages...%RESET%
    pip install Flask python-dotenv SQLAlchemy PyMySQL
    pip install google-cloud-aiplatform google-auth cryptography
    pip install vertexai Markdown openai langchain langchain-community
    pip install reportlab streamlit pandas plotly numpy
)

echo.
echo =========================================================================
echo  PHASE 3: Database Configuration
echo =========================================================================

echo %BLUE%Setting up MySQL database...%RESET%

:: Get MySQL credentials
set /p MYSQL_ROOT_PASSWORD="Enter MySQL root password: "
set /p DB_PASSWORD="Enter password for new mobility_bot database user: "

:: Create database and user
echo %BLUE%Creating database and user...%RESET%
mysql -u root -p%MYSQL_ROOT_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS mobility_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p%MYSQL_ROOT_PASSWORD% -e "CREATE USER IF NOT EXISTS 'mobility_user'@'localhost' IDENTIFIED BY '%DB_PASSWORD%';"
mysql -u root -p%MYSQL_ROOT_PASSWORD% -e "GRANT ALL PRIVILEGES ON mobility_bot.* TO 'mobility_user'@'localhost';"
mysql -u root -p%MYSQL_ROOT_PASSWORD% -e "FLUSH PRIVILEGES;"

if errorlevel 1 (
    echo %RED%Database setup failed. Please check your MySQL root password%RESET%
    pause
    exit /b 1
) else (
    echo %GREEN%Database setup completed successfully%RESET%
)

echo.
echo =========================================================================
echo  PHASE 4: Environment Configuration
echo =========================================================================

:: Create .env file
echo %BLUE%Creating environment configuration...%RESET%

(
echo # Flask configuration
echo FLASK_ENV=development
echo SECRET_KEY=schaeffler_mobility_secret_key_2024
echo.
echo # LLM provider: "openai" ^(default^) or "vertex"
echo LLM_PROVIDER=openai
echo.
echo # OpenAI API settings
echo OPENAI_API_KEY=your-openai-api-key-here
echo.
echo # Google Vertex AI settings ^(if using Vertex^)
echo VERTEX_PROJECT=your-gcp-project-id
echo VERTEX_LOCATION=us-central1
echo VERTEX_MODEL=gemini-1.0-pro
echo.
echo # MySQL database credentials
echo DB_HOST=localhost
echo DB_PORT=3306
echo DB_USER=mobility_user
echo DB_PASSWORD=%DB_PASSWORD%
echo DB_NAME=mobility_bot
echo.
echo # Google Form for Feedback
echo FEEDBACK_FORM_URL=https://docs.google.com/forms/d/e/your-form-id/viewform
) > .env

echo %GREEN%Environment file created: .env%RESET%

echo.
echo =========================================================================
echo  PHASE 5: Application Setup
echo =========================================================================

:: Run database initialization
echo %BLUE%Initializing database structure...%RESET%
python fix_database.py

:: Run health check
echo %BLUE%Running health check...%RESET%
python health_check.py

echo.
echo =========================================================================
echo  PHASE 6: API Key Configuration
echo =========================================================================

echo %YELLOW%IMPORTANT: You need to configure your LLM API key%RESET%
echo.
echo For OpenAI:
echo 1. Get your API key from: https://platform.openai.com/api-keys
echo 2. Edit .env file and replace 'your-openai-api-key-here' with your actual key
echo.
echo For Google Vertex AI:
echo 1. Set up Google Cloud Project with Vertex AI enabled
echo 2. Configure authentication and update VERTEX_PROJECT in .env
echo.

set /p OPENAI_KEY="Enter your OpenAI API key (or press Enter to skip): "
if not "!OPENAI_KEY!"=="" (
    powershell -Command "(Get-Content .env) -replace 'your-openai-api-key-here', '!OPENAI_KEY!' | Set-Content .env"
    echo %GREEN%OpenAI API key configured%RESET%
)

echo.
echo =========================================================================
echo  PHASE 7: Final Setup and Testing
echo =========================================================================

:: Create startup scripts
echo %BLUE%Creating startup scripts...%RESET%

:: Main application startup script
(
echo @echo off
echo cd /d "%INSTALL_DIR%\schaeffler-mobility-insight"
echo call venv\Scripts\activate.bat
echo echo Starting Schaeffler Mobility Insight Platform...
echo python Final_Structured_app.py
echo pause
) > start_mobility_platform.bat

:: Assessment dashboard startup script
(
echo @echo off
echo cd /d "%INSTALL_DIR%\schaeffler-mobility-insight"
echo call venv\Scripts\activate.bat
echo echo Starting Assessment Dashboard...
echo streamlit run final_assessment_dashboard.py --server.port 8502
echo pause
) > start_assessment_dashboard.bat

:: Health check script
(
echo @echo off
echo cd /d "%INSTALL_DIR%\schaeffler-mobility-insight"
echo call venv\Scripts\activate.bat
echo echo Running Health Check...
echo python health_check.py
echo pause
) > run_health_check.bat

echo %GREEN%Startup scripts created:%RESET%
echo - start_mobility_platform.bat
echo - start_assessment_dashboard.bat  
echo - run_health_check.bat

:: Create desktop shortcuts
echo %BLUE%Creating desktop shortcuts...%RESET%
set "DESKTOP=%USERPROFILE%\Desktop"

:: Main application shortcut
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\Schaeffler Mobility Platform.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\schaeffler-mobility-insight\start_mobility_platform.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\schaeffler-mobility-insight'; $Shortcut.IconLocation = '%INSTALL_DIR%\schaeffler-mobility-insight\static\schaeffler-logo.ico'; $Shortcut.Save()"

:: Assessment dashboard shortcut  
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\Mobility Assessment Dashboard.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\schaeffler-mobility-insight\start_assessment_dashboard.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\schaeffler-mobility-insight'; $Shortcut.Save()"

echo.
echo =========================================================================
echo  Installation Complete!
echo =========================================================================
echo.
echo %GREEN%✓ All components installed successfully%RESET%
echo.
echo %BLUE%Installation Location:%RESET% %INSTALL_DIR%\schaeffler-mobility-insight
echo.
echo %BLUE%Next Steps:%RESET%
echo 1. Configure your API key in the .env file (if not done above)
echo 2. Run health check: run_health_check.bat
echo 3. Start the application: start_mobility_platform.bat
echo 4. Access via browser: http://localhost:5000
echo.
echo %BLUE%Assessment Dashboard:%RESET%
echo - Start with: start_assessment_dashboard.bat
echo - Access via browser: http://localhost:8502
echo.
echo %BLUE%Desktop shortcuts created:%RESET%
echo - Schaeffler Mobility Platform
echo - Mobility Assessment Dashboard
echo.
echo %YELLOW%Important Files:%RESET%
echo - Configuration: .env
echo - Health Check: run_health_check.bat
echo - Application: start_mobility_platform.bat
echo - Dashboard: start_assessment_dashboard.bat
echo.

set /p START_NOW="Would you like to start the application now? (y/n): "
if /i "!START_NOW!"=="y" (
    echo %BLUE%Starting application...%RESET%
    start start_mobility_platform.bat
    
    set /p START_DASHBOARD="Would you like to start the assessment dashboard too? (y/n): "
    if /i "!START_DASHBOARD!"=="y" (
        echo %BLUE%Starting assessment dashboard...%RESET%
        start start_assessment_dashboard.bat
    )
)

echo.
echo %GREEN%Setup completed! Enjoy using Schaeffler Mobility Insight Platform!%RESET%
echo.
pause