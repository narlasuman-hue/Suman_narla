@echo off
rem Starts the Job Lineage demo: backend + frontend, loads the demo data, opens the browser.
rem Put this file in the Suman_narla folder (next to "src" and "frontend") and double-click it.
setlocal
title Job Lineage demo
cd /d "%~dp0"

if not exist "src\api\main.py" (
  echo This file must be in the Suman_narla folder, next to the src and frontend folders.
  pause
  exit /b 1
)

rem ---- Check Python 3.12 / 3.11 and Node.js ----
set "PY="
py -3.12 --version >nul 2>&1 && set "PY=py -3.12"
if not defined PY ( py -3.11 --version >nul 2>&1 && set "PY=py -3.11" )
if not defined PY (
  echo Python 3.12 was not found. Install it with:
  echo     winget install -e --id Python.Python.3.12
  echo then close this window and double-click run_demo.bat again.
  pause
  exit /b 1
)
where npm >nul 2>&1 || (
  echo Node.js was not found. Install it with:
  echo     winget install -e --id OpenJS.NodeJS.LTS
  echo then close this window and double-click run_demo.bat again.
  pause
  exit /b 1
)

rem ---- First run only: install packages ----
if not exist "venv\Scripts\python.exe" (
  echo Creating the Python environment...
  %PY% -m venv venv || goto :fail
)
if not exist "venv\.installed" (
  echo Installing backend packages - first run only, takes a few minutes...
  "venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
  echo ok> "venv\.installed"
)
if not exist "frontend\node_modules" (
  echo Installing frontend packages - first run only, takes a few minutes...
  pushd frontend
  call npm install --legacy-peer-deps
  if errorlevel 1 (
    popd
    goto :fail
  )
  popd
)

rem ---- Settings (inherited by both server windows) ----
set "DATABASE_URL=sqlite:///./lineage_demo.db"
set "DANGEROUSLY_DISABLE_HOST_CHECK=true"
set "TSC_COMPILE_ON_ERROR=true"
set "BROWSER=none"
set "PORT=3000"

rem ---- Start both servers in their own windows ----
echo Starting the backend and frontend in two new windows. Keep them open during the demo.
start "Lineage BACKEND - keep open" cmd /k venv\Scripts\python.exe -m uvicorn src.api.main:app --port 8000
start "Lineage FRONTEND - keep open" /d frontend cmd /k npm start

rem ---- Wait for the backend, then load the demo data ----
echo Waiting for the backend...
set /a tries=0
:waitapi
curl -s -f -o nul http://127.0.0.1:8000/api/v1/job-lineage/platforms
if not errorlevel 1 goto apiready
set /a tries+=1
if %tries% geq 60 (
  echo The backend did not start. Look at the "Lineage BACKEND" window for the error.
  pause
  exit /b 1
)
timeout /t 2 /nobreak >nul
goto waitapi
:apiready
echo Loading the demo data...
curl -s -f -o nul -X POST http://127.0.0.1:8000/api/v1/job-lineage/sync || echo Could not load the data - click "Sync job metadata" on the page.

rem ---- Wait for the frontend, then open the browser ----
echo Waiting for the frontend - the first start can take a minute...
set /a tries=0
:waitweb
curl -s -f -o nul http://127.0.0.1:3000
if not errorlevel 1 goto webready
set /a tries+=1
if %tries% geq 120 (
  echo The frontend did not start. Look at the "Lineage FRONTEND" window for the error.
  pause
  exit /b 1
)
timeout /t 2 /nobreak >nul
goto waitweb
:webready
start "" http://localhost:3000/job-lineage
echo.
echo The demo is open at http://localhost:3000/job-lineage
echo To stop it, close the two "Lineage" windows.
pause
exit /b 0

:fail
echo.
echo Setup failed - see the messages above.
echo If the pip step failed, delete the "venv" folder, make sure Python 3.12 is installed, and run this again.
pause
exit /b 1
