import asyncio
from typing import Optional, List
from firebase_admin import messaging
from sqlalchemy.orm import Session
from app.modules.notificaciones.models import NotificacionToken, PreferenciaNotificacion, HistorialNotificacion
from app.modules.solicitudes.models import Solicitud
from app.modules.pagos.models import Pago

class NotificationService:
    """Servicio de Notificaciones Push con Firebase Cloud Messaging (FCM v1)"""
    
    def __init__(self, db: Session):
        self.db = db

    async def _send_push(self, token: str, title: str, body: str, data: Optional[dict] = None) -> bool:
        """Envía una notificación push individual a FCM"""
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
            data=data or {},
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))
            )
        )
        try:
            # En producción real, envolver en asyncio.to_thread(messaging.send, message) para no bloquear el event loop
            #messaging.send(message)
            # 🔥 Ejecuta la llamada síncrona en un hilo separado para no bloquear FastAPI
            response = await asyncio.to_thread(messaging.send, message)
            return True
        except Exception as e:
            print(f"❌ Error FCM: {str(e)}")
            return False

    def _get_active_tokens(self, user_id: int) -> List[str]:
        """Obtiene tokens FCM activos de un usuario"""
        tokens = self.db.query(NotificacionToken).filter(
            NotificacionToken.id_usuario == user_id,
            NotificacionToken.activo == True
        ).all()
        return [t.token_fcm for t in tokens]

    def _check_preference(self, user_id: int, preference_key: str) -> bool:
        """Verifica si el usuario tiene activada la categoría de notificación"""
        prefs = self.db.query(PreferenciaNotificacion).filter(
            PreferenciaNotificacion.id_usuario == user_id
        ).first()
        if not prefs:
            return True  # Por defecto: permitir
        return getattr(prefs, preference_key, True)

    async def notify_cliente_solicitud_aceptada(self, solicitud: Solicitud):
        """CU07/11: Notifica al cliente cuando un taller acepta su emergencia"""
        if not self._check_preference(solicitud.id_cliente, "actualizaciones_servicio"):
            return

        tokens = self._get_active_tokens(solicitud.id_cliente)
        exitosos = 0
        errores = []
        for token in tokens:
            try:
                exito = await self._send_push(
                    token=token,
                    title="✅ Taller Asignado",
                    body="Un técnico ha aceptado tu solicitud y está en camino.",
                    data={"solicitud_id": str(solicitud.id), "tipo": "aceptada"}
                )
                if exito:
                    exitosos += 1
                else:
                    errores.append(f"Fallo en token {token}")
            except Exception as e:
                errores.append(f"Error FCM en token {token}: {str(e)}")

        estado = 'Enviada' if exitosos > 0 else 'Fallida'
        error_detalle = '; '.join(errores) if errores else None

        historial = HistorialNotificacion(
            id_usuario=solicitud.id_cliente,
            id_solicitud=solicitud.id,
            tipo='Push',
            titulo="✅ Taller Asignado",
            contenido="Un técnico ha aceptado tu solicitud y está en camino.",
            estado=estado,
            error_detalle=error_detalle
        )
        self.db.add(historial)
        self.db.commit()

    async def notify_estado_actualizado(self, solicitud: Solicitud):
        """CU13: Notifica cambios en el estado del servicio"""
        if not self._check_preference(solicitud.id_cliente, "actualizaciones_servicio"):
            return

        tokens = self._get_active_tokens(solicitud.id_cliente)
        mensajes = {
            "Pendiente": "Tu solicitud ha sido registrada.",
            "En proceso": "El taller está trabajando en tu vehículo.",
            "Atendido": "Servicio finalizado. Puedes proceder al pago."
        }
        body = mensajes.get(solicitud.estado, f"Estado actualizado a: {solicitud.estado}")

        exitosos = 0
        errores = []
        for token in tokens:
            try:
                exito = await self._send_push(
                    token=token,
                    title=f"🔄 Estado: {solicitud.estado}",
                    body=body,
                    data={"solicitud_id": str(solicitud.id), "estado": solicitud.estado}
                )
                if exito:
                    exitosos += 1
                else:
                    errores.append(f"Fallo en token {token}")
            except Exception as e:
                errores.append(f"Error FCM en token {token}: {str(e)}")

        estado = 'Enviada' if exitosos > 0 else 'Fallida'
        error_detalle = '; '.join(errores) if errores else None

        historial = HistorialNotificacion(
            id_usuario=solicitud.id_cliente,
            id_solicitud=solicitud.id,
            tipo='Push',
            titulo=f"🔄 Estado: {solicitud.estado}",
            contenido=body,
            estado=estado,
            error_detalle=error_detalle
        )
        self.db.add(historial)
        self.db.commit()

    async def notify_pago_completado(self, pago: Pago):
        """CU08: Notifica confirmación de pago exitoso"""
        if not self._check_preference(pago.solicitud.id_cliente, "estado_pago"):
            return

        tokens = self._get_active_tokens(pago.solicitud.id_cliente)
        exitosos = 0
        errores = []
        for token in tokens:
            try:
                exito = await self._send_push(
                    token=token,
                    title="💳 Pago Confirmado",
                    body=f"Tu pago de ${pago.monto_total} fue procesado exitosamente.",
                    data={"pago_id": str(pago.id), "solicitud_id": str(pago.solicitud.id)}
                )
                if exito:
                    exitosos += 1
                else:
                    errores.append(f"Fallo en token {token}")
            except Exception as e:
                errores.append(f"Error FCM en token {token}: {str(e)}")

        estado = 'Enviada' if exitosos > 0 else 'Fallida'
        error_detalle = '; '.join(errores) if errores else None

        historial = HistorialNotificacion(
            id_usuario=pago.solicitud.id_cliente,
            id_solicitud=pago.solicitud.id,
            tipo='Push',
            titulo="💳 Pago Confirmado",
            contenido=f"Tu pago de ${pago.monto_total} fue procesado exitosamente.",
            estado=estado,
            error_detalle=error_detalle
        )
        self.db.add(historial)
        self.db.commit()