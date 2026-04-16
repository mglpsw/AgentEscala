"""Serviço de governança administrativa para perfis médicos."""

import logging
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from ..models import MedicalProfile, UFEnum

logger = logging.getLogger("agentescala.medical_profiles")


class MedicalProfileService:
    """Regras de negócio para identidade médica estruturada."""

    @staticmethod
    def create_profile(
        db: Session,
        user_id: int,
        profile_data: Any,
    ) -> MedicalProfile:
        """Criar perfil médico garantindo unicidade de usuário, CPF e CRM."""
        if MedicalProfileService.get_profile_by_user(db, user_id):
            raise ValueError("Usuário já possui perfil médico cadastrado.")

        MedicalProfileService._validate_unique_cpf(db, profile_data.cpf)
        MedicalProfileService._validate_unique_crm(db, profile_data.crm_numero, profile_data.crm_uf)

        profile = MedicalProfile(user_id=user_id, **profile_data.model_dump())
        db.add(profile)
        db.commit()
        db.refresh(profile)

        logger.info("perfil_medico_criado user_id=%s profile_id=%s", user_id, profile.id)
        return profile

    @staticmethod
    def get_profile(db: Session, profile_id: int) -> Optional[MedicalProfile]:
        """Buscar perfil médico pelo ID administrativo."""
        return db.query(MedicalProfile).filter(MedicalProfile.id == profile_id).first()

    @staticmethod
    def get_profile_by_user(db: Session, user_id: int) -> Optional[MedicalProfile]:
        """Buscar perfil médico vinculado a um usuário."""
        return db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()

    @staticmethod
    def list_profiles(db: Session, skip: int = 0, limit: int = 100) -> List[MedicalProfile]:
        """Listar perfis médicos para governança administrativa."""
        return (
            db.query(MedicalProfile)
            .order_by(MedicalProfile.nome_completo.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_profile(
        db: Session,
        profile: MedicalProfile,
        profile_data: Any,
    ) -> MedicalProfile:
        """Atualizar perfil médico com validação de duplicidades sensíveis."""
        update_data = profile_data.model_dump(exclude_unset=True)

        new_cpf = update_data.get("cpf")
        if new_cpf and new_cpf != profile.cpf:
            MedicalProfileService._validate_unique_cpf(db, new_cpf, ignore_profile_id=profile.id)

        new_crm_numero = update_data.get("crm_numero", profile.crm_numero)
        new_crm_uf = update_data.get("crm_uf", profile.crm_uf)
        if new_crm_numero != profile.crm_numero or new_crm_uf != profile.crm_uf:
            MedicalProfileService._validate_unique_crm(
                db,
                new_crm_numero,
                new_crm_uf,
                ignore_profile_id=profile.id,
            )

        for key, value in update_data.items():
            setattr(profile, key, value)

        db.commit()
        db.refresh(profile)

        logger.info("perfil_medico_atualizado profile_id=%s user_id=%s", profile.id, profile.user_id)
        return profile

    @staticmethod
    def delete_profile(db: Session, profile: MedicalProfile) -> None:
        """Remover perfil médico sem remover o usuário vinculado."""
        profile_id = profile.id
        user_id = profile.user_id
        db.delete(profile)
        db.commit()
        logger.info("perfil_medico_removido profile_id=%s user_id=%s", profile_id, user_id)

    @staticmethod
    def _validate_unique_cpf(
        db: Session,
        cpf: str,
        ignore_profile_id: Optional[int] = None,
    ) -> None:
        query = db.query(MedicalProfile).filter(MedicalProfile.cpf == cpf)
        if ignore_profile_id is not None:
            query = query.filter(MedicalProfile.id != ignore_profile_id)

        if query.first():
            raise ValueError("Já existe perfil médico com este CPF.")

    @staticmethod
    def _validate_unique_crm(
        db: Session,
        crm_numero: str,
        crm_uf: UFEnum,
        ignore_profile_id: Optional[int] = None,
    ) -> None:
        query = db.query(MedicalProfile).filter(
            MedicalProfile.crm_numero == crm_numero,
            MedicalProfile.crm_uf == crm_uf,
        )
        if ignore_profile_id is not None:
            query = query.filter(MedicalProfile.id != ignore_profile_id)

        if query.first():
            raise ValueError("Já existe perfil médico com este CRM e UF.")
