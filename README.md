# taller_backend

## 📱 Endpoints para App Móvil

Ver documentación completa en: [ENDPOINTS_APP_MOVIL.md](ENDPOINTS_APP_MOVIL.md)

### Quick Start para App Móvil:

1. **Registro**: `POST /api/register`
2. **Login**: `POST /api/auth/token`
3. **Reportar Emergencia**: `POST /api/solicitudes`
4. **Consultar Estado**: `GET /api/solicitudes/mis-solicitudes`
5. **Ver Taller Asignado**: `GET /api/solicitudes/{id}/taller-asignado`
6. **Realizar Pago**: `POST /api/pagos/crear-intencion`
7. **Notificaciones Push**: `POST /api/notificaciones/token`