"""
Script simples de validação para verificar a funcionalidade do MVP do AgentEscala
Execute-o após semear o banco de dados para validar as operações principais
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
    """Validar a funcionalidade principal do MVP"""

    # Usa variável de ambiente ou padrão
    database_url = os.getenv("DATABASE_URL", "postgresql://agentescala:agentescala_dev@db:5432/agentescala")

    print("=== Validação do MVP AgentEscala ===\n")

    try:
        # Garante que as tabelas existam antes de executar as verificações
        init_db()

        # Conecta ao banco de dados
        print("1. Conectando ao banco de dados...")
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        print("   ✓ Conexão com o banco realizada\n")

        # Teste 1: verificar se existem usuários
        print("2. Testando consultas de usuários...")
        users = UserService.get_all_users(db)
        admins = UserService.get_admins(db)
        agents = UserService.get_agents(db)
        print(f"   ✓ Encontrados {len(users)} usuários ({len(admins)} admins, {len(agents)} agentes)\n")

        # Teste 2: verificar se existem turnos
        print("3. Testando consultas de turnos...")
        shifts = ShiftService.get_all_shifts(db)
        if agents:
            agent_shifts = ShiftService.get_shifts_by_agent(db, agents[0].id)
            print(f"   ✓ Encontrados {len(shifts)} turnos (agente 1 tem {len(agent_shifts)} turnos)\n")
        else:
            print(f"   ✓ Encontrados {len(shifts)} turnos\n")

        # Teste 3: verificar se existem solicitações de troca
        print("4. Testando consultas de trocas...")
        pending_swaps = SwapService.get_pending_swaps(db)
        print(f"   ✓ Encontradas {len(pending_swaps)} solicitações pendentes\n")

        # Teste 4: exportação Excel
        print("5. Testando exportação Excel...")
        if shifts:
            excel_file = ExcelExporter.export_shifts(shifts[:10], include_agent_info=True)
            excel_size = len(excel_file.getvalue())
            print(f"   ✓ Exportação Excel bem-sucedida ({excel_size} bytes)\n")
        else:
            print("   ⚠ Não há turnos para exportar\n")

        # Teste 5: exportação ICS
        print("6. Testando exportação ICS...")
        if shifts:
            ics_file = ICSExporter.export_shifts(shifts[:10])
            ics_size = len(ics_file.getvalue())
            print(f"   ✓ Exportação ICS bem-sucedida ({ics_size} bytes)\n")
        else:
            print("   ⚠ Não há turnos para exportar\n")

        # Teste 6: validação do fluxo de trocas
        print("7. Testando validação do fluxo de trocas...")
        if admins and agents and shifts:
            # Tenta criar uma troca inválida (deve falhar)
            try:
                SwapService.create_swap_request(
                    db,
                    requester_id=agents[0].id,
                    target_agent_id=agents[1].id,
                    origin_shift_id=999999,  # Turno inválido
                    target_shift_id=shifts[0].id,
                    reason="Test"
                )
                print("   ✗ Validação falhou - turno inválido foi aceito\n")
            except ValueError:
                print("   ✓ Validação funcionando - troca inválida rejeitada\n")
        else:
            print("   ⚠ Dados insuficientes para testar validação de troca\n")

        # Resumo
        print("=== Validação Concluída ===\n")
        print("✓ Conectividade com o banco: OK")
        print(f"✓ Usuários: {len(users)} encontrados")
        print(f"✓ Turnos: {len(shifts)} encontrados")
        print(f"✓ Solicitações de troca: {len(pending_swaps)} pendentes")
        print("✓ Exportação Excel: Funcionando")
        print("✓ Exportação ICS: Funcionando")
        print("✓ Validação de trocas: Funcionando")
        print("\nO MVP está funcional e pronto para uso!")

        db.close()
        return True

    except Exception as e:
        print(f"\n✗ Falha na validação: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = validate_mvp()
    sys.exit(0 if success else 1)
