from backend.config.database import SessionLocal
from backend.models import User
from backend.seed import PRIMARY_ADMIN_EMAIL, ensure_primary_admin
from backend.utils.auth import verify_password


def test_ensure_primary_admin_uses_default_password_when_env_missing(monkeypatch):
    monkeypatch.delenv("AGENTESCALA_PRIMARY_ADMIN_PASSWORD", raising=False)

    db = SessionLocal()
    try:
        ensure_primary_admin(db)
        user = db.query(User).filter(User.email == PRIMARY_ADMIN_EMAIL).first()
        assert user is not None
        assert verify_password("CHANGE_ME", user.hashed_password)
    finally:
        db.close()


def test_ensure_primary_admin_honors_env_password(monkeypatch):
    monkeypatch.setenv("AGENTESCALA_PRIMARY_ADMIN_PASSWORD", "CHANGE_ME_FROM_ENV")

    db = SessionLocal()
    try:
        ensure_primary_admin(db)
        user = db.query(User).filter(User.email == PRIMARY_ADMIN_EMAIL).first()
        assert user is not None
        assert verify_password("CHANGE_ME_FROM_ENV", user.hashed_password)
        assert not verify_password("CHANGE_ME", user.hashed_password)
    finally:
        db.close()
