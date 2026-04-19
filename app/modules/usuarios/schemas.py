from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RoleEnum(str, Enum):
    CLIENTE = "cliente"
    TALLER = "taller"
    ADMIN = "admin"


# Schemas base
class UserBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr


class UserCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    tipo: RoleEnum
    
    # Campos opcionales según tipo
    telefono: Optional[str] = Field(None, max_length=20)
    direccion_default: Optional[str] = None
    nombre_comercial: Optional[str] = Field(None, max_length=150)
    direccion: Optional[str] = None
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v


class UserUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    telefono: Optional[str] = Field(None, max_length=20)
    direccion_default: Optional[str] = None
    nombre_comercial: Optional[str] = Field(None, max_length=150)
    direccion: Optional[str] = None
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)


class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre: str


class TokenData(BaseModel):
    sub: Optional[int] = None
    email: Optional[str] = None
    rol: Optional[str] = None


# Schemas de respuesta
class RoleResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    
    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    accion: str
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    fecha_registro: datetime
    activo: bool
    roles: List[RoleResponse] = []
    
    class Config:
        from_attributes = True


class ClienteResponse(UserResponse):
    tipo: str = "cliente"
    telefono: Optional[str] = None
    direccion_default: Optional[str] = None
    
    class Config:
        from_attributes = True


class TallerResponse(UserResponse):
    tipo: str = "taller"
    nombre_comercial: str
    direccion: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    disponible: bool = True
    calificacion: float = 0.00
    
    class Config:
        from_attributes = True


# Vehículo
class VehiculoBase(BaseModel):
    marca: str = Field(..., max_length=50)
    modelo: str = Field(..., max_length=50)
    anio: int = Field(..., ge=1900, le=2100)
    placa: str = Field(..., max_length=20)


class VehiculoCreate(VehiculoBase):
    pass


class VehiculoUpdate(BaseModel):
    marca: Optional[str] = Field(None, max_length=50)
    modelo: Optional[str] = Field(None, max_length=50)
    anio: Optional[int] = Field(None, ge=1900, le=2100)
    placa: Optional[str] = Field(None, max_length=20)


class VehiculoResponse(BaseModel):
    id: int
    marca: str
    modelo: str
    anio: int
    placa: str
    
    class Config:
        from_attributes = True


# Técnico
class TecnicoBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    especialidad: Optional[str] = Field(None, max_length=100)
    disponible: bool = True


class TecnicoCreate(TecnicoBase):
    pass


class TecnicoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, max_length=100)
    especialidad: Optional[str] = Field(None, max_length=100)
    disponible: Optional[bool] = None


class TecnicoResponse(BaseModel):
    id: int
    nombre: str
    especialidad: Optional[str]
    disponible: bool
    
    class Config:
        from_attributes = True