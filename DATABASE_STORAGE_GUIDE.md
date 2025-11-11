# Database Storage Guide - Human-AI Co-Creation System

## 📊 Data Storage Architecture

The system uses a **hybrid storage approach** for production readiness and reliability:

---

## 🗄️ Storage Layers

### **1. MongoDB (Primary Storage)**
**Purpose:** Session workspace data, user data, metadata  
**Location:** Docker volume `mongo_data`  
**Connection:** `mongodb://root:password@localhost:27017/human_ai_cocreation`

**Stores:**
- Session workspaces (content, metadata, policy)
- User profiles and authentication data
- Character data and story elements
- Events and KB triples
- Projections and branches

**Docker Volume:**
```yaml
volumes:
  mongo_data:  # Named Docker volume
    # Data persists across container restarts
    # Located in Docker's volume storage
```

---

### **2. ArangoDB (Graph Storage)**
**Purpose:** Knowledge graph, relationships, semantic connections  
**Location:** Docker volumes `arango_data` and `arango_apps`  
**Connection:** `http://localhost:8529`

**Stores:**
- Graph nodes (characters, events, settings)
- Graph edges (relationships between entities)
- Semantic relationships
- Story structure connections

**Docker Volumes:**
```yaml
volumes:
  arango_data:      # Database files
  arango_apps:      # ArangoDB applications
```

---

### **3. JSON Fallback (Local Filesystem)**
**Purpose:** Backup storage when databases unavailable  
**Location:** `./data/sessions/` directory  
**Format:** `session_{id}.json`

**Stores:**
- Complete workspace snapshots
- Used when MongoDB connection fails
- Automatic fallback mechanism

**File Structure:**
```
human-ai-co-create/
├── data/
│   ├── sessions/
│   │   ├── session_abc123.json
│   │   ├── session_def456.json
│   │   └── ...
│   └── backups/
│       └── ... (optional backup copies)
```

---

## 🔍 Accessing the Data

### **Option 1: MongoDB (Recommended)**

#### **Using MongoDB Compass (GUI):**
1. Download: https://www.mongodb.com/try/download/compass
2. Connect: `mongodb://root:password@localhost:27017`
3. Database: `human_ai_cocreation`
4. Collection: `workspaces`

#### **Using mongosh (CLI):**
```bash
# Connect to MongoDB
docker exec -it human_ai_mongodb mongosh -u root -p password

# Switch to database
use human_ai_cocreation

# Show collections
show collections

# Query sessions
db.workspaces.find().pretty()

# Find specific session
db.workspaces.findOne({session_id: "session_abc123"})

# Count total sessions
db.workspaces.count()

# Exit
exit
```

#### **Using Docker Exec:**
```powershell
# Windows PowerShell
docker exec -it human_ai_mongodb mongosh --eval "use human_ai_cocreation; db.workspaces.find().pretty()"
```

---

### **Option 2: ArangoDB (For Graph Data)**

#### **Using ArangoDB Web UI:**
1. Open browser: http://localhost:8529
2. Username: `root`
3. Password: `password`
4. Database: `human_ai_cocreation`
5. Navigate to Collections → Graphs

#### **Using arangosh (CLI):**
```bash
# Connect to ArangoDB
docker exec -it human_ai_arangodb arangosh --server.username root --server.password password

# Switch to database
db._useDatabase("human_ai_cocreation")

# List collections
db._collections()

# Query nodes
db.nodes.toArray()

# Query edges
db.edges.toArray()

# Exit
quit
```

---

### **Option 3: JSON Files (Local Access)**

#### **Direct File Access:**
```powershell
# Windows PowerShell - Navigate to data directory
cd D:\Projects2.0\BTP_HumanAICoCreation\human-ai-co-create\data\sessions

# List all session files
ls

# View session content (pretty-print)
Get-Content session_abc123.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

#### **Python Script to Read:**
```python
import json
from pathlib import Path

# Read session data
session_id = "session_abc123"
file_path = Path(f"data/sessions/{session_id}.json")

with open(file_path, 'r') as f:
    data = json.load(f)
    
print(f"Session: {data['session_id']}")
print(f"Content: {data['topic_content'][:100]}...")
print(f"Characters: {list(data.get('characters', {}).keys())}")
```

---

## 💾 Docker Volume Locations

### **Windows:**
Docker Desktop stores volumes in WSL2:
```
\\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\

mongo_data\_data\         # MongoDB data files
arango_data\_data\        # ArangoDB data files
arango_apps\_data\        # ArangoDB apps
```

### **Linux/Mac:**
```
/var/lib/docker/volumes/

mongo_data/_data/         # MongoDB data files
arango_data/_data/        # ArangoDB data files
arango_apps/_data/        # ArangoDB apps
```

---

## 🔧 Database Management Commands

### **Start Databases:**
```powershell
# Start all services
docker-compose up -d

# Start only databases
docker-compose up -d mongodb arangodb
```

### **Stop Databases:**
```powershell
# Stop all
docker-compose down

# Keep data (volumes persist)
docker-compose down --volumes=false
```

### **Backup Data:**

#### **MongoDB Backup:**
```powershell
# Create backup
docker exec human_ai_mongodb mongodump --username root --password password --authenticationDatabase admin --out /tmp/backup

# Copy from container to host
docker cp human_ai_mongodb:/tmp/backup ./backup_mongodb
```

#### **ArangoDB Backup:**
```powershell
# Create dump
docker exec human_ai_arangodb arangodump --server.username root --server.password password --output-directory /tmp/backup

# Copy from container to host
docker cp human_ai_arangodb:/tmp/backup ./backup_arangodb
```

#### **JSON Backup:**
```powershell
# Simply copy the data folder
cp -r ./data/sessions ./backup_sessions_$(date +%Y%m%d)
```

### **Restore Data:**

#### **MongoDB Restore:**
```powershell
# Copy backup to container
docker cp ./backup_mongodb human_ai_mongodb:/tmp/backup

# Restore
docker exec human_ai_mongodb mongorestore --username root --password password --authenticationDatabase admin /tmp/backup
```

---

## 📈 Data Flow

```
User Input (Frontend)
       ↓
FastAPI Server (Backend)
       ↓
Session Manager
       ↓
┌──────────────┬──────────────┬──────────────┐
│   MongoDB    │   ArangoDB   │  JSON File   │
│   (Primary)  │   (Graph)    │  (Fallback)  │
│              │              │              │
│  Workspace   │   Nodes      │   Complete   │
│  Metadata    │   Edges      │   Snapshot   │
│  Characters  │   Relations  │              │
│  Events      │              │              │
└──────────────┴──────────────┴──────────────┘
       ↑
   Retrieve
       ↓
  API Response
       ↓
Frontend Display
```

---

## 🎯 Current Status Check

### **Check if Databases are Running:**
```powershell
# Check containers
docker ps

# Expected output:
# - human_ai_mongodb    (port 27017)
# - human_ai_arangodb   (port 8529)
```

### **Check MongoDB Connection:**
```powershell
docker exec -it human_ai_mongodb mongosh --eval "db.adminCommand('ping')"
# Expected: { ok: 1 }
```

### **Check ArangoDB Connection:**
```powershell
curl http://localhost:8529/_api/version
# Expected: JSON response with version info
```

### **Check Logs:**
```powershell
# MongoDB logs
docker logs human_ai_mongodb --tail 50

# ArangoDB logs
docker logs human_ai_arangodb --tail 50

# Server logs (shows which storage is being used)
docker logs human_ai_server --tail 50
# Look for: "✅ MongoDB connection established" or "📁 Using JSON fallback"
```

---

## 🐛 Troubleshooting

### **Issue: "Workspace loaded from JSON fallback"**
**Cause:** MongoDB not connected  
**Check:**
```powershell
docker ps | findstr mongodb
docker logs human_ai_mongodb --tail 20
```
**Fix:**
```powershell
docker-compose restart mongodb
```

### **Issue: Can't access MongoDB Compass**
**Cause:** Connection string wrong  
**Solution:** Use `mongodb://root:password@localhost:27017`

### **Issue: Data not persisting**
**Cause:** Volumes not mounted  
**Check:**
```powershell
docker volume ls | findstr "mongo\|arango"
```

### **Issue: Permission denied on volumes**
**Solution (Linux/Mac):**
```bash
sudo chown -R $(whoami):$(whoami) ./data
```

---

## 📝 Best Practices

1. **Regular Backups:** Run backup commands weekly
2. **Monitor Logs:** Check for "JSON fallback" warnings
3. **Volume Management:** Never delete volumes without backup
4. **Access Pattern:** Use MongoDB for 99% of queries, ArangoDB for complex graph queries
5. **JSON Files:** Keep as emergency backup, don't rely on for production

---

## 🚀 Production Considerations

### **Current Setup (Development):**
- MongoDB: Single instance, no replication
- ArangoDB: Single instance, no clustering
- Data: Docker volumes (suitable for dev)

### **For Production:**
- MongoDB: Replica set (3+ nodes)
- ArangoDB: Cluster mode (3+ coordinators)
- Volumes: External storage (AWS EBS, Azure Disks)
- Backups: Automated daily with retention policy
- Monitoring: Health checks, alerts, metrics

---

## 📚 Quick Reference

| Storage | GUI Access | CLI Access | Port | Default Creds |
|---------|-----------|------------|------|---------------|
| MongoDB | MongoDB Compass | mongosh | 27017 | root:password |
| ArangoDB | http://localhost:8529 | arangosh | 8529 | root:password |
| JSON | File Explorer | cat/type | N/A | N/A |

---

## ✅ Summary

**Your data is stored in 3 places:**
1. **MongoDB** - Primary (workspaces, characters, events)
2. **ArangoDB** - Graphs (nodes, edges, relationships)
3. **JSON Files** - Fallback (`./data/sessions/*.json`)

**To access:**
- MongoDB: Use Compass GUI or mongosh CLI
- ArangoDB: Use web UI at http://localhost:8529
- JSON: Direct file access in `./data/sessions/`

**Data persists:** Yes, in Docker volumes even after container restart

**Backup location:** Docker volumes + local JSON files

