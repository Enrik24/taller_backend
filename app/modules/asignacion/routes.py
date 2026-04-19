from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.modules.usuarios.models import Usuario, Taller  # ← Agregar importación de Usuario y Taller
from app.modules.asignacion.ai_scaffold import (
    transcribe_audio, classify_image, generate_summary, smart_assign_taller
)
from app.modules.solicitudes.services import SolicitudService
from app.modules.solicitudes.models import Solicitud  # ← Agregar importación de Solicitud
from app.modules.talleres.services import TallerService

router = APIRouter(prefix="/api/asignacion", tags=["Asignación IA"])


@router.get("/solicitudes/{solicitud_id}/info-enriquecida")
async def get_info_enriquecida(
    solicitud_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """CU10 - Consultar información enriquecida con IA"""
    service = SolicitudService(db)
    solicitud = service.get_solicitud_by_id(solicitud_id)
    
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    # Verificar permisos
    if solicitud.id_cliente != current_user.id and (
        not hasattr(current_user, 'taller') or current_user.id != solicitud.id_taller
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para acceder"
        )
    
    # TODO IA: Aquí se integrarían las llamadas reales a modelos de IA
    # Por ahora retornamos datos dummy o procesamos si hay evidencias
    
    return {
        'solicitud_id': solicitud.id,
        'resumen_ia': solicitud.resumen_ia or "Resumen pendiente de procesamiento",
        'tipo_problema': solicitud.tipo_problema,
        'prioridad': solicitud.prioridad,
        'transcripcion_audio': None,  # Placeholder
        'clasificacion_imagen': None,  # Placeholder
        'evidencias_procesadas': len(solicitud.evidencias),
        'estado_procesamiento': 'pendiente' if not solicitud.resumen_ia else 'completado'
    }


@router.post("/procesar/{solicitud_id}")
async def procesar_evidencias_ia(
    solicitud_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    CU15 - Procesar Evidencias con IA (SCAFFOLDING)
    
    # TODO IA: Enviar audios a Whisper/Speech-to-Text y guardar transcripción. 
    # Enviar imágenes a modelo Computer Vision y clasificar en 
    # [batería, llanta, choque, motor, otros]. 
    # Generar resumen_ia automático.
    """
    service = SolicitudService(db)
    solicitud = service.get_solicitud_by_id(solicitud_id)
    
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    # Placeholder: simulación de procesamiento
    # En producción, aquí se iteraría sobre las evidencias y se llamaría a los servicios de IA
    
    resultados = {
        'solicitud_id': solicitud_id,
        'evidencias_procesadas': [],
        'resumen_generado': False
    }
    
    for evidencia in solicitud.evidencias:
        if evidencia.tipo == 'Audio':
            # TODO: transcripcion = await transcribe_audio(evidencia.url_archivo)
            transcripcion = await transcribe_audio(evidencia.url_archivo)
            resultados['evidencias_procesadas'].append({
                'id': evidencia.id,
                'tipo': 'Audio',
                'transcripcion': transcripcion
            })
        
        elif evidencia.tipo == 'Imagen':
            # TODO: clasificacion = await classify_image(evidencia.url_archivo)
            clasificacion = await classify_image(evidencia.url_archivo)
            resultados['evidencias_procesadas'].append({
                'id': evidencia.id,
                'tipo': 'Imagen',
                'clasificacion': clasificacion
            })
    
    # TODO: resumen = await generate_summary(...)
    if resultados['evidencias_procesadas']:
        solicitud.resumen_ia = await generate_summary(
            texto=solicitud.descripcion_texto,
            transcripcion=None,
            clasificacion_imagen=None
        )
        db.commit()
        resultados['resumen_generado'] = True
    
    return resultados


@router.post("/asignar/{solicitud_id}")
async def asignar_taller_inteligente(
    solicitud_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    CU16 - Asignar Taller Inteligentemente (SCAFFOLDING)
    
    # TODO IA: Motor de asignación que evalúe distancia geográfica (Haversine), 
    # disponibilidad taller, capacidad (cantidad técnicos), 
    # tipo de problema vs especialidad, prioridad.
    """
    # TODO IA: Implementar lógica completa de asignación
    
    service = SolicitudService(db)
    taller_service = TallerService(db)
    
    solicitud = service.get_solicitud_by_id(solicitud_id)
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    if not (solicitud.latitud and solicitud.longitud):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La solicitud debe tener coordenadas para asignación inteligente"
        )
    
    # Obtener talleres disponibles (placeholder)
    # TODO: Consultar talleres con filtros avanzados
    talleres = taller_service.db.query(Taller).filter(
        Taller.disponible == True
    ).all()
    
    talleres_data = []
    for t in talleres:
        talleres_data.append({
            'id': t.id_usuario,
            'nombre': t.nombre_comercial,
            'latitud': float(t.latitud) if t.latitud else None,
            'longitud': float(t.longitud) if t.longitud else None,
            'disponible': t.disponible,
            'calificacion': float(t.calificacion) if t.calificacion else 0.0,
            'tecnicos_disponibles': len(taller_service.get_disponibles_tecnicos(t.id_usuario))
        })
    
    # TODO IA: smart_assign_taller con algoritmo completo
    taller_asignado = await smart_assign_taller(
        solicitud_id=solicitud_id,
        solicitud_lat=float(solicitud.latitud),
        solicitud_lon=float(solicitud.longitud),
        tipo_problema=solicitud.tipo_problema,
        prioridad=solicitud.prioridad,
        talleres_disponibles=talleres_data
    )
    
    if not taller_asignado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró taller disponible para asignación"
        )
    
    # Asignar (esto actualizaría la solicitud)
    # TODO: Implementar asignación completa con validaciones
    
    return {
        'solicitud_id': solicitud_id,
        'taller_asignado': taller_asignado,
        'distancia_km': taller_asignado.get('distancia_km'),
        'score_asignacion': taller_asignado.get('score'),
        'nota': "Asignación basada en filtrado básico por distancia. TODO: Implementar algoritmo completo con pesos."
    }