from sqlalchemy.orm import Session
from typing import List, Optional
from app.modules.usuarios.models import Taller, Tecnico
from app.modules.usuarios.services import TallerService as BaseTallerService


class TallerService(BaseTallerService):
    """Extensión de TallerService con métodos específicos del dominio"""
    
    def __init__(self, db: Session):
        super().__init__(db)
    
    def get_nearby_tallers(
        self, 
        latitud: float, 
        longitud: float, 
        radio_km: float = 10.0
    ) -> List[Taller]:
        """
        Obtener talleres cercanos (placeholder para cálculo geoespacial)
        TODO: Implementar con extensión PostGIS para consultas espaciales eficientes
        """
        # Placeholder: filtrado básico (en producción usar ST_DWithin de PostGIS)
        return self.db.query(Taller).filter(
            Taller.disponible == True,
            Taller.latitud != None,
            Taller.longitud != None
        ).all()
    
    def get_taller_with_stats(self, taller_id: int) -> Optional[dict]:
        """Obtener taller con estadísticas de desempeño"""
        taller = self.get_taller_by_user_id(taller_id)
        if not taller:
            return None
        
        # TODO: Calcular estadísticas reales desde historial
        return {
            'id': taller.id_usuario,
            'nombre_comercial': taller.nombre_comercial,
            'calificacion': float(taller.calificacion),
            'solicitudes_atendidas': 0,  # Placeholder
            'tiempo_promedio_respuesta_min': None,  # Placeholder
            'tecnicos_disponibles': len(self.get_disponibles_tecnicos(taller_id))
        }