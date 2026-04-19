from sqlalchemy.orm import Session
from typing import Optional
import stripe
from app.config import settings
from app.modules.pagos.models import Pago
from app.core.logging_service import log_audit


stripe.api_key = settings.STRIPE_SECRET_KEY


class PagoService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_payment_intent(self, solicitud_id: int, monto: float, usuario_email: str) -> dict:
        """Crear PaymentIntent en Stripe con customer vinculado"""
        # Buscar o crear Customer en Stripe
        try:
            customers = stripe.Customer.list(email=usuario_email, limit=1)
            if customers.data:
                customer_id = customers.data[0].id
            else:
                customer = stripe.Customer.create(
                    email=usuario_email,
                    metadata={'solicitud_id': solicitud_id}
                )
                customer_id = customer.id
        except stripe.error.StripeError as e:
            # Fallback: crear sin customer si hay error
            customer_id = None
            print(f"Warning: No se pudo crear/find Stripe customer: {e}")
        
        # Crear PaymentIntent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(monto * 100),  # Stripe usa centavos
            currency='usd',  # O dinámico según configuración
            customer=customer_id if customer_id else None,
            metadata={
                'solicitud_id': solicitud_id,
                'plataforma': 'emergencias_vehiculares'
            },
            automatic_payment_methods={'enabled': True}
        )
        
        return {
            'client_secret': payment_intent.client_secret,
            'stripe_customer_id': customer_id,
            'email_usuario': usuario_email
        }
    
    def handle_webhook(self, payload: bytes, sig_header: str) -> Optional[Pago]:
        """Procesar webhook de Stripe"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return None
        
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            solicitud_id = payment_intent['metadata'].get('solicitud_id')
            
            if solicitud_id:
                # Crear o actualizar registro de Pago
                pago = self.db.query(Pago).filter(
                    Pago.stripe_payment_intent_id == payment_intent['id']
                ).first()
                
                if not pago:
                    pago = Pago(
                        id_solicitud=int(solicitud_id),
                        monto_total=payment_intent['amount'] / 100,
                        metodo_pago=payment_intent['payment_method_types'][0],
                        estado='Pagado',
                        stripe_payment_intent_id=payment_intent['id'],
                        stripe_customer_id=payment_intent.get('customer')
                    )
                    self.db.add(pago)
                else:
                    pago.estado = 'Pagado'
                    pago.fecha_pago = func.now()
                
                self.db.commit()
                
                # Log de auditoría (la comisión se crea automáticamente vía event listener)
                log_audit(
                    db=self.db,
                    user_id=None,  # System event
                    action="PAGO_PROCESADO",
                    description=f"PaymentIntent {payment_intent['id']} exitoso para solicitud {solicitud_id}",
                    ip_origen=None,
                    entidad_afectada=f"Pago:{pago.id}"
                )
                
                return pago
        
        return None
    
    def get_pago_by_solicitud(self, solicitud_id: int) -> Optional[Pago]:
        return self.db.query(Pago).filter(Pago.id_solicitud == solicitud_id).first()