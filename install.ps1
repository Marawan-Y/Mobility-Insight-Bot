#Requires -Version 5.1

<#
.SYNOPSIS
    Schaeffler Mobility Insight Platform - PowerShell Installer

.DESCRIPTION
    Complete installation script for the Schaeffler Mobility Insight Platform.
    Installs all prerequisites, sets up the environment, and configures the application.

.PARAMETER InstallPath
    Installation directory path. Default: $env:USERPROFILE\SchaefflerMobility

.PARAMETER SkipPrerequisites
    Skip installation of prerequisites (Git, Python, MySQL)

.PARAMETER OpenAIKey
    OpenAI API key for configuration

.EXAMPLE
    .\Install-SchaefflerMobility.ps1

.EXAMPLE
    .\Install-SchaefflerMobility.ps1 -InstallPath "C:\SchaefflerMobility" -OpenAIKey "sk-..."

#>

[CmdletBinding()]
param(
    [string]$InstallPath = "$env:USERPROFILE\SchaefflerMobility",
    [switch]$SkipPrerequisites,
    [string]$OpenAIKey
)

# Set execution policy for current session
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Color functions
function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Blue
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "=========================================================================" -ForegroundColor Blue
    Write-Host " $Message " -ForegroundColor Blue
    Write-Host "=========================================================================" -ForegroundColor Blue
    Write-Host ""
}

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Install-Chocolatey {
    Write-Info "Installing Chocolatey package manager..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    
    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    if (Test-Command choco) {
        Write-Success "Chocolatey installed successfully"
        return $true
    } else {
        Write-Error "Failed to install Chocolatey"
        return $false
    }
}

function Install-Prerequisites {
    Write-Header "Installing Prerequisites"
    
    # Install Chocolatey if not present
    if (-not (Test-Command choco)) {
        if (-not (Install-Chocolatey)) {
            Write-Error "Cannot proceed without Chocolatey. Please install it manually."
            exit 1
        }
    } else {
        Write-Success "Chocolatey is already installed"
    }

    # Install Git
    Write-Info "Checking for Git..."
    if (Test-Command git) {
        $gitVersion = git --version
        Write-Success "Git is already installed ($gitVersion)"
    } else {
        Write-Info "Installing Git..."
        choco install git -y
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        if (Test-Command git) {
            Write-Success "Git installed successfully"
        } else {
            Write-Error "Failed to install Git"
            exit 1
        }
    }

    # Install Python
    Write-Info "Checking for Python..."
    if (Test-Command python) {
        $pythonVersion = python --version
        Write-Success "Python is already installed ($pythonVersion)"
    } else {
        Write-Info "Installing Python..."
        choco install python -y
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        if (Test-Command python) {
            Write-Success "Python installed successfully"
        } else {
            Write-Error "Failed to install Python"
            exit 1
        }
    }

    # Install MySQL
    Write-Info "Checking for MySQL..."
    if (Test-Command mysql) {
        Write-Success "MySQL is already installed"
    } else {
        Write-Info "Installing MySQL..."
        choco install mysql -y
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        if (Test-Command mysql) {
            Write-Success "MySQL installed successfully"
        } else {
            Write-Error "Failed to install MySQL"
            exit 1
        }
    }

    # Install Visual C++ redistributables (needed for some Python packages)
    Write-Info "Installing Visual C++ redistributables..."
    choco install vcredist2019 -y
}

function Initialize-Project {
    Write-Header "Project Setup"
    
    # Create installation directory
    Write-Info "Creating installation directory: $InstallPath"
    if (-not (Test-Path $InstallPath)) {
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    }
    Set-Location $InstallPath

    # Clone or update repository
    $repoPath = Join-Path $InstallPath "schaeffler-mobility-insight"
    if (Test-Path $repoPath) {
        Write-Info "Updating existing repository..."
        Set-Location $repoPath
        git pull
    } else {
        Write-Info "Cloning repository..."
        git clone https://github.com/your-org/schaeffler-mobility-insight.git
        Set-Location $repoPath
    }

    # Create virtual environment
    Write-Info "Creating Python virtual environment..."
    if (Test-Path "venv") {
        Write-Warning "Virtual environment already exists, recreating..."
        Remove-Item -Recurse -Force venv
    }
    python -m venv venv

    # Activate virtual environment
    Write-Info "Activating virtual environment..."
    & ".\venv\Scripts\Activate.ps1"

    # Upgrade pip
    Write-Info "Upgrading pip..."
    python -m pip install --upgrade pip

    # Install Python dependencies
    Write-Info "Installing Python dependencies..."
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to install from requirements.txt. Installing individual packages..."
            pip install Flask python-dotenv SQLAlchemy PyMySQL
            pip install google-cloud-aiplatform google-auth cryptography
            pip install vertexai Markdown openai langchain langchain-community
            pip install reportlab streamlit pandas plotly numpy
        }
    } else {
        Write-Info "Installing core dependencies..."
        pip install Flask python-dotenv SQLAlchemy PyMySQL
        pip install google-cloud-aiplatform google-auth cryptography
        pip install vertexai Markdown openai langchain langchain-community
        pip install reportlab streamlit pandas plotly numpy
    }
}

function Initialize-Database {
    Write-Header "Database Configuration"
    
    Write-Info "Setting up MySQL database..."

    # Get MySQL credentials
    $mysqlRootPassword = Read-Host "Enter MySQL root password (press Enter if no password)" -AsSecureString
    $mysqlRootPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($mysqlRootPassword))
    
    $dbPassword = Read-Host "Enter password for new mobility_bot database user" -AsSecureString
    $dbPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword))

    # Create database and user
    Write-Info "Creating database and user..."
    
    $mysqlArgs = @("-u", "root")
    if ($mysqlRootPasswordPlain) {
        $mysqlArgs += @("-p$mysqlRootPasswordPlain")
    }
    
    try {
        & mysql @mysqlArgs -e "CREATE DATABASE IF NOT EXISTS mobility_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        & mysql @mysqlArgs -e "CREATE USER IF NOT EXISTS 'mobility_user'@'localhost' IDENTIFIED BY '$dbPasswordPlain';"
        & mysql @mysqlArgs -e "GRANT ALL PRIVILEGES ON mobility_bot.* TO 'mobility_user'@'localhost';"
        & mysql @mysqlArgs -e "FLUSH PRIVILEGES;"
        
        Write-Success "Database setup completed successfully"
        return $dbPasswordPlain
    }
    catch {
        Write-Error "Database setup failed. Please check your MySQL root password"
        exit 1
    }
}

function Initialize-Configuration {
    param([string]$DatabasePassword)
    
    Write-Header "Environment Configuration"
    
    # Create .env file
    Write-Info "Creating environment configuration..."
    
    $envContent = @"
# Flask configuration
FLASK_ENV=development
SECRET_KEY=schaeffler_mobility_secret_key_2024

# LLM provider: "openai" (default) or "vertex"
LLM_PROVIDER=openai

# OpenAI API settings
OPENAI_API_KEY=your-openai-api-key-here

# Google Vertex AI settings (if using Vertex)
VERTEX_PROJECT=your-gcp-project-id
VERTEX_LOCATION=us-central1
VERTEX_MODEL=gemini-1.0-pro

# MySQL database credentials
DB_HOST=localhost
DB_PORT=3306
DB_USER=mobility_user
DB_PASSWORD=$DatabasePassword
DB_NAME=mobility_bot

# Google Form for Feedback
FEEDBACK_FORM_URL=https://docs.google.com/forms/d/e/your-form-id/viewform
"@

    Set-Content -Path ".env" -Value $envContent -Encoding UTF8
    Write-Success "Environment file created: .env"
}

function Initialize-Application {
    Write-Header "Application Setup"
    
    # Run database initialization
    Write-Info "Initializing database structure..."
    python fix_database.py

    # Run health check
    Write-Info "Running health check..."
    python health_check.py
}

function Set-APIConfiguration {
    Write-Header "API Key Configuration"
    
    Write-Warning "IMPORTANT: You need to configure your LLM API key"
    Write-Host ""
    Write-Host "For OpenAI:"
    Write-Host "1. Get your API key from: https://platform.openai.com/api-keys"
    Write-Host "2. Edit .env file and replace 'your-openai-api-key-here' with your actual key"
    Write-Host ""
    Write-Host "For Google Vertex AI:"
    Write-Host "1. Set up Google Cloud Project with Vertex AI enabled"
    Write-Host "2. Configure authentication and update VERTEX_PROJECT in .env"
    Write-Host ""

    if (-not $OpenAIKey) {
        $OpenAIKey = Read-Host "Enter your OpenAI API key (or press Enter to skip)"
    }

    if ($OpenAIKey) {
        $envContent = Get-Content ".env" -Raw
        $envContent = $envContent -replace "your-openai-api-key-here", $OpenAIKey
        Set-Content -Path ".env" -Value $envContent -Encoding UTF8
        Write-Success "OpenAI API key configured"
    }
}

function New-StartupScripts {
    Write-Header "Final Setup and Testing"
    
    Write-Info "Creating startup scripts..."

    # Main application startup script
    $mainAppScript = @'
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting Schaeffler Mobility Insight Platform...
echo Access the application at: http://localhost:5000
python Final_Structured_app.py
pause
'@
    Set-Content -Path "start_mobility_platform.bat" -Value $mainAppScript

    # PowerShell version of main app script
    $mainAppPSScript = @'
# Schaeffler Mobility Platform Starter
Set-Location $PSScriptRoot
& ".\venv\Scripts\Activate.ps1"
Write-Host "Starting Schaeffler Mobility Insight Platform..." -ForegroundColor Green
Write-Host "Access the application at: http://localhost:5000" -ForegroundColor Yellow
python Final_Structured_app.py
Read-Host "Press Enter to continue"
'@
    Set-Content -Path "Start-MobilityPlatform.ps1" -Value $mainAppPSScript

    # Assessment dashboard startup script
    $dashboardScript = @'
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting Assessment Dashboard...
echo Access the dashboard at: http://localhost:8502
streamlit run final_assessment_dashboard.py --server.port 8502
pause
'@
    Set-Content -Path "start_assessment_dashboard.bat" -Value $dashboardScript

    # PowerShell version of dashboard script
    $dashboardPSScript = @'
# Assessment Dashboard Starter
Set-Location $PSScriptRoot
& ".\venv\Scripts\Activate.ps1"
Write-Host "Starting Assessment Dashboard..." -ForegroundColor Green
Write-Host "Access the dashboard at: http://localhost:8502" -ForegroundColor Yellow
streamlit run final_assessment_dashboard.py --server.port 8502
Read-Host "Press Enter to continue"
'@
    Set-Content -Path "Start-AssessmentDashboard.ps1" -Value $dashboardPSScript

    # Health check script
    $healthCheckScript = @'
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Running Health Check...
python health_check.py
pause
'@
    Set-Content -Path "run_health_check.bat" -Value $healthCheckScript

    # PowerShell version of health check
    $healthCheckPSScript = @'
# Health Check Runner
Set-Location $PSScriptRoot
& ".\venv\Scripts\Activate.ps1"
Write-Host "Running Health Check..." -ForegroundColor Green
python health_check.py
Read-Host "Press Enter to continue"
'@
    Set-Content -Path "Start-HealthCheck.ps1" -Value $healthCheckPSScript

    Write-Success "Startup scripts created:"
    Write-Info "- start_mobility_platform.bat / Start-MobilityPlatform.ps1"
    Write-Info "- start_assessment_dashboard.bat / Start-AssessmentDashboard.ps1"
    Write-Info "- run_health_check.bat / Start-HealthCheck.ps1"
}

function New-DesktopShortcuts {
    Write-Info "Creating desktop shortcuts..."
    
    $desktop = [Environment]::GetFolderPath("Desktop")
    $workingDir = Get-Location
    
    # Main application shortcut
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$desktop\Schaeffler Mobility Platform.lnk")
    $Shortcut.TargetPath = "$workingDir\start_mobility_platform.bat"
    $Shortcut.WorkingDirectory = $workingDir
    $Shortcut.IconLocation = "$workingDir\static\schaeffler-logo.ico"
    $Shortcut.Description = "Schaeffler Mobility Insight Platform"
    $Shortcut.Save()

    # Assessment dashboard shortcut
    $Shortcut = $WshShell.CreateShortcut("$desktop\Mobility Assessment Dashboard.lnk")
    $Shortcut.TargetPath = "$workingDir\start_assessment_dashboard.bat"
    $Shortcut.WorkingDirectory = $workingDir
    $Shortcut.Description = "Mobility Assessment Dashboard"
    $Shortcut.Save()

    # PowerShell shortcuts
    $Shortcut = $WshShell.CreateShortcut("$desktop\Mobility Platform (PowerShell).lnk")
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$workingDir\Start-MobilityPlatform.ps1`""
    $Shortcut.WorkingDirectory = $workingDir
    $Shortcut.Description = "Schaeffler Mobility Platform (PowerShell)"
    $Shortcut.Save()

    Write-Success "Desktop shortcuts created"
}

function Show-CompletionSummary {
    Write-Header "Installation Complete!"
    
    Write-Success "All components installed successfully"
    Write-Host ""
    Write-Info "Installation Location: $(Get-Location)"
    Write-Host ""
    Write-Info "Next Steps:"
    Write-Host "1. Configure your API key in the .env file (if not done above)"
    Write-Host "2. Run health check: .\run_health_check.bat or .\Start-HealthCheck.ps1"
    Write-Host "3. Start the application: .\start_mobility_platform.bat or .\Start-MobilityPlatform.ps1"
    Write-Host "4. Access via browser: http://localhost:5000"
    Write-Host ""
    Write-Info "Assessment Dashboard:"
    Write-Host "- Start with: .\start_assessment_dashboard.bat or .\Start-AssessmentDashboard.ps1"
    Write-Host "- Access via browser: http://localhost:8502"
    Write-Host ""
    Write-Warning "Important Files:"
    Write-Host "- Configuration: .env"
    Write-Host "- Health Check: run_health_check.bat / Start-HealthCheck.ps1"
    Write-Host "- Application: start_mobility_platform.bat / Start-MobilityPlatform.ps1"
    Write-Host "- Dashboard: start_assessment_dashboard.bat / Start-AssessmentDashboard.ps1"
    Write-Host ""

    $startNow = Read-Host "Would you like to start the application now? (y/n)"
    
    if ($startNow -match '^[Yy]') {
        Write-Info "Starting application..."
        Start-Process -FilePath ".\start_mobility_platform.bat" -WorkingDirectory (Get-Location)
        
        $startDashboard = Read-Host "Would you like to start the assessment dashboard too? (y/n)"
        
        if ($startDashboard -match '^[Yy]') {
            Write-Info "Starting assessment dashboard..."
            Start-Process -FilePath ".\start_assessment_dashboard.bat" -WorkingDirectory (Get-Location)
        }
    }

    Write-Host ""
    Write-Success "Setup completed! Enjoy using Schaeffler Mobility Insight Platform!"
    Write-Host ""
}

# Main execution
function Main {
    Clear-Host
    
    Write-Host @"
  ____       _                __  __  _            
 / ___|  ___| |__   __ _  ___|  \/  || | ___ _ __  
 \___ \ / __| '_ \ / _`` |/ _ \ |\/| || |/ _ \ '__| 
  ___) | (__| | | | (_| |  __/ |  | || |  __/ |    
 |____/ \___|_| |_|\__,_|\___|_|  |_||_|\___|_|    
                                                   
 Mobility Insight Platform - PowerShell Installer      
"@ -ForegroundColor Magenta

    Write-Header "Schaeffler Mobility Insight Platform - Complete Installation"
    Write-Host "This script will install all prerequisites and set up your environment"
    Write-Host "Please ensure you have administrator privileges for package installation"
    Write-Host ""

    try {
        if (-not $SkipPrerequisites) {
            Install-Prerequisites
        }
        
        Initialize-Project
        $dbPassword = Initialize-Database
        Initialize-Configuration -DatabasePassword $dbPassword
        Initialize-Application
        Set-APIConfiguration
        New-StartupScripts
        New-DesktopShortcuts
        Show-CompletionSummary
    }
    catch {
        Write-Error "Installation failed: $($_.Exception.Message)"
        Write-Host "Stack trace:" -ForegroundColor Red
        Write-Host $_.ScriptStackTrace -ForegroundColor Red
        exit 1
    }
}

# Run main function
Main