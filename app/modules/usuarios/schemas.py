from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class RoleEnum(str, Enum):
    CLIENTE = "cliente"
    TALLER = "taller"
    ADMIN = "administrador"


class LoginRequest(BaseModel):
    username: EmailStr
    password: str


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
    rol_ids: Optional[List[int]] = []
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v


class UserUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(None, max_length=20)
    direccion_default: Optional[str] = None
    nombre_comercial: Optional[str] = Field(None, max_length=150)
    direccion: Optional[str] = None
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)
    password: Optional[str] = Field(None, min_length=8)


class UserRolesUpdate(BaseModel):
    rol_ids: List[int]


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
    permisos: List[PermissionResponse] = []

    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    fecha_registro: datetime
    activo: bool
    roles: List[RoleResponse] = []
    tipo: str = "usuario"
    
    class Config:
        from_attributes = True


class ClienteResponse(UserResponse):
    tipo: Literal["cliente"] = "cliente"
    telefono: Optional[str] = None
    direccion_default: Optional[str] = None
    
    class Config:
        from_attributes = True


class TallerResponse(UserResponse):
    tipo: Literal["taller"] = "taller"
    nombre_comercial: Optional[str] = None
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


# Roles
class RoleCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=255)
    permiso_ids: Optional[List[int]] = []


class RoleUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=255)


class PermisoIdsUpdate(BaseModel):
    permiso_ids: List[int]


class PermisoCreate(BaseModel):
    codigo: str = Field(..., min_length=2, max_length=50)
    nombre: str = Field(..., min_length=2, max_length=100)
    descripcion: str = Field(..., max_length=250)


class PermisoUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=2, max_length=50)
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=250)


"""nuevos esquemas para registro desde web y app"""
class TallerWebRegister(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirmar_password: str = Field(..., min_length=8)
    telefono: Optional[str] = Field(None, max_length=20)
    direccion_default: Optional[str] = None
    nombre_comercial: Optional[str] = Field(None, max_length=150)
    direccion: Optional[str] = None
    latitud: Optional[float] = Field(None, ge=-90, le=90)
    longitud: Optional[float] = Field(None, ge=-180, le=180)


class ClienteAppRegister(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirmar_password: str = Field(..., min_length=8)
    telefono: Optional[str] = Field(None, max_length=20)
    direccion_default: Optional[str] = None