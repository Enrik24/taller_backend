from datetime import datetime, timedelta
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError, JWSError, JWSSignatureError
from typing import Optional, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    logger.debug(f"[JWT] Creando token con SECRET_KEY[:10]={settings.SECRET_KEY[:10]}, ALGORITHM={settings.ALGORITHM}")
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Dict[str, Any]:
    try:
        logger.debug(f"[JWT] Verificando token con SECRET_KEY[:10]={settings.SECRET_KEY[:10]}, ALGORITHM={settings.ALGORITHM}")
        logger.debug(f"[JWT] Token recibido (primeros 50 chars): {token[:50]}")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug(f"[JWT] Token verificado exitosamente: {payload}")
        return payload
    except ExpiredSignatureError as e:
        logger.error(f"[JWT] ❌ Token EXPIRADO - Detalle: {str(e)}")
        raise JWTError(f"Token expirado")
    except JWSSignatureError as e:
        logger.error(f"[JWT] ❌ Firma INVÁLIDA - Detalle: {str(e)}")
        raise JWTError(f"Firma inválida")
    except JWSError as e:
        logger.error(f"[JWT] ❌ Error JWS - Detalle: {str(e)}")
        raise JWTError(f"Token inválido")
    except JWTError as e:
        logger.error(f"[JWT] Error genérico - Tipo: {type(e).__name__}, Detalle: {str(e)}")
        raise JWTError(f"Token inválido: {str(e)}")