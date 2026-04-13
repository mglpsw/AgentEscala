# AgentEscala Backend

This is the backend service for AgentEscala shift management system.

## Structure

- `main.py` - FastAPI application entry point
- `config/` - Configuration and database setup
- `models/` - SQLAlchemy database models
- `services/` - Business logic layer
- `api/` - REST API endpoints
- `utils/` - Utility functions (Excel, ICS exporters)

## Running

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
