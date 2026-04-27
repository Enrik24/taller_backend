from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class NotificacionToken(Base):
    """Tokens FCM para notificaciones push"""
    __tablename__ = 'notificacion_token'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuario.id'), nullable=False)
    token_fcm = Column(String(255), nullable=False, unique=True)
    plataforma = Column(String(20))  # 'android', 'ios', 'web'
    activo = Column(Boolean, default=True)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())
    fecha_ultima_uso = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    usuario = relationship('Usuario', back_populates='tokens_notificacion')


class PreferenciaNotificacion(Base):
    """Preferencias de notificación por usuario"""
    __tablename__ = 'preferencia_notificacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuario.id'), nullable=False, unique=True)
    actualizaciones_servicio = Column(Boolean, default=True)
    promociones = Column(Boolean, default=False)
    estado_pago = Column(Boolean, default=True)
    recordatorios = Column(Boolean, default=True)
    fecha_actualizacion = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relaciones
    usuario = relationship('Usuario')


class HistorialNotificacion(Base):
    """Historial de notificaciones enviadas"""
    __tablename__ = 'historial_notificacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuario.id'), nullable=True)
    id_solicitud = Column(Integer, ForeignKey('solicitud.id'), nullable=True)
    tipo = Column(String(20))  # 'Push', 'SMS', 'Email'
    titulo = Column(String(100), nullable=False)
    contenido = Column(Text, nullable=False)
    estado = Column(String(20))  # 'Enviada', 'Leida', 'Fallida'
    fecha_envio = Column(DateTime(timezone=True), server_default=func.now())
    error_detalle = Column(Text, nullable=True)

    # Relaciones
    usuario = relationship('Usuario', back_populates='historial_notificaciones')
    solicitud = relationship('Solicitud', back_populates='historial_notificaciones')


# Agregar relación en Usuario (en usuarios/models.py):
# Usuario.tokens_notificacion = relationship('NotificacionToken', back_populates='usuario', cascade='all, delete-orphan')
# Usuario.historial_notificaciones = relationship('HistorialNotificacion', back_populates='usuario')

# Agregar relación en Solicitud (en solicitudes/models.py):
# Solicitud.historial_notificaciones = relationship('HistorialNotificacion', back_populates='solicitud')