#!/bin/bash

# Human-AI Co-Creation Local Development Launcher
# This script sets up and runs the development environment

set -e  # Exit on any error

echo "🚀 Starting Human-AI Co-Creation Development Environment"
echo "========================================================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ] || [ ! -d "web" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is required but not installed"
    exit 1
fi

# Check MongoDB
if ! command_exists mongod && ! command_exists docker; then
    echo "⚠️  Warning: Neither MongoDB nor Docker found"
    echo "   Please ensure MongoDB is running or start with Docker:"
    echo "   docker run -d --name mongodb -p 27017:27017 mongo:5.0"
fi

# Python version check
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $REQUIRED_VERSION+ required, found $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION found"

# Node version check
NODE_VERSION=$(node --version | cut -d'v' -f2)
REQUIRED_NODE="16.0.0"

if [ "$(printf '%s\n' "$REQUIRED_NODE" "$NODE_VERSION" | sort -V | head -n1)" != "$REQUIRED_NODE" ]; then
    echo "❌ Node.js $REQUIRED_NODE+ required, found $NODE_VERSION"
    exit 1
fi

echo "✅ Node.js $NODE_VERSION found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd web
npm install
cd ..

# Set up environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating environment file..."
    cp .env.example .env
    echo "📝 Please update .env with your configuration before proceeding"
fi

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
pre-commit install

# Start MongoDB if Docker is available and no MongoDB is running
if command_exists docker && ! pgrep -x "mongod" > /dev/null; then
    echo "🐳 Starting MongoDB with Docker..."
    if ! docker ps | grep -q mongodb; then
        docker run -d --name mongodb -p 27017:27017 mongo:5.0 || {
            echo "⚠️  Could not start MongoDB with Docker"
            echo "   Please ensure MongoDB is running manually"
        }
    fi
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    if [ ! -z "$BACKEND_PID" ]; then
        echo "🛑 Stopping backend server (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "🛑 Stopping frontend server (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo "👋 Goodbye!"
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Start backend server
echo "🔧 Starting backend server..."
cd server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Start frontend server
echo "🎨 Starting frontend development server..."
cd web
npm start &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 10

echo ""
echo "🎉 Development environment is ready!"
echo "========================================="
echo "🖥️  Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "📊 API Redoc: http://localhost:8000/redoc"
echo ""
echo "💡 Tips:"
echo "   - Press Ctrl+C to stop all servers"
echo "   - Backend auto-reloads on file changes"
echo "   - Frontend auto-reloads on file changes"
echo "   - Check .env file for configuration"
echo ""
echo "🏃‍♂️ Running... (Press Ctrl+C to stop)"

# Wait for user interrupt
wait
