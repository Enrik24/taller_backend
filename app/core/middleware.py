from fastapi import Request, FastAPI
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import time
import re


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware para registrar auditoría de requests críticos"""
    
    # Endpoints que requieren logging de auditoría
    CRITICAL_ENDPOINTS = [
        r"^/api/solicitudes/.*$",
        r"^/api/pagos/.*$",
        r"^/api/admin/.*$",
        r"^/api/auth/.*$",
    ]
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Verificar si es endpoint crítico
        is_critical = any(
            re.match(pattern, request.url.path) 
            for pattern in self.CRITICAL_ENDPOINTS
        )
        
        if not is_critical:
            return await call_next(request)
        
        # Capturar datos del request
        start_time = time.time()
        ip_origin = request.client.host if request.client else None
        method = request.method
        path = request.url.path
        
        # Procesar request
        response = await call_next(request)
        
        # Calcular tiempo de procesamiento
        process_time = time.time() - start_time
        
        # Aquí se podría encolar el log para procesamiento asíncrono
        # Por ahora, el logging se hace en los servicios cuando ocurren acciones críticas
        
        # Agregar header de tiempo de procesamiento
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class CORSMiddlewareConfig:
    """Configuración centralizada de CORS"""
    
    @staticmethod
    def configure(app: FastAPI, origins: list):
        from fastapi.middleware.cors import CORSMiddleware
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )