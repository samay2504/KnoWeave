#!/usr/bin/env python3
"""
ArangoDB Management Script with Authentication
Helps manage ArangoDB server and database setup using environment variables
"""

import asyncio
import sys
import os
import subprocess
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add server directory to path
server_dir = Path(__file__).parent / "server"
sys.path.append(str(server_dir))

# Get configuration from environment
ARANGO_URL = os.getenv("ARANGO_URL", "http://localhost:8529")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "samay2504")
ARANGO_DATABASE = os.getenv("ARANGO_DATABASE", "human_ai_co_create")

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
    """Test ArangoDB connection with environment credentials"""
    try:
        print("🔍 Testing ArangoDB connection...")
        print(f"   URL: {ARANGO_URL}")
        print(f"   User: {ARANGO_USER}")
        print(f"   Database: {ARANGO_DATABASE}")
        
        try:
            from db.arango_client import create_arango_client
            config = {
                'url': ARANGO_URL,
                'user': ARANGO_USER, 
                'password': ARANGO_PASSWORD,
                'database': ARANGO_DATABASE
            }
            
            client = await create_arango_client(config)
            if client and hasattr(client, 'connected') and client.connected:
                print("✅ ArangoDB connection successful!")
                return True
            else:
                print("❌ ArangoDB connection failed")
                return False
        except ImportError:
            # Fallback to direct connection test
            return await test_direct_connection()
            
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

async def test_direct_connection():
    """Test direct ArangoDB connection using arango library"""
    try:
        from arango import ArangoClient as SyncArangoClient
        
        client = SyncArangoClient(hosts=ARANGO_URL)
        
        # Connect to _system database first
        sys_db = client.db(
            name="_system",
            username=ARANGO_USER,
            password=ARANGO_PASSWORD,
        )
        
        # Test connection
        version = sys_db.version()
        print(f"✅ ArangoDB version: {version}")
        
        # Check/create our database
        if not sys_db.has_database(ARANGO_DATABASE):
            print(f"📝 Creating database: {ARANGO_DATABASE}")
            sys_db.create_database(ARANGO_DATABASE)
            print(f"✅ Database {ARANGO_DATABASE} created successfully")
        else:
            print(f"✅ Database {ARANGO_DATABASE} already exists")
            
        return True
        
    except Exception as e:
        print(f"❌ Direct connection test failed: {e}")
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
