from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.config import settings
from app.modules.usuarios.schemas import Token, TokenData, UserResponse
from app.modules.usuarios.services import UserService
from app.auth.jwt_handler import create_access_token
from app.auth.hashing import verify_password
from app.core.logging_service import log_audit

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


@router.post("/register", response_model=UserResponse)
async def register_user(
    nombre: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    tipo: str = Form(...),  # 'cliente' o 'taller'
    # Campos opcionales según tipo
    telefono: str = Form(None),
    direccion_default: str = Form(None),
    nombre_comercial: str = Form(None),
    direccion: str = Form(None),
    latitud: float = Form(None),
    longitud: float = Form(None),
    db: Session = Depends(get_db)
):
    """CU01 - Registrar Usuario (Cliente/Taller)"""
    user_service = UserService(db)
    
    # Validar email único
    if user_service.get_user_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Validar tipo de usuario
    if tipo not in ['cliente', 'taller']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de usuario inválido. Debe ser 'cliente' o 'taller'"
        )
    
    # Crear usuario
    user_data = {
        "nombre": nombre,
        "email": email,
        "password": password,
        "tipo": tipo
    }
    
    if tipo == 'cliente':
        user_data.update({
            "telefono": telefono,
            "direccion_default": direccion_default
        })
    else:  # taller
        user_data.update({
            "nombre_comercial": nombre_comercial,
            "direccion": direccion,
            "latitud": latitud,
            "longitud": longitud
        })
    
    created_user = user_service.create_user(user_data)
    
    # Log de auditoría
    log_audit(
        db=db,
        user_id=created_user.id,
        action="USUARIO_CREADO",
        description=f"Nuevo usuario registrado: {email} como {tipo}",
        ip_origen=None  # Se capturará en middleware
    )
    
    # TODO: Enviar email de verificación (simulado)
    # user_service.send_verification_email(created_user)
    
    return UserResponse.model_validate(created_user)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """CU02 - Iniciar Sesión con bloqueo tras 3 intentos fallidos"""
    user_service = UserService(db)
    
    user = user_service.get_user_by_email(form_data.username)
    
    # Verificar si el usuario existe y está activo
    if not user or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar si la cuenta está bloqueada por intentos fallidos
    if user.intentos_fallidos >= settings.MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Cuenta temporalmente bloqueada por múltiples intentos fallidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar contraseña
    if not verify_password(form_data.password, user.password_hash):
        # Incrementar contador de intentos fallidos
        user_service.increment_failed_attempts(user)
        
        # Si alcanza el límite, desactivar temporalmente
        if user.intentos_fallidos >= settings.MAX_LOGIN_ATTEMPTS:
            user_service.deactivate_user(user.id)
            log_audit(
                db=db,
                user_id=user.id,
                action="CUENTA_BLOQUEADA",
                description="Cuenta bloqueada por intentos fallidos de login",
                ip_origen=None
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Login exitoso: resetear intentos fallidos
    user_service.reset_failed_attempts(user)
    
    # Crear token con claims
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "rol": user.roles[0].nombre if user.roles else "cliente"
        },
        expires_delta=access_token_expires
    )
    
    # Log de auditoría
    log_audit(
        db=db,
        user_id=user.id,
        action="LOGIN_EXITOSO",
        description=f"Usuario {user.email} inició sesión",
        ip_origen=None
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "rol": user.roles[0].nombre if user.roles else "cliente",
        "nombre": user.nombre
    }