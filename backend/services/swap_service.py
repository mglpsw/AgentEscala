from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import SwapRequest, SwapStatus, User, Shift, UserRole


class SwapService:
    """Service for managing shift swap requests"""

    @staticmethod
    def create_swap_request(
        db: Session,
        requester_id: int,
        target_agent_id: int,
        origin_shift_id: int,
        target_shift_id: int,
        reason: Optional[str] = None
    ) -> SwapRequest:
        """Create a new swap request"""
        # Validate that shifts exist and belong to correct agents
        origin_shift = db.query(Shift).filter(Shift.id == origin_shift_id).first()
        target_shift = db.query(Shift).filter(Shift.id == target_shift_id).first()

        if not origin_shift or not target_shift:
            raise ValueError("One or both shifts not found")

        if origin_shift.agent_id != requester_id:
            raise ValueError("Origin shift does not belong to requester")

        if target_shift.agent_id != target_agent_id:
            raise ValueError("Target shift does not belong to target agent")

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
        """Get a swap request by ID"""
        return db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()

    @staticmethod
    def get_pending_swaps(db: Session) -> List[SwapRequest]:
        """Get all pending swap requests"""
        return db.query(SwapRequest).filter(SwapRequest.status == SwapStatus.PENDING).all()

    @staticmethod
    def get_swaps_by_agent(db: Session, agent_id: int) -> List[SwapRequest]:
        """Get all swap requests involving an agent"""
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
        """Approve a swap request (admin only) and execute the swap"""
        swap = db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
        if not swap:
            return None

        if swap.status != SwapStatus.PENDING:
            raise ValueError("Only pending swap requests can be approved")

        # Verify admin role
        admin = db.query(User).filter(User.id == admin_id).first()
        if not admin or admin.role != UserRole.ADMIN:
            raise ValueError("Only admins can approve swap requests")

        # Execute the swap by swapping agent_ids
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
        """Reject a swap request (admin only)"""
        swap = db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
        if not swap:
            return None

        if swap.status != SwapStatus.PENDING:
            raise ValueError("Only pending swap requests can be rejected")

        # Verify admin role
        admin = db.query(User).filter(User.id == admin_id).first()
        if not admin or admin.role != UserRole.ADMIN:
            raise ValueError("Only admins can reject swap requests")

        swap.status = SwapStatus.REJECTED
        swap.reviewed_by = admin_id
        swap.admin_notes = admin_notes

        db.commit()
        db.refresh(swap)
        return swap

    @staticmethod
    def cancel_swap(db: Session, swap_id: int, user_id: int) -> Optional[SwapRequest]:
        """Cancel a swap request (requester only)"""
        swap = db.query(SwapRequest).filter(SwapRequest.id == swap_id).first()
        if not swap:
            return None

        if swap.requester_id != user_id:
            raise ValueError("Only the requester can cancel a swap request")

        if swap.status != SwapStatus.PENDING:
            raise ValueError("Only pending swap requests can be cancelled")

        swap.status = SwapStatus.CANCELLED

        db.commit()
        db.refresh(swap)
        return swap
