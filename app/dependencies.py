from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List, Union

from app.database import get_db
from app.config import settings
from app.modules.usuarios.models import Usuario, Cliente, Taller
from app.auth.jwt_handler import verify_token, create_access_token
from app.core.logging_service import log_audit

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Usuario:
    """Obtiene el usuario actual desde el token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(token)
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if user is None or not user.activo:
        raise credentials_exception
    
    return user


def require_role(roles: List[str]):
    """Dependency factory para verificar roles"""
    def role_checker(
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None
    ) -> Usuario:
        # Obtener roles del usuario
        user_roles = [rol.nombre for rol in current_user.roles]
        
        if not any(role in user_roles for role in roles):
            log_audit(
                db=db,
                user_id=current_user.id,
                action="ACCESO_DENEGADO",
                description=f"Intento de acceso con roles {roles}, usuario tiene {user_roles}",
                ip_origen=request.client.host if request else None
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos suficientes"
            )
        return current_user
    return role_checker


def require_permission(permission_code: str):
    """Dependency factory para verificar permisos específicos"""
    def permission_checker(
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None
    ) -> Usuario:
        # Obtener permisos del usuario a través de sus roles
        permissions = set()
        for role in current_user.roles:
            for perm in role.permisos:
                permissions.add(perm.codigo)
        
        if permission_code not in permissions:
            log_audit(
                db=db,
                user_id=current_user.id,
                action="PERMISO_DENEGADO",
                description=f"Permiso '{permission_code}' requerido, usuario tiene: {permissions}",
                ip_origen=request.client.host if request else None
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso '{permission_code}' requerido"
            )
        return current_user
    return permission_checker


def get_current_cliente(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Cliente:
    """Obtiene el cliente asociado al usuario"""
    if not hasattr(current_user, 'cliente'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo clientes pueden acceder"
        )
    return current_user.cliente


def get_current_taller(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Taller:
    """Obtiene el taller asociado al usuario"""
    if not hasattr(current_user, 'taller'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo talleres pueden acceder"
        )
    return current_user.taller