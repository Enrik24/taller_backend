#!/usr/bin/env python3
"""
Script de seed para poblar datos iniciales:
- Roles: Admin, Cliente, Taller
- Permisos básicos
- Usuario admin por defecto
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import Base
from app.modules.usuarios.models import Usuario, Cliente, Taller, Rol, Permiso, usuario_rol
from app.auth.hashing import get_password_hash

from app.modules.usuarios.models import *
from app.modules.solicitudes.models import *
from app.modules.pagos.models import *

def seed_database():
    """Poblar base de datos con datos iniciales"""
    
    # Crear engine y sesión
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("🌱 Iniciando seed de base de datos...")
        
        # Crear roles si no existen
        roles_data = [
            {'nombre': 'administrador', 'descripcion': 'Administrador del sistema con acceso total'},
            {'nombre': 'cliente', 'descripcion': 'Usuario cliente que reporta emergencias'},
            {'nombre': 'taller', 'descripcion': 'Taller mecánico que brinda servicios'}
        ]
        
        roles = {}
        for role_data in roles_data:
            role = db.query(Rol).filter(Rol.nombre == role_data['nombre']).first()
            if not role:
                role = Rol(**role_data)
                db.add(role)
                db.flush()
                print(f"✓ Rol creado: {role_data['nombre']}")
            roles[role_data['nombre']] = role
        
        # Crear permisos básicos
        permisos_data = [
            # Usuarios
            {'codigo': 'usuarios:read', 'nombre': 'Leer usuarios', 'descripcion': 'Permite leer información de usuarios'},
            {'codigo': 'usuarios:write', 'nombre': 'Escribir usuarios', 'descripcion': 'Permite crear/editar usuarios'},
            {'codigo': 'usuarios:delete', 'nombre': 'Eliminar usuarios', 'descripcion': 'Permite eliminar usuarios'},
            
            # Solicitudes
            {'codigo': 'solicitudes:create', 'nombre': 'Crear solicitud', 'descripcion': 'Permite crear solicitudes de servicio'},
            {'codigo': 'solicitudes:read', 'nombre': 'Leer solicitudes', 'descripcion': 'Permite ver solicitudes'},
            {'codigo': 'solicitudes:update', 'nombre': 'Actualizar solicitud', 'descripcion': 'Permite actualizar solicitudes'},
            {'codigo': 'solicitudes:assign', 'nombre': 'Asignar solicitud', 'descripcion': 'Permite asignar solicitudes a técnicos'},
            
            # Pagos
            {'codigo': 'pagos:create', 'nombre': 'Crear pago', 'descripcion': 'Permite registrar pagos'},
            {'codigo': 'pagos:read', 'nombre': 'Leer pagos', 'descripcion': 'Permite ver pagos'},
            
            # Admin
            {'codigo': 'admin:bitacora', 'nombre': 'Acceder a bitácora', 'descripcion': 'Permite acceder a la bitácora del sistema'},
            {'codigo': 'admin:comisiones', 'nombre': 'Gestionar comisiones', 'descripcion': 'Permite gestionar comisiones de talleres'},
        ]
        
        permisos = {}
        for perm_data in permisos_data:
            perm = db.query(Permiso).filter(Permiso.codigo == perm_data['codigo']).first()
            if not perm:
                perm = Permiso(**perm_data)
                db.add(perm)
                db.flush()
                print(f"✓ Permiso creado: {perm_data['codigo']}")
            permisos[perm_data['codigo']] = perm
        
        # Asignar permisos a roles
        role_permissions = {
            'administrador': list(permisos.keys()),  # Todos los permisos
            'cliente': [
                'usuarios:read', 'usuarios:write',
                'solicitudes:create', 'solicitudes:read', 'solicitudes:update',
                'pagos:create', 'pagos:read'
            ],
            'taller': [
                'usuarios:read', 'usuarios:write',
                'solicitudes:read', 'solicitudes:update', 'solicitudes:assign',
                'pagos:read'
            ]
        }
        
        for role_name, perm_codes in role_permissions.items():
            role = roles[role_name]
            for code in perm_codes:
                if permisos[code] not in role.permisos:
                    role.permisos.append(permisos[code])
        
        # Crear usuario admin por defecto si no existe
        admin_email = "admin@gmail.com"
        admin_user = db.query(Usuario).filter(Usuario.email == admin_email).first()
        
        if not admin_user:
            admin_user = Usuario(
                nombre="Administrador",
                email=admin_email,
                password_hash=get_password_hash("Admin123!"),
                tipo="usuario",
                activo=True
            )
            db.add(admin_user)
            db.flush()
            
            # Asignar rol admin
            admin_user.roles.append(roles['administrador'])
            print(f"✓ Usuario administrador creado: {admin_email} / Admin123!")
        
        # Commit de todas las transacciones
        db.commit()
        print("✅ Seed completado exitosamente!")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error en seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()