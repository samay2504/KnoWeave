# Human-AI Co-Creation Local Development Launcher (PowerShell)
# This script sets up and runs the development environment on Windows

param(
    [switch]$SkipDependencyCheck,
    [switch]$NoMongoDB,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Human-AI Co-Creation Local Development Launcher

Usage: .\run_local.ps1 [OPTIONS]

Options:
  -SkipDependencyCheck    Skip dependency version checks
  -NoMongoDB             Don't attempt to start MongoDB
  -Help                  Show this help message

Examples:
  .\run_local.ps1                          # Full setup and run
  .\run_local.ps1 -SkipDependencyCheck    # Skip version checks
  .\run_local.ps1 -NoMongoDB              # Don't start MongoDB
"@
    exit 0
}

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Human-AI Co-Creation Development Environment" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "requirements.txt") -or -not (Test-Path "web")) {
    Write-Host "❌ Error: Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

# Function to check if command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Check dependencies
if (-not $SkipDependencyCheck) {
    Write-Host "🔍 Checking dependencies..." -ForegroundColor Yellow

    if (-not (Test-Command "python")) {
        Write-Host "❌ Python is required but not found in PATH" -ForegroundColor Red
        Write-Host "   Please install Python 3.9+ from https://python.org" -ForegroundColor Yellow
        exit 1
    }

    if (-not (Test-Command "node")) {
        Write-Host "❌ Node.js is required but not found in PATH" -ForegroundColor Red
        Write-Host "   Please install Node.js 16+ from https://nodejs.org" -ForegroundColor Yellow
        exit 1
    }

    if (-not (Test-Command "npm")) {
        Write-Host "❌ npm is required but not found in PATH" -ForegroundColor Red
        exit 1
    }

    # Check MongoDB or Docker
    if (-not $NoMongoDB) {
        if (-not (Test-Command "mongod") -and -not (Test-Command "docker")) {
            Write-Host "⚠️  Warning: Neither MongoDB nor Docker found" -ForegroundColor Yellow
            Write-Host "   Please ensure MongoDB is running or start with Docker:" -ForegroundColor Yellow
            Write-Host "   docker run -d --name mongodb -p 27017:27017 mongo:5.0" -ForegroundColor Yellow
        }
    }

    # Python version check
    try {
        $pythonVersion = python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
        $requiredVersion = [version]"3.9"
        $currentVersion = [version]$pythonVersion

        if ($currentVersion -lt $requiredVersion) {
            Write-Host "❌ Python 3.9+ required, found $pythonVersion" -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ Python $pythonVersion found" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Unable to check Python version" -ForegroundColor Red
        exit 1
    }

    # Node version check
    try {
        $nodeVersion = node --version
        $nodeVersionNumber = $nodeVersion.Substring(1)  # Remove 'v' prefix
        $requiredNodeVersion = [version]"16.0.0"
        $currentNodeVersion = [version]$nodeVersionNumber

        if ($currentNodeVersion -lt $requiredNodeVersion) {
            Write-Host "❌ Node.js 16+ required, found $nodeVersionNumber" -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ Node.js $nodeVersionNumber found" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Unable to check Node.js version" -ForegroundColor Red
        exit 1
    }
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "🔌 Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location web
npm install
Set-Location ..

# Set up environment file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "⚙️  Creating environment file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "📝 Please update .env with your configuration before proceeding" -ForegroundColor Yellow
}

# Install pre-commit hooks
Write-Host "🔧 Setting up pre-commit hooks..." -ForegroundColor Yellow
try {
    pre-commit install
}
catch {
    Write-Host "⚠️  Pre-commit hooks installation failed (this is optional)" -ForegroundColor Yellow
}

# Start MongoDB if Docker is available and no MongoDB is running
if (-not $NoMongoDB) {
    if (Test-Command "docker") {
        $mongoRunning = docker ps --filter "name=mongodb" --filter "status=running" -q
        if (-not $mongoRunning) {
            Write-Host "🐳 Starting MongoDB with Docker..." -ForegroundColor Yellow
            try {
                docker run -d --name mongodb -p 27017:27017 mongo:5.0
            }
            catch {
                Write-Host "⚠️  Could not start MongoDB with Docker" -ForegroundColor Yellow
                Write-Host "   Please ensure MongoDB is running manually" -ForegroundColor Yellow
            }
        }
    }
}

# Function to cleanup on exit
function Cleanup {
    Write-Host ""
    Write-Host "🧹 Cleaning up..." -ForegroundColor Yellow
    if ($Global:BackendProcess) {
        Write-Host "🛑 Stopping backend server..." -ForegroundColor Yellow
        Stop-Process -Id $Global:BackendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($Global:FrontendProcess) {
        Write-Host "🛑 Stopping frontend server..." -ForegroundColor Yellow
        Stop-Process -Id $Global:FrontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "👋 Goodbye!" -ForegroundColor Green
}

# Set up signal handlers
Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

try {
    # Start backend server
    Write-Host "🔧 Starting backend server..." -ForegroundColor Yellow
    Set-Location server
    $Global:BackendProcess = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -PassThru
    Set-Location ..

    # Wait for backend to start
    Write-Host "⏳ Waiting for backend to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5

    # Start frontend server
    Write-Host "🎨 Starting frontend development server..." -ForegroundColor Yellow
    Set-Location web
    $Global:FrontendProcess = Start-Process -FilePath "npm" -ArgumentList "start" -PassThru
    Set-Location ..

    # Wait for frontend to start
    Write-Host "⏳ Waiting for frontend to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    Write-Host ""
    Write-Host "🎉 Development environment is ready!" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "🖥️  Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "🔧 Backend API: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "📚 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "📊 API Redoc: http://localhost:8000/redoc" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "💡 Tips:" -ForegroundColor Yellow
    Write-Host "   - Press Ctrl+C to stop all servers" -ForegroundColor White
    Write-Host "   - Backend auto-reloads on file changes" -ForegroundColor White
    Write-Host "   - Frontend auto-reloads on file changes" -ForegroundColor White
    Write-Host "   - Check .env file for configuration" -ForegroundColor White
    Write-Host ""
    Write-Host "🏃‍♂️ Running... (Press Ctrl+C to stop)" -ForegroundColor Green

    # Wait for user interrupt
    try {
        while ($true) {
            Start-Sleep -Seconds 1
            # Check if processes are still running
            if ($Global:BackendProcess.HasExited) {
                Write-Host "❌ Backend process has exited unexpectedly" -ForegroundColor Red
                break
            }
            if ($Global:FrontendProcess.HasExited) {
                Write-Host "❌ Frontend process has exited unexpectedly" -ForegroundColor Red
                break
            }
        }
    }
    catch [System.Management.Automation.PipelineStoppedException] {
        # User pressed Ctrl+C
    }
}
finally {
    Cleanup
}
