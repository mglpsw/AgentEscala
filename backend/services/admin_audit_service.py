from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..models import AdminUserAuditLog


class AdminAuditService:
    """Persistência mínima de auditoria de ações administrativas de usuários."""

    @staticmethod
    def log_user_action(
        db: Session,
        *,
        action: str,
        admin_user_id: int,
        target_user_id: int,
        summary: Dict[str, Any] | None = None,
    ) -> AdminUserAuditLog:
        payload = summary or {}
        entry = AdminUserAuditLog(
            action=action,
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            change_summary=json.dumps(payload, ensure_ascii=False),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def list_user_audit_logs(
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50,
        action: str | None = None,
        target_user_id: int | None = None,
    ) -> List[AdminUserAuditLog]:
        capped_limit = max(1, min(limit, 200))
        query = db.query(AdminUserAuditLog)
        if action is not None:
            query = query.filter(AdminUserAuditLog.action == action)
        if target_user_id is not None:
            query = query.filter(AdminUserAuditLog.target_user_id == target_user_id)
        return (
            query
            .order_by(AdminUserAuditLog.created_at.desc(), AdminUserAuditLog.id.desc())
            .offset(skip)
            .limit(capped_limit)
            .all()
        )

    @staticmethod
    def build_create_summary(*, email: str, name: str, role: str, is_active: bool) -> Dict[str, Any]:
        return {
            "email": email,
            "name": name,
            "role": role,
            "is_active": is_active,
        }

    @staticmethod
    def build_update_summary(*, changes: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        for key, value in changes.items():
            if key in {"password", "hashed_password"}:
                sanitized["password_changed"] = True
                continue
            if isinstance(value, datetime):
                sanitized[key] = value.isoformat()
            else:
                sanitized[key] = value
        return sanitized
