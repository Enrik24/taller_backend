from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import cloudinary.uploader
from app.config import settings

from app.database import get_db
from app.dependencies import get_current_user, get_current_cliente, get_current_taller
from app.modules.solicitudes.schemas import (
    SolicitudCreate, SolicitudResponse, SolicitudDisponibleResponse,
    TallerAsignadoResponse, EvidenciaResponse, EstadoSolicitudEnum, TipoEvidenciaEnum
)
from app.modules.usuarios.models import Usuario, Cliente, Taller, Tecnico
from app.modules.solicitudes.services import SolicitudService
from app.modules.solicitudes.models import Solicitud
from app.modules.talleres.services import TallerService
from app.core.logging_service import log_audit

from app.modules.notificaciones.services import NotificationService

router = APIRouter(prefix="/api/solicitudes", tags=["Solicitudes"])


def upload_to_cloudinary(file: UploadFile, folder: str) -> str:
    """Función reutilizable para subir archivos a Cloudinary"""
    result = cloudinary.uploader.upload(
        file.file,
        folder=f"emergencias/{folder}",
        resource_type="auto"  # Detecta automáticamente imagen/audio
    )
    return result['secure_url']


@router.post("/", response_model=SolicitudResponse, status_code=status.HTTP_201_CREATED)
async def reportar_emergencia(
    request: Request,
    descripcion_texto: Optional[str] = Form(None),
    id_vehiculo: Optional[int] = Form(None),
    latitud: Optional[float] = Form(None),
    longitud: Optional[float] = Form(None),
    tipo_problema: Optional[str] = Form(None),
    prioridad: Optional[str] = Form(None),
    archivos: List[UploadFile] = File([]),
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """CU04 - Reportar Emergencia con archivos multimedia"""
    service = SolicitudService(db)
    
    # Crear solicitud
    solicitud_data = SolicitudCreate(
        descripcion_texto=descripcion_texto,
        id_vehiculo=id_vehiculo,
        latitud=latitud,
        longitud=longitud,
        tipo_problema=tipo_problema,
        prioridad=prioridad
    )
    
    solicitud = service.create_solicitud(current_cliente.id_usuario, solicitud_data)
    
    # Procesar archivos y subir a Cloudinary
    for archivo in archivos:
        if archivo.filename:
            try:
                url = upload_to_cloudinary(archivo, f"solicitud_{solicitud.id}")
                # Determinar tipo usando el enum
                content_type = archivo.content_type or ""
                if content_type.startswith("image/"):
                    tipo = TipoEvidenciaEnum.IMAGEN.value
                elif content_type.startswith("audio/"):
                    tipo = TipoEvidenciaEnum.AUDIO.value
                else:
                    tipo = TipoEvidenciaEnum.TEXTO.value
                
                service.add_evidencia(solicitud.id, tipo, url)
            except Exception as e:
                # Log error pero continuar con la solicitud
                print(f"Error subiendo archivo {archivo.filename}: {e}")
    
    db.commit()
    db.refresh(solicitud)
    
    # TODO: Notificar a talleres cercanos (placeholder)
    # notification_service.notify_nearby_tallers(solicitud)
    
    return SolicitudResponse.model_validate(solicitud)


@router.get("/mis-solicitudes", response_model=List[SolicitudResponse])
async def get_mis_solicitudes(
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """CU05 - Consultar estado de solicitudes del cliente"""
    service = SolicitudService(db)
    solicitudes = service.get_solicitudes_by_cliente(current_cliente.id_usuario)
    return [SolicitudResponse.model_validate(s) for s in solicitudes]


@router.get("/{solicitud_id}", response_model=SolicitudResponse)
async def get_solicitud_detalle(
    solicitud_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener detalle completo de una solicitud"""
    service = SolicitudService(db)
    solicitud = service.get_solicitud_by_id(solicitud_id)
    
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    # Verificar permisos: cliente dueño o taller asignado
    if solicitud.id_cliente != current_user.id:
        # Verificar si es taller asignado
        is_taller_asignado = (hasattr(current_user, 'taller') and 
                             current_user.id == solicitud.id_taller)
        if not is_taller_asignado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para ver esta solicitud"
            )
    
    return SolicitudResponse.model_validate(solicitud)


@router.get("/{solicitud_id}/taller-asignado", response_model=Optional[TallerAsignadoResponse])
async def get_taller_asignado(
    solicitud_id: int,
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """CU06 - Ver taller asignado y tiempo estimado"""
    service = SolicitudService(db)
    solicitud = service.get_solicitud_by_id(solicitud_id)
    
    if not solicitud or solicitud.id_cliente != current_cliente.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    if not solicitud.id_taller:
        return None
    
    taller = db.query(Taller).filter(Taller.id_usuario == solicitud.id_taller).first()
    if not taller:
        return None
    
    # Obtener teléfono del usuario padre
    usuario_taller = db.query(Usuario).filter(Usuario.id == taller.id_usuario).first()
    
    # TODO: Calcular tiempo estimado real basado en distancia y tráfico
    tiempo_estimado = None  # Placeholder
    
    return TallerAsignadoResponse(
        id=taller.id_usuario,
        nombre_comercial=taller.nombre_comercial,
        calificacion=float(taller.calificacion) if taller.calificacion else 0.0,
        direccion=taller.direccion,
        latitud=float(taller.latitud) if taller.latitud else None,
        longitud=float(taller.longitud) if taller.longitud else None,
        telefono=getattr(usuario_taller, 'telefono', None),
        tiempo_estimado_min=tiempo_estimado
    )


@router.get("/disponibles", response_model=List[SolicitudDisponibleResponse])
async def get_solicitudes_disponibles(
    current_taller: Taller = Depends(get_current_taller),
    db: Session = Depends(get_db)
):
    """CU09 - Visualizar solicitudes disponibles para el taller"""
    service = SolicitudService(db)
    solicitudes = service.get_solicitudes_pendientes_disponibles()
    
    results = []
    for s in solicitudes:
        # TODO: Calcular distancia real usando fórmula Haversine
        distancia = None  # Placeholder
        
        # Asegurar que el cliente tiene atributo nombre
        cliente_nombre = s.cliente.nombre if s.cliente and hasattr(s.cliente, 'nombre') else "Cliente no especificado"
        vehiculo_info = f"{s.vehiculo.marca} {s.vehiculo.modelo} ({s.vehiculo.placa})" if s.vehiculo else "No especificado"
        
        results.append(SolicitudDisponibleResponse(
            id=s.id,
            cliente_nombre=cliente_nombre,
            vehiculo_info=vehiculo_info,
            distancia_km=distancia,
            tipo_problema=s.tipo_problema,
            prioridad=s.prioridad,
            fecha_reporte=s.fecha_reporte
        ))
    
    return results

@router.post("/{solicitud_id}/aceptar", response_model=SolicitudResponse)
async def aceptar_solicitud(
    solicitud_id: int,
    current_taller: Taller = Depends(get_current_taller),
    db: Session = Depends(get_db)
):
    """CU11 - Aceptar solicitud (validar técnico disponible)"""
    service = SolicitudService(db)
    taller_service = TallerService(db)
    
    solicitud = service.get_solicitud_by_id(solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada")
        
    if solicitud.estado != EstadoSolicitudEnum.PENDIENTE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La solicitud no está en estado Pendiente")
        
    if not taller_service.has_available_tecnico(current_taller.id_usuario):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El taller debe tener al menos 1 técnico disponible para aceptar solicitudes")
        
    # Asignar taller y cambiar estado a "En proceso"
    solicitud = service.asignar_taller(solicitud, current_taller.id_usuario)
    db.commit()
    db.refresh(solicitud)
    
    # 🔔 NOTIFICACIÓN PUSH AL CLIENTE
    notif_service = NotificationService(db)
    await notif_service.notify_cliente_solicitud_aceptada(solicitud)
    
    return SolicitudResponse.model_validate(solicitud)

@router.post("/{solicitud_id}/rechazar")
async def rechazar_solicitud(
    solicitud_id: int,
    motivo: Optional[str] = Form(None),
    current_taller: Taller = Depends(get_current_taller),
    db: Session = Depends(get_db)
):
    """CU11 - Rechazar solicitud"""
    service = SolicitudService(db)
    
    solicitud = service.get_solicitud_by_id(solicitud_id)
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    # Validar que esté pendiente y asignada a este taller
    if solicitud.estado != EstadoSolicitudEnum.PENDIENTE.value or solicitud.id_taller != current_taller.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede rechazar esta solicitud"
        )
    
    solicitud = service.rechazar_solicitud(solicitud, motivo)
    
    db.commit()
    
    return {"message": "Solicitud rechazada exitosamente"}


@router.put("/{solicitud_id}/estado", response_model=SolicitudResponse)
async def actualizar_estado_servicio(
    solicitud_id: int,
    nuevo_estado: EstadoSolicitudEnum,
    current_taller: Taller = Depends(get_current_taller),
    db: Session = Depends(get_db)
):
    """CU13 - Actualizar estado del servicio con máquina de estados"""
    service = SolicitudService(db)
    
    solicitud = service.get_solicitud_by_id(solicitud_id)
    if not solicitud:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada")
        
    if solicitud.id_taller != current_taller.id_usuario:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para actualizar esta solicitud")
        
    estado_actual = solicitud.estado
    nuevo_estado_str = nuevo_estado.value
    
    transiciones_permitidas = {
        EstadoSolicitudEnum.PENDIENTE.value: [EstadoSolicitudEnum.EN_PROCESO.value, EstadoSolicitudEnum.ATENDIDO.value],
        EstadoSolicitudEnum.EN_PROCESO.value: [EstadoSolicitudEnum.ATENDIDO.value],
        EstadoSolicitudEnum.ATENDIDO.value: []
    }
    
    if nuevo_estado_str not in transiciones_permitidas.get(estado_actual, []):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Transición de estado inválida: no se puede pasar de {estado_actual} a {nuevo_estado_str}")
        
    solicitud.estado = nuevo_estado_str
    db.commit()
    db.refresh(solicitud)
    
    # 🔔 NOTIFICACIÓN PUSH DE CAMBIO DE ESTADO
    notif_service = NotificationService(db)
    await notif_service.notify_estado_actualizado(solicitud)
    
    return SolicitudResponse.model_validate(solicitud)