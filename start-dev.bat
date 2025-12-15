@echo off
REM DevPlatform Development Startup Script for Windows

echo 🚀 Starting DevPlatform Development Environment
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.12+
    exit /b 1
)

REM Check if Node is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed. Please install Node.js 20+
    exit /b 1
)

echo ✅ Prerequisites check passed
echo.

REM Start backend
echo 📦 Starting backend server...
cd backend

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist ".venv\.installed" (
    echo Installing backend dependencies...
    pip install -r requirements.txt
    type nul > .venv\.installed
)

REM Start backend in new window
echo Starting backend on http://localhost:8000
start "DevPlatform Backend" cmd /k "uvicorn main:app --reload --port 8000"
cd ..

REM Wait a bit for backend to start
timeout /t 2 /nobreak >nul

REM Start frontend
echo 📦 Starting frontend server...
cd frontend

REM Install dependencies if needed
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)

REM Start frontend in new window
echo Starting frontend on http://localhost:5173
start "DevPlatform Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ✅ DevPlatform is running!
echo.
echo 📍 Backend:  http://localhost:8000
echo 📍 Frontend: http://localhost:5173
echo.
echo Close the terminal windows to stop the services
pause

