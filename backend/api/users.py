from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..config.database import get_db
from ..services import UserService
from ..models import UserRole
from .schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Criar um novo usuário"""
    existing_user = UserService.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário com este e-mail"
        )
    return UserService.create_user(db, user.email, user.name, user.password, user.role)


@router.get("/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Listar todos os usuários"""
    return UserService.get_all_users(db, skip, limit)


@router.get("/agents", response_model=List[UserResponse])
def list_agents(db: Session = Depends(get_db)):
    """Listar todos os agentes ativos"""
    return UserService.get_agents(db)


@router.get("/admins", response_model=List[UserResponse])
def list_admins(db: Session = Depends(get_db)):
    """Listar todos os administradores ativos"""
    return UserService.get_admins(db)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Obter um usuário pelo ID"""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    """Desativar um usuário"""
    success = UserService.deactivate_user(db, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    return None
