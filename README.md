# Human-AI Co-Creation Platform

A sophisticated platform for collaborative content creation between humans and AI, featuring dynamic prompt modes, knowledge graph visualization, and comprehensive authentication.

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 16+**
- **MongoDB 5.0+** (or Docker)
- **Git**

### Local Development

#### Option 1: Quick Start Script

**Linux/macOS:**
```bash
chmod +x run_local.sh
./run_local.sh
```

**Windows (PowerShell):**
```powershell
.\run_local.ps1
```

#### Option 2: Manual Setup

1. **Clone and Setup**
```bash
git clone <repository-url>
cd human-ai-co-create
cp .env.example .env
```

2. **Backend Setup**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

3. **Frontend Setup**
```bash
cd web
npm install
cd ..
```

4. **Start Services**
```bash
# Terminal 1: Start MongoDB (if not using Docker)
mongod

# Terminal 2: Start Backend
cd server
python -m uvicorn main:app --reload

# Terminal 3: Start Frontend
cd web
npm start
```

### Docker Development

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up

# Start with logs
docker-compose -f docker-compose.dev.yml up --build

# Stop services
docker-compose -f docker-compose.dev.yml down
```

## 🏗️ Architecture

### Backend (FastAPI)
- **Authentication**: Google OAuth 2.0 with JWT tokens
- **Database**: MongoDB with motor (async)
- **Rate Limiting**: slowapi integration
- **Security**: CORS, secure cookies, input validation

### Frontend (React + Tailwind)
- **Authentication Flow**: OAuth integration with protected routes
- **UI Components**: Modern dark theme with accessibility
- **State Management**: React hooks with localStorage persistence
- **Responsive Design**: Mobile-first approach

### Key Features
- 🔐 **Secure Authentication**: Google OAuth with rate limiting
- 📝 **Dynamic Content Creation**: Multi-mode AI assistance
- 🌐 **Knowledge Graph**: Interactive relationship visualization
- 🎨 **Modern UI**: Dark theme with Tailwind CSS
- 🧪 **Comprehensive Testing**: Backend (pytest) + Frontend (Jest)
- 🔄 **CI/CD Pipeline**: GitHub Actions with security scanning

2. **Set up environment**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Set LLM provider API keys and database preferences
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install NLP models**
```bash
# For spaCy (recommended)
python -m spacy download en_core_web_sm

# For stanza (alternative)
python -c "import stanza; stanza.download('en')"
```

### Running the Application

#### Option 1: Direct Python
```bash
python run.py
```

#### Option 2: Docker Compose
```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## Configuration

The system uses environment variables for configuration. Key settings include:

### LLM Provider Configuration
```env
# Primary LLM provider
LLM_PROVIDER=google  # google, groq, huggingface, openai

# API Keys (set only what you need)
GOOGLE_API_KEY=your_google_api_key
GROQ_API_KEY=your_groq_api_key
HUGGINGFACE_API_KEY=your_hf_api_key
OPENAI_API_KEY=your_openai_api_key

# Provider preferences (fallback order)
LLM_PROVIDERS=google,groq,openai,huggingface
```

### Database Configuration
```env
# Database mode
DATABASE_MODE=json  # arangodb, mongodb, json

# Database URLs (for ArangoDB/MongoDB)
ARANGODB_URL=http://localhost:8529
MONGODB_URL=mongodb://localhost:27017
```

### Server Configuration
```env
# Server settings
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=true

# Data directory (for JSON fallback)
DATA_DIR=./data
```

## API Usage

### Create a Session
```bash
curl -X POST "http://localhost:8000/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "A mystery story",
    "mode": "story",
    "user_preferences": {"style": "suspenseful"}
  }'
```

### Generate Content
```bash
curl -X POST "http://localhost:8000/api/v1/sessions/{session_id}/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "The detective entered the room...",
    "num_projections": 3
  }'
```

### Run Complete Workflow
```bash
curl -X POST "http://localhost:8000/api/v1/sessions/{session_id}/workflow" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Continue the story with a plot twist"
  }'
```

## Architecture

### Core Components

1. **Session Manager**: Orchestrates workspace management and prompt generation
2. **Perception Agent**: Analyzes content using multiple NLP approaches
3. **Planner Agent**: Generates content projections with branching narratives
4. **Graph Manager**: Maintains knowledge graphs with importance scoring
5. **Verifier Agent**: Checks consistency, grammar, and factual accuracy

### Database Architecture

- **Primary Storage**: ArangoDB (graph database) or MongoDB (document database)
- **Caching**: Redis for session and embedding caches
- **Fallback**: JSON file storage for development and lightweight deployments

### LLM Integration

The system supports multiple LLM providers with intelligent fallback:

1. **Google Gemini**: Primary recommendation for balanced performance
2. **Groq**: Fast inference with good quality
3. **OpenAI**: High quality with API rate considerations
4. **HuggingFace**: Open source models with local inference option

## Development

### Project Structure
```
human-ai-co-create/
├── server/
│   ├── agents/           # AI agent implementations
│   ├── api/             # REST API routes
│   ├── database/        # Database clients
│   ├── utils/           # Utilities and schemas
│   ├── llm_provider.py  # LLM integration
│   ├── server_config.py # Configuration management
│   └── main.py          # FastAPI application
├── docker-compose.yml   # Container orchestration
├── Dockerfile          # Container definition
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Project configuration
└── run.py             # Application entry point
```

### Adding New Agents

1. Create agent class in `server/agents/`
2. Implement `invoke()` method with proper error handling
3. Add factory function to `agents/__init__.py`
4. Register with `AgentOrchestrator`

### Adding New LLM Providers

1. Extend `AsyncLLMProvider` class in `llm_provider.py`
2. Add provider-specific configuration to `ServerConfig`
3. Update fallback chain in provider preferences

### Adding New Database Backends

1. Create client class in `server/database/`
2. Implement async methods matching the interface
3. Add configuration options to `ServerConfig`
4. Update initialization logic in `main.py`

## Testing

```bash
# Run unit tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=server

# Test specific component
python -m pytest tests/test_agents.py -v
```

## Deployment

### Production Docker
```bash
# Build production image
docker build -t human-ai-co-create:prod .

# Run with production configuration
docker run -d \
  --name co-creation-api \
  -p 8000:8000 \
  --env-file .env.prod \
  human-ai-co-create:prod
```

### Environment-Specific Configuration

Create environment-specific configuration files:
- `.env.development`
- `.env.staging`
- `.env.production`

## Troubleshooting

### Common Issues

1. **Import Errors**: Install missing dependencies with `pip install -r requirements.txt`
2. **NLP Model Errors**: Download required models (see Installation section)
3. **Database Connection Issues**: Check database URLs and credentials in `.env`
4. **LLM API Errors**: Verify API keys and rate limits

### Fallback Behavior

The system is designed with comprehensive fallbacks:
- **Missing Dependencies**: Graceful degradation with pattern-based alternatives
- **Database Failures**: Automatic fallback to JSON storage
- **LLM Failures**: Intelligent provider switching based on preferences
- **NLP Failures**: Pattern-based text analysis when libraries unavailable

### Logging

Logs are available at multiple levels:
- **INFO**: General application flow
- **WARNING**: Fallback activations and recoverable issues
- **ERROR**: Failed operations and exceptions
- **DEBUG**: Detailed agent interactions and processing steps

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with comprehensive tests
4. Update documentation as needed
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support:
- Check the documentation in `/docs`
- Review the API documentation at `/docs` when server is running
- File issues in the project repository
- Check logs for detailed error information
