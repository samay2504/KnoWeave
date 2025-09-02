#!/usr/bin/env python3
"""
ArangoDB Management Script
Helps manage ArangoDB server and database setup
"""

import asyncio
import sys
import os
import subprocess
from pathlib import Path

# Add server directory to path
server_dir = Path(__file__).parent / "server"
sys.path.append(str(server_dir))

async def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker is available: {result.stdout.strip()}")
            return True
        else:
            print("❌ Docker is not working")
            return False
    except FileNotFoundError:
        print("❌ Docker is not installed")
        return False

async def check_arango_container():
    """Check if ArangoDB container is running"""
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=arangodb', '--format', 'table {{.Names}}\\t{{.Status}}'], capture_output=True, text=True)
        if 'arangodb' in result.stdout:
            print("✅ ArangoDB container is running")
            return True
        else:
            print("❌ ArangoDB container is not running")
            return False
    except Exception as e:
        print(f"❌ Error checking container: {e}")
        return False

async def start_arangodb():
    """Start ArangoDB container"""
    try:
        print("🚀 Starting ArangoDB container...")
        result = subprocess.run([
            'docker', 'run', '-d', 
            '--name', 'arangodb',
            '-p', '8529:8529',
            '-e', 'ARANGO_ROOT_PASSWORD=samay2504',
            'arangodb/arangodb:latest'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ ArangoDB container started successfully")
            return True
        else:
            print(f"❌ Failed to start container: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error starting container: {e}")
        return False

async def test_arango_connection():
    """Test ArangoDB connection"""
    try:
        from db.arango_client import create_arango_client
        config = {
            'url': 'http://localhost:8529',
            'user': 'root', 
            'password': 'samay2504',
            'database': 'human_ai_co_create'
        }
        
        print("🔍 Testing ArangoDB connection...")
        client = await create_arango_client(config)
        if client:
            print("✅ ArangoDB connection successful!")
            return True
        else:
            print("❌ ArangoDB connection failed")
            return False
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

async def create_database():
    """Create the human_ai_co_create database"""
    try:
        from arango import ArangoClient as SyncArangoClient
        
        print("🔧 Creating database...")
        client = SyncArangoClient(hosts='http://localhost:8529')
        sys_db = client.db('_system', username='root', password='samay2504')
        
        if sys_db.has_database('human_ai_co_create'):
            print("✅ Database 'human_ai_co_create' already exists")
        else:
            sys_db.create_database('human_ai_co_create')
            print("✅ Database 'human_ai_co_create' created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Database creation error: {e}")
        return False

async def main():
    """Main function"""
    print("🔧 ArangoDB Setup and Management")
    print("=" * 40)
    
    # Check Docker
    if not await check_docker():
        print("Please install Docker first: https://www.docker.com/")
        return False
    
    # Check if container is running
    if not await check_arango_container():
        print("Starting ArangoDB container...")
        if not await start_arangodb():
            print("Failed to start ArangoDB")
            return False
        
        # Wait a moment for container to start
        print("⏳ Waiting for ArangoDB to start...")
        await asyncio.sleep(10)
    
    # Create database
    if not await create_database():
        return False
    
    # Test connection
    if not await test_arango_connection():
        return False
    
    print("\n🎉 ArangoDB is fully set up and working!")
    print("📊 ArangoDB Web UI: http://localhost:8529")
    print("🔐 Username: root")
    print("🔑 Password: samay2504")
    print("🗄️  Database: human_ai_co_create")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
