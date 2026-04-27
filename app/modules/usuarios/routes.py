from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Union

from app.database import get_db
from app.dependencies import (
    get_current_user, require_role, get_current_cliente, get_current_taller
)
from app.modules.usuarios.schemas import (
    UserResponse, ClienteResponse, TallerResponse,
    VehiculoResponse, VehiculoCreate, VehiculoUpdate,
    TecnicoResponse, TecnicoCreate, TecnicoUpdate,
    UserUpdate, UserCreate
)
# Al inicio del archivo, agrega:
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.services import ClienteService, TallerService, UserService
from app.modules.usuarios.models import Cliente, Taller, Vehiculo, Tecnico
from app.auth.hashing import get_password_hash

router = APIRouter(prefix="/api", tags=["Usuarios"])


# REGISTRO PÚBLICO (para app móvil)
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request,
    data: UserCreate,
    db: Session = Depends(get_db)
):
    """CU01 - Registrar usuario (Cliente/Taller) público"""
    # Validar que el email no exista
    usuario_existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email"
        )
    
    # Validar tipo de usuario
    if data.tipo not in ['cliente', 'taller']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de usuario inválido. Use 'cliente' o 'taller'"
        )
    
    password_hash = get_password_hash(data.password)
    
    # Crear usuario según tipo
    if data.tipo == 'cliente':
        usuario = Cliente(
            nombre=data.nombre,
            email=data.email,
            password_hash=password_hash,
            tipo='cliente',
            telefono=data.telefono,
            direccion_default=data.direccion_default
        )
    else:  # tipo == 'taller'
        usuario = Taller(
            nombre=data.nombre,
            email=data.email,
            password_hash=password_hash,
            tipo='taller',
            nombre_comercial=data.nombre_comercial,
            direccion=data.direccion,
            latitud=data.latitud,
            longitud=data.longitud
        )
    
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    
    # Recargar el usuario con sus roles para la respuesta
    usuario = db.query(Usuario).filter(Usuario.id == usuario.id).first()
    
    return usuario


# Perfil del usuario actual
@router.get("/perfil", response_model=dict)
async def get_profile(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """CU03 - Gestionar Perfil: Obtener datos del usuario logueado"""
    base_data = UserResponse.model_validate(current_user).model_dump()
    if current_user.tipo == 'cliente':
        # Es cliente, incluir vehículos
        service = ClienteService(db)
        cliente = service.get_cliente_by_user_id(current_user.id)
        if cliente:
            base_data.update({
                'telefono': cliente.telefono,
                'direccion_default': cliente.direccion_default
            })
    elif current_user.tipo == 'taller':
        # Es taller, incluir técnicos
        service = TallerService(db)
        taller = service.get_taller_by_user_id(current_user.id)
        if not taller:
            # Crear registro básico en Taller si no existe
            taller = Taller(
                id_usuario=current_user.id,
                nombre_comercial=current_user.nombre,
                direccion=None,
                latitud=None,
                longitud=None
            )
            db.add(taller)
            db.commit()
            db.refresh(taller)
        base_data.update({
            'nombre_comercial': taller.nombre_comercial,
            'direccion': taller.direccion,
            'latitud': taller.latitud,
            'longitud': taller.longitud,
            'disponible': taller.disponible,
            'calificacion': taller.calificacion
        })
    return base_data

@router.put("/perfil", response_model=Union[ClienteResponse, TallerResponse, UserResponse])
async def update_profile(
    update_data: UserUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """CU03 - Gestionar Perfil: Actualizar datos permitidos"""
    if current_user.tipo == 'cliente':
        service = ClienteService(db)
        cliente = service.get_cliente_by_user_id(current_user.id)
        if cliente:
            updated = service.update_user(cliente, update_data)
            db.commit()
            return ClienteResponse.model_validate(updated)
    elif current_user.tipo == 'taller':
        service = TallerService(db)
        taller = service.get_taller_by_user_id(current_user.id)
        if taller:
            updated = service.update_user(taller, update_data)
            db.commit()
            return TallerResponse.model_validate(updated)
    
    updated = UserService(db).update_user(current_user, update_data)
    db.commit()
    return UserResponse.model_validate(updated)


# Sub-rutas para vehículos (solo Cliente)
@router.get("/perfil/vehiculos", response_model=List[VehiculoResponse])
async def get_vehiculos(
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Obtener vehículos del cliente logueado"""
    service = ClienteService(db)
    return service.get_vehiculos(current_cliente.id_usuario)


@router.post("/perfil/vehiculos", response_model=VehiculoResponse, status_code=status.HTTP_201_CREATED)
async def create_vehiculo(
    vehiculo_data: VehiculoCreate,
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Crear nuevo vehículo para el cliente"""
    service = ClienteService(db)
    
    # Validar placa única
    existing = db.query(Vehiculo).filter(Vehiculo.placa == vehiculo_data.placa).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La placa ya está registrada"
        )
    
    new_vehiculo = service.create_vehiculo(current_cliente.id_usuario, vehiculo_data)
    db.commit()
    db.refresh(new_vehiculo)
    return VehiculoResponse.model_validate(new_vehiculo)


@router.put("/perfil/vehiculos/{vehiculo_id}", response_model=VehiculoResponse)
async def update_vehiculo(
    vehiculo_id: int,
    update_data: VehiculoUpdate,
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Actualizar vehículo del cliente"""
    service = ClienteService(db)
    
    vehiculo = db.query(Vehiculo).filter(
        Vehiculo.id == vehiculo_id,
        Vehiculo.id_cliente == current_cliente.id_usuario
    ).first()
    
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehículo no encontrado"
        )
    
    updated = service.update_vehiculo(vehiculo, update_data)
    db.commit()
    db.refresh(updated)
    return VehiculoResponse.model_validate(updated)


@router.delete("/perfil/vehiculos/{vehiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehiculo(
    vehiculo_id: int,
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Eliminar vehículo del cliente"""
    service = ClienteService(db)
    
    vehiculo = db.query(Vehiculo).filter(
        Vehiculo.id == vehiculo_id,
        Vehiculo.id_cliente == current_cliente.id_usuario
    ).first()
    
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehículo no encontrado"
        )
    
    service.delete_vehiculo(vehiculo_id)
    db.commit()


# Sub-rutas para técnicos (solo Taller)
@router.get("/perfil/tecnicos", response_model=List[TecnicoResponse])
async def get_tecnicos(
    current_taller: Taller = Depends(get_current_taller),
    db: Session = Depends(get_db)
):
    """Obtener técnicos del taller logueado"""
    service = TallerService(db)
    return service.get_tecnicos(current_taller.id_usuario)


@router.post("/perfil/tecnicos", response_model=TecnicoResponse, status_code=status.HTTP_201_CREATED)
async def create_tecnico(
    tecnico_data: TecnicoCreate,
    current_taller: Taller = Depends(get_current_taller),
    db: Session = Depends(get_db)
):
    """Crear nuevo técnico para el taller"""
    service = TallerService(db)
    new_tecnico = service.create_tecnico(current_taller.id_usuario, tecnico_data)
    db.commit()
    db.refresh(new_tecnico)
    return TecnicoResponse.model_validate(new_tecnico)


@router.put("/perfil/tecnicos/{tecnico_id}", response_model=TecnicoResponse)
async def update_tecnico(
    tecnico_id: int,
    update_data: TecnicoUpdate,
    current_taller: Taller = Depends(get_current_taller),
    db: Session = Depends(get_db)
):
    """Actualizar técnico del taller"""
    service = TallerService(db)
    
    tecnico = db.query(Tecnico).filter(
        Tecnico.id == tecnico_id,
        Tecnico.id_taller == current_taller.id_usuario
    ).first()
    
    if not tecnico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Técnico no encontrado"
        )
    
    updated = service.update_tecnico(tecnico, update_data)
    db.commit()
    db.refresh(updated)
    return TecnicoResponse.model_validate(updated)


@router.delete("/perfil/tecnicos/{tecnico_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tecnico(
    tecnico_id: int,
    current_taller: Taller = Depends(get_current_taller),
    db: Session = Depends(get_db)
):
    """Eliminar técnico del taller"""
    tecnico = db.query(Tecnico).filter(
        Tecnico.id == tecnico_id,
        Tecnico.id_taller == current_taller.id_usuario
    ).first()
    
    if not tecnico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Técnico no encontrado"
        )
    
    db.delete(tecnico)
    db.commit()