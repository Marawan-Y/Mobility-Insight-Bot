@echo off
echo Setting up Mobility Insight Bot...

REM Create virtual environment
python -m venv venv
call venv\Scripts\activate

REM Install dependencies
pip install -r requirements.txt

REM Run database fix
python fix_database.py

REM Run health check
python health_check.py

echo Setup complete! Run 'python Final_Structured_app.py' to start the application.