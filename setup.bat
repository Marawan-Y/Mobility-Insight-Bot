@echo off
echo Setting up Mobility Insight Bot...

REM Create virtual environment
@REM python -m venv venv
call venv\Scripts\activate

REM Install dependencies
@REM pip install -r requirements.txt

REM Run database fix
python fix_database.py

REM Run health check
python health_check.py

echo Setup complete!

:: ---- START THE APP ----
echo Starting application...

python Final_Structured_app.py

goto :end

:fail
echo.
echo Setup failed. See messages above.
pause

:end
popd
endlocal