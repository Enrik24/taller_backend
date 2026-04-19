from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_current_cliente
from app.modules.usuarios.models import Usuario, Cliente  # ← Agregar Cliente y Usuario
from app.modules.pagos.services import PagoService
from app.modules.pagos.models import Pago
from app.modules.solicitudes.services import SolicitudService
from app.modules.solicitudes.models import Solicitud  # ← Agregar importación de Solicitud
from app.modules.solicitudes.schemas import EstadoSolicitudEnum  # ← Importar desde schemas
from app.config import settings

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])


@router.post("/crear-intencion")
async def crear_intencion_pago(
    solicitud_id: int,
    monto: float,
    current_cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """CU08 - Crear PaymentIntent de Stripe"""
    service = PagoService(db)
    solicitud_service = SolicitudService(db)
    
    # Validar solicitud
    solicitud = solicitud_service.get_solicitud_by_id(solicitud_id)
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    # Validar que sea del cliente actual
    if solicitud.id_cliente != current_cliente.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para pagar esta solicitud"
        )
    
    # Validar que esté finalizada y sin pago previo
    if solicitud.estado != EstadoSolicitudEnum.ATENDIDO.value:  # ← Usar .value
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede pagar solicitudes en estado 'Atendido'"
        )
    
    if db.query(Pago).filter(Pago.id_solicitud == solicitud_id).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta solicitud ya tiene un pago registrado"
        )
    
    # Obtener email del usuario
    usuario = db.query(Usuario).filter(Usuario.id == current_cliente.id_usuario).first()
    
    # Crear PaymentIntent en Stripe
    try:
        payment_data = service.create_payment_intent(
            solicitud_id=solicitud_id,
            monto=monto,
            usuario_email=usuario.email
        )
        return payment_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando PaymentIntent: {str(e)}"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db)
):
    """Endpoint para webhooks de Stripe"""
    payload = await request.body()
    service = PagoService(db)
    
    pago = service.handle_webhook(payload, stripe_signature)
    
    if pago is None:
        # Evento no procesado o error de firma
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook no procesado"
        )
    
    return {"status": "success", "pago_id": pago.id}


@router.get("/{solicitud_id}/comprobante")
async def obtener_comprobante_pago(
    solicitud_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """CU08 - Obtener datos del pago/comprobante"""
    service = PagoService(db)
    pago = service.get_pago_by_solicitud(solicitud_id)
    
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado para esta solicitud"
        )
    
    # Verificar permisos
    solicitud = pago.solicitud
    # Verificar si es admin (verificar roles)
    is_admin = any(role.nombre == 'admin' for role in current_user.roles) if current_user.roles else False
    
    if (solicitud.id_cliente != current_user.id and 
        (not hasattr(current_user, 'taller') or current_user.id != solicitud.id_taller) and 
        not is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para ver este comprobante"
        )
    
    return {
        'id': pago.id,
        'solicitud_id': pago.id_solicitud,
        'monto_total': float(pago.monto_total),
        'monto_comision': float(pago.comision.monto) if pago.comision else 0,
        'metodo_pago': pago.metodo_pago,
        'estado': pago.estado,
        'fecha_pago': pago.fecha_pago,
        'comprobante_url': pago.comprobante_url,
        'stripe_payment_intent_id': pago.stripe_payment_intent_id
    }