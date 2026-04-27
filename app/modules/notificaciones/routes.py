from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.modules.usuarios.models import Usuario  # ← Agregar importación de Usuario
from app.modules.notificaciones.models import NotificacionToken, PreferenciaNotificacion, HistorialNotificacion
from app.modules.notificaciones.services import NotificationService

router = APIRouter(prefix="/api/notificaciones", tags=["Notificaciones"])


@router.post("/token", status_code=status.HTTP_201_CREATED)
async def registrar_token_fcm(
    token_fcm: str,
    plataforma: str,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """CU07 - Guardar token FCM del dispositivo"""
    # Verificar si ya existe el token
    existing = db.query(NotificacionToken).filter(
        NotificacionToken.token_fcm == token_fcm
    ).first()
    
    if existing:
        existing.activo = True
        existing.plataforma = plataforma
        existing.fecha_ultima_uso = func.now()
    else:
        # Verificar si el usuario ya tiene un token para esta plataforma
        old_token = db.query(NotificacionToken).filter(
            NotificacionToken.id_usuario == current_user.id,
            NotificacionToken.plataforma == plataforma,
            NotificacionToken.activo == True
        ).first()
        
        if old_token:
            old_token.activo = False
        
        new_token = NotificacionToken(
            id_usuario=current_user.id,
            token_fcm=token_fcm,
            plataforma=plataforma
        )
        db.add(new_token)
    
    db.commit()
    return {"message": "Token registrado exitosamente"}


@router.get("/configuracion")
async def get_preferencias(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener preferencias de notificación del usuario"""
    prefs = db.query(PreferenciaNotificacion).filter(
        PreferenciaNotificacion.id_usuario == current_user.id
    ).first()
    
    if not prefs:
        # Crear preferencias por defecto
        prefs = PreferenciaNotificacion(
            id_usuario=current_user.id,
            actualizaciones_servicio=True,
            promociones=False,
            estado_pago=True,
            recordatorios=True
        )
        db.add(prefs)
        db.commit()
    
    return {
        'actualizaciones_servicio': prefs.actualizaciones_servicio,
        'promociones': prefs.promociones,
        'estado_pago': prefs.estado_pago,
        'recordatorios': prefs.recordatorios
    }


@router.put("/configuracion")
async def update_preferencias(
    actualizaciones_servicio: Optional[bool] = None,
    promociones: Optional[bool] = None,
    estado_pago: Optional[bool] = None,
    recordatorios: Optional[bool] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar preferencias de notificación"""
    prefs = db.query(PreferenciaNotificacion).filter(
        PreferenciaNotificacion.id_usuario == current_user.id
    ).first()
    
    if not prefs:
        prefs = PreferenciaNotificacion(id_usuario=current_user.id)
        db.add(prefs)
    
    # Actualizar campos proporcionados
    if actualizaciones_servicio is not None:
        prefs.actualizaciones_servicio = actualizaciones_servicio
    if promociones is not None:
        prefs.promociones = promociones
    if estado_pago is not None:
        prefs.estado_pago = estado_pago
    if recordatorios is not None:
        prefs.recordatorios = recordatorios
    
    prefs.fecha_actualizacion = func.now()
    db.commit()
    
    return {"message": "Preferencias actualizadas"}


@router.post("/enviar")
async def enviar_notificacion_manual(
    usuario_id: int,
    titulo: str,
    mensaje: str,
    current_user: Usuario = Depends(require_role(['administrador'])),
    db: Session = Depends(get_db)
):
    """Enviar notificación push manual (solo admin)"""
    # TODO: Implementar envío real
    service = NotificationService(db)
    
    # Obtener tokens activos del usuario
    tokens = db.query(NotificacionToken).filter(
        NotificacionToken.id_usuario == usuario_id,
        NotificacionToken.activo == True
    ).all()
    
    resultados = []
    exitosos = 0
    errores = []
    for token in tokens:
        try:
            exito = await service.send_push_notification(
                token=token.token_fcm,
                title=titulo,
                body=mensaje
            )
            if exito:
                exitosos += 1
            else:
                errores.append(f"Fallo en token {token.id}")
        except Exception as e:
            errores.append(f"Error en token {token.id}: {str(e)}")
        resultados.append({'token_id': token.id, 'exitoso': exito})

    estado = 'Enviada' if exitosos > 0 else 'Fallida'
    error_detalle = '; '.join(errores) if errores else None

    historial = HistorialNotificacion(
        id_usuario=usuario_id,
        tipo='Push',
        titulo=titulo,
        contenido=mensaje,
        estado=estado,
        error_detalle=error_detalle
    )
    db.add(historial)
    db.commit()

    return {"enviados": exitosos, "detalles": resultados}


@router.patch("/{historial_id}/marcar-leida", status_code=status.HTTP_200_OK)
async def marcar_notificacion_leida(
    historial_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marcar una notificación como leída desde la app móvil"""
    historial = db.query(HistorialNotificacion).filter(
        HistorialNotificacion.id == historial_id,
        HistorialNotificacion.id_usuario == current_user.id
    ).first()

    if not historial:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    if historial.estado != 'Enviada':
        raise HTTPException(status_code=400, detail="La notificación no está en estado enviada")

    historial.estado = 'Leida'
    db.commit()

    return {"message": "Notificación marcada como leída"}