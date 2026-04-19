from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Index
from app.database import Base
import enum


class EstadoSolicitud(enum.Enum):
    PENDIENTE = "Pendiente"
    EN_PROCESO = "En proceso"
    ATENDIDO = "Atendido"


class TipoEvidencia(enum.Enum):
    IMAGEN = "Imagen"
    AUDIO = "Audio"
    TEXTO = "Texto"


class Solicitud(Base):
    __tablename__ = 'solicitud'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(Integer, ForeignKey('cliente.id_usuario'), nullable=False)
    id_vehiculo = Column(Integer, ForeignKey('vehiculo.id'), nullable=True)
    fecha_reporte = Column(DateTime(timezone=True), server_default=func.now())
    latitud = Column(Numeric(9, 6), nullable=True)
    longitud = Column(Numeric(9, 6), nullable=True)
    estado = Column(
        ENUM(EstadoSolicitud, name='estado_solicitud'),
        default=EstadoSolicitud.PENDIENTE,
        nullable=False
    )
    tipo_problema = Column(String(50), nullable=True)
    prioridad = Column(String(20), nullable=True)
    resumen_ia = Column(Text, nullable=True)
    descripcion_texto = Column(Text, nullable=True)
    
    # Asignaciones (nullable - 0..1)
    id_taller = Column(Integer, ForeignKey('taller.id_usuario'), nullable=True)
    id_tecnico = Column(Integer, ForeignKey('tecnico.id'), nullable=True)
    
    # Relaciones
    cliente = relationship('Cliente', back_populates='solicitudes')
    vehiculo = relationship('Vehiculo', back_populates='solicitudes')
    taller = relationship('Taller', back_populates='solicitudes_atendidas', foreign_keys=[id_taller])
    tecnico = relationship('Tecnico', back_populates='solicitudes_asignadas')
    evidencias = relationship('Evidencia', back_populates='solicitud', cascade='all, delete-orphan')
    pago = relationship('Pago', back_populates='solicitud', uselist=False, cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_solicitud_estado', 'estado'),
        Index('idx_solicitud_fecha', 'fecha_reporte'),
        Index('idx_solicitud_cliente', 'id_cliente'),
    )


class Evidencia(Base):
    __tablename__ = 'evidencia'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_solicitud = Column(Integer, ForeignKey('solicitud.id'), nullable=False)
    tipo = Column(
        ENUM(TipoEvidencia, name='tipo_evidencia'),
        nullable=False
    )
    url_archivo = Column(String(255), nullable=False)
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    solicitud = relationship('Solicitud', back_populates='evidencias')