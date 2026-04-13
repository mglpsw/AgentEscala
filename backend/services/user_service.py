from sqlalchemy.orm import Session
from typing import List, Optional
from ..models import User, UserRole


class UserService:
    """Service for managing users"""

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        name: str,
        role: UserRole = UserRole.AGENT
    ) -> User:
        """Create a new user"""
        user = User(email=email, name=name, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user(db: Session, user_id: int) -> Optional[User]:
        """Get a user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get a user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def get_agents(db: Session) -> List[User]:
        """Get all agents"""
        return db.query(User).filter(User.role == UserRole.AGENT, User.is_active == True).all()

    @staticmethod
    def get_admins(db: Session) -> List[User]:
        """Get all admins"""
        return db.query(User).filter(User.role == UserRole.ADMIN, User.is_active == True).all()

    @staticmethod
    def update_user(db: Session, user_id: int, **kwargs) -> Optional[User]:
        """Update a user"""
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
        """Deactivate a user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        user.is_active = False
        db.commit()
        return True
