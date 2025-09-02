# Human-AI Co-Creation System - Application Structure

## File Cleanup Summary

### Removed Files (Redundant)
- `server/main.py` → Backup saved as `main.py.backup`
- `server/app_simple.py` → Backup saved as `app_simple.py.backup`

These files served similar purposes to `app.py` and created maintenance overhead.

### Current Application Structure

#### Primary Application Files

1. **`run.py`** - Main entry point
   - Purpose: Application startup and uvicorn server configuration
   - Imports: Uses `server.app:app` for uvicorn
   - Usage: `python run.py` to start the server

2. **`server/app.py`** - Core FastAPI application
   - Purpose: Complete FastAPI app with full agent orchestration
   - Features: All session endpoints, agent pipeline, lifespan management
   - Status: **MAIN APPLICATION FILE**

3. **`server/server_config.py`** - Configuration management
   - Purpose: Pydantic-based configuration with environment variables
   - Features: Multi-provider LLM config, OAuth, database settings

4. **`server/workspace.py`** - Workspace (Blackboard) system
   - Purpose: Session state management with MongoDB/JSON fallback
   - Features: Checkpointing, snapshots, delta operations

5. **`server/llm_provider.py`** - LLM provider system
   - Purpose: Multi-provider LLM support with robust fallbacks
   - Providers: Google Gemini, Groq, OpenRouter, OpenAI, HuggingFace, Local

#### Supporting Files

6. **`server/__init__.py`** - Package initialization
   - Exports: ServerConfig and app

7. **`server/api/`** - API routes and endpoints
   - `health.py` - Health check endpoints
   - `routes.py` - Main API routes (v1)
   - `__init__.py` - Router exports

8. **`server/agents/`** - Agent implementation
   - Individual agent files for the 6-agent system

9. **`server/utils/`** - Utility functions
   - `schemas.py` - Pydantic schemas
   - `logging_cfg.py` - Logging configuration
   - `chunker.py` - Text processing utilities
   - Note: `embeddings.py` imports commented out to avoid heavy dependencies

## Rationale for Cleanup

### Why Remove `main.py` and `app_simple.py`?

1. **Redundancy**: All three files (`app.py`, `main.py`, `app_simple.py`) served as FastAPI entry points
2. **Import Issues**: `main.py` had relative import problems and missing dependencies
3. **Maintenance Burden**: Multiple similar files created confusion about which to use
4. **Feature Completeness**: `app.py` was the most complete with proper agent orchestration

### Why Keep `app.py`?

1. **Most Complete**: Full agent pipeline implementation
2. **Proper Structure**: Well-organized lifespan management and error handling
3. **Best Practices**: Comprehensive endpoint implementation
4. **Working Imports**: Uses relative imports correctly within package structure

## Current Working Structure

```
Human-AI Co-Creation System
├── run.py                    # Entry point → uvicorn server.app:app
├── server/
│   ├── app.py               # Main FastAPI application ⭐
│   ├── server_config.py     # Configuration management
│   ├── workspace.py         # Workspace/Blackboard system
│   ├── llm_provider.py      # Multi-LLM provider system
│   ├── api/                 # API endpoints
│   ├── agents/              # 6-agent system
│   └── utils/               # Utilities and schemas
├── web/                     # Frontend (React)
└── data/                    # Data storage
```

## Configuration Status

✅ **Environment**: All LLM providers configured  
✅ **OAuth**: Google OAuth properly configured  
✅ **Database**: MongoDB + JSON fallback working  
✅ **Imports**: Heavy dependencies (sentence-transformers) lazy-loaded  
✅ **Entry Point**: `run.py` → `uvicorn server.app:app`  

## Usage

Start the development server:
```bash
cd human-ai-co-create
python run.py
```

This will start uvicorn with:
- Host: 0.0.0.0
- Port: 8000
- Reload: True
- App: server.app:app

## Notes

- **No `workflow.py`**: This file was mentioned but doesn't exist in the codebase
- **Backup Files**: Original `main.py` and `app_simple.py` are preserved as `.backup` files
- **Import Strategy**: Relative imports used within server package, absolute imports from outside
- **Heavy Dependencies**: Embeddings and transformers are lazy-loaded to improve startup time

The system now has a single, clear entry point and application structure without redundant files.
