# Validation Checklist for AgentEscala MVP

This checklist can be used to validate the complete MVP implementation.

## Prerequisites Validation

- [ ] Docker installed (`docker --version`)
- [ ] Docker Compose installed (`docker-compose --version`)
- [ ] Git repository cloned
- [ ] Located in project root directory

## Local Development Validation

### 1. Start the Application

```bash
cd /path/to/AgentEscala
docker-compose up -d
```

**Expected:**
- PostgreSQL container starts
- Backend container starts after DB is healthy
- No error messages

**Validation:**
```bash
docker-compose ps
# Both containers should be "Up" and healthy
```

### 2. Check Logs

```bash
docker-compose logs backend
```

**Expected:**
- No error messages
- "Application startup complete" message
- Uvicorn running on port 8000

### 3. Health Check

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-13T...",
  "version": "1.0.0"
}
```

### 4. API Documentation

Open in browser: http://localhost:8000/docs

**Expected:**
- Swagger UI loads
- Three API sections visible: users, shifts, swaps
- All endpoints listed with documentation

### 5. Database Seeding

```bash
docker-compose exec backend python -m backend.seed
```

**Expected Output:**
- "Initializing database..."
- "Creating users..."
- "Creating shifts..."
- "Creating sample swap requests..."
- "Seed Complete"
- No errors

**Validation:**
```bash
curl http://localhost:8000/users
```

**Expected:** JSON array with 6 users (1 admin + 5 agents)

### 6. Basic API Operations

**List Shifts:**
```bash
curl http://localhost:8000/shifts | jq '.[:2]'
```

**Expected:** JSON array with shift objects

**Get Single Shift:**
```bash
curl http://localhost:8000/shifts/1
```

**Expected:** Single shift object with agent information

**List Pending Swaps:**
```bash
curl http://localhost:8000/swaps/pending
```

**Expected:** JSON array with pending swap requests

### 7. Excel Export

```bash
curl http://localhost:8000/shifts/export/excel -o test_shifts.xlsx
```

**Expected:**
- File created: `test_shifts.xlsx`
- File size > 0 bytes
- Can be opened in Excel/LibreOffice

**Validation:**
```bash
ls -lh test_shifts.xlsx
# Should show file with size ~5-15KB
```

### 8. ICS Export

```bash
curl http://localhost:8000/shifts/export/ics -o test_shifts.ics
```

**Expected:**
- File created: `test_shifts.ics`
- File size > 0 bytes
- Valid iCalendar format

**Validation:**
```bash
head -5 test_shifts.ics
# Should start with "BEGIN:VCALENDAR"
```

### 9. Swap Approval Workflow

**Create a Swap Request:**
```bash
curl -X POST "http://localhost:8000/swaps?requester_id=2" \
  -H "Content-Type: application/json" \
  -d '{
    "target_agent_id": 3,
    "origin_shift_id": 1,
    "target_shift_id": 2,
    "reason": "Test swap request"
  }'
```

**Expected:** JSON response with swap request (status: "pending")

**Approve the Swap (as admin):**
```bash
curl -X POST "http://localhost:8000/swaps/4/approve?admin_id=1" \
  -H "Content-Type: application/json" \
  -d '{"admin_notes": "Approved for testing"}'
```

**Expected:**
- Status changed to "approved"
- `reviewed_by` set to 1
- Shifts have swapped agents

**Verify Swap Execution:**
```bash
# Check that shifts 1 and 2 have swapped agents
curl http://localhost:8000/shifts/1
curl http://localhost:8000/shifts/2
```

### 10. Validation Script

```bash
docker-compose exec backend python -m backend.validate
```

**Expected Output:**
- "=== AgentEscala MVP Validation ==="
- All checks show "✓"
- "MVP is functional and ready to use!"
- Exit code 0

## Homelab Deployment Validation

### 1. Prerequisites Check

```bash
# Check Traefik network
docker network inspect traefik-public

# Expected: Network exists with external: true
```

### 2. Configuration

```bash
cd infra
cp .env.homelab.example .env.homelab
nano .env.homelab
```

**Required edits:**
- [ ] POSTGRES_PASSWORD changed
- [ ] SECRET_KEY generated and set
- [ ] ADMIN_EMAIL set
- [ ] DOMAIN set to your domain
- [ ] TRAEFIK_NETWORK matches your setup

### 3. Deploy

```bash
./infra/scripts/couple_to_homelab.sh --build
```

**Expected:**
- Script validates configuration
- Image builds successfully
- Containers start
- "Deployment Complete" message

### 4. Verify Deployment

```bash
docker-compose -f infra/docker-compose.homelab.yml ps
```

**Expected:**
- Both containers "Up"
- Backend has "healthy" status

### 5. Access via Domain

```bash
curl https://agentescala.yourdomain.com/health
```

**Expected:**
- HTTPS connection successful (SSL certificate valid)
- JSON response with "healthy" status

### 6. Check Traefik Dashboard

Open: https://traefik.yourdomain.com/dashboard/

**Expected:**
- AgentEscala router visible
- Green (healthy) status
- Correct domain and entrypoint

## Code Quality Validation

### 1. Python Syntax

```bash
find backend -name "*.py" -exec python3 -m py_compile {} \;
```

**Expected:** No syntax errors

### 2. File Structure

```bash
tree -L 2 -I '__pycache__|*.pyc|.git'
```

**Expected Structure:**
```
.
├── backend/
│   ├── api/
│   ├── config/
│   ├── models/
│   ├── services/
│   ├── utils/
│   └── main.py
├── docs/
├── infra/
├── docker-compose.yml
└── Dockerfile
```

### 3. Documentation Exists

- [ ] README.md exists and is comprehensive
- [ ] QUICKSTART.md exists with step-by-step guide
- [ ] PROJECT_STATUS.md exists with current status
- [ ] IMPLEMENTATION_SUMMARY.md exists with code details
- [ ] docs/architecture.md exists
- [ ] docs/assumptions.md exists
- [ ] docs/homelab_deploy.md exists

## Functional Requirements Validation

- [x] **Backend functional**: FastAPI running with all endpoints
- [x] **Database**: PostgreSQL with proper models and relationships
- [x] **User Management**: CRUD operations work
- [x] **Shift Management**: CRUD operations work
- [x] **Swap Workflow**: Create, approve, reject, cancel work
- [x] **Excel Export**: Generates valid professional Excel files
- [x] **ICS Export**: Generates valid iCalendar files
- [x] **Admin Approval**: Swap requires admin approval
- [x] **Swap Execution**: Shifts swap on approval
- [x] **Health Check**: Endpoint responds correctly
- [x] **Docker Local**: One-command startup works
- [x] **Docker Homelab**: Deployment script works
- [x] **Documentation**: Comprehensive and current
- [x] **Seed Data**: Sample data creation works
- [x] **Validation**: Validation script passes

## Non-Functional Requirements Validation

- [x] **Clean Code**: Three-layer architecture implemented
- [x] **Separation of Concerns**: API, Services, Models separated
- [x] **Type Safety**: Pydantic models for validation
- [x] **Error Handling**: HTTPException with proper codes
- [x] **Documentation**: Auto-generated API docs available
- [x] **Logging**: Uvicorn logs all requests
- [x] **Security**: Database on isolated network
- [x] **SSL/TLS**: Traefik labels configured
- [x] **Health Checks**: Database and backend health checks
- [x] **Restart Policy**: Auto-restart configured

## Known Limitations (Expected)

- [ ] No authentication (expected - future work)
- [ ] No frontend (expected - future work)
- [ ] No tests (expected - future work)
- [ ] No email notifications (expected - future work)
- [ ] Single timezone (UTC) (expected - future work)

## Issue Tracking

If any validation fails:

1. Note which step failed
2. Check logs: `docker-compose logs`
3. Verify configuration: `.env` files
4. Check GitHub issues: https://github.com/mglpsw/AgentEscala/issues
5. Review documentation in `/docs`

## Success Criteria

✅ **MVP is complete when:**
- All "Local Development Validation" steps pass
- All "Functional Requirements" are validated
- Documentation is comprehensive and current
- Code is clean and follows architecture
- Can be deployed to homelab successfully

## Final Validation Command

Run all validations in sequence:

```bash
# Start local
docker-compose up -d

# Wait for startup
sleep 10

# Seed
docker-compose exec backend python -m backend.seed

# Validate
docker-compose exec backend python -m backend.validate

# Test API
curl http://localhost:8000/health
curl http://localhost:8000/users
curl http://localhost:8000/shifts

# Test exports
curl http://localhost:8000/shifts/export/excel -o test.xlsx
curl http://localhost:8000/shifts/export/ics -o test.ics

# Verify files created
ls -lh test.xlsx test.ics

# Check documentation
ls -1 *.md docs/*.md
```

**If all pass:** ✅ MVP is complete and functional!
