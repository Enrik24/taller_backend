from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
import csv
import io

from app.database import get_db
from app.dependencies import require_role, get_current_user
from app.modules.usuarios.models import Usuario, Rol, Permiso, Bitacora
from app.modules.usuarios.schemas import UserResponse, RoleResponse, PermissionResponse
from app.modules.pagos.models import Comision, Pago

router = APIRouter(prefix="/api/admin", tags=["Administración"])


# Gestión de Usuarios
@router.get("/usuarios", response_model=List[UserResponse])
async def listar_usuarios(
    rol: Optional[str] = None,
    activo: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
):
    """CU18 - Listar usuarios con filtros y paginación"""
    query = db.query(Usuario)
    
    if rol:
        query = query.join(Usuario.roles).filter(Rol.nombre == rol)
    if activo is not None:
        query = query.filter(Usuario.activo == activo)
    
    # Paginación
    offset = (page - 1) * page_size
    usuarios = query.offset(offset).limit(page_size).all()
    
    return [UserResponse.model_validate(u) for u in usuarios]


@router.get("/usuarios/{usuario_id}", response_model=UserResponse)
async def detalle_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
):
    """Obtener detalle de usuario"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return UserResponse.model_validate(usuario)


@router.put("/usuarios/{usuario_id}/estado")
async def actualizar_estado_usuario(
    usuario_id: int,
    activo: bool,
    confirmacion: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
):
    """Activar/desactivar usuario"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Validación de seguridad: no desactivar último admin
    if not activo and usuario.roles:
        admin_role = db.query(Rol).filter(Rol.nombre == 'admin').first()
        if admin_role in usuario.roles:
            admins_activos = db.query(Usuario).join(Usuario.roles).filter(
                Rol.nombre == 'admin',
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
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
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
    # TODO: Considerar anonimización de datos personales según GDPR
    
    db.commit()


# Gestión de Roles y Permisos
@router.get("/roles", response_model=List[RoleResponse])
async def listar_roles(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
):
    """CU19 - Listar roles con sus permisos"""
    roles = db.query(Rol).all()
    return [RoleResponse.model_validate(r) for r in roles]


@router.get("/permisos", response_model=List[PermissionResponse])
async def listar_permisos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
):
    """Listar todos los permisos disponibles"""
    permisos = db.query(Permiso).all()
    return [PermissionResponse.model_validate(p) for p in permisos]


@router.put("/roles/{rol_id}/permisos")
async def actualizar_permisos_rol(
    rol_id: int,
    permiso_ids: List[int],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
):
    """Actualizar permisos de un rol"""
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Validación: no quitar todos los permisos a rol esencial
    if rol.nombre == 'admin' and not permiso_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol Admin debe tener al menos un permiso"
        )
    
    # Actualizar permisos
    rol.permisos = db.query(Permiso).filter(Permiso.id.in_(permiso_ids)).all()
    db.commit()
    
    return {"message": "Permisos actualizados", "rol_id": rol_id, "permisos_count": len(permiso_ids)}


# Gestión de Bitácora
@router.get("/bitacora")
async def listar_bitacora(
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    id_usuario: Optional[int] = None,
    entidad_afectada: Optional[str] = None,
    accion: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
):
    """CU20 - Listar eventos de bitácora con filtros"""
    query = db.query(Bitacora)
    
    if fecha_desde:
        query = query.filter(Bitacora.fecha_hora >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Bitacora.fecha_hora <= fecha_hasta)
    if id_usuario:
        query = query.filter(Bitacora.id_usuario == id_usuario)
    if entidad_afectada:
        query = query.filter(Bitacora.entidad_afectada == entidad_afectada)
    if accion:
        query = query.filter(Bitacora.accion == accion)
    
    # Ordenar por fecha descendente
    query = query.order_by(Bitacora.fecha_hora.desc())
    
    # Paginación
    offset = (page - 1) * page_size
    logs = query.offset(offset).limit(page_size).all()
    
    return {
        'logs': [
            {
                'id': l.id,
                'fecha_hora': l.fecha_hora,
                'usuario': l.usuario.email if l.usuario else None,
                'accion': l.accion,
                'descripcion': l.descripcion,
                'ip_origen': l.ip_origen,
                'entidad_afectada': l.entidad_afectada
            }
            for l in logs
        ],
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': query.with_entities(func.count()).scalar()
        }
    }


@router.post("/bitacora/exportar")
async def exportar_bitacora_csv(
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
):
    """Exportar bitácora a CSV"""
    query = db.query(Bitacora)
    
    if fecha_desde:
        query = query.filter(Bitacora.fecha_hora >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Bitacora.fecha_hora <= fecha_hasta)
    
    logs = query.order_by(Bitacora.fecha_hora.desc()).all()
    
    # Generar CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        'ID', 'Fecha/Hora', 'Usuario', 'Acción', 
        'Descripción', 'IP Origen', 'Entidad Afectada'
    ])
    
    # Datos
    for log in logs:
        writer.writerow([
            log.id,
            log.fecha_hora.isoformat(),
            log.usuario.email if log.usuario else 'Sistema',
            log.accion,
            log.descripcion or '',
            log.ip_origen or '',
            log.entidad_afectada or ''
        ])
    
    # Preparar respuesta de descarga
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bitacora_export.csv"}
    )


# Gestión de Comisiones
@router.get("/comisiones")
async def listar_comisiones(
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(['admin']))
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
    current_user: Usuario = Depends(require_role(['admin']))
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