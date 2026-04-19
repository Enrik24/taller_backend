from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EstadoSolicitudEnum(str, Enum):
    PENDIENTE = "Pendiente"
    EN_PROCESO = "En proceso"
    ATENDIDO = "Atendido"


class TipoEvidenciaEnum(str, Enum):
    IMAGEN = "Imagen"
    AUDIO = "Audio"
    TEXTO = "Texto"


# Solicitud
class SolicitudBase(BaseModel):
    descripcion_texto: Optional[str] = Field(None, max_length=1000)
    id_vehiculo: Optional[int] = None
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)
    tipo_problema: Optional[str] = Field(None, max_length=50)
    prioridad: Optional[str] = Field(None, max_length=20)


class SolicitudCreate(SolicitudBase):
    pass


class SolicitudUpdate(BaseModel):
    estado: Optional[EstadoSolicitudEnum] = None
    id_taller: Optional[int] = None
    id_tecnico: Optional[int] = None
    tipo_problema: Optional[str] = Field(None, max_length=50)
    prioridad: Optional[str] = Field(None, max_length=20)


class EvidenciaBase(BaseModel):
    tipo: TipoEvidenciaEnum
    url_archivo: str


class EvidenciaResponse(BaseModel):
    id: int
    tipo: str
    url_archivo: str
    fecha_subida: datetime
    
    class Config:
        from_attributes = True


class VehiculoMiniResponse(BaseModel):
    id: int
    marca: str
    modelo: str
    anio: int
    placa: str
    
    class Config:
        from_attributes = True


class TallerMiniResponse(BaseModel):
    id: int
    nombre_comercial: str
    calificacion: float
    direccion: Optional[str]
    
    class Config:
        from_attributes = True


class SolicitudResponse(BaseModel):
    id: int
    id_cliente: int
    fecha_reporte: datetime
    latitud: Optional[float]
    longitud: Optional[float]
    estado: str
    tipo_problema: Optional[str]
    prioridad: Optional[str]
    resumen_ia: Optional[str]
    descripcion_texto: Optional[str]
    id_taller: Optional[int]
    id_tecnico: Optional[int]
    evidencias: List[EvidenciaResponse] = []
    vehiculo: Optional[VehiculoMiniResponse] = None
    taller: Optional[TallerMiniResponse] = None
    
    class Config:
        from_attributes = True


# Respuestas específicas
class SolicitudDisponibleResponse(BaseModel):
    id: int
    cliente_nombre: str
    vehiculo_info: str  # "Marca Modelo (Placa)"
    distancia_km: Optional[float]
    tipo_problema: Optional[str]
    prioridad: Optional[str]
    fecha_reporte: datetime
    
    class Config:
        from_attributes = True


class TallerAsignadoResponse(BaseModel):
    id: int
    nombre_comercial: str
    calificacion: float
    direccion: Optional[str]
    latitud: Optional[float]
    longitud: Optional[float]
    telefono: Optional[str]
    tiempo_estimado_min: Optional[int] = None
    
    class Config:
        from_attributes = True