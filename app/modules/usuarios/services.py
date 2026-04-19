from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from app.modules.usuarios.repository import UserRepository, ClienteRepository, TallerRepository
from app.modules.usuarios.models import Usuario, Cliente, Taller, Vehiculo, Tecnico
from app.modules.usuarios.schemas import UserCreate, UserUpdate, VehiculoCreate, VehiculoUpdate, TecnicoCreate, TecnicoUpdate
from app.auth.hashing import get_password_hash
from app.core.logging_service import log_audit


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)
        self.db = db
    
    def get_user_by_email(self, email: str) -> Optional[Usuario]:
        return self.repo.get_user_by_email(email)
    
    def get_user_by_id(self, user_id: int) -> Optional[Usuario]:
        return self.repo.get_user_by_id(user_id)
    
    def create_user(self, user_data: UserCreate) -> Usuario:
        # Hashear contraseña
        user_dict = user_data.model_dump()
        user_dict['password_hash'] = get_password_hash(user_dict.pop('password'))
        
        return self.repo.create_user(user_dict)
    
    def update_user(self, user: Usuario, update_data: UserUpdate) -> Usuario:
        update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
        return self.repo.update_user(user, update_dict)
    
    def increment_failed_attempts(self, user: Usuario):
        self.repo.increment_failed_attempts(user)
        self.db.commit()
    
    def reset_failed_attempts(self, user: Usuario):
        self.repo.reset_failed_attempts(user)
        self.db.commit()
    
    def deactivate_user(self, user_id: int) -> Optional[Usuario]:
        user = self.repo.deactivate_user(user_id)
        if user:
            self.db.commit()
            log_audit(
                db=self.db,
                user_id=user_id,
                action="CUENTA_DESACTIVADA",
                description=f"Cuenta de usuario {user.email} desactivada",
                ip_origen=None
            )
        return user
    
    def send_verification_email(self, user: Usuario):
        # TODO: Implementar envío real de email
        print(f"Email de verificación enviado a {user.email}")
        pass


class ClienteService(UserService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.cliente_repo = ClienteRepository(db)
    
    def get_cliente_by_user_id(self, user_id: int) -> Optional[Cliente]:
        return self.db.query(Cliente).filter(Cliente.id_usuario == user_id).first()
    
    def get_vehiculos(self, cliente_id: int) -> List[Vehiculo]:
        return self.cliente_repo.get_vehiculos_by_cliente(cliente_id)
    
    def create_vehiculo(self, cliente_id: int, vehiculo_data: VehiculoCreate) -> Vehiculo:
        return self.cliente_repo.create_vehiculo(cliente_id, vehiculo_data.model_dump())
    
    def update_vehiculo(self, vehiculo: Vehiculo, update_data: VehiculoUpdate) -> Vehiculo:
        update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
        return self.cliente_repo.update_vehiculo(vehiculo, update_dict)
    
    def delete_vehiculo(self, vehiculo_id: int) -> bool:
        result = self.cliente_repo.delete_vehiculo(vehiculo_id)
        if result:
            self.db.commit()
        return result


class TallerService(UserService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.taller_repo = TallerRepository(db)
    
    def get_taller_by_user_id(self, user_id: int) -> Optional[Taller]:
        return self.db.query(Taller).filter(Taller.id_usuario == user_id).first()
    
    def get_tecnicos(self, taller_id: int) -> List[Tecnico]:
        return self.taller_repo.get_tecnicos_by_taller(taller_id)
    
    def create_tecnico(self, taller_id: int, tecnico_data: TecnicoCreate) -> Tecnico:
        return self.taller_repo.create_tecnico(taller_id, tecnico_data.model_dump())
    
    def update_tecnico(self, tecnico: Tecnico, update_data: TecnicoUpdate) -> Tecnico:
        update_dict = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}
        return self.taller_repo.update_tecnico(tecnico, update_dict)
    
    def update_disponibilidad(self, taller_id: int, disponible: bool) -> Optional[Taller]:
        result = self.taller_repo.update_disponibilidad(taller_id, disponible)
        if result:
            self.db.commit()
            log_audit(
                db=self.db,
                user_id=taller_id,
                action="DISPONIBILIDAD_ACTUALIZADA",
                description=f"Taller cambió disponibilidad a {disponible}",
                ip_origen=None
            )
        return result
    
    def has_available_tecnico(self, taller_id: int) -> bool:
        """Verifica si el taller tiene al menos 1 técnico disponible"""
        tecnicos = self.taller_repo.get_disponibles_tecnicos(taller_id)
        return len(tecnicos) > 0