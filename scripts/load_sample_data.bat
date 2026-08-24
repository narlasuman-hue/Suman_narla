@echo off
REM Load sample data into Database Metadata Catalog
REM Usage: load_sample_data.bat

setlocal enabledelayedexpansion

echo Database Metadata Catalog - Sample Data Loader
echo ==================================================
echo.

REM Check if virtual environment is activated
if "%VIRTUAL_ENV%"=="" (
    echo Activating virtual environment...
    if exist "venv\Scripts\activate.bat" (
        call venv\Scripts\activate.bat
    ) else if exist ".venv\Scripts\activate.bat" (
        call .venv\Scripts\activate.bat
    ) else (
        echo Error: Virtual environment not found
        echo Please create one with: python -m venv venv
        exit /b 1
    )
)

REM Check if .env file exists
if not exist ".env" (
    echo Error: .env file not found
    echo Please copy .env.example to .env and configure your database settings
    exit /b 1
)

REM Initialize database schema first
echo Initializing database schema...
python -c "from src.catalog.database import init_db; init_db()" 2>nul

echo Loading sample data...
python -m src.sample_data

echo.
echo Sample data loaded successfully!
echo.
echo Next steps:
echo   1. Start the backend API: python main.py
echo   2. Start the frontend: cd frontend ^&^& npm start
echo   3. Open http://localhost:3000 in your browser
echo.
echo API Documentation: http://localhost:8000/docs
