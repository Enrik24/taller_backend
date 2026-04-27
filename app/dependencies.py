from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List, Union
import logging

from app.database import get_db
from app.config import settings
from app.modules.usuarios.models import Usuario, Cliente, Taller
from app.auth.jwt_handler import verify_token, create_access_token
from app.core.logging_service import log_audit

logger = logging.getLogger(__name__)
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
    
    logger.debug(f"[AUTH] Token recibido: {token[:20] if token else 'None'}...")
    
    try:
        payload = verify_token(token)
        logger.debug(f"[AUTH] Payload decodificado: {payload}")
        user_id_str: str = payload.get("sub")
        logger.debug(f"[AUTH] user_id_str extraído: {user_id_str}")
        
        if user_id_str is None:
            logger.warning("[AUTH] user_id_str es None en el payload")
            raise credentials_exception
        
        try:
            user_id = int(user_id_str)
            logger.debug(f"[AUTH] user_id convertido a int: {user_id}")
        except ValueError:
            logger.warning(f"[AUTH] user_id_str '{user_id_str}' no es un número válido")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"[AUTH] Error al verificar token: {str(e)}")
        raise credentials_exception
    
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    logger.debug(f"[AUTH] Usuario encontrado: {user is not None}, Activo: {user.activo if user else 'N/A'}")
    
    if user is None:
        logger.warning(f"[AUTH] Usuario con id {user_id} no existe en BD")
        raise credentials_exception
    
    if not user.activo:
        logger.warning(f"[AUTH] Usuario {user.email} está inactivo")
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
    if current_user.tipo != 'cliente':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo clientes pueden acceder"
        )
    return db.query(Cliente).filter(Cliente.id_usuario == current_user.id).first()


def get_current_taller(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Taller:
    """Obtiene el taller asociado al usuario"""
    if current_user.tipo != 'taller':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo talleres pueden acceder"
        )
    return db.query(Taller).filter(Taller.id_usuario == current_user.id).first()