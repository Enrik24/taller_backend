from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import (
    get_current_user, require_role, get_current_cliente, get_current_taller
)
from app.modules.usuarios.schemas import (
    UserResponse, ClienteResponse, TallerResponse,
    VehiculoResponse, VehiculoCreate, VehiculoUpdate,
    TecnicoResponse, TecnicoCreate, TecnicoUpdate,
    UserUpdate
)
# Al inicio del archivo, agrega:
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.services import ClienteService, TallerService
from app.modules.usuarios.models import Cliente, Taller, Vehiculo, Tecnico

router = APIRouter(prefix="/api", tags=["Usuarios"])


# Perfil del usuario actual
@router.get("/perfil", response_model=UserResponse)
async def get_profile(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """CU03 - Gestionar Perfil: Obtener datos del usuario logueado"""
    if hasattr(current_user, 'cliente'):
        # Es cliente, incluir vehículos
        service = ClienteService(db)
        cliente = service.get_cliente_by_user_id(current_user.id)
        return ClienteResponse.model_validate(cliente)
    elif hasattr(current_user, 'taller'):
        # Es taller, incluir técnicos
        service = TallerService(db)
        taller = service.get_taller_by_user_id(current_user.id)
        return TallerResponse.model_validate(taller)
    
    return UserResponse.model_validate(current_user)


@router.put("/perfil", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """CU03 - Gestionar Perfil: Actualizar datos permitidos"""
    if hasattr(current_user, 'cliente'):
        service = ClienteService(db)
        cliente = service.get_cliente_by_user_id(current_user.id)
        updated = service.update_user(cliente, update_data)
        db.commit()
        return ClienteResponse.model_validate(updated)
    elif hasattr(current_user, 'taller'):
        service = TallerService(db)
        taller = service.get_taller_by_user_id(current_user.id)
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