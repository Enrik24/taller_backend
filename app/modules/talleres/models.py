# Los modelos de Taller ya están definidos en usuarios/models.py
# Este archivo puede contener modelos específicos de dominio de talleres si se requieren
from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class EspecialidadTaller(Base):
    """Tabla para especialidades de talleres (opcional, para filtrado avanzado)"""
    __tablename__ = 'especialidad_taller'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_taller = Column(Integer, ForeignKey('taller.id_usuario'), nullable=False)
    especialidad = Column(String(100), nullable=False)
    nivel_experiencia = Column(String(20), default='Intermedio')  # Básico, Intermedio, Experto
    
    # Relaciones
    taller = relationship('Taller', foreign_keys=[id_taller])


# Agregar relación inversa en Taller (se haría en usuarios/models.py o vía back_populates)
# Taller.especialidades = relationship('EspecialidadTaller', back_populates='taller', cascade='all, delete-orphan')