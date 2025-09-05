# 🚀 Human-AI Co-Creation System - CLI Commands Reference

## 📍 **Path Context**
**Project Root:** `d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create`

All commands should be run from the project root unless otherwise specified.

---

## 🐳 **Docker Commands**

### **Start Databases**
```bash
# Start all databases (ArangoDB + MongoDB) in background
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"
docker compose -f docker-compose.databases.yml up -d

# Start databases with logs visible
docker compose -f docker-compose.databases.yml up

# Start only ArangoDB
docker compose up -d arangodb

# Start only MongoDB  
docker compose up -d mongodb
```

### **Start Full System**
```bash
# Start entire system (databases + server + frontend)
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"
docker compose up -d

# Start with logs visible
docker compose up

# Start for development (if dev compose exists)
docker compose -f docker-compose.dev.yml up -d
```

### **Docker Management**
```bash
# Check running containers
docker ps

# Check all containers (including stopped)
docker ps -a

# Check logs for specific service
docker logs human_ai_arangodb
docker logs human_ai_mongodb
docker logs human_ai_server

# Stop all services
docker compose down

# Stop and remove volumes (CAUTION: deletes data)
docker compose down -v

# Restart specific service
docker compose restart arangodb
docker compose restart mongodb
```

---

## 🚀 **Server Commands**

### **Start Backend Server**
```bash
# Start FastAPI server
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"
python run_server.py

# Alternative server start
python run.py

# Start with specific configuration
python server/app.py
```

### **Server Health Checks**
```bash
# Check server health
curl http://localhost:8000/health

# PowerShell version
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET

# Test specific endpoints
curl http://localhost:8000/api/session/new
curl http://localhost:8000/docs  # API documentation
```

---

## 🌐 **Frontend Commands**

### **Start React Development Server**
```bash
# Navigate to frontend directory
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create\web"

# Install dependencies (first time only)
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

---

## 🗄️ **Database Commands**

### **MongoDB Commands**
```bash
# Connect to MongoDB (if running locally)
mongo mongodb://localhost:27017/human_ai_co_create

# Connect with authentication
mongo mongodb://samay2504:250403@localhost:27017/human_ai_co_create

# Export database
mongodump --uri="mongodb://samay2504:250403@localhost:27017/human_ai_co_create"

# Import database
mongorestore --uri="mongodb://samay2504:250403@localhost:27017/human_ai_co_create" dump/
```

### **ArangoDB Commands**
```bash
# Access ArangoDB shell (Docker)
docker exec -it arangodb arangosh

# ArangoDB Web UI
# Open browser: http://localhost:8529
# Username: root
# Password: password

# Check ArangoDB connection
curl http://localhost:8529/_api/version
```

---

## 🧪 **Testing Commands**

### **Run Tests**
```bash
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"

# Run agent pipeline test
python test_agent_pipeline.py

# Run comprehensive tests
python test_comprehensive_canonical_system.py

# Run server tests
python test_server.py

# Run specific test modules
python -m pytest tests/
python -m pytest server/tests/
```

### **Integration Tests**
```bash
# Test frontend integration
python test_frontend_integration_validation.py

# Test multi-domain validation
python test_multi_domain_validation.py

# Test authentication flow
python test_auth_flow.py

# Test health endpoints
python test_health.py
```

---

## 📦 **Environment & Dependencies**

### **Python Environment**
```bash
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"

# Install dependencies
pip install -r requirements.txt

# Install locked dependencies
pip install -r requirements-locked.txt

# Install with pip-tools
pip-sync requirements-locked.txt

# Update dependencies
pip-compile requirements.txt
```

### **Virtual Environment**
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (PowerShell)
venv\Scripts\Activate.ps1

# Deactivate
deactivate
```

---

## 🔧 **Development Commands**

### **Database Setup**
```bash
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"

# Setup ArangoDB
python setup_arangodb.py

# Check ArangoDB connection
python check_arangodb.py

# Test MongoDB connection
python scripts/test_mongodb_connection.py
```

### **Code Quality**
```bash
# Format code
black server/
black web/src/

# Lint code
flake8 server/
eslint web/src/

# Type checking
mypy server/
```

---

## 🌍 **Network & API Commands**

### **API Testing**
```bash
# Test session creation
curl -X POST http://localhost:8000/api/session/new \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "topic": "story", "topic_descriptor": "Test story"}'

# Test suggestion system
curl -X POST http://localhost:8000/api/session/{session_id}/suggestion_signal \
  -H "Content-Type: application/json" \
  -d '{"trigger_type": "user_button", "topic_content": "Test content"}'

# PowerShell API testing
$body = '{"user_id": "test", "topic": "story", "topic_descriptor": "Test story"}'
Invoke-RestMethod -Uri "http://localhost:8000/api/session/new" -Method POST -Body $body -ContentType "application/json"
```

### **Authentication Testing**
```bash
# Test Google OAuth
curl http://localhost:8000/auth/google/login

# Test auth callback
curl http://localhost:8000/auth/google/callback
```

---

## 📊 **Monitoring & Logs**

### **System Monitoring**
```bash
# Check all service status
docker compose ps

# Monitor logs in real-time
docker compose logs -f

# Monitor specific service
docker compose logs -f arangodb
docker compose logs -f mongodb

# Check system resources
docker stats
```

### **Log Analysis**
```bash
# View application logs
tail -f logs/app.log

# Check error logs
grep ERROR logs/app.log

# Monitor specific component
tail -f logs/agent_pipeline.log
```

---

## 🔄 **Backup & Restore**

### **Data Backup**
```bash
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"

# Backup MongoDB
mongodump --uri="mongodb://samay2504:250403@localhost:27017/human_ai_co_create" --out=data/backups/

# Backup ArangoDB (through Docker)
docker exec arangodb arangodump --server.endpoint http://localhost:8529 --output-directory /tmp/backup

# Backup JSON data
cp -r data/ data_backup_$(date +%Y%m%d_%H%M%S)/
```

### **System Restore**
```bash
# Restore MongoDB
mongorestore --uri="mongodb://samay2504:250403@localhost:27017/human_ai_co_create" data/backups/human_ai_co_create/

# Restore from backup
cp -r data_backup_20250905_020000/ data/
```

---

## 🚦 **Quick Start Sequences**

### **Development Startup**
```bash
# 1. Start databases
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"
docker compose -f docker-compose.databases.yml up -d

# 2. Start backend server
python run_server.py

# 3. Start frontend (new terminal)
cd web
npm start
```

### **Full System Startup**
```bash
# Start everything with Docker
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"
docker compose up -d

# Check all services are running
docker compose ps
curl http://localhost:8000/health
curl http://localhost:3000
```

### **Testing Sequence**
```bash
# 1. Ensure databases are running
docker compose -f docker-compose.databases.yml up -d

# 2. Run core tests
python test_agent_pipeline.py

# 3. Test server endpoints
python test_server.py

# 4. Test frontend integration
python test_frontend_integration_validation.py
```

---

## 🛠️ **Troubleshooting Commands**

### **Reset System**
```bash
# Stop all services
docker compose down

# Remove all containers and volumes (CAUTION)
docker compose down -v
docker system prune -a

# Restart fresh
docker compose up -d
```

### **Check Connections**
```bash
# Test database connections
python -c "
import sys; sys.path.append('server')
from workspace import Workspace
w = Workspace('test', {})
print('✅ Workspace created successfully')
"

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8529/_api/version
```

### **Debug Issues**
```bash
# Check logs for errors
docker compose logs | grep ERROR

# Test individual components
python check_arangodb.py
python test_health.py

# Validate configuration
python -c "
import sys; sys.path.append('server')
from server_config import ServerConfig
config = ServerConfig()
print('✅ Configuration valid')
"
```

---

## 📝 **Git Commands**

### **Version Control**
```bash
cd "d:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create"

# Stage all changes
git add .

# Commit changes
git commit -m "feat: description of changes"

# Check status
git status

# View changes
git diff
git log --oneline
```

---

## 🎯 **Production Commands**

### **Production Deployment**
```bash
# Build for production
docker compose -f docker-compose.prod.yml build

# Start production services
docker compose -f docker-compose.prod.yml up -d

# Check production health
curl https://your-domain.com/health
```

---

**📍 Remember:** Always run commands from the correct directory path and ensure Docker is running before executing Docker commands!
