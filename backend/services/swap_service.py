from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import SwapRequest, SwapStatus, User, Shift, UserRole


class SwapService:
    """Serviço para gerenciar solicitações de troca de turnos"""

    @staticmethod
    def create_swap_request(
        db: Session,
        requester_id: int,
        target_agent_id: int,
        origin_shift_id: int,
        target_shift_id: int,
        reason: Optional[str] = None
    ) -> SwapRequest:
        """Criar uma nova solicitação de troca"""
        # Valida se os turnos existem e pertencem aos agentes corretos
        origin_shift = db.query(Shift).filter(Shift.id == origin_shift_id).first()
        target_shift = db.query(Shift).filter(Shift.id == target_shift_id).first()

        if not origin_shift or not target_shift:
            raise ValueError("Um ou ambos os turnos não foram encontrados")

        if origin_shift.agent_id != requester_id:
            raise ValueError("O turno de origem não pertence ao solicitante")

        if target_shift.agent_id != target_agent_id:
            raise ValueError("O turno de destino não pertence ao agente alvo")

        swap_request = SwapRequest(
            requester_id=requester_id,
            target_agent_id=target_agent_id,
            origin_shift_id=origin_shift_id,
            target_shift_id=target_shift_id,
            reason=reason,
            status=SwapStatus.PENDING
        )
        db.add(swap_request)
        db.commit()
        db.refresh(swap_request)
        return swap_request

    @staticmethod
    def get_swap_request(db: Session, swap_id: int) -> Optional[SwapRequest]:
        """Obter uma solicitação de troca pelo ID"""
        return db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()

    @staticmethod
    def get_pending_swaps(db: Session) -> List[SwapRequest]:
        """Listar todas as solicitações de troca pendentes"""
        return db.query(SwapRequest).filter(SwapRequest.status == SwapStatus.PENDING).all()

    @staticmethod
    def get_all_swaps(db: Session, skip: int = 0, limit: int = 100) -> List[SwapRequest]:
        """Listar todas as solicitações de troca com paginação"""
        return (
            db.query(SwapRequest)
            .order_by(SwapRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_swaps_by_agent(db: Session, agent_id: int) -> List[SwapRequest]:
        """Listar todas as solicitações de troca que envolvem um agente"""
        return db.query(SwapRequest).filter(
            (SwapRequest.requester_id == agent_id) |
            (SwapRequest.target_agent_id == agent_id)
        ).all()

    @staticmethod
    def approve_swap(
        db: Session,
        swap_id: int,
        admin_id: int,
        admin_notes: Optional[str] = None
    ) -> Optional[SwapRequest]:
        """Aprovar uma solicitação de troca (somente administrador) e executar a troca"""
        swap = db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
        if not swap:
            return None

        if swap.status != SwapStatus.PENDING:
            raise ValueError("Apenas solicitações pendentes podem ser aprovadas")

        # Verifica papel de administrador
        admin = db.query(User).filter(User.id == admin_id).first()
        if not admin or admin.role != UserRole.ADMIN:
            raise ValueError("Somente administradores podem aprovar solicitações de troca")

        # Executa a troca invertendo os agent_ids
        origin_shift = swap.origin_shift
        target_shift = swap.target_shift

        temp_agent_id = origin_shift.agent_id
        origin_shift.agent_id = target_shift.agent_id
        target_shift.agent_id = temp_agent_id

        # Update swap request status
        swap.status = SwapStatus.APPROVED
        swap.reviewed_by = admin_id
        swap.admin_notes = admin_notes

        db.commit()
        db.refresh(swap)
        return swap

    @staticmethod
    def reject_swap(
        db: Session,
        swap_id: int,
        admin_id: int,
        admin_notes: Optional[str] = None
    ) -> Optional[SwapRequest]:
        """Rejeitar uma solicitação de troca (somente administrador)"""
        swap = db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
        if not swap:
            return None

        if swap.status != SwapStatus.PENDING:
            raise ValueError("Apenas solicitações pendentes podem ser rejeitadas")

        # Verifica papel de administrador
        admin = db.query(User).filter(User.id == admin_id).first()
        if not admin or admin.role != UserRole.ADMIN:
            raise ValueError("Somente administradores podem rejeitar solicitações de troca")

        swap.status = SwapStatus.REJECTED
        swap.reviewed_by = admin_id
        swap.admin_notes = admin_notes

        db.commit()
        db.refresh(swap)
        return swap

    @staticmethod
    def cancel_swap(db: Session, swap_id: int, user_id: int) -> Optional[SwapRequest]:
        """Cancelar uma solicitação de troca (somente o solicitante)"""
        swap = db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
        if not swap:
            return None

        if swap.requester_id != user_id:
            raise ValueError("Apenas o solicitante pode cancelar uma solicitação de troca")

        if swap.status != SwapStatus.PENDING:
            raise ValueError("Apenas solicitações pendentes podem ser canceladas")

        swap.status = SwapStatus.CANCELLED

        db.commit()
        db.refresh(swap)
        return swap
