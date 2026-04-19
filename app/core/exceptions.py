from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
import traceback


async def http_exception_handler(request: Request, exc):
    """Handler global para HTTPException"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para errores de validación de Pydantic"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(map(str, error["loc"])),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Error de validación", "errors": errors},
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handler para errores de integridad de base de datos"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Error de integridad de datos", "error": str(exc.orig)},
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handler global para excepciones no manejadas"""
    # Log del error (en producción enviar a sistema de monitoreo)
    traceback.print_exc()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"},
    )


# Estado de solicitudes - máquina de estados
VALID_STATE_TRANSITIONS = {
    "Pendiente": ["En proceso"],
    "En proceso": ["Atendido"],
    "Atendido": []  # Estado terminal
}


class InvalidStateTransitionError(Exception):
    """Excepción para transiciones de estado inválidas"""
    def __init__(self, current_state: str, target_state: str):
        super().__init__(
            f"Transición inválida de '{current_state}' a '{target_state}'. "
            f"Transiciones válidas desde '{current_state}': {VALID_STATE_TRANSITIONS.get(current_state, [])}"
        )
        self.current_state = current_state
        self.target_state = target_state