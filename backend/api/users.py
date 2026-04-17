from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..models import User, UserRole
from ..services import AdminAuditService, UserService
from ..utils.auth import get_password_hash
from ..utils.dependencies import get_current_user, require_admin
from .schemas import (
    AdminUserAuditResponse,
    AdminUserCreate,
    AdminUserStatusUpdate,
    AdminUserUpdate,
    UserCreate,
    UserResponse,
)

router = APIRouter(tags=["Usuários"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Criar um novo usuário (compatibilidade)."""
    existing_user = UserService.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário com este e-mail",
        )
    created_user = UserService.create_user(db, user.email, user.name, user.password, user.role)
    AdminAuditService.log_user_action(
        db,
        action="user_create",
        admin_user_id=current_user.id,
        target_user_id=created_user.id,
        summary=AdminAuditService.build_create_summary(
            email=created_user.email,
            name=created_user.name,
            role=created_user.role.value,
            is_active=created_user.is_active,
        ),
    )
    return created_user


@router.get("/users", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Listar todos os usuários (compatibilidade)."""
    return UserService.get_all_users(db, skip, limit)


@router.get("/users/agents", response_model=List[UserResponse])
def list_agents(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Listar médicos/agentes ativos."""
    return UserService.get_agents(db)


@router.get("/users/admins", response_model=List[UserResponse])
def list_admins(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Listar todos os administradores ativos."""
    return UserService.get_admins(db)


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obter um usuário pelo ID."""
    is_admin = current_user.role == UserRole.ADMIN or current_user.is_admin
    if not is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para consultar este usuário",
        )

    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Desativar um usuário (compatibilidade)."""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    success = UserService.deactivate_user(db, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    AdminAuditService.log_user_action(
        db,
        action="user_deactivate",
        admin_user_id=current_user.id,
        target_user_id=user_id,
        summary={"is_active": False},
    )
    return None


@router.get("/admin/users", response_model=List[UserResponse])
def admin_list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Listagem administrativa de usuários."""
    return UserService.get_all_users(db, skip, limit)


@router.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Criar usuário via área administrativa."""
    if UserService.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")

    created_user = UserService.create_user(
        db,
        email=payload.email,
        name=payload.name,
        password=payload.password,
        role=payload.role,
        is_active=payload.is_active,
    )

    AdminAuditService.log_user_action(
        db,
        action="admin_user_create",
        admin_user_id=current_user.id,
        target_user_id=created_user.id,
        summary=AdminAuditService.build_create_summary(
            email=created_user.email,
            name=created_user.name,
            role=created_user.role.value,
            is_active=created_user.is_active,
        ),
    )
    return created_user


@router.put("/admin/users/{user_id}", response_model=UserResponse)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Atualiza nome, e-mail, senha, role e status do usuário."""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    data = payload.model_dump(exclude_unset=True)
    new_email = data.get("email")
    if new_email and new_email != user.email:
        existing = UserService.get_user_by_email(db, new_email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")

    summary_data = AdminAuditService.build_update_summary(changes=data.copy())

    password = data.pop("password", None)
    if password:
        data["hashed_password"] = get_password_hash(password)

    if "role" in data:
        data["is_admin"] = data["role"] == UserRole.ADMIN

    updated_user = UserService.update_user(db, user_id, **data)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    AdminAuditService.log_user_action(
        db,
        action="admin_user_update",
        admin_user_id=current_user.id,
        target_user_id=updated_user.id,
        summary=summary_data,
    )

    return updated_user


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Remove usuário da base, impedindo auto-exclusão."""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é permitido excluir o próprio usuário",
        )

    user = UserService.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    db.delete(user)
    db.commit()

    AdminAuditService.log_user_action(
        db,
        action="admin_user_delete",
        admin_user_id=current_user.id,
        target_user_id=user_id,
        summary={"deleted": True},
    )
    return None


@router.patch("/admin/users/{user_id}/status", response_model=UserResponse)
def admin_update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Ativa/desativa usuário via endpoint administrativo dedicado."""
    if current_user.id == user_id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é permitido desativar o próprio usuário",
        )

    updated_user = UserService.update_user(db, user_id, is_active=payload.is_active)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    AdminAuditService.log_user_action(
        db,
        action="admin_user_status_change",
        admin_user_id=current_user.id,
        target_user_id=updated_user.id,
        summary={"is_active": updated_user.is_active},
    )

    return updated_user


@router.get("/admin/audit/users", response_model=List[AdminUserAuditResponse])
def admin_list_user_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None, min_length=1, max_length=64),
    target_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Lista eventos recentes de auditoria de administração de usuários."""
    return AdminAuditService.list_user_audit_logs(
        db,
        skip=skip,
        limit=limit,
        action=action,
        target_user_id=target_user_id,
    )
