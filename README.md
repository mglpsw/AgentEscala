# AgentEscala

**AgentEscala** is a professional shift management and swap system designed for teams that need to efficiently manage work schedules and handle shift exchange requests.

## Features

- **Shift Management**: Create, update, and manage work shifts for agents
- **Swap Workflow**: Request and manage shift swaps with mandatory admin approval
- **Excel Export**: Professional Excel export with formatting and metadata
- **ICS Export**: Simple iCalendar export for calendar integration
- **REST API**: Complete RESTful API built with FastAPI
- **Role-Based Access**: Admin and Agent roles (JWT login available; enforcement planned)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/mglpsw/AgentEscala.git
cd AgentEscala
```

2. Start the application:
```bash
docker-compose up -d
```

This will apply database migrations automatically before starting the API.

3. Seed the database with sample data (password for all sample users: `password123`):
```bash
docker-compose exec backend python -m backend.seed
```

4. Access the application:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Architecture

AgentEscala is built with:

- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy
- **Export**: openpyxl (Excel), icalendar (ICS)

### Project Structure

```
AgentEscala/
├── backend/
│   ├── api/           # REST API endpoints
│   ├── config/        # Configuration and database
│   ├── models/        # SQLAlchemy models
│   ├── services/      # Business logic
│   ├── utils/         # Exporters and utilities
│   ├── main.py        # FastAPI application
│   └── seed.py        # Database seeding
├── docs/              # Documentation
├── infra/             # Homelab deployment
│   ├── scripts/       # Deployment scripts
│   └── docker-compose.homelab.yml
├── tests/             # Tests (future)
├── docker-compose.yml # Local development
└── Dockerfile         # Container image
```

## Core Functionality

### Shift Management

- Create shifts with start/end times, titles, descriptions, and locations
- Assign shifts to specific agents
- Update and delete shifts
- Query shifts by agent or date range
- Export shifts to Excel or ICS formats

### Swap Workflow

1. **Request**: Agent initiates swap request specifying origin and target shifts
2. **Pending**: Request awaits admin review
3. **Admin Review**: Admin approves or rejects with notes
4. **Execution**: Upon approval, shifts are automatically swapped
5. **Status Tracking**: All requests tracked with full history

### Export Capabilities

**Excel Export**:
- Professional formatting with headers
- Agent information included
- Duration calculations
- Metadata sheet
- Available for both shifts and swap requests

**ICS Export**:
- Standard iCalendar format
- Single or bulk export
- Compatible with Google Calendar, Outlook, etc.
- Includes agent information in descriptions

## API Endpoints

### Users
- `POST /users` - Create user
- `GET /users` - List all users
- `GET /users/agents` - List agents
- `GET /users/admins` - List admins
- `GET /users/{id}` - Get user details

### Shifts
- `POST /shifts` - Create shift
- `GET /shifts` - List all shifts
- `GET /shifts/agent/{id}` - List agent's shifts
- `GET /shifts/{id}` - Get shift details
- `PATCH /shifts/{id}` - Update shift
- `DELETE /shifts/{id}` - Delete shift
- `GET /shifts/export/excel` - Export to Excel
- `GET /shifts/export/ics` - Export to ICS

### Swaps
- `POST /swaps` - Create swap request
- `GET /swaps` - List all swaps
- `GET /swaps/pending` - List pending swaps
- `GET /swaps/agent/{id}` - List agent's swaps
- `GET /swaps/{id}` - Get swap details
- `POST /swaps/{id}/approve` - Approve swap (admin)
- `POST /swaps/{id}/reject` - Reject swap (admin)
- `POST /swaps/{id}/cancel` - Cancel swap (requester)
- `GET /swaps/export/excel` - Export to Excel

## Deployment

### Local Development
```bash
docker-compose up -d
```

### Homelab Deployment

1. Copy and configure environment:
```bash
cp infra/.env.homelab.example infra/.env.homelab
# Edit infra/.env.homelab with your settings
```

2. Run deployment script:
```bash
./infra/scripts/couple_to_homelab.sh
```

See [docs/homelab_deploy.md](docs/homelab_deploy.md) for detailed deployment instructions.

## Development

### Running without Docker
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/agentescala"

# Run the application
uvicorn backend.main:app --reload
```

### Database Migrations

Alembic migrations run automatically when the container starts (see docker-compose commands). You can also run them manually:

```bash
cd backend
alembic upgrade head
```

## Status

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for current implementation status and roadmap.

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Current status and roadmap
- [docs/architecture.md](docs/architecture.md) - Architecture details
- [docs/homelab_deploy.md](docs/homelab_deploy.md) - Homelab deployment guide
- [docs/assumptions.md](docs/assumptions.md) - Technical decisions and assumptions

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
