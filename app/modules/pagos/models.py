from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.database import Base
from app.config import settings


class Pago(Base):
    __tablename__ = 'pago'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_solicitud = Column(Integer, ForeignKey('solicitud.id'), unique=True, nullable=False)
    monto_total = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(String(50), nullable=False)
    estado = Column(String(50), nullable=False)  # 'Pendiente', 'Pagado', 'Completado', 'Fallido'
    fecha_pago = Column(DateTime(timezone=True), server_default=func.now())
    comprobante_url = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(100), nullable=True)
    stripe_customer_id = Column(String(100), nullable=True)
    
    # Relaciones
    solicitud = relationship('Solicitud', back_populates='pago')
    comision = relationship('Comision', back_populates='pago', uselist=False, cascade='all, delete-orphan')


class Comision(Base):
    __tablename__ = 'comision'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_pago = Column(Integer, ForeignKey('pago.id'), unique=True, nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    porcentaje = Column(Numeric(5, 2), nullable=False)
    estado = Column(String(50), default='Pendiente')
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    pago = relationship('Pago', back_populates='comision')


# Event listeners para comisión automática (Regla de negocio #4)
@event.listens_for(Pago, 'after_insert')
def receive_after_insert(mapper, connection, target):
    """Crear comisión automáticamente al crear un pago"""
    _create_comision_if_paid(target, connection)


@event.listens_for(Pago, 'after_update')
def receive_after_update(mapper, connection, target):
    """Crear comisión automáticamente al actualizar pago a estado pagado"""
    _create_comision_if_paid(target, connection)


def _create_comision_if_paid(pago, connection):
    """Lógica atómica para crear comisión cuando el pago está completado"""
    if pago.estado in ['Pagado', 'Completado']:
        # Verificar si ya existe comisión
        existing = connection.execute(
            Comision.__table__.select().where(Comision.id_pago == pago.id)
        ).first()
        
        if not existing:
            # Calcular 10% del monto total
            monto_comision = float(pago.monto_total) * (settings.COMMISSION_PERCENTAGE / 100)
            
            # Insertar comisión directamente vía connection (fuera de sesión SQLAlchemy)
            connection.execute(
                Comision.__table__.insert().values(
                    id_pago=pago.id,
                    monto=monto_comision,
                    porcentaje=settings.COMMISSION_PERCENTAGE,
                    estado='Registrada',
                    fecha_registro=func.now()
                )
            )