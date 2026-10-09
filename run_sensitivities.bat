@echo off
REM Double-click to run every prespecified sensitivity analysis not yet run,
REM then collect the aggregate results into one review file.
REM Each sensitivity runs ONCE; finished ones are skipped, never rerun.
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo .venv not found in %CD% - create it first, see README.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python project.py sensitivity-all
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo Done. Opening the review file - send it to Claude for the interpretation.
  start "" notepad "logs\sensitivity_results_for_review.txt"
) else (
  echo Something stopped the run - see the messages above and the newest file in logs\.
)
pause
