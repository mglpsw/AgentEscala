# AgentEscala Architecture

## Overview

AgentEscala is a shift management and swap system built with a modern, scalable architecture. This document describes the technical architecture and design decisions.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                         │
│  (Future: Web UI, Mobile App, Telegram Bot)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP/REST
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Users   │  │  Shifts  │  │  Swaps   │                  │
│  │  Router  │  │  Router  │  │  Router  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
        │             │             │
┌───────┴─────────────┴─────────────┴────────────────────────┐
│                   Service Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  User    │  │  Shift   │  │  Swap    │                  │
│  │ Service  │  │ Service  │  │ Service  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
        │             │             │
┌───────┴─────────────┴─────────────┴────────────────────────┐
│                   Data Layer (SQLAlchemy)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │   User   │  │  Shift   │  │  Swap    │                  │
│  │  Model   │  │  Model   │  │ Request  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
        └─────────────┴─────────────┘
                      │
              ┌───────┴────────┐
              │   PostgreSQL   │
              └────────────────┘
```

## Layer Descriptions

### API Layer
- **Technology**: FastAPI
- **Responsibility**: HTTP request/response handling, validation, routing
- **Components**:
  - Routers (users, shifts, swaps)
  - Pydantic schemas for validation
  - Dependency injection for database sessions
  - Exception handling and error responses

### Service Layer
- **Technology**: Python classes
- **Responsibility**: Business logic, transaction management, validation
- **Components**:
  - UserService: User management operations
  - ShiftService: Shift CRUD and queries
  - SwapService: Swap workflow and approval logic
- **Why separate**: Reusable across different interfaces, testable in isolation

### Data Layer
- **Technology**: SQLAlchemy ORM
- **Responsibility**: Database interaction, relationships, constraints
- **Components**:
  - User model (users table)
  - Shift model (shifts table)
  - SwapRequest model (swap_requests table)

### Database
- **Technology**: PostgreSQL 15
- **Why PostgreSQL**: ACID compliance, robust, excellent for relational data

## Data Model

### Entity-Relationship Diagram

```
┌────────────────┐
│     User       │
├────────────────┤
│ id (PK)        │
│ email          │
│ name           │
│ role           │◄───────┐
│ is_active      │        │
│ created_at     │        │
│ updated_at     │        │
└────────┬───────┘        │
         │                │
         │ 1:N            │ N:1
         │                │
         ▼                │
┌────────────────┐        │
│     Shift      │        │
├────────────────┤        │
│ id (PK)        │        │
│ agent_id (FK)  │────────┘
│ start_time     │
│ end_time       │        ┌────────────┐
│ title          │        │ SwapRequest│
│ description    │◄───┐   ├────────────┤
│ location       │    │   │ id (PK)    │
│ created_at     │    │   │ requester_id (FK) ───┐
│ updated_at     │    │   │ target_agent_id (FK) ─┼──► User
└────────────────┘    │   │ origin_shift_id (FK) ─┤
                      ├───┤ target_shift_id (FK) ─┘
                      │   │ status     │
                      │   │ reason     │
                      │   │ admin_notes│
                      │   │ reviewed_by│
                      │   │ created_at │
                      │   │ updated_at │
                      │   └────────────┘
                      │
                      └─────────────────────┐
                                            │
                                            ▼
                              (origin_shift & target_shift)
```

### User Entity
- **Purpose**: Represents agents and admins
- **Key Fields**:
  - `role`: ADMIN or AGENT (enum)
  - `is_active`: Soft delete flag
- **Relationships**:
  - Has many Shifts (as agent)
  - Has many SwapRequests (as requester or target)

### Shift Entity
- **Purpose**: Represents work shifts
- **Key Fields**:
  - `start_time`, `end_time`: Shift schedule
  - `agent_id`: Assigned agent
- **Relationships**:
  - Belongs to User (agent)
  - Referenced by SwapRequests

### SwapRequest Entity
- **Purpose**: Manages shift swap workflow
- **Key Fields**:
  - `status`: PENDING, APPROVED, REJECTED, CANCELLED
  - `reviewed_by`: Admin who reviewed
- **Relationships**:
  - Belongs to User (requester)
  - Belongs to User (target_agent)
  - References two Shifts (origin and target)

## API Design

### RESTful Principles
- Resource-based URLs (`/users`, `/shifts`, `/swaps`)
- HTTP methods for operations (GET, POST, PATCH, DELETE)
- Proper status codes (201 Created, 404 Not Found, etc.)
- JSON request/response bodies

### Authentication (Future)
Currently, user_id/admin_id are passed as query parameters.

**Future Implementation**:
```
Authorization: Bearer <JWT_TOKEN>
```

JWT claims will include:
- user_id
- role
- email

### Example Request Flow

**Creating a Swap Request**:
```
Client → POST /swaps → API Router → SwapService → Database
                                         ↓
                                    Validation:
                                    - Shifts exist?
                                    - Correct owners?
                                         ↓
                                    Create record
                                         ↓
                                    Return 201
```

**Approving a Swap**:
```
Admin → POST /swaps/1/approve → SwapService → Database
                                      ↓
                                 Validation:
                                 - Is admin?
                                 - Is pending?
                                      ↓
                                 Begin Transaction:
                                 - Swap agent_ids
                                 - Update status
                                 - Set reviewer
                                      ↓
                                 Commit
                                      ↓
                                 Return 200
```

## Export Architecture

### Excel Exporter
```
Shifts → ExcelExporter → openpyxl → BytesIO → StreamingResponse
                 ↓
          - Format headers
          - Calculate durations
          - Add metadata sheet
          - Professional styling
```

### ICS Exporter
```
Shifts → ICSExporter → icalendar → BytesIO → StreamingResponse
              ↓
       - Create calendar
       - Add events
       - Include agent info
       - Standard format (RFC 5545)
```

## Deployment Architecture

### Local Development
```
Docker Compose
  ├── PostgreSQL Container (port 5432)
  └── Backend Container (port 8000)
       └── Volume mount for hot reload
```

### Homelab Production
```
Docker Network: traefik-public
  │
  ├── Traefik (reverse proxy, SSL termination)
  │     │
  │     └── Routes to Backend
  │
Docker Network: agentescala_internal
  │
  ├── Backend Container
  │     └── Connects to Database
  │
  └── PostgreSQL Container
        └── Isolated from external access
```

## Scalability Considerations

### Current Design
- Stateless API (easy to scale horizontally)
- Database connection pooling
- In-memory export generation (no shared filesystem)

### Future Optimizations
- **Caching**: Redis for frequently accessed data
- **Job Queue**: Celery for long-running exports
- **Read Replicas**: PostgreSQL replicas for read-heavy loads
- **CDN**: For static assets (frontend)

## Security Architecture

### Current (MVP)
- PostgreSQL connection over internal network
- No public database access
- Input validation via Pydantic
- CORS configured (adjust for production)

### Future
- **Authentication**: JWT with refresh tokens
- **Authorization**: Role-based access control
- **Rate Limiting**: Prevent abuse
- **Encryption**: Encrypt sensitive data at rest
- **Audit Logging**: Track all sensitive operations

## Monitoring and Observability (Future)

### Planned Integration
- **Metrics**: Prometheus
  - Request rate, latency
  - Database query performance
  - Export generation time
- **Logging**: Structured JSON logs
  - Request/response logging
  - Error tracking
  - Audit trail
- **Tracing**: OpenTelemetry (if needed)
- **Alerts**: Based on error rate, response time

## Performance Characteristics

### Expected Performance
- API Response Time: < 100ms (CRUD operations)
- Excel Export: < 2s (for 1000 shifts)
- ICS Export: < 1s (for 1000 shifts)
- Database Queries: < 50ms (simple), < 200ms (complex joins)

### Bottlenecks to Watch
- Large exports (thousands of shifts)
- Complex queries with many joins
- High concurrent swap approvals (database locks)

## Technology Choices Summary

| Component | Technology | Why |
|-----------|-----------|-----|
| API Framework | FastAPI | Fast, modern, automatic docs, type hints |
| Language | Python 3.11 | Easy to develop, great ecosystem, fast enough |
| Database | PostgreSQL 15 | Reliable, ACID, great for relational data |
| ORM | SQLAlchemy | Mature, powerful, standard for Python |
| Validation | Pydantic | Type-safe, automatic validation, works with FastAPI |
| Excel | openpyxl | Mature, full-featured, good formatting support |
| ICS | icalendar | Standard RFC 5545 implementation |
| Container | Docker | Standard, portable, easy deployment |
| Orchestration | Docker Compose | Simple, good for single-host deployment |
| Reverse Proxy | Traefik | Dynamic config, Let's Encrypt, homelab standard |

## Design Patterns Used

- **Layered Architecture**: API → Service → Data
- **Repository Pattern**: Services abstract database access
- **Dependency Injection**: Database sessions via FastAPI Depends
- **DTO Pattern**: Pydantic schemas separate from models
- **Factory Pattern**: Database session factory
- **Strategy Pattern**: Different exporters (Excel, ICS)

## Testing Strategy (Future)

```
Unit Tests (70%)
  └── Services, utilities, business logic

Integration Tests (20%)
  └── API endpoints with test database

End-to-End Tests (10%)
  └── Full workflows (create shift, swap, approve)
```

## Conclusion

AgentEscala follows modern architectural principles:
- Separation of concerns
- Single responsibility
- Dependency injection
- Stateless design
- RESTful API
- Clean code practices

The architecture is designed to be:
- **Maintainable**: Clear structure, documented
- **Testable**: Layered, dependency injection
- **Scalable**: Stateless, horizontal scaling ready
- **Secure**: Network isolation, validation
- **Observable**: Logging, health checks (future: metrics)
