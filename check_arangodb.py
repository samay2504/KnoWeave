#!/usr/bin/env python3
"""
Quick ArangoDB Status Check
"""

import subprocess
import requests

def check_docker_container():
    """Check if ArangoDB container is running"""
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=arangodb', '--format', '{{.Names}}'], capture_output=True, text=True)
        return 'arangodb' in result.stdout
    except:
        return False

def check_arango_api():
    """Check if ArangoDB API is responding"""
    try:
        response = requests.get('http://localhost:8529/_api/version', 
                              auth=('root', 'samay2504'), 
                              timeout=5)
        return response.status_code == 200
    except:
        return False

def check_port():
    """Check if port 8529 is listening"""
    try:
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
        return ':8529' in result.stdout
    except:
        return False

def main():
    print("🔍 ArangoDB Status Check")
    print("=" * 30)
    
    container_running = check_docker_container()
    port_listening = check_port()
    api_responding = check_arango_api()
    
    print(f"Docker Container: {'✅ Running' if container_running else '❌ Not Running'}")
    print(f"Port 8529:        {'✅ Listening' if port_listening else '❌ Not Listening'}")
    print(f"ArangoDB API:     {'✅ Responding' if api_responding else '❌ Not Responding'}")
    
    if container_running and port_listening and api_responding:
        print("\n🎉 ArangoDB is fully operational!")
        print("🌐 Web UI: http://localhost:8529")
        return True
    else:
        print("\n❌ ArangoDB has issues. Run setup_arangodb.py to fix.")
        return False

if __name__ == "__main__":
    main()
