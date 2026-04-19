from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, ForeignKey, Table, Enum as SQLEnum
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.sql import func
from app.database import Base
import enum


# Tablas intermedias
usuario_rol = Table(
    'usuario_rol',
    Base.metadata,
    Column('id_usuario', Integer, ForeignKey('usuario.id'), primary_key=True),
    Column('id_rol', Integer, ForeignKey('rol.id'), primary_key=True)
)

rol_permiso = Table(
    'rol_permiso',
    Base.metadata,
    Column('id_rol', Integer, ForeignKey('rol.id'), primary_key=True),
    Column('id_permiso', Integer, ForeignKey('permiso.id'), primary_key=True)
)


class Usuario(Base):
    __tablename__ = 'usuario'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())
    activo = Column(Boolean, default=True)
    intentos_fallidos = Column(Integer, default=0)
    
    # Relaciones
    roles = relationship('Rol', secondary=usuario_rol, back_populates='usuarios')
    
    # Herencia: discriminator para Class Table Inheritance
    __mapper_args__ = {
        'polymorphic_identity': 'usuario',
        'polymorphic_on': 'tipo'
    }
    
    @declared_attr
    def tipo(cls):
        return Column(String(20))
    
    # Relación inversa para bitácora
    bitacoras = relationship('Bitacora', back_populates='usuario')


class Cliente(Usuario):
    __tablename__ = 'cliente'
    
    id_usuario = Column(Integer, ForeignKey('usuario.id'), primary_key=True)
    telefono = Column(String(20), nullable=True)
    direccion_default = Column(Text, nullable=True)
    
    # Relaciones
    vehiculos = relationship('Vehiculo', back_populates='cliente', cascade='all, delete-orphan')
    solicitudes = relationship('Solicitud', back_populates='cliente', cascade='all, delete-orphan')
    
    __mapper_args__ = {
        'polymorphic_identity': 'cliente',
    }


class Taller(Usuario):
    __tablename__ = 'taller'
    
    id_usuario = Column(Integer, ForeignKey('usuario.id'), primary_key=True)
    nombre_comercial = Column(String(150), nullable=False)
    direccion = Column(Text, nullable=True)
    latitud = Column(Numeric(9, 6), nullable=True)
    longitud = Column(Numeric(9, 6), nullable=True)
    disponible = Column(Boolean, default=True)
    calificacion = Column(Numeric(3, 2), default=0.00)
    
    # Relaciones
    tecnicos = relationship('Tecnico', back_populates='taller', cascade='all, delete-orphan')
    solicitudes_atendidas = relationship('Solicitud', back_populates='taller', foreign_keys='Solicitud.id_taller')
    
    __mapper_args__ = {
        'polymorphic_identity': 'taller',
    }


class Rol(Base):
    __tablename__ = 'rol'
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    
    # Relaciones
    usuarios = relationship('Usuario', secondary=usuario_rol, back_populates='roles')
    permisos = relationship('Permiso', secondary=rol_permiso, back_populates='roles')


class Permiso(Base):
    __tablename__ = 'permiso'
    
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(250), nullable=False)
    
    # Relaciones
    roles = relationship('Rol', secondary=rol_permiso, back_populates='permisos')


class Tecnico(Base):
    __tablename__ = 'tecnico'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_taller = Column(Integer, ForeignKey('taller.id_usuario'), nullable=False)
    nombre = Column(String(100), nullable=False)
    especialidad = Column(String(100), nullable=True)
    disponible = Column(Boolean, default=True)
    
    # Relaciones
    taller = relationship('Taller', back_populates='tecnicos')
    solicitudes_asignadas = relationship('Solicitud', back_populates='tecnico')


class Vehiculo(Base):
    __tablename__ = 'vehiculo'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(Integer, ForeignKey('cliente.id_usuario'), nullable=False)
    marca = Column(String(50), nullable=False)
    modelo = Column(String(50), nullable=False)
    anio = Column(Integer, nullable=False)
    placa = Column(String(20), unique=True, nullable=False)
    
    # Relaciones
    cliente = relationship('Cliente', back_populates='vehiculos')
    solicitudes = relationship('Solicitud', back_populates='vehiculo')


class Bitacora(Base):
    __tablename__ = 'bitacora'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuario.id'), nullable=True)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    accion = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    ip_origen = Column(String(45), nullable=True)
    entidad_afectada = Column(String(100), nullable=True)
    
    # Relaciones
    usuario = relationship('Usuario', back_populates='bitacoras')

    from app.modules.solicitudes.models import Solicitud