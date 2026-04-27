from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional, Union
from datetime import datetime
import csv
import io
import logging

from app.database import get_db
from app.dependencies import require_role, get_current_user
from app.modules.usuarios.models import Usuario, Rol, Permiso, Bitacora, Cliente, Taller, Vehiculo, Tecnico
from app.auth.hashing import get_password_hash
from app.modules.usuarios.schemas import (
    UserResponse, RoleResponse, PermissionResponse,
    RoleCreate, RoleUpdate, PermisoIdsUpdate,
    PermisoCreate, PermisoUpdate,
    UserCreate, UserUpdate, UserRolesUpdate,
    ClienteResponse, TallerResponse, VehiculoResponse, TecnicoResponse
)
from app.modules.pagos.models import Comision, Pago
from app.core.logging_service import log_audit, get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Administración"])


# Gestión de Usuarios
@router.get("/usuarios", response_model=List[Union[ClienteResponse, TallerResponse, UserResponse]])
async def listar_usuarios(
    rol: Optional[str] = None,
    activo: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """CU18 - Listar usuarios con filtros y paginación"""
    query = db.query(Usuario)
    
    if rol:
        # Filtramos directamente por la columna 'tipo' de la tabla usuario
        query = query.filter(Usuario.tipo == rol)
    if activo is not None:
        query = query.filter(Usuario.activo == activo)
    
    # Paginación
    offset = (page - 1) * page_size
    usuarios = query.options(joinedload(Usuario.roles)).offset(offset).limit(page_size).all()
    
    return usuarios


@router.post("/usuarios", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    request: Request,
    data: UserCreate,
    rol_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Crear nuevo usuario"""
    usuario_existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese email"
        )
    
    password_hash = get_password_hash(data.password)
    
    if data.tipo == 'cliente':
        usuario = Cliente(
            nombre=data.nombre,
            email=data.email,
            password_hash=password_hash,
            tipo='cliente',
            telefono=data.telefono,
            direccion_default=data.direccion_default
        )
    elif data.tipo == 'taller':
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
    else:
        usuario = Usuario(
            nombre=data.nombre,
            email=data.email,
            password_hash=password_hash,
            tipo=data.tipo.value
        )
    
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    
    if rol_ids:
        roles = db.query(Rol).filter(Rol.id.in_(rol_ids)).all()
        usuario.roles = roles
        db.commit()
    
    usuario = db.query(Usuario).options(joinedload(Usuario.roles)).filter(Usuario.id == usuario.id).first()
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="USUARIO_CREADO",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Usuario:{usuario.email}"
    )
    
    return UserResponse.model_validate(usuario)


@router.patch("/usuarios/{usuario_id}", response_model=UserResponse)
async def actualizar_usuario(
    request: Request,
    usuario_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Actualizar usuario"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if data.nombre is not None:
        usuario.nombre = data.nombre
    
    if data.email is not None:
        # Validar que el email no esté en uso por otro usuario
        existing = db.query(Usuario).filter(Usuario.email == data.email, Usuario.id != usuario_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con ese email"
            )
        usuario.email = data.email
    
    if data.telefono is not None:
        usuario.telefono = data.telefono
    
    if data.direccion_default is not None:
        usuario.direccion_default = data.direccion_default
    
    if data.nombre_comercial is not None:
        usuario.nombre_comercial = data.nombre_comercial
    
    if data.direccion is not None:
        usuario.direccion = data.direccion
    
    if data.latitud is not None:
        usuario.latitud = data.latitud
    
    if data.longitud is not None:
        usuario.longitud = data.longitud
    
    if data.password is not None:
        usuario.password_hash = get_password_hash(data.password)
    
    db.commit()
    db.refresh(usuario)
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="USUARIO_ACTUALIZADO",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Usuario:{usuario.email}"
    )
    
    return UserResponse.model_validate(usuario)


@router.put("/usuarios/{usuario_id}/roles", response_model=UserResponse)
async def actualizar_roles_usuario(
    request: Request,
    usuario_id: int,
    data: UserRolesUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Actualizar roles de un usuario"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Buscar roles
    roles = db.query(Rol).filter(Rol.id.in_(data.rol_ids)).all()
    if len(roles) != len(data.rol_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Algunos IDs de roles no existen"
        )
    
    usuario.roles = roles
    db.commit()
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="USUARIO_ROL_ACTUALIZADO",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Usuario:{usuario.email}"
    )
    
    usuario = db.query(Usuario).options(joinedload(Usuario.roles)).filter(Usuario.id == usuario_id).first()
    return UserResponse.model_validate(usuario)


@router.get("/usuarios/{usuario_id}", response_model=Union[ClienteResponse, TallerResponse, UserResponse])
async def detalle_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Obtener detalle de usuario"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return usuario

@router.get("/talleres/{taller_id}/tecnicos", response_model=List[TecnicoResponse])
async def obtener_tecnicos_taller(
    taller_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Obtener técnicos de un taller específico"""
    tecnicos = db.query(Tecnico).filter(Tecnico.id_taller == taller_id).all()
    return tecnicos

@router.get("/clientes/{cliente_id}/vehiculos", response_model=List[VehiculoResponse])
async def obtener_vehiculos_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Obtener vehículos de un cliente específico"""
    vehiculos = db.query(Vehiculo).filter(Vehiculo.id_cliente == cliente_id).all()
    return vehiculos

@router.get("/tecnicos", response_model=List[TecnicoResponse])
async def listar_todos_tecnicos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Listar todos los técnicos del sistema"""
    tecnicos = db.query(Tecnico).all()
    return tecnicos

@router.get("/vehiculos", response_model=List[VehiculoResponse])
async def listar_todos_vehiculos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Listar todos los vehículos del sistema"""
    vehiculos = db.query(Vehiculo).all()
    return vehiculos


@router.put("/usuarios/{usuario_id}/estado")
async def actualizar_estado_usuario(
    request: Request,
    usuario_id: int,
    activo: bool,
    confirmacion: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Activar/desactivar usuario y reiniciar intentos fallidos si se activa"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if activo and usuario.intentos_fallidos > 0:
        usuario.intentos_fallidos = 0
        log_audit(
            db=db,
            user_id=current_user.id,
            action="DESBLOQUEAR",
            ip_origen=get_client_ip(request),
            entidad_afectada=f"Usuario:{usuario.email}"
        )
    
    if not activo and usuario.roles:
        admin_role = db.query(Rol).filter(Rol.nombre == 'administrador').first()
        if admin_role in usuario.roles:
            admins_activos = db.query(Usuario).join(Usuario.roles).filter(
                Rol.nombre == 'administrador',
                Usuario.activo == True
            ).count()
            
            if admins_activos <= 1 and not confirmacion:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede desactivar el último administrador. Requiere confirmación explícita."
                )
    
    usuario.activo = activo
    db.commit()
    
    return {"message": f"Usuario {'activado' if activo else 'desactivado'} exitosamente"}


@router.delete("/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(
    request: Request,
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Eliminación lógica de usuario"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Eliminación lógica
    usuario.activo = False
    db.commit()
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="USUARIO_ELIMINADO",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Usuario:{usuario.email}"
    )


# Gestión de Roles y Permisos
@router.get("/roles", response_model=List[RoleResponse])
async def listar_roles(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """CU19 - Listar roles con sus permisos"""
    roles = db.query(Rol).options(joinedload(Rol.permisos)).all()
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def crear_rol(
    request: Request,
    data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Crear nuevo rol"""
    rol_existente = db.query(Rol).filter(Rol.nombre == data.nombre).first()
    if rol_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un rol con ese nombre"
        )
    
    rol = Rol(
        nombre=data.nombre,
        descripcion=data.descripcion
    )
    
    if data.permiso_ids:
        permisos = db.query(Permiso).filter(Permiso.id.in_(data.permiso_ids)).all()
        rol.permisos = permisos
    
    db.add(rol)
    db.commit()
    db.refresh(rol)
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="CREAR",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Rol:{rol.nombre}"
    )
    
    return RoleResponse.model_validate(rol)


@router.get("/roles/{rol_id}", response_model=RoleResponse)
async def obtener_rol(
    rol_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Obtener un rol específico"""
    rol = db.query(Rol).options(joinedload(Rol.permisos)).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    return RoleResponse.model_validate(rol)


@router.patch("/roles/{rol_id}", response_model=RoleResponse)
async def actualizar_rol(
    request: Request,
    rol_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Actualizar un rol"""
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    if data.nombre is not None:
        rol_existente = db.query(Rol).filter(Rol.nombre == data.nombre, Rol.id != rol_id).first()
        if rol_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro rol con ese nombre"
            )
        rol.nombre = data.nombre
    
    if data.descripcion is not None:
        rol.descripcion = data.descripcion
    
    db.commit()
    db.refresh(rol)
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="ACTUALIZAR",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Rol:{rol.nombre}"
    )
    
    return RoleResponse.model_validate(rol)


@router.delete("/roles/{rol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_rol(
    request: Request,
    rol_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Eliminar un rol"""
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    if rol.nombre == 'administrador':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el rol administrador"
        )
    
    if rol.usuarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un rol que tiene usuarios asignados"
        )
    
    nombre_rol = rol.nombre
    db.delete(rol)
    db.commit()
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="ELIMINAR",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Rol:{nombre_rol}"
    )


@router.get("/permisos", response_model=List[PermissionResponse])
async def listar_permisos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Listar todos los permisos disponibles"""
    permisos = db.query(Permiso).all()
    return [PermissionResponse.model_validate(p) for p in permisos]


@router.put("/roles/{rol_id}/permisos")
async def actualizar_permisos_rol(
    request: Request,
    rol_id: int,
    data: PermisoIdsUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Actualizar permisos de un rol"""
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    permiso_ids = data.permiso_ids
    
    # Validación: no quitar todos los permisos a rol esencial
    if rol.nombre == 'administrador' and not permiso_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol Admin debe tener al menos un permiso"
        )
    
    # Actualizar permisos
    rol.permisos = db.query(Permiso).filter(Permiso.id.in_(permiso_ids)).all()
    db.commit()
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="PERMISOS_ACTUALIZADOS",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Rol:{rol.nombre}"
    )
    
    return {"message": "Permisos actualizados", "rol_id": rol_id, "permisos_count": len(permiso_ids)}


@router.post("/permisos", response_model=PermissionResponse)
async def crear_permiso(
    request: Request,
    data: PermisoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Crear nuevo permiso"""
    permiso_existente = db.query(Permiso).filter(Permiso.codigo == data.codigo).first()
    if permiso_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un permiso con ese código"
        )
    
    permiso = Permiso(codigo=data.codigo, nombre=data.nombre, descripcion=data.descripcion)
    db.add(permiso)
    db.commit()
    db.refresh(permiso)
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="PERMISO_CREADO",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Permiso:{permiso.codigo}"
    )
    
    return PermissionResponse.model_validate(permiso)


@router.patch("/permisos/{permiso_id}", response_model=PermissionResponse)
async def actualizar_permiso(
    request: Request,
    permiso_id: int,
    data: PermisoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Actualizar permiso"""
    permiso = db.query(Permiso).filter(Permiso.id == permiso_id).first()
    if not permiso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permiso no encontrado"
        )
    
    if data.codigo is not None:
        existente = db.query(Permiso).filter(Permiso.codigo == data.codigo, Permiso.id != permiso_id).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro permiso con ese código"
            )
        permiso.codigo = data.codigo
    
    if data.nombre is not None:
        permiso.nombre = data.nombre
    
    if data.descripcion is not None:
        permiso.descripcion = data.descripcion
    
    db.commit()
    db.refresh(permiso)
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="PERMISO_ACTUALIZADO",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Permiso:{permiso.codigo}"
    )
    
    return PermissionResponse.model_validate(permiso)


@router.delete("/permisos/{permiso_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_permiso(
    request: Request,
    permiso_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Eliminar permiso"""
    permiso = db.query(Permiso).filter(Permiso.id == permiso_id).first()
    if not permiso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permiso no encontrado"
        )
    
    if permiso.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un permiso asignado a roles"
        )
    
    permiso_codigo = permiso.codigo
    db.delete(permiso)
    db.commit()
    
    log_audit(
        db=db,
        user_id=current_user.id,
        action="PERMISO_ELIMINADO",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Permiso:{permiso_codigo}"
    )


# Gestión de Bitácora
@router.get("/bitacora")
async def listar_bitacora(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    id_usuario: Optional[int] = None,
    entidad_afectada: Optional[str] = None,
    accion: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """CU20 - Listar eventos de bitácora con filtros"""
    logger.info(f"[BITACORA] Usuario={current_user.email}, filters: fecha_desde={fecha_desde}, fecha_hasta={fecha_hasta}, id_usuario={id_usuario}")
    
    try:
        query = db.query(Bitacora)
        logger.info(f"[BITACORA] Query base creada: {query}")
        
        # Convertir fechas de string a datetime si se proporcionan
        if fecha_desde:
            try:
                # Intentar parsear como fecha ISO (acepta "2026-04-18" o "2026-04-18T10:30:00")
                desde_dt = datetime.fromisoformat(fecha_desde)
                query = query.filter(Bitacora.fecha_hora >= desde_dt)
                logger.info(f"[BITACORA] Filtro fecha_desde: {desde_dt}")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="fecha_desde debe ser formato ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)"
                )
        
        if fecha_hasta:
            try:
                hasta_dt = datetime.fromisoformat(fecha_hasta)
                query = query.filter(Bitacora.fecha_hora <= hasta_dt)
                logger.info(f"[BITACORA] Filtro fecha_hasta: {hasta_dt}")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="fecha_hasta debe ser formato ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)"
                )
        
        if id_usuario:
            query = query.filter(Bitacora.id_usuario == id_usuario)
        if entidad_afectada:
            query = query.filter(Bitacora.entidad_afectada == entidad_afectada)
        if accion:
            query = query.filter(Bitacora.accion == accion)
        
        logger.info(f"[BITACORA] Filtros aplicados. Query: {query}")
        
        # Ordenar por fecha descendente
        query = query.order_by(Bitacora.fecha_hora.desc())
        
        # Obtener total SIN orden (PostgreSQL no permite ORDER BY en COUNT)
        total = query.order_by(None).with_entities(func.count()).scalar()
        logger.info(f"[BITACORA] Total registros: {total}")
        
        # Paginación
        offset = (page - 1) * page_size
        logs = query.offset(offset).limit(page_size).all()
        logger.info(f"[BITACORA] Registros obtenidos: {len(logs)}")
        
        return {
            'logs': [
                {
                    'id': l.id,
                    'fecha_hora': l.fecha_hora,
                    'usuario': l.usuario.email if l.usuario else None,
                    'accion': l.accion,
                    'ip_origen': l.ip_origen,
                    'entidad_afectada': l.entidad_afectada
                }
                for l in logs
            ],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total
            }
        }
    except Exception as e:
        logger.error(f"[BITACORA] Error: {type(e).__name__}: {e}", exc_info=True)
        raise


@router.get("/bitacora/exportar")
async def exportar_bitacora_csv(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """Exportar bitácora a CSV"""
    query = db.query(Bitacora)
    
    if fecha_desde:
        try:
            desde_dt = datetime.fromisoformat(fecha_desde)
            query = query.filter(Bitacora.fecha_hora >= desde_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fecha_desde debe ser formato ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)"
            )
    
    if fecha_hasta:
        try:
            hasta_dt = datetime.fromisoformat(fecha_hasta)
            query = query.filter(Bitacora.fecha_hora <= hasta_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fecha_hasta debe ser formato ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)"
            )
    
    logs = query.order_by(Bitacora.fecha_hora.desc()).all()
    
    # Usar punto y coma como delimitador (estándar en Excel latinoamérica)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    writer.writerow([
        'ID', 'Fecha/Hora', 'Usuario', 'Acción',
        'IP Origen', 'Entidad Afectada'
    ])
    
    for log in logs:
        writer.writerow([
            log.id,
            log.fecha_hora.isoformat(),
            log.usuario.email if log.usuario else 'Sistema',
            log.accion,
            log.ip_origen or '',
            log.entidad_afectada or ''
        ])
    
    output.seek(0)
    
    # BOM UTF-8 para que Excel detecte encoding y separador correctamente
    content = '\ufeff' + output.getvalue()
    
    return Response(
        content=content.encode('utf-8'),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=bitacora_export.csv"}
    )


# Gestión de Comisiones
@router.get("/comisiones")
async def listar_comisiones(
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """CU17 - Listar comisiones con filtros"""
    query = db.query(Comision).join(Comision.pago).join(Pago.solicitud)
    
    if fecha_desde:
        query = query.filter(Comision.fecha_registro >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Comision.fecha_registro <= fecha_hasta)
    if estado:
        query = query.filter(Comision.estado == estado)
    
    comisiones = query.all()
    
    return [
        {
            'id': c.id,
            'monto': float(c.monto),
            'porcentaje': float(c.porcentaje),
            'estado': c.estado,
            'fecha_registro': c.fecha_registro,
            'solicitud_id': c.pago.id_solicitud,
            'taller_id': c.pago.solicitud.id_taller,
            'monto_total_pago': float(c.pago.monto_total)
        }
        for c in comisiones
    ]


@router.get("/comisiones/resumen")
async def resumen_comisiones(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['administrador']))
):
    """CU17 - Totales de comisiones por taller"""
    from sqlalchemy import func
    
    resumen = db.query(
        Pago.solicitud.id_taller.label('taller_id'),
        func.sum(Comision.monto).label('total_comisiones'),
        func.count(Comision.id).label('cantidad_transacciones')
    ).join(
        Comision
    ).join(
        Pago
    ).filter(
        Comision.estado == 'Registrada'
    ).group_by(
        Pago.solicitud.id_taller
    ).all()
    
    return [
        {
            'taller_id': r.taller_id,
            'total_comisiones': float(r.total_comisiones) if r.total_comisiones else 0,
            'cantidad_transacciones': r.cantidad_transacciones
        }
        for r in resumen
    ]