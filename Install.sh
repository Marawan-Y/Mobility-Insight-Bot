#!/bin/bash

# ============================================================================
# Schaeffler Mobility Insight Platform - Linux/Unix Installer
# ============================================================================

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
RESET='\033[0m'

# Installation directory
INSTALL_DIR="$HOME/SchaefflerMobility"

print_header() {
    echo -e "\n${BLUE}=========================================================================${RESET}"
    echo -e "${BLUE} $1 ${RESET}"
    echo -e "${BLUE}=========================================================================${RESET}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${RESET}"
}

print_error() {
    echo -e "${RED}✗ $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${RESET}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${RESET}"
}

check_command() {
    if command -v $1 &> /dev/null; then
        return 0
    else
        return 1
    fi
}

install_package() {
    local package=$1
    print_info "Installing $package..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if check_command apt-get; then
            sudo apt-get update && sudo apt-get install -y $package
        elif check_command yum; then
            sudo yum install -y $package
        elif check_command dnf; then
            sudo dnf install -y $package
        elif check_command pacman; then
            sudo pacman -S --noconfirm $package
        else
            print_error "Package manager not found. Please install $package manually."
            return 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if check_command brew; then
            brew install $package
        else
            print_error "Homebrew not found. Please install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            return 1
        fi
    fi
}

# Main installation function
main() {
    clear
    echo -e "${PURPLE}"
    echo "  ____       _                __  __  _            "
    echo " / ___|  ___| |__   __ _  ___|  \/  || | ___ _ __  "
    echo " \___ \ / __| '_ \ / _\` |/ _ \ |\/| || |/ _ \ '__| "
    echo "  ___) | (__| | | | (_| |  __/ |  | || |  __/ |    "
    echo " |____/ \___|_| |_|\__,_|\___|_|  |_||_|\___|_|    "
    echo "                                                   "
    echo " Mobility Insight Platform - Linux Installer      "
    echo -e "${RESET}"

    print_header "Schaeffler Mobility Insight Platform - Complete Installation"
    echo "This script will install all prerequisites and set up your environment"
    echo "Please ensure you have sudo privileges for package installation"
    echo ""

    # Create installation directory
    print_info "Creating installation directory: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    print_header "PHASE 1: Installing Prerequisites"

    # Check and install Git
    print_info "Checking for Git..."
    if check_command git; then
        print_success "Git is already installed ($(git --version))"
    else
        print_warning "Git not found. Installing Git..."
        install_package git
        if check_command git; then
            print_success "Git installed successfully"
        else
            print_error "Failed to install Git. Please install manually."
            exit 1
        fi
    fi

    # Check and install Python
    print_info "Checking for Python..."
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        print_success "Python is installed ($PYTHON_VERSION)"
    else
        print_warning "Python3 not found. Installing Python..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            install_package python3
            install_package python3-pip
            install_package python3-venv
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            install_package python3
        fi
        
        if check_command python3; then
            print_success "Python installed successfully"
        else
            print_error "Failed to install Python. Please install manually."
            exit 1
        fi
    fi

    # Check and install MySQL
    print_info "Checking for MySQL..."
    if check_command mysql; then
        print_success "MySQL is already installed"
    else
        print_warning "MySQL not found. Installing MySQL..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            install_package mysql-server
            # Start MySQL service
            sudo systemctl start mysql
            sudo systemctl enable mysql
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            install_package mysql
            # Start MySQL service on macOS
            brew services start mysql
        fi
        
        if check_command mysql; then
            print_success "MySQL installed successfully"
        else
            print_error "Failed to install MySQL. Please install manually."
            exit 1
        fi
    fi

    # Install additional dependencies
    print_info "Installing additional system dependencies..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        install_package curl
        install_package wget
        install_package build-essential
        install_package libssl-dev
        install_package libffi-dev
        install_package python3-dev
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS usually has these or they come with Xcode tools
        if ! xcode-select -p &> /dev/null; then
            print_info "Installing Xcode command line tools..."
            xcode-select --install
        fi
    fi

    print_header "PHASE 2: Project Setup"

    # Clone or update repository
    if [ -d "schaeffler-mobility-insight" ]; then
        print_info "Updating existing repository..."
        cd schaeffler-mobility-insight
        git pull
    else
        print_info "Cloning repository..."
        git clone https://github.com/your-org/schaeffler-mobility-insight.git
        cd schaeffler-mobility-insight
    fi

    # Create virtual environment
    print_info "Creating Python virtual environment..."
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists, recreating..."
        rm -rf venv
    fi
    python3 -m venv venv

    # Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate

    # Upgrade pip
    print_info "Upgrading pip..."
    python -m pip install --upgrade pip

    # Install Python dependencies
    print_info "Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            print_warning "Failed to install from requirements.txt. Installing individual packages..."
            pip install Flask python-dotenv SQLAlchemy PyMySQL
            pip install google-cloud-aiplatform google-auth cryptography
            pip install vertexai Markdown openai langchain langchain-community
            pip install reportlab streamlit pandas plotly numpy
        fi
    else
        print_info "Installing core dependencies..."
        pip install Flask python-dotenv SQLAlchemy PyMySQL
        pip install google-cloud-aiplatform google-auth cryptography
        pip install vertexai Markdown openai langchain langchain-community
        pip install reportlab streamlit pandas plotly numpy
    fi

    print_header "PHASE 3: Database Configuration"

    print_info "Setting up MySQL database..."

    # Get MySQL credentials
    echo -n "Enter MySQL root password (press Enter if no password): "
    read -s MYSQL_ROOT_PASSWORD
    echo ""

    echo -n "Enter password for new mobility_bot database user: "
    read -s DB_PASSWORD
    echo ""

    # Create database and user
    print_info "Creating database and user..."
    
    if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
        MYSQL_CMD="mysql -u root"
    else
        MYSQL_CMD="mysql -u root -p$MYSQL_ROOT_PASSWORD"
    fi

    $MYSQL_CMD -e "CREATE DATABASE IF NOT EXISTS mobility_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null
    $MYSQL_CMD -e "CREATE USER IF NOT EXISTS 'mobility_user'@'localhost' IDENTIFIED BY '$DB_PASSWORD';" 2>/dev/null
    $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON mobility_bot.* TO 'mobility_user'@'localhost';" 2>/dev/null
    $MYSQL_CMD -e "FLUSH PRIVILEGES;" 2>/dev/null

    if [ $? -eq 0 ]; then
        print_success "Database setup completed successfully"
    else
        print_error "Database setup failed. Please check your MySQL root password"
        exit 1
    fi

    print_header "PHASE 4: Environment Configuration"

    # Create .env file
    print_info "Creating environment configuration..."

    cat > .env << EOF
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
DB_PASSWORD=$DB_PASSWORD
DB_NAME=mobility_bot

# Google Form for Feedback
FEEDBACK_FORM_URL=https://docs.google.com/forms/d/e/your-form-id/viewform
EOF

    print_success "Environment file created: .env"

    print_header "PHASE 5: Application Setup"

    # Run database initialization
    print_info "Initializing database structure..."
    python fix_database.py

    # Run health check
    print_info "Running health check..."
    python health_check.py

    print_header "PHASE 6: API Key Configuration"

    print_warning "IMPORTANT: You need to configure your LLM API key"
    echo ""
    echo "For OpenAI:"
    echo "1. Get your API key from: https://platform.openai.com/api-keys"
    echo "2. Edit .env file and replace 'your-openai-api-key-here' with your actual key"
    echo ""
    echo "For Google Vertex AI:"
    echo "1. Set up Google Cloud Project with Vertex AI enabled"
    echo "2. Configure authentication and update VERTEX_PROJECT in .env"
    echo ""

    echo -n "Enter your OpenAI API key (or press Enter to skip): "
    read OPENAI_KEY

    if [ ! -z "$OPENAI_KEY" ]; then
        sed -i "s/your-openai-api-key-here/$OPENAI_KEY/" .env
        print_success "OpenAI API key configured"
    fi

    print_header "PHASE 7: Final Setup and Testing"

    # Create startup scripts
    print_info "Creating startup scripts..."

    # Main application startup script
    cat > start_mobility_platform.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting Schaeffler Mobility Insight Platform..."
echo "Access the application at: http://localhost:5000"
python Final_Structured_app.py
EOF

    # Assessment dashboard startup script
    cat > start_assessment_dashboard.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting Assessment Dashboard..."
echo "Access the dashboard at: http://localhost:8502"
streamlit run final_assessment_dashboard.py --server.port 8502
EOF

    # Health check script
    cat > run_health_check.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Running Health Check..."
python health_check.py
EOF

    # Make scripts executable
    chmod +x start_mobility_platform.sh
    chmod +x start_assessment_dashboard.sh
    chmod +x run_health_check.sh

    print_success "Startup scripts created and made executable:"
    print_info "- start_mobility_platform.sh"
    print_info "- start_assessment_dashboard.sh"
    print_info "- run_health_check.sh"

    # Create desktop entries (Linux only)
    if [[ "$OSTYPE" == "linux-gnu"* ]] && [ -d "$HOME/.local/share/applications" ]; then
        print_info "Creating desktop entries..."
        
        # Main application desktop entry
        cat > "$HOME/.local/share/applications/schaeffler-mobility-platform.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Schaeffler Mobility Platform
Comment=AI-Powered Technology Trend Analysis
Exec=$INSTALL_DIR/schaeffler-mobility-insight/start_mobility_platform.sh
Icon=$INSTALL_DIR/schaeffler-mobility-insight/static/schaeffler-logo.png
Path=$INSTALL_DIR/schaeffler-mobility-insight
Terminal=true
Categories=Development;Office;
EOF

        # Assessment dashboard desktop entry
        cat > "$HOME/.local/share/applications/mobility-assessment-dashboard.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Mobility Assessment Dashboard
Comment=LLM Output Analysis Dashboard
Exec=$INSTALL_DIR/schaeffler-mobility-insight/start_assessment_dashboard.sh
Icon=$INSTALL_DIR/schaeffler-mobility-insight/static/schaeffler-logo.png
Path=$INSTALL_DIR/schaeffler-mobility-insight
Terminal=true
Categories=Development;Office;
EOF

        print_success "Desktop entries created"
    fi

    print_header "Installation Complete!"

    print_success "All components installed successfully"
    echo ""
    print_info "Installation Location: $INSTALL_DIR/schaeffler-mobility-insight"
    echo ""
    print_info "Next Steps:"
    echo "1. Configure your API key in the .env file (if not done above)"
    echo "2. Run health check: ./run_health_check.sh"
    echo "3. Start the application: ./start_mobility_platform.sh"
    echo "4. Access via browser: http://localhost:5000"
    echo ""
    print_info "Assessment Dashboard:"
    echo "- Start with: ./start_assessment_dashboard.sh"
    echo "- Access via browser: http://localhost:8502"
    echo ""
    print_warning "Important Files:"
    echo "- Configuration: .env"
    echo "- Health Check: run_health_check.sh"
    echo "- Application: start_mobility_platform.sh"
    echo "- Dashboard: start_assessment_dashboard.sh"
    echo ""

    echo -n "Would you like to start the application now? (y/n): "
    read START_NOW

    if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
        print_info "Starting application..."
        gnome-terminal -- bash -c "./start_mobility_platform.sh; exec bash" 2>/dev/null || \
        xterm -e "./start_mobility_platform.sh" 2>/dev/null || \
        ./start_mobility_platform.sh &
        
        echo -n "Would you like to start the assessment dashboard too? (y/n): "
        read START_DASHBOARD
        
        if [[ "$START_DASHBOARD" =~ ^[Yy]$ ]]; then
            print_info "Starting assessment dashboard..."
            gnome-terminal -- bash -c "./start_assessment_dashboard.sh; exec bash" 2>/dev/null || \
            xterm -e "./start_assessment_dashboard.sh" 2>/dev/null || \
            ./start_assessment_dashboard.sh &
        fi
    fi

    echo ""
    print_success "Setup completed! Enjoy using Schaeffler Mobility Insight Platform!"
    echo ""
}

# Error handling
set -e
trap 'echo -e "\n${RED}Installation failed at line $LINENO. Check the error above.${RESET}"; exit 1' ERR

# Run main function
main "$@"