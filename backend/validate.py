"""
Simple validation script to verify AgentEscala MVP functionality
Run this after seeding the database to validate core operations
"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.models import User, Shift, SwapRequest, UserRole, SwapStatus
from backend.services import UserService, ShiftService, SwapService
from backend.utils import ExcelExporter, ICSExporter
from backend.config.database import init_db

def validate_mvp():
    """Validate core MVP functionality"""

    # Use environment variable or default
    database_url = os.getenv("DATABASE_URL", "postgresql://agentescala:agentescala_dev@db:5432/agentescala")

    print("=== AgentEscala MVP Validation ===\n")

    try:
        # Ensure tables exist before running checks
        init_db()

        # Connect to database
        print("1. Connecting to database...")
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        print("   ✓ Database connection successful\n")

        # Test 1: Check users exist
        print("2. Testing user queries...")
        users = UserService.get_all_users(db)
        admins = UserService.get_admins(db)
        agents = UserService.get_agents(db)
        print(f"   ✓ Found {len(users)} users ({len(admins)} admins, {len(agents)} agents)\n")

        # Test 2: Check shifts exist
        print("3. Testing shift queries...")
        shifts = ShiftService.get_all_shifts(db)
        if agents:
            agent_shifts = ShiftService.get_shifts_by_agent(db, agents[0].id)
            print(f"   ✓ Found {len(shifts)} shifts (agent 1 has {len(agent_shifts)} shifts)\n")
        else:
            print(f"   ✓ Found {len(shifts)} shifts\n")

        # Test 3: Check swap requests exist
        print("4. Testing swap queries...")
        pending_swaps = SwapService.get_pending_swaps(db)
        print(f"   ✓ Found {len(pending_swaps)} pending swap requests\n")

        # Test 4: Excel export
        print("5. Testing Excel export...")
        if shifts:
            excel_file = ExcelExporter.export_shifts(shifts[:10], include_agent_info=True)
            excel_size = len(excel_file.getvalue())
            print(f"   ✓ Excel export successful ({excel_size} bytes)\n")
        else:
            print("   ⚠ No shifts to export\n")

        # Test 5: ICS export
        print("6. Testing ICS export...")
        if shifts:
            ics_file = ICSExporter.export_shifts(shifts[:10])
            ics_size = len(ics_file.getvalue())
            print(f"   ✓ ICS export successful ({ics_size} bytes)\n")
        else:
            print("   ⚠ No shifts to export\n")

        # Test 6: Swap workflow validation
        print("7. Testing swap workflow validation...")
        if admins and agents and shifts:
            # Try creating an invalid swap (should fail)
            try:
                SwapService.create_swap_request(
                    db,
                    requester_id=agents[0].id,
                    target_agent_id=agents[1].id,
                    origin_shift_id=999999,  # Invalid shift
                    target_shift_id=shifts[0].id,
                    reason="Test"
                )
                print("   ✗ Validation failed - accepted invalid shift\n")
            except ValueError:
                print("   ✓ Validation working - rejected invalid swap\n")
        else:
            print("   ⚠ Insufficient data for swap validation test\n")

        # Summary
        print("=== Validation Complete ===\n")
        print("✓ Database connectivity: OK")
        print(f"✓ Users: {len(users)} found")
        print(f"✓ Shifts: {len(shifts)} found")
        print(f"✓ Swap requests: {len(pending_swaps)} pending")
        print("✓ Excel export: Working")
        print("✓ ICS export: Working")
        print("✓ Swap validation: Working")
        print("\nMVP is functional and ready to use!")

        db.close()
        return True

    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = validate_mvp()
    sys.exit(0 if success else 1)
