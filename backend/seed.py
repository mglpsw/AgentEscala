"""
Script de seed do AgentEscala - Cria dados de exemplo para testes
"""
import os
from datetime import datetime, timedelta
from backend.config.database import SessionLocal
from backend.config.database import init_db
from backend.models import User, Shift, SwapRequest, UserRole, SwapStatus
from backend.utils.auth import get_password_hash

PRIMARY_ADMIN_EMAIL = "mf.soares@ks-sm.net"


def ensure_primary_admin(db) -> None:
    """Garante usuário admin principal de forma idempotente."""
    existing = db.query(User).filter(User.email == PRIMARY_ADMIN_EMAIL).first()
    desired_name = os.getenv("AGENTESCALA_PRIMARY_ADMIN_NAME", "Administrador Principal")
    initial_password = os.getenv("AGENTESCALA_PRIMARY_ADMIN_PASSWORD")

    if existing:
        existing.role = UserRole.ADMIN
        existing.is_admin = True
        existing.is_active = True
        if desired_name and existing.name != desired_name:
            existing.name = desired_name
        if initial_password:
            existing.hashed_password = get_password_hash(initial_password)
        db.commit()
        print(f"Admin principal ajustado: {PRIMARY_ADMIN_EMAIL}")
        return

    if not initial_password:
        generated = os.urandom(12).hex()
        initial_password = generated
        print("AGENTESCALA_PRIMARY_ADMIN_PASSWORD não definido; senha temporária segura gerada.")
        print("Altere a senha após o primeiro login via fluxo de gestão de usuários.")

    primary_admin = User(
        email=PRIMARY_ADMIN_EMAIL,
        name=desired_name,
        hashed_password=get_password_hash(initial_password),
        role=UserRole.ADMIN,
        is_admin=True,
        is_active=True,
    )
    db.add(primary_admin)
    db.commit()
    print(f"Admin principal criado: {PRIMARY_ADMIN_EMAIL}")


def seed_database():
    """Popular o banco de dados com dados de exemplo"""
    print("Inicializando banco de dados...")
    init_db()

    db = SessionLocal()

    try:
        ensure_primary_admin(db)

        # Verifica se já existem dados
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"O banco já contém {existing_users} usuários. Pulando seed.")
            return

        print("Criando usuários...")

        # Senha padrão para todos os usuários: "password123"
        default_password = get_password_hash("password123")

        # Cria admin
        admin = User(
            email="admin@agentescala.com",
            name="Admin User",
            hashed_password=default_password,
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)

        # Cria agentes
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
        print(f"Criados {len(agents) + 1} usuários (1 admin + {len(agents)} agentes)")

        # Atualiza para obter os IDs
        db.refresh(admin)
        for agent in agents:
            db.refresh(agent)

        print("Criando turnos...")

        # Cria turnos para os próximos 30 dias
        base_date = datetime.utcnow()
        shifts = []

        for day in range(30):
            current_date = base_date + timedelta(days=day)

            # Turno da manhã (8:00 - 16:00)
            morning_agent = agents[day % len(agents)]
            morning_shift = Shift(
                agent_id=morning_agent.id,
                user_id=morning_agent.id,
                start_time=current_date.replace(hour=8, minute=0, second=0, microsecond=0),
                end_time=current_date.replace(hour=16, minute=0, second=0, microsecond=0),
                title="Turno da Manhã",
                description="Turno regular da manhã",
                location="Escritório"
            )
            shifts.append(morning_shift)
            db.add(morning_shift)

            # Turno da tarde (16:00 - 00:00)
            afternoon_agent = agents[(day + 1) % len(agents)]
            afternoon_shift = Shift(
                agent_id=afternoon_agent.id,
                user_id=afternoon_agent.id,
                start_time=current_date.replace(hour=16, minute=0, second=0, microsecond=0),
                end_time=(current_date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                title="Turno da Tarde",
                description="Turno regular da tarde",
                location="Escritório"
            )
            shifts.append(afternoon_shift)
            db.add(afternoon_shift)

            # Turno da noite (00:00 - 08:00)
            night_agent = agents[(day + 2) % len(agents)]
            night_shift = Shift(
                agent_id=night_agent.id,
                user_id=night_agent.id,
                start_time=(current_date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                end_time=(current_date + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0),
                title="Turno da Noite",
                description="Turno regular da noite",
                location="Escritório"
            )
            shifts.append(night_shift)
            db.add(night_shift)

        db.commit()
        print(f"Criados {len(shifts)} turnos")

        # Atualiza turnos para obter os IDs
        for shift in shifts:
            db.refresh(shift)

        print("Criando solicitações de troca de exemplo...")

        # Cria algumas solicitações de troca de exemplo
        swap1 = SwapRequest(
            requester_id=agents[0].id,
            target_agent_id=agents[1].id,
            origin_shift_id=shifts[0].id,
            target_shift_id=shifts[1].id,
            reason="Preciso ir a uma consulta médica",
            status=SwapStatus.PENDING
        )
        db.add(swap1)

        swap2 = SwapRequest(
            requester_id=agents[2].id,
            target_agent_id=agents[3].id,
            origin_shift_id=shifts[6].id,
            target_shift_id=shifts[7].id,
            reason="Compromisso familiar",
            status=SwapStatus.PENDING
        )
        db.add(swap2)

        swap3 = SwapRequest(
            requester_id=agents[1].id,
            target_agent_id=agents[4].id,
            origin_shift_id=shifts[3].id,
            target_shift_id=shifts[4].id,
            reason="Motivos pessoais",
            status=SwapStatus.APPROVED,
            reviewed_by=admin.id,
            admin_notes="Aprovado - Motivo válido"
        )
        db.add(swap3)

        db.commit()
        print("Criadas 3 solicitações de troca (2 pendentes, 1 aprovada)")

        print("\n=== Seed concluído ===")
        print("\nCredenciais de exemplo:")
        print(f"  Admin: {admin.email}")
        print(f"  Agentes: {', '.join([a.email for a in agents])}")
        print("\nAgora você pode:")
        print("  - Acessar a API em http://localhost:8000")
        print("  - Ver a documentação em http://localhost:8000/docs")
        print("  - Verificar saúde em http://localhost:8000/health")

    except Exception as e:
        print(f"Erro ao realizar seed do banco: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
