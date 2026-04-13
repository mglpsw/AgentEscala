# Quick Start Guide

This guide will get you up and running with AgentEscala in under 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- Git

## Steps

### 1. Clone the Repository

```bash
git clone https://github.com/mglpsw/AgentEscala.git
cd AgentEscala
```

### 2. Start the Application

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database on port 5432
- FastAPI backend on port 8000

Wait for services to be healthy (about 10-20 seconds).

### 3. Seed Sample Data

```bash
docker-compose exec backend python -m backend.seed
```

This creates:
- 1 admin user
- 5 agent users
- 90 shifts (30 days × 3 shifts/day)
- 3 sample swap requests

### 4. Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **API Root**: http://localhost:8000

### 5. Try It Out

#### View All Shifts
```bash
curl http://localhost:8000/shifts
```

#### Export Shifts to Excel
```bash
curl http://localhost:8000/shifts/export/excel -o shifts.xlsx
```

#### Export Shifts to ICS
```bash
curl http://localhost:8000/shifts/export/ics -o shifts.ics
```

#### View Pending Swap Requests
```bash
curl http://localhost:8000/swaps/pending
```

#### Approve a Swap Request (as admin, user_id=1)
```bash
curl -X POST "http://localhost:8000/swaps/1/approve?admin_id=1" \
  -H "Content-Type: application/json" \
  -d '{"admin_notes": "Approved"}'
```

### 6. Explore the API

Open http://localhost:8000/docs in your browser to see the interactive API documentation powered by Swagger UI.

## Sample Credentials

After seeding, you'll have:

**Admin**:
- Email: admin@agentescala.com
- Name: Admin User

**Agents**:
- alice@agentescala.com (Alice Silva)
- bob@agentescala.com (Bob Santos)
- carol@agentescala.com (Carol Oliveira)
- david@agentescala.com (David Costa)
- eve@agentescala.com (Eve Martins)

## Common Commands

### View Logs
```bash
docker-compose logs -f backend
```

### Stop Application
```bash
docker-compose down
```

### Restart Application
```bash
docker-compose restart backend
```

### Reset Database
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec backend python -m backend.seed
```

### Access Database Directly
```bash
docker-compose exec db psql -U agentescala -d agentescala
```

## Troubleshooting

### Backend won't start
Check if the database is healthy:
```bash
docker-compose ps
```

### Database connection errors
Ensure the database container is running:
```bash
docker-compose up -d db
```

### Port already in use
If port 8000 or 5432 is already in use, edit `docker-compose.yml` to use different ports.

## Next Steps

- Read [README.md](README.md) for full feature documentation
- Check [PROJECT_STATUS.md](PROJECT_STATUS.md) for current status
- See [docs/architecture.md](docs/architecture.md) for technical details
- Review [docs/homelab_deploy.md](docs/homelab_deploy.md) for production deployment
