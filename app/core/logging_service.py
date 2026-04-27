from sqlalchemy.orm import Session
from app.modules.usuarios.models import Bitacora
from datetime import datetime
from typing import Optional


def get_client_ip(request) -> Optional[str]:
    """Extrae la IP real del cliente considerando proxys"""
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.client.host if request.client else None


def log_audit(
    db: Session,
    user_id: Optional[int],
    action: str,
    ip_origen: Optional[str],
    entidad_afectada: Optional[str]
):
    """Registra un evento en la bitácora de auditoría"""
    log_entry = Bitacora(
        id_usuario=user_id,
        fecha_hora=datetime.utcnow(),
        accion=action,
        ip_origen=ip_origen,
        entidad_afectada=entidad_afectada
    )
    db.add(log_entry)
    db.commit()