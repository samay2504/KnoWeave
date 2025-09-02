#!/usr/bin/env powershell
<#
.SYNOPSIS
    Database startup script for Human-AI Co-Creation System
.DESCRIPTION
    Starts ArangoDB and MongoDB containers for the application
#>

Write-Host "🗄️ Starting Database Services for Human-AI Co-Creation System" -ForegroundColor Green

# Check if Docker is running
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running or not installed" -ForegroundColor Red
    Write-Host "Please install Docker Desktop and ensure it's running" -ForegroundColor Yellow
    exit 1
}

# Start the database services
Write-Host "🚀 Starting ArangoDB and MongoDB containers..." -ForegroundColor Cyan

try {
    docker-compose -f docker-compose.databases.yml up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database containers started successfully" -ForegroundColor Green
        
        # Wait for services to be ready
        Write-Host "⏳ Waiting for services to initialize..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        # Check ArangoDB
        Write-Host "🔍 Checking ArangoDB connection..." -ForegroundColor Cyan
        try {
            $arangoResponse = Invoke-WebRequest -Uri "http://localhost:8529" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "✅ ArangoDB is running on http://localhost:8529" -ForegroundColor Green
        } catch {
            Write-Host "⚠️ ArangoDB may still be starting up..." -ForegroundColor Yellow
        }
        
        # Check MongoDB
        Write-Host "🔍 Checking MongoDB connection..." -ForegroundColor Cyan
        try {
            $mongoCheck = docker exec mongodb mongosh --eval "db.runCommand('ping')" 2>`$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ MongoDB is running on localhost:27017" -ForegroundColor Green
            } else {
                Write-Host "⚠️ MongoDB may still be starting up..." -ForegroundColor Yellow
            }
        } catch {
            Write-Host "⚠️ MongoDB connection check failed, but container is running" -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host "🎉 Database Services Status:" -ForegroundColor Green
        Write-Host "   📊 ArangoDB Web UI: http://localhost:8529" -ForegroundColor Cyan
        Write-Host "      Username: root" -ForegroundColor Gray
        Write-Host "      Password: samay2504" -ForegroundColor Gray
        Write-Host "   📊 MongoDB: mongodb://localhost:27017" -ForegroundColor Cyan
        Write-Host "      Username: samay2504" -ForegroundColor Gray
        Write-Host "      Password: 250403" -ForegroundColor Gray
        Write-Host ""
        Write-Host "🚀 You can now start the server with: python run_server.py" -ForegroundColor Green
        
    } else {
        Write-Host "❌ Failed to start database containers" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "❌ Error starting databases: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Show running containers
Write-Host ""
Write-Host "📋 Running containers:" -ForegroundColor Cyan
docker ps --filter "name=arangodb" --filter "name=mongodb" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
