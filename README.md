# Schaeffler Mobility Insight Platform

An AI-powered web application for exploring, validating, and implementing emerging mobility technology trends. Built for Schaeffler's Advanced Innovations in Mobility Solutions, this platform leverages large language models to generate strategic insights and actionable implementation roadmaps.

##  Project Overview

The Mobility Insight Platform transforms how Schaeffler identifies and evaluates disruptive technologies in the mobility sector. By combining AI-generated insights with structured assessment frameworks, the platform accelerates innovation decision-making from months to minutes.

### Key Benefits
- **Rapid Technology Scouting**: Generate and evaluate multiple technology trends in real-time
- **Structured Assessment**: Apply Schaeffler's P³ innovation framework consistently
- **Data-Driven Decisions**: Track confidence scores, variance metrics, and implementation readiness
- **Strategic Alignment**: Ensure technologies align with Schaeffler's core competencies and market position

##  Features

### Core Workflow
- **4-Phase Innovation Pipeline**:
  1. **Identification**: Define mobility use-case, sector, and specific demands
  2. **Scouting**: AI generates 3 disruptive technology trends with confidence scores
  3. **Validation**: Comprehensive assessment using radar positioning and PESTEL analysis
  4. **Implementation**: Market-ready solutions with partnership strategies and roadmaps

### Intelligent Components
- **Multi-Model LLM Support**: OpenAI GPT-4 Turbo or Google Vertex AI (Gemini)
- **Fallback Mechanisms**: Ensures consistent output even during API failures
- **Variance Analysis Dashboard**: Track output consistency across multiple trials
- **Quality Assessment Framework**: Automated testing for diversity, compliance, and performance metrics
- **Session Persistence**: Large data handling through file-based storage

### Analytics & Monitoring
- **Real-time Metrics**: API calls, token usage, latency tracking
- **Historical Analysis**: Complete audit trail of all queries and responses
- **Regression Testing**: Automated baseline comparison for output quality
- **Export Capabilities**: CSV/JSON data export for further analysis

## 🛠 Tech Stack

### Backend
- **Python 3.8+** - Core application logic
- **Flask 2.0+** - Web framework
- **SQLAlchemy** - Database ORM with connection pooling
- **PyMySQL** - MySQL database connector

### Frontend
- **Bootstrap 5.3** - Responsive UI framework
- **Jinja2** - Template engine
- **Markdown** - Content rendering with table support

### AI/ML
- **OpenAI API** - GPT-4 Turbo integration
- **Google Vertex AI** - Gemini model support
- **tiktoken** - Token counting and optimization

### Analytics
- **Streamlit** - Interactive dashboards
- **Plotly/Pandas** - Data visualization and analysis
- **NumPy/SciPy** - Statistical computations

### Infrastructure
- **MySQL 5.7+** - Primary database
- **Redis** (optional) - Session caching
- **Docker** (optional) - Containerization

##  Installation & Setup

### Prerequisites
- Python 3.8 or higher
- MySQL 5.7 or higher
- OpenAI API key or Google Cloud project with Vertex AI enabled

### Step 1: Clone Repository
```bash
git clone https://github.com/schaeffler/mobility-insight-platform.git
cd mobility-insight-platform
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment
Create a `.env` file in the root directory:
```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=mobility_bot

# LLM Configuration (choose one)
LLM_PROVIDER=openai  # or "vertex"

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# OR Google Vertex AI Configuration
VERTEX_PROJECT=your-gcp-project-id
VERTEX_LOCATION=us-central1
VERTEX_MODEL=gemini-1.0-pro

# Optional: Feedback Form
FEEDBACK_FORM_URL=https://your-google-form-url
```

### Step 5: Initialize Database
```bash
# Create database
mysql -u root -p
CREATE DATABASE mobility_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;

# Run database setup
python fix_database.py
python setup_assessment_db.py
```

### Step 6: Verify Installation
```bash
python health_check.py
```

##  Usage

### Running the Application

#### Option 1: Quick Start (Windows)
```bash
setup.bat
```

#### Option 2: Manual Start
```bash
python Final_Structured_app.py
```
The application will be available at `http://localhost:5000`

### Running Analytics Dashboard
```bash
streamlit run assessment_dashboard.py
```
Dashboard will open at `http://localhost:8501`

### Workflow Example

1. **Navigate to** `http://localhost:5000`
2. **Select** your mobility use-case (e.g., "People mover mobility")
3. **Choose** sector (e.g., "RoboTaxi")
4. **Describe** your demand (e.g., "Optimize navigation for urban environments")
5. **Review** AI-generated technology trends
6. **Validate** selected trends for detailed assessment
7. **Implement** chosen technology with market-ready solutions

### Advanced Features

#### Generate Variance Trials
```bash
python generate_variance_trials.py --use-case "People mover mobility" --sector "RoboTaxi" --demand "navigation" --trials 5
```

#### Run Quality Assessment
```bash
python assessment_runner.py --use-case "Your use case" --sector "Your sector" --demand "Your demand" --trials 3
```

#### Batch Processing
```bash
python batch_assessment.py --test-cases assessments/test_cases.json --trials 5
```

##  Database Management

### Backup & Restore
```bash
# Create backup
python bin/backup_automation.py

# Switch between local/server databases
python bin/config_manager.py
```

### Remote Access Setup
```bash
python bin/setup_remote_access.py
```

##  Testing & Quality

### Run Tests
```bash
# Regression testing
python regression_testing.py

# API connectivity test
python test_openai_apikey.py
```

### Performance Monitoring
- Access metrics at `/metrics` endpoint
- View quality dashboard via Streamlit
- Check `logs/` directory for detailed logs

##  Project Structure
```
mobility-insight-platform/
├── Final_Structured_app.py      # Main Flask application
├── assessment_dashboard.py      # Streamlit analytics dashboard
├── llm_quality_assessment.py    # Quality assessment framework
├── templates/                   # HTML templates
│   ├── index.html              # Main interface
│   └── base.html               # Base template
├── static/                      # CSS, JS, images
├── bin/                         # Database & deployment tools
├── assessments/                 # Test cases & reports
└── logs/                        # Application logs
```

##  Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add unit tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

##  License

This project is proprietary software owned by Schaeffler AG. All rights reserved.

##  Support

For issues or questions:
- Check the [documentation](docs.md/)

##  Acknowledgments

- Schaeffler Advanced Innovations Team
- OpenAI for GPT-4 API
- Google Cloud for Vertex AI
- Open source community contributors

---
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.<ID>.svg)](https://doi.org/10.5281/zenodo.<ID>)
## 📚 Cite this software
```bibtex
@software{Younis_MobilityInsightBot_2025,
  author    = {Marawan Younis},
  title     = {Mobility Insight Bot (v1.0.0)},
  year      = {2025},
  publisher = {Zenodo},
  version   = {1.0.0},
  doi       = {10.5281/zenodo.<17247162>},
  url       = {(https://doi.org/10.5281/zenodo.17247162)}
}
