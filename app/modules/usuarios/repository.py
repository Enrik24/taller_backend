from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List

from app.modules.usuarios.models import Usuario, Cliente, Taller, Rol, Permiso, Vehiculo, Tecnico


class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: int) -> Optional[Usuario]:
        return self.db.query(Usuario).filter(Usuario.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[Usuario]:
        return self.db.query(Usuario).filter(Usuario.email == email).first()
    
    def create_user(self, user_data: dict) -> Usuario:
        tipo = user_data.get('tipo')
        
        # Crear directamente la subclase para que SQLAlchemy maneje la herencia correctamente
        if tipo == 'cliente':
            user = Cliente(
                nombre=user_data['nombre'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                tipo='cliente',
                telefono=user_data.get('telefono'),
                direccion_default=user_data.get('direccion_default')
            )
        elif tipo == 'taller':
            user = Taller(
                nombre=user_data['nombre'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                tipo='taller',
                nombre_comercial=user_data.get('nombre_comercial'),
                direccion=user_data.get('direccion'),
                latitud=user_data.get('latitud'),
                longitud=user_data.get('longitud')
            )
        else:
            user = Usuario(
                nombre=user_data['nombre'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                tipo=tipo
            )
        
        self.db.add(user)
        self.db.flush()  # Obtener el ID generado
        
        # Asignar rol por defecto
        default_role = self.db.query(Rol).filter(Rol.nombre == tipo).first()
        if default_role:
            user.roles.append(default_role)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_user(self, user: Usuario, update_data: dict) -> Usuario:
        for field, value in update_data.items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)
        return user
    
    def increment_failed_attempts(self, user: Usuario) -> Usuario:
        user.intentos_fallidos += 1
        return user
    
    def reset_failed_attempts(self, user: Usuario) -> Usuario:
        user.intentos_fallidos = 0
        return user
    
    def deactivate_user(self, user_id: int) -> Optional[Usuario]:
        user = self.get_user_by_id(user_id)
        if user:
            user.activo = False
        return user
    
    def get_role_by_name(self, role_name: str) -> Optional[Rol]:
        return self.db.query(Rol).filter(Rol.nombre == role_name).first()
    
    def get_permission_by_code(self, code: str) -> Optional[Permiso]:
        return self.db.query(Permiso).filter(Permiso.codigo == code).first()
    
    def get_all_roles(self) -> List[Rol]:
        return self.db.query(Rol).all()
    
    def get_all_permissions(self) -> List[Permiso]:
        return self.db.query(Permiso).all()


class ClienteRepository(UserRepository):
    def get_vehiculos_by_cliente(self, cliente_id: int) -> List[Vehiculo]:
        return self.db.query(Vehiculo).filter(Vehiculo.id_cliente == cliente_id).all()
    
    def create_vehiculo(self, cliente_id: int, vehiculo_data: dict) -> Vehiculo:
        vehiculo = Vehiculo(
            id_cliente=cliente_id,
            **vehiculo_data
        )
        self.db.add(vehiculo)
        return vehiculo
    
    def update_vehiculo(self, vehiculo: Vehiculo, update_data: dict) -> Vehiculo:
        for field, value in update_data.items():
            if hasattr(vehiculo, field) and value is not None:
                setattr(vehiculo, field, value)
        return vehiculo
    
    def delete_vehiculo(self, vehiculo_id: int) -> bool:
        vehiculo = self.db.query(Vehiculo).filter(Vehiculo.id == vehiculo_id).first()
        if vehiculo:
            self.db.delete(vehiculo)
            return True
        return False


class TallerRepository(UserRepository):
    def get_tecnicos_by_taller(self, taller_id: int) -> List[Tecnico]:
        return self.db.query(Tecnico).filter(Tecnico.id_taller == taller_id).all()
    
    def create_tecnico(self, taller_id: int, tecnico_data: dict) -> Tecnico:
        tecnico = Tecnico(
            id_taller=taller_id,
            **tecnico_data
        )
        self.db.add(tecnico)
        return tecnico
    
    def update_tecnico(self, tecnico: Tecnico, update_data: dict) -> Tecnico:
        for field, value in update_data.items():
            if hasattr(tecnico, field) and value is not None:
                setattr(tecnico, field, value)
        return tecnico
    
    def get_disponibles_tecnicos(self, taller_id: int) -> List[Tecnico]:
        return self.db.query(Tecnico).filter(
            Tecnico.id_taller == taller_id,
            Tecnico.disponible == True
        ).all()
    
    def update_disponibilidad(self, taller_id: int, disponible: bool) -> Optional[Taller]:
        taller = self.db.query(Taller).filter(Taller.id_usuario == taller_id).first()
        if taller:
            taller.disponible = disponible
        return taller