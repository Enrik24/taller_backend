from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from app.database import get_db
from app.config import settings
from app.modules.usuarios.schemas import Token, TokenData, UserResponse, UserCreate, LoginRequest, RoleEnum, TallerWebRegister, ClienteAppRegister
from app.modules.usuarios.services import UserService
from app.auth.jwt_handler import create_access_token
from app.auth.hashing import verify_password
from app.core.logging_service import log_audit, get_client_ip

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


async def _register_user(
    request: Request,
    data: UserCreate,
    tipo_forzado: str,
    db: Session
):
    """Helper function para registrar usuario con tipo forzado"""
    user_service = UserService(db)

    # Forzar tipo
    data.tipo = RoleEnum(tipo_forzado)

    # Validar email único
    if user_service.get_user_by_email(data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )

    # Crear usuario
    created_user = user_service.create_user(data)

    # Asignar roles si se proporcionan
    if data.rol_ids:
        from app.modules.usuarios.models import Rol
        roles = db.query(Rol).filter(Rol.id.in_(data.rol_ids)).all()
        created_user.roles = roles
        db.commit()

    # Log de auditoría
    log_audit(
        db=db,
        user_id=created_user.id,
        action="USUARIO_CREADO",
        ip_origen=get_client_ip(request),
        entidad_afectada=f"Usuario:{data.email}"
    )

    # TODO: Enviar email de verificación (simulado)
    # user_service.send_verification_email(created_user)

    return UserResponse.model_validate(created_user)


@router.post("/register", response_model=UserResponse)
async def register_user(
    request: Request,
    data: UserCreate,
    db: Session = Depends(get_db)
):
    """CU01 - Registrar Usuario (Cliente/Taller) - Endpoint general"""
    # Validar tipo de usuario
    if data.tipo.value not in ['cliente', 'taller']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de usuario inválido. Debe ser 'cliente' o 'taller'"
        )

    return await _register_user(request, data, data.tipo.value, db)


@router.post("/register/web", response_model=UserResponse)
async def register_taller_web(
    request: Request,
    data: TallerWebRegister,  # ← FastAPI lee esto del body JSON
    db: Session = Depends(get_db)
):
    """Registrar Taller desde Web"""
    
    if data.password != data.confirmar_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden"
        )
    
    user_data = UserCreate(
        nombre=data.nombre,
        email=data.email,
        password=data.password,
        tipo=RoleEnum.TALLER,
        telefono=data.telefono,
        direccion_default=data.direccion_default,
        nombre_comercial=data.nombre_comercial,
        direccion=data.direccion,
        latitud=data.latitud,
        longitud=data.longitud,
        rol_ids=[]
    )
    return await _register_user(request, user_data, 'taller', db)


@router.post("/register/app", response_model=UserResponse)
async def register_cliente_app(
    request: Request,
    data: ClienteAppRegister,  # ← FastAPI lee esto del body JSON
    db: Session = Depends(get_db)
):
    """Registrar Cliente desde App Móvil"""
    
    if data.password != data.confirmar_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden"
        )
    
    user_data = UserCreate(
        nombre=data.nombre,
        email=data.email,
        password=data.password,
        tipo=RoleEnum.CLIENTE,
        telefono=data.telefono,
        direccion_default=data.direccion_default,
        rol_ids=[]
    )
    return await _register_user(request, user_data, 'cliente', db)


@router.post("/login", response_model=Token)
async def login(
    request: Request,
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
    client_ip = get_client_ip(request)
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
                ip_origen=client_ip,
                entidad_afectada="Usuario"
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
            "sub": str(user.id),  # Convertir a string
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
        ip_origen=client_ip,
        entidad_afectada="Usuario"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "rol": user.roles[0].nombre if user.roles else "cliente",
        "nombre": user.nombre
    }


@router.post("/login/json", response_model=Token)
async def login_json(
    request: Request,
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login que acepta JSON"""
    user_service = UserService(db)
    
    user = user_service.get_user_by_email(data.username)
    
    if not user or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.intentos_fallidos >= settings.MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Cuenta temporalmente bloqueada por múltiples intentos fallidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    client_ip = get_client_ip(request)
    if not verify_password(data.password, user.password_hash):
        user_service.increment_failed_attempts(user)
        
        if user.intentos_fallidos >= settings.MAX_LOGIN_ATTEMPTS:
            user_service.deactivate_user(user.id)
            log_audit(
                db=db,
                user_id=user.id,
                action="CUENTA_BLOQUEADA",
                ip_origen=client_ip,
                entidad_afectada="Usuario"
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_service.reset_failed_attempts(user)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "rol": user.roles[0].nombre if user.roles else "cliente"
        },
        expires_delta=access_token_expires
    )
    
    log_audit(
        db=db,
        user_id=user.id,
        action="LOGIN_EXITOSO",
        ip_origen=client_ip,
        entidad_afectada="Usuario"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "rol": user.roles[0].nombre if user.roles else "cliente",
        "nombre": user.nombre
    }