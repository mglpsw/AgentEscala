# Technical Assumptions and Decisions

**Last Updated**: 2026-04-13

This document records technical decisions made during the MVP implementation of AgentEscala.

## General Assumptions

### 1. Repository Organization
**Decision**: AgentEscala is a standalone product repository, separate from homelab infrastructure.

**Rationale**:
- Clean separation of concerns
- AgentEscala can be deployed anywhere, not just homelab
- Easier to version and maintain
- Better for collaboration and open source

### 2. MVP Scope
**Decision**: Focus on core backend functionality before frontend or bots.

**Rationale**:
- Backend provides the foundation for all interfaces
- API can be consumed by multiple frontends (web, mobile, Telegram)
- Easier to validate core business logic
- Faster time to functional MVP

### 3. Technology Stack
**Decision**: Python + FastAPI + PostgreSQL + SQLAlchemy

**Rationale**:
- FastAPI: Modern, fast, automatic API documentation, type hints
- PostgreSQL: Robust, reliable, good for relational data
- SQLAlchemy: Mature ORM, good for complex queries
- Python 3.11: Latest stable version with performance improvements

## Database Decisions

### 1. Schema Design
**Decision**: Three main entities (User, Shift, SwapRequest) with clear relationships.

**Rationale**:
- Simple enough for MVP
- Extensible for future features
- Normalized to avoid data duplication
- Foreign keys ensure referential integrity

### 2. Enum Types
**Decision**: Use SQLAlchemy Enum types for UserRole and SwapStatus.

**Rationale**:
- Type safety at database level
- Clear valid values
- Easy to extend
- Good for queries and filtering

### 3. Timestamps
**Decision**: Include created_at and updated_at on all entities.

**Rationale**:
- Essential for debugging
- Useful for auditing
- Supports future features (e.g., "recently updated")
- Minimal cost

### 4. Soft Deletes
**Decision**: Use is_active flag for users instead of hard deletes.

**Rationale**:
- Preserve historical data
- Maintain referential integrity
- Can reactivate users if needed
- Shifts reference users, so user shouldn't be fully deleted

## API Decisions

### 1. RESTful Design
**Decision**: Follow REST conventions with resource-based URLs.

**Rationale**:
- Industry standard
- Easy to understand
- Works well with HTTP methods
- Good for API clients and documentation

### 2. Response Models
**Decision**: Use Pydantic models for all API responses.

**Rationale**:
- Type validation
- Automatic JSON serialization
- API documentation generation
- Clear contracts

### 3. Error Handling
**Decision**: Use HTTPException with appropriate status codes.

**Rationale**:
- Standard HTTP semantics
- Easy for clients to handle
- Clear error messages
- Follows FastAPI best practices

### 4. Authentication present but not enforced
**Decision**: Provide login/JWT issuance now, defer endpoint protection and role enforcement to the next iteration.

**Assumption**: Current deployments run in trusted environments (local dev or private homelab).

**Rationale**:
- Keep MVP delivery fast while enabling real credentials and hashed passwords
- Auth middleware/guards can be added incrementally
- Allows testing login/token flow without blocking other features

**Note**: user_id and admin_id are still accepted as parameters on most endpoints. In production they must come from authenticated sessions with role checks.

## Service Layer Decisions

### 1. Separation of Concerns
**Decision**: Three-layer architecture (API → Services → Models).

**Rationale**:
- Business logic in services, not controllers
- Easier to test
- Can reuse services across different interfaces
- Clear responsibilities

### 2. Transaction Management
**Decision**: Services manage database transactions.

**Rationale**:
- Atomic operations
- Rollback on errors
- Keeps controllers thin
- Consistent error handling

### 3. Validation
**Decision**: Validate business rules in services, not just at API level.

**Rationale**:
- Protection even if bypassing API
- Business rules in one place
- Can call services from different interfaces
- Defense in depth

## Swap Workflow Decisions

### 1. Mandatory Admin Approval
**Decision**: All swap requests require admin approval.

**Assumption**: This is a business requirement.

**Rationale**:
- Prevents unauthorized schedule changes
- Maintains operational control
- Allows admin to verify reason and feasibility
- Standard practice in shift management

### 2. Automatic Swap Execution
**Decision**: On approval, shifts are swapped automatically.

**Rationale**:
- Reduces manual work
- Prevents errors
- Atomic operation (approval + swap)
- Clear state transitions

### 3. Swap Validation
**Decision**: Validate that shifts belong to correct agents before creating swap request.

**Rationale**:
- Prevent invalid requests early
- Better user experience
- Data integrity
- Clear error messages

### 4. Cancellation Rules
**Decision**: Only requester can cancel, only if still pending.

**Rationale**:
- Once approved/rejected, swap is finalized
- Requester owns their request
- Clear ownership model
- Prevents abuse

## Export Decisions

### 1. Excel Export
**Decision**: Use openpyxl with professional formatting.

**Rationale**:
- Excel is ubiquitous in business
- Professional appearance matters
- Openpyxl is mature and reliable
- Formatting makes data more readable

### 2. ICS Export
**Decision**: Simple, unidirectional ICS export.

**Rationale**:
- Calendar integration is useful
- Unidirectional is simpler (no sync conflicts)
- Standard format (RFC 5545)
- Works with all major calendar apps

### 3. In-Memory Generation
**Decision**: Generate exports in memory (BytesIO), not as files.

**Rationale**:
- No filesystem clutter
- Stateless (good for containers)
- Immediate delivery to client
- No cleanup needed

## Docker Decisions

### 1. Separate Environments
**Decision**: Two docker-compose files (dev and homelab).

**Rationale**:
- Different requirements for dev vs production
- Dev needs volume mounts for hot reload
- Homelab needs Traefik labels
- Clear separation

### 2. Health Checks
**Decision**: Database health check before backend starts.

**Rationale**:
- Prevents connection errors
- Clean startup sequence
- Better in orchestration
- FastAPI depends on DB

### 3. Network Isolation
**Decision**: Internal network for backend-db, external for Traefik-backend.

**Rationale**:
- Security best practice
- Database not exposed
- Only backend exposed via Traefik
- Standard microservices pattern

## Homelab Integration Decisions

### 1. Traefik Labels
**Decision**: Configure Traefik via Docker labels.

**Rationale**:
- Standard homelab practice
- Dynamic configuration
- No separate config files
- Self-documenting

### 2. SSL/TLS
**Decision**: Use Let's Encrypt via Traefik.

**Assumption**: Homelab has Traefik with Let's Encrypt configured.

**Rationale**:
- HTTPS is essential
- Let's Encrypt is free and automatic
- Traefik handles renewal
- Standard setup

### 3. Deployment Script
**Decision**: Provide deployment script for homelab.

**Rationale**:
- Easier for users
- Documents deployment process
- Validates configuration
- Consistent deployment

## Documentation Decisions

### 1. Multiple Documentation Files
**Decision**: README, QUICKSTART, PROJECT_STATUS, detailed docs.

**Rationale**:
- Different audiences (users, developers, ops)
- Different purposes (overview, quick start, status)
- Easier to maintain
- Easier to find information

### 2. Markdown Format
**Decision**: Use Markdown for all documentation.

**Rationale**:
- Renders well on GitHub
- Easy to write and read
- Version control friendly
- Widely supported

### 3. Living Documentation
**Decision**: Documentation includes "last updated" dates and status indicators.

**Rationale**:
- Shows documentation freshness
- Makes status clear
- Helps users know what's current
- Easy to update

## Future Considerations

### 1. Authentication
**Plan**: JWT-based authentication with role-based access control.

**Why JWT**: Stateless, works well with APIs, scalable.

### 2. Testing
**Plan**: pytest for unit and integration tests, focus on services first.

**Why pytest**: Standard in Python, good fixtures, easy to write.

### 3. Migrations
**Plan**: Alembic for database migrations.

**Why Alembic**: Standard with SQLAlchemy, version control for schema.

### 4. Monitoring
**Plan**: Prometheus metrics, integrate with homelab observability.

**Why Prometheus**: Standard for metrics, homelab likely already has it.

### 5. Caching
**Plan**: Redis for caching if performance becomes an issue.

**Why Redis**: Fast, widely used, good for session storage too.

## Reversible Decisions

All decisions are documented so they can be reconsidered if requirements change:

- Technology stack can be changed (though costly)
- API design can be versioned
- Database schema can be migrated
- Export formats can be added
- Authentication can be implemented

## Non-Negotiable Requirements

Based on the problem statement:

1. AgentEscala must remain in its own repository
2. No mixing with homelab repository
3. Must have functional backend
4. Must have Excel and ICS export
5. Swap workflow must have admin approval
6. Must be deployable to homelab
7. Must work locally for development

All of these requirements have been met in the MVP.
