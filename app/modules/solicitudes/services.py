from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.modules.solicitudes.models import Solicitud, Evidencia, EstadoSolicitud
from app.modules.solicitudes.schemas import SolicitudCreate, SolicitudUpdate
from app.core.exceptions import InvalidStateTransitionError, VALID_STATE_TRANSITIONS
from app.core.logging_service import log_audit


class SolicitudService:
    # Máquina de estados
    VALID_TRANSITIONS = {
        EstadoSolicitud.PENDIENTE: [EstadoSolicitud.EN_PROCESO],
        EstadoSolicitud.EN_PROCESO: [EstadoSolicitud.ATENDIDO],
        EstadoSolicitud.ATENDIDO: []  # Terminal
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_solicitud(self, cliente_id: int, solicitud_data: SolicitudCreate) -> Solicitud:
        """Crear nueva solicitud de emergencia"""
        solicitud = Solicitud(
            id_cliente=cliente_id,
            id_vehiculo=solicitud_data.id_vehiculo,
            latitud=solicitud_data.latitud,
            longitud=solicitud_data.longitud,
            estado=EstadoSolicitud.PENDIENTE,
            tipo_problema=solicitud_data.tipo_problema,
            prioridad=solicitud_data.prioridad,
            descripcion_texto=solicitud_data.descripcion_texto
        )
        self.db.add(solicitud)
        self.db.flush()  # Obtener ID
        
        log_audit(
            db=self.db,
            user_id=cliente_id,
            action="SOLICITUD_CREADA",
            description=f"Nueva emergencia reportada: ID {solicitud.id}",
            ip_origen=None,
            entidad_afectada=f"Solicitud:{solicitud.id}"
        )
        
        return solicitud
    
    def add_evidencia(self, solicitud_id: int, tipo: str, url_archivo: str) -> Evidencia:
        """Agregar evidencia a una solicitud"""
        evidencia = Evidencia(
            id_solicitud=solicitud_id,
            tipo=tipo,
            url_archivo=url_archivo
        )
        self.db.add(evidencia)
        return evidencia
    
    def get_solicitud_by_id(self, solicitud_id: int) -> Optional[Solicitud]:
        return self.db.query(Solicitud).filter(Solicitud.id == solicitud_id).first()
    
    def get_solicitudes_by_cliente(self, cliente_id: int) -> List[Solicitud]:
        return self.db.query(Solicitud).filter(
            Solicitud.id_cliente == cliente_id
        ).order_by(Solicitud.fecha_reporte.desc()).all()
    
    def get_solicitudes_pendientes_disponibles(self) -> List[Solicitud]:
        """Obtener solicitudes pendientes sin taller asignado (para vista de talleres)"""
        return self.db.query(Solicitud).filter(
            Solicitud.estado == EstadoSolicitud.PENDIENTE,
            Solicitud.id_taller == None
        ).order_by(
            # Prioridad: alta primero, luego por fecha
            Solicitud.prioridad.desc(),
            Solicitud.fecha_reporte.asc()
        ).all()
    
    def validate_state_transition(self, current_state: EstadoSolicitud, new_state: EstadoSolicitud):
        """Validar transición de estado según máquina de estados"""
        if new_state not in self.VALID_TRANSITIONS.get(current_state, []):
            raise InvalidStateTransitionError(current_state.value, new_state.value)
    
    def update_estado(self, solicitud: Solicitud, nuevo_estado: EstadoSolicitud) -> Solicitud:
        """Actualizar estado de solicitud con validación de transición"""
        # Validar transición
        self.validate_state_transition(solicitud.estado, nuevo_estado)
        
        # No permitir modificar si ya está atendido
        if solicitud.estado == EstadoSolicitud.ATENDIDO:
            raise InvalidStateTransitionError(
                solicitud.estado.value, nuevo_estado.value
            )
        
        old_state = solicitud.estado
        solicitud.estado = nuevo_estado
        
        log_audit(
            db=self.db,
            user_id=solicitud.id_cliente,
            action="ESTADO_SOLICITUD_ACTUALIZADO",
            description=f"Solicitud {solicitud.id}: {old_state.value} → {nuevo_estado.value}",
            ip_origen=None,
            entidad_afectada=f"Solicitud:{solicitud.id}"
        )
        
        return solicitud
    
    def asignar_taller(self, solicitud: Solicitud, taller_id: int, tecnico_id: Optional[int] = None) -> Solicitud:
        """Asignar taller y opcionalmente técnico a una solicitud"""
        if solicitud.estado != EstadoSolicitud.PENDIENTE:
            raise HTTPException(
                status_code=400,
                detail="Solo se pueden asignar solicitudes en estado Pendiente"
            )
        
        solicitud.id_taller = taller_id
        solicitud.id_tecnico = tecnico_id
        solicitud.estado = EstadoSolicitud.EN_PROCESO
        
        log_audit(
            db=self.db,
            user_id=taller_id,
            action="SOLICITUD_ACEPTADA",
            description=f"Taller {taller_id} aceptó solicitud {solicitud.id}",
            ip_origen=None,
            entidad_afectada=f"Solicitud:{solicitud.id}"
        )
        
        return solicitud
    
    def rechazar_solicitud(self, solicitud: Solicitud, motivo: Optional[str] = None) -> Solicitud:
        """Rechazar una solicitud (vuelve al pool disponible)"""
        # Solo se puede rechazar si está pendiente y asignada
        if solicitud.estado != EstadoSolicitud.PENDIENTE or solicitud.id_taller is None:
            raise HTTPException(
                status_code=400,
                detail="Solo se pueden rechazar solicitudes pendientes asignadas"
            )
        
        # Desasignar taller pero mantener en pendiente
        solicitud.id_taller = None
        solicitud.id_tecnico = None
        
        log_audit(
            db=self.db,
            user_id=solicitud.id_taller,  # ID del taller que rechazó
            action="SOLICITUD_RECHAZADA",
            description=f"Solicitud {solicitud.id} rechazada: {motivo or 'Sin motivo'}",
            ip_origen=None,
            entidad_afectada=f"Solicitud:{solicitud.id}"
        )
        
        return solicitud