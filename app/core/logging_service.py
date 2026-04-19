from sqlalchemy.orm import Session
from app.modules.usuarios.models import Bitacora
from datetime import datetime
from typing import Optional


def log_audit(
    db: Session,
    user_id: Optional[int],
    action: str,
    description: Optional[str],
    ip_origen: Optional[str],
    entidad_afectada: Optional[str] = None
):
    """Registra un evento en la bitácora de auditoría"""
    log_entry = Bitacora(
        id_usuario=user_id,
        fecha_hora=datetime.utcnow(),
        accion=action,
        descripcion=description,
        ip_origen=ip_origen,
        entidad_afectada=entidad_afectada
    )
    db.add(log_entry)
    db.commit()