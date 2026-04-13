from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import User, UserRole
from ..utils.auth import get_password_hash


class UserService:
    """Serviço para gerenciar usuários"""

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        name: str,
        password: str,
        role: UserRole = UserRole.AGENT
    ) -> User:
        """Criar um novo usuário"""
        hashed_password = get_password_hash(password)
        user = User(email=email, name=name, hashed_password=hashed_password, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user(db: Session, user_id: int) -> Optional[User]:
        """Obter um usuário pelo ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Obter um usuário pelo e-mail"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Listar todos os usuários com paginação"""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def get_agents(db: Session) -> List[User]:
        """Listar todos os agentes ativos"""
        return db.query(User).filter(User.role == UserRole.AGENT, User.is_active == True).all()

    @staticmethod
    def get_admins(db: Session) -> List[User]:
        """Listar todos os administradores ativos"""
        return db.query(User).filter(User.role == UserRole.ADMIN, User.is_active == True).all()

    @staticmethod
    def update_user(db: Session, user_id: int, **kwargs) -> Optional[User]:
        """Atualizar um usuário"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> bool:
        """Desativar um usuário"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        user.is_active = False
        db.commit()
        return True
