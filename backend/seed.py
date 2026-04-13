"""
Seed script for AgentEscala - Creates sample data for testing
"""
from datetime import datetime, timedelta
from backend.config.database import SessionLocal
from backend.config.database import init_db
from backend.models import User, Shift, SwapRequest, UserRole, SwapStatus
from backend.utils.auth import get_password_hash


def seed_database():
    """Seed the database with sample data"""
    print("Initializing database...")
    init_db()

    db = SessionLocal()

    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"Database already contains {existing_users} users. Skipping seed.")
            return

        print("Creating users...")

        # Default password for all users: "password123"
        default_password = get_password_hash("password123")

        # Create admin
        admin = User(
            email="admin@agentescala.com",
            name="Admin User",
            hashed_password=default_password,
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)

        # Create agents
        agents = [
            User(email="alice@agentescala.com", name="Alice Silva", hashed_password=default_password, role=UserRole.AGENT),
            User(email="bob@agentescala.com", name="Bob Santos", hashed_password=default_password, role=UserRole.AGENT),
            User(email="carol@agentescala.com", name="Carol Oliveira", hashed_password=default_password, role=UserRole.AGENT),
            User(email="david@agentescala.com", name="David Costa", hashed_password=default_password, role=UserRole.AGENT),
            User(email="eve@agentescala.com", name="Eve Martins", hashed_password=default_password, role=UserRole.AGENT),
        ]

        for agent in agents:
            db.add(agent)

        db.commit()
        print(f"Created {len(agents) + 1} users (1 admin + {len(agents)} agents)")

        # Refresh to get IDs
        db.refresh(admin)
        for agent in agents:
            db.refresh(agent)

        print("Creating shifts...")

        # Create shifts for the next 30 days
        base_date = datetime.utcnow()
        shifts = []

        for day in range(30):
            current_date = base_date + timedelta(days=day)

            # Morning shift (8:00 - 16:00)
            morning_agent = agents[day % len(agents)]
            morning_shift = Shift(
                agent_id=morning_agent.id,
                start_time=current_date.replace(hour=8, minute=0, second=0, microsecond=0),
                end_time=current_date.replace(hour=16, minute=0, second=0, microsecond=0),
                title="Morning Shift",
                description="Regular morning shift",
                location="Office"
            )
            shifts.append(morning_shift)
            db.add(morning_shift)

            # Afternoon shift (16:00 - 00:00)
            afternoon_agent = agents[(day + 1) % len(agents)]
            afternoon_shift = Shift(
                agent_id=afternoon_agent.id,
                start_time=current_date.replace(hour=16, minute=0, second=0, microsecond=0),
                end_time=(current_date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                title="Afternoon Shift",
                description="Regular afternoon shift",
                location="Office"
            )
            shifts.append(afternoon_shift)
            db.add(afternoon_shift)

            # Night shift (00:00 - 08:00)
            night_agent = agents[(day + 2) % len(agents)]
            night_shift = Shift(
                agent_id=night_agent.id,
                start_time=(current_date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                end_time=(current_date + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0),
                title="Night Shift",
                description="Regular night shift",
                location="Office"
            )
            shifts.append(night_shift)
            db.add(night_shift)

        db.commit()
        print(f"Created {len(shifts)} shifts")

        # Refresh shifts to get IDs
        for shift in shifts:
            db.refresh(shift)

        print("Creating sample swap requests...")

        # Create a few sample swap requests
        swap1 = SwapRequest(
            requester_id=agents[0].id,
            target_agent_id=agents[1].id,
            origin_shift_id=shifts[0].id,
            target_shift_id=shifts[1].id,
            reason="Need to attend medical appointment",
            status=SwapStatus.PENDING
        )
        db.add(swap1)

        swap2 = SwapRequest(
            requester_id=agents[2].id,
            target_agent_id=agents[3].id,
            origin_shift_id=shifts[6].id,
            target_shift_id=shifts[7].id,
            reason="Family commitment",
            status=SwapStatus.PENDING
        )
        db.add(swap2)

        swap3 = SwapRequest(
            requester_id=agents[1].id,
            target_agent_id=agents[4].id,
            origin_shift_id=shifts[3].id,
            target_shift_id=shifts[4].id,
            reason="Personal reasons",
            status=SwapStatus.APPROVED,
            reviewed_by=admin.id,
            admin_notes="Approved - Valid reason"
        )
        db.add(swap3)

        db.commit()
        print("Created 3 sample swap requests (2 pending, 1 approved)")

        print("\n=== Seed Complete ===")
        print("\nSample Credentials:")
        print(f"  Admin: {admin.email}")
        print(f"  Agents: {', '.join([a.email for a in agents])}")
        print("\nYou can now:")
        print("  - Access the API at http://localhost:8000")
        print("  - View API docs at http://localhost:8000/docs")
        print("  - Check health at http://localhost:8000/health")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
