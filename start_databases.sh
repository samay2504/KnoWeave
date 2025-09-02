#!/bin/bash
# Database startup script for Human-AI Co-Creation System (Linux/Mac)

echo "🗄️ Starting Database Services for Human-AI Co-Creation System"

# Check if Docker is running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "Please install Docker and ensure it's running"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running"
    echo "Please start Docker service"
    exit 1
fi

echo "✅ Docker is available"

# Start the database services
echo "🚀 Starting ArangoDB and MongoDB containers..."

if docker-compose -f docker-compose.databases.yml up -d; then
    echo "✅ Database containers started successfully"
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to initialize..."
    sleep 10
    
    # Check ArangoDB
    echo "🔍 Checking ArangoDB connection..."
    if curl -s http://localhost:8529 > /dev/null; then
        echo "✅ ArangoDB is running on http://localhost:8529"
    else
        echo "⚠️ ArangoDB may still be starting up..."
    fi
    
    # Check MongoDB
    echo "🔍 Checking MongoDB connection..."
    if docker exec mongodb mongosh --eval "db.runCommand('ping')" &> /dev/null; then
        echo "✅ MongoDB is running on localhost:27017"
    else
        echo "⚠️ MongoDB may still be starting up..."
    fi
    
    echo ""
    echo "🎉 Database Services Status:"
    echo "   📊 ArangoDB Web UI: http://localhost:8529"
    echo "      Username: root"
    echo "      Password: samay2504"
    echo "   📊 MongoDB: mongodb://localhost:27017"
    echo "      Username: samay2504"
    echo "      Password: 250403"
    echo ""
    echo "🚀 You can now start the server with: python run_server.py"
    
else
    echo "❌ Failed to start database containers"
    exit 1
fi

# Show running containers
echo ""
echo "📋 Running containers:"
docker ps --filter "name=arangodb" --filter "name=mongodb" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
