from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import engine, Base
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    general_exception_handler,
    InvalidStateTransitionError
)
from app.core.middleware import AuditLogMiddleware, CORSMiddlewareConfig

# Importar routers de módulos
from app.auth.oauth2 import router as auth_router
from app.modules.usuarios.routes import router as usuarios_router
from app.modules.solicitudes.routes import router as solicitudes_router
from app.modules.pagos.routes import router as pagos_router
from app.modules.asignacion.routes import router as asignacion_router
from app.modules.notificaciones.routes import router as notificaciones_router
from app.modules.admin.routes import router as admin_router


def create_application() -> FastAPI:
    """Factory para crear la aplicación FastAPI"""
    
    app = FastAPI(
        title="Plataforma de Emergencias Vehiculares",
        description="API REST para conectar conductores con talleres mecánicos",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configurar CORS
    CORSMiddlewareConfig.configure(app, settings.BACKEND_CORS_ORIGINS)
    
    # Middleware de auditoría
    app.add_middleware(AuditLogMiddleware)
    
    # Registrar handlers de excepciones globales
    app.add_exception_handler(InvalidStateTransitionError, http_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Incluir routers de módulos
    app.include_router(auth_router)
    app.include_router(usuarios_router)
    app.include_router(solicitudes_router)
    app.include_router(pagos_router)
    app.include_router(asignacion_router)
    app.include_router(notificaciones_router)
    app.include_router(admin_router)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "database": "connected",  # TODO: Verificar conexión real
            "environment": settings.ENVIRONMENT
        }
    
    return app


app = create_application()


# Para desarrollo: crear tablas automáticamente (solo si no usa Alembic)
# if settings.ENVIRONMENT == "development":
#     @app.on_event("startup")
#     def startup():
#         Base.metadata.create_all(bind=engine)