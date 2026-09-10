@echo off
cd /d "%~dp0.."
echo Starting DreamTalk Backend with updated FLAME fitting...
echo.
echo Using Python: %PYTHON% (or default)
python -m uvicorn dreamtalk.backend.main:app --host 0.0.0.0 --port 5000 --log-level info
pause
