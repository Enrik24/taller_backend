#!/usr/bin/env python3
"""
Script de seed para poblar datos iniciales:
- Roles: Admin, Cliente, Taller
- Permisos básicos
- 2 Administradores, 2 Talleres, 2 Clientes
- Datos de prueba para todas las tablas
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
from app.modules.usuarios.models import (
    Usuario, Administrador, Cliente, Taller, Rol, Permiso,
    usuario_rol, Tecnico, Vehiculo, Bitacora
)
from app.auth.hashing import get_password_hash
from app.modules.solicitudes.models import Solicitud, Evidencia, EstadoSolicitud, TipoEvidencia
from app.modules.pagos.models import Pago, Comision
from app.modules.notificaciones.models import (
    NotificacionToken, PreferenciaNotificacion, HistorialNotificacion
)


def seed_database():
    """Poblar base de datos con datos iniciales"""

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("🌱 Iniciando seed de base de datos...")

        # ─────────────────────────────────────────
        # ROLES
        # ─────────────────────────────────────────
        roles_data = [
            {'nombre': 'administrador', 'descripcion': 'Administrador del sistema con acceso total'},
            {'nombre': 'cliente',       'descripcion': 'Usuario cliente que reporta emergencias'},
            {'nombre': 'taller',        'descripcion': 'Taller mecánico que brinda servicios'},
        ]

        roles = {}
        for rd in roles_data:
            role = db.query(Rol).filter(Rol.nombre == rd['nombre']).first()
            if not role:
                role = Rol(**rd)
                db.add(role)
                db.flush()
                print(f"✓ Rol creado: {rd['nombre']}")
            roles[rd['nombre']] = role

        # ─────────────────────────────────────────
        # PERMISOS
        # ─────────────────────────────────────────
        permisos_data = [
            {'codigo': 'usuarios:read',      'nombre': 'Leer usuarios',         'descripcion': 'Permite leer información de usuarios'},
            {'codigo': 'usuarios:write',     'nombre': 'Escribir usuarios',     'descripcion': 'Permite crear/editar usuarios'},
            {'codigo': 'usuarios:delete',    'nombre': 'Eliminar usuarios',     'descripcion': 'Permite eliminar usuarios'},
            {'codigo': 'solicitudes:create', 'nombre': 'Crear solicitud',       'descripcion': 'Permite crear solicitudes de servicio'},
            {'codigo': 'solicitudes:read',   'nombre': 'Leer solicitudes',      'descripcion': 'Permite ver solicitudes'},
            {'codigo': 'solicitudes:update', 'nombre': 'Actualizar solicitud',  'descripcion': 'Permite actualizar solicitudes'},
            {'codigo': 'solicitudes:assign', 'nombre': 'Asignar solicitud',     'descripcion': 'Permite asignar solicitudes a técnicos'},
            {'codigo': 'pagos:create',       'nombre': 'Crear pago',            'descripcion': 'Permite registrar pagos'},
            {'codigo': 'pagos:read',         'nombre': 'Leer pagos',            'descripcion': 'Permite ver pagos'},
            {'codigo': 'admin:bitacora',     'nombre': 'Acceder a bitácora',    'descripcion': 'Permite acceder a la bitácora del sistema'},
            {'codigo': 'admin:comisiones',   'nombre': 'Gestionar comisiones',  'descripcion': 'Permite gestionar comisiones de talleres'},
        ]

        permisos = {}
        for pd in permisos_data:
            perm = db.query(Permiso).filter(Permiso.codigo == pd['codigo']).first()
            if not perm:
                perm = Permiso(**pd)
                db.add(perm)
                db.flush()
                print(f"✓ Permiso creado: {pd['codigo']}")
            permisos[pd['codigo']] = perm

        # Asignar permisos a roles
        role_permissions = {
            'administrador': list(permisos.keys()),
            'cliente': [
                'usuarios:read', 'usuarios:write',
                'solicitudes:create', 'solicitudes:read', 'solicitudes:update',
                'pagos:create', 'pagos:read',
            ],
            'taller': [
                'usuarios:read', 'usuarios:write',
                'solicitudes:read', 'solicitudes:update', 'solicitudes:assign',
                'pagos:read',
            ],
        }

        for role_name, codes in role_permissions.items():
            role = roles[role_name]
            for code in codes:
                if permisos[code] not in role.permisos:
                    role.permisos.append(permisos[code])

        db.flush()

        # ─────────────────────────────────────────
        # ADMINISTRADORES (tipo = 'administrador', sin tabla hija)
        # ─────────────────────────────────────────
        admins_data = [
            {'nombre': 'Administrador Principal', 'email': 'admin@gmail.com',   'password': 'Admin123!'},
            {'nombre': 'Administrador Soporte',   'email': 'admin2@gmail.com',  'password': 'Admin123!'},
        ]

        admins = []
        for ad in admins_data:
            u = db.query(Usuario).filter(Usuario.email == ad['email']).first()
            if not u:
                u = Administrador(
                    nombre=ad['nombre'],
                    email=ad['email'],
                    password_hash=get_password_hash(ad['password']),
                    activo=True,
                )
                db.add(u)
                db.flush()
                u.roles.append(roles['administrador'])
                print(f"✓ Admin creado: {ad['email']}")
            admins.append(u)

        db.flush()

        # ─────────────────────────────────────────
        # TALLERES (tipo = 'taller', tabla hija: taller)
        # ─────────────────────────────────────────
        talleres_data = [
            {
                'nombre': 'Taller AutoFix',   'email': 'taller1@gmail.com', 'password': 'Taller123!',
                'nombre_comercial': 'AutoFix Mecánica',
                'direccion': 'Av. Cañoto 235, Primer Anillo, Santa Cruz de la Sierra',
                'latitud': -17.7833, 'longitud': -63.1821,
                'disponible': True, 'calificacion': 4.50,
            },
            {
                'nombre': 'Taller MotoSpeed', 'email': 'taller2@gmail.com', 'password': 'Taller123!',
                'nombre_comercial': 'MotoSpeed Taller',
                'direccion': 'Calle Murillo 890, Barrio Las Palmas, Santa Cruz de la Sierra',
                'latitud': -17.7694, 'longitud': -63.1960,
                'disponible': True, 'calificacion': 4.20,
            },
        ]

        talleres = []
        for td in talleres_data:
            u = db.query(Usuario).filter(Usuario.email == td['email']).first()
            if not u:
                u = Taller(
                    nombre=td['nombre'],
                    email=td['email'],
                    password_hash=get_password_hash(td['password']),
                    activo=True,
                    nombre_comercial=td['nombre_comercial'],
                    direccion=td['direccion'],
                    latitud=td['latitud'],
                    longitud=td['longitud'],
                    disponible=td['disponible'],
                    calificacion=td['calificacion'],
                )
                db.add(u)
                db.flush()
                u.roles.append(roles['taller'])
                print(f"✓ Taller creado: {td['email']}")
            talleres.append(u)

        db.flush()

        # ─────────────────────────────────────────
        # CLIENTES (tipo = 'cliente', tabla hija: cliente)
        # ─────────────────────────────────────────
        clientes_data = [
            {
                'nombre': 'Carlos Martínez', 'email': 'cliente1@gmail.com', 'password': 'Cliente123!',
                'telefono': '7777-1111', 'direccion_default': 'Av. San Martín 456, Barrio Equipetrol, Santa Cruz de la Sierra',
            },
            {
                'nombre': 'María López',     'email': 'cliente2@gmail.com', 'password': 'Cliente123!',
                'telefono': '7777-2222', 'direccion_default': 'Calle Beni 123, Barrio Hamacas, Santa Cruz de la Sierra',
            },
        ]

        clientes = []
        for cd in clientes_data:
            u = db.query(Usuario).filter(Usuario.email == cd['email']).first()
            if not u:
                u = Cliente(
                    nombre=cd['nombre'],
                    email=cd['email'],
                    password_hash=get_password_hash(cd['password']),
                    activo=True,
                    telefono=cd['telefono'],
                    direccion_default=cd['direccion_default'],
                )
                db.add(u)
                db.flush()
                u.roles.append(roles['cliente'])
                print(f"✓ Cliente creado: {cd['email']}")
            clientes.append(u)

        db.flush()

        # ─────────────────────────────────────────
        # TÉCNICOS (2 por taller)
        # ─────────────────────────────────────────
        tecnicos_data = [
            {'id_taller': talleres[0].id, 'nombre': 'Juan Pérez',    'especialidad': 'Motor y transmisión', 'disponible': True},
            {'id_taller': talleres[0].id, 'nombre': 'Pedro Gómez',   'especialidad': 'Electricidad automotriz', 'disponible': True},
            {'id_taller': talleres[1].id, 'nombre': 'Luis Hernández', 'especialidad': 'Frenos y suspensión', 'disponible': True},
            {'id_taller': talleres[1].id, 'nombre': 'Ana Ramírez',   'especialidad': 'Diagnóstico general', 'disponible': True},
        ]

        tecnicos = []
        for tec in tecnicos_data:
            existing = db.query(Tecnico).filter(
                Tecnico.id_taller == tec['id_taller'],
                Tecnico.nombre == tec['nombre']
            ).first()
            if not existing:
                existing = Tecnico(**tec)
                db.add(existing)
                db.flush()
                print(f"✓ Técnico creado: {tec['nombre']}")
            tecnicos.append(existing)

        db.flush()

        # ─────────────────────────────────────────
        # VEHÍCULOS (2 por cliente)
        # ─────────────────────────────────────────
        vehiculos_data = [
            {'id_cliente': clientes[0].id, 'marca': 'Toyota',  'modelo': 'Corolla', 'anio': 2018, 'placa': 'P123-456'},
            {'id_cliente': clientes[0].id, 'marca': 'Honda',   'modelo': 'Civic',   'anio': 2020, 'placa': 'P234-567'},
            {'id_cliente': clientes[1].id, 'marca': 'Nissan',  'modelo': 'Sentra',  'anio': 2019, 'placa': 'P345-678'},
            {'id_cliente': clientes[1].id, 'marca': 'Hyundai', 'modelo': 'Tucson',  'anio': 2021, 'placa': 'P456-789'},
        ]

        vehiculos = []
        for vd in vehiculos_data:
            existing = db.query(Vehiculo).filter(Vehiculo.placa == vd['placa']).first()
            if not existing:
                existing = Vehiculo(**vd)
                db.add(existing)
                db.flush()
                print(f"✓ Vehículo creado: {vd['placa']}")
            vehiculos.append(existing)

        db.flush()

        # ─────────────────────────────────────────
        # SOLICITUDES
        # ─────────────────────────────────────────
        solicitudes_data = [
            {
                'id_cliente': clientes[0].id, 'id_vehiculo': vehiculos[0].id,
                'latitud': -17.7833, 'longitud': -63.1821,
                'estado': EstadoSolicitud.ATENDIDO,
                'tipo_problema': 'Falla de motor',
                'prioridad': 'Alta',
                'descripcion_texto': 'El motor hace ruido extraño al arrancar.',
                'resumen_ia': 'Posible falla en el sistema de arranque o bujías.',
                'id_taller': talleres[0].id, 'id_tecnico': tecnicos[0].id,
            },
            {
                'id_cliente': clientes[0].id, 'id_vehiculo': vehiculos[1].id,
                'latitud': -17.7750, 'longitud': -63.1900,
                'estado': EstadoSolicitud.EN_PROCESO,
                'tipo_problema': 'Problema eléctrico',
                'prioridad': 'Media',
                'descripcion_texto': 'Las luces delanteras parpadean.',
                'resumen_ia': 'Posible falla en alternador o fusibles.',
                'id_taller': talleres[0].id, 'id_tecnico': tecnicos[1].id,
            },
            {
                'id_cliente': clientes[1].id, 'id_vehiculo': vehiculos[2].id,
                'latitud': -17.7694, 'longitud': -63.1960,
                'estado': EstadoSolicitud.PENDIENTE,
                'tipo_problema': 'Frenos',
                'prioridad': 'Alta',
                'descripcion_texto': 'Los frenos chirrían al frenar.',
                'resumen_ia': 'Posible desgaste de pastillas de freno.',
                'id_taller': None, 'id_tecnico': None,
            },
            {
                'id_cliente': clientes[1].id, 'id_vehiculo': vehiculos[3].id,
                'latitud': -17.7900, 'longitud': -63.2050,
                'estado': EstadoSolicitud.ATENDIDO,
                'tipo_problema': 'Suspensión',
                'prioridad': 'Baja',
                'descripcion_texto': 'El carro vibra mucho en carretera.',
                'resumen_ia': 'Posible desbalanceo de llantas o amortiguadores desgastados.',
                'id_taller': talleres[1].id, 'id_tecnico': tecnicos[2].id,
            },
        ]

        solicitudes = []
        for sd in solicitudes_data:
            existing = db.query(Solicitud).filter(
                Solicitud.id_cliente == sd['id_cliente'],
                Solicitud.tipo_problema == sd['tipo_problema']
            ).first()
            if not existing:
                existing = Solicitud(**sd)
                db.add(existing)
                db.flush()
                print(f"✓ Solicitud creada: {sd['tipo_problema']} - cliente {sd['id_cliente']}")
            solicitudes.append(existing)

        db.flush()

        # ─────────────────────────────────────────
        # EVIDENCIAS
        # ─────────────────────────────────────────
        evidencias_data = [
            {'id_solicitud': solicitudes[0].id, 'tipo': TipoEvidencia.IMAGEN, 'url_archivo': 'https://res.cloudinary.com/demo/image/upload/sample_motor.jpg'},
            {'id_solicitud': solicitudes[0].id, 'tipo': TipoEvidencia.TEXTO,  'url_archivo': 'https://res.cloudinary.com/demo/raw/upload/nota_motor.txt'},
            {'id_solicitud': solicitudes[1].id, 'tipo': TipoEvidencia.IMAGEN, 'url_archivo': 'https://res.cloudinary.com/demo/image/upload/sample_electrico.jpg'},
            {'id_solicitud': solicitudes[3].id, 'tipo': TipoEvidencia.AUDIO,  'url_archivo': 'https://res.cloudinary.com/demo/video/upload/sample_suspension.mp3'},
        ]

        for ev in evidencias_data:
            existing = db.query(Evidencia).filter(
                Evidencia.id_solicitud == ev['id_solicitud'],
                Evidencia.url_archivo == ev['url_archivo']
            ).first()
            if not existing:
                db.add(Evidencia(**ev))
                print(f"✓ Evidencia creada para solicitud {ev['id_solicitud']}")

        db.flush()

        # ─────────────────────────────────────────
        # PAGOS (solo para solicitudes ATENDIDO)
        # ─────────────────────────────────────────
        pagos_data = [
            {
                'id_solicitud': solicitudes[0].id,
                'monto_total': 150.00, 'metodo_pago': 'Stripe',
                'estado': 'Completado', 'comprobante_url': 'https://res.cloudinary.com/demo/image/upload/comprobante1.jpg',
                'stripe_payment_intent_id': 'pi_test_001', 'stripe_customer_id': 'cus_test_001',
            },
            {
                'id_solicitud': solicitudes[3].id,
                'monto_total': 200.00, 'metodo_pago': 'Stripe',
                'estado': 'Completado', 'comprobante_url': 'https://res.cloudinary.com/demo/image/upload/comprobante2.jpg',
                'stripe_payment_intent_id': 'pi_test_002', 'stripe_customer_id': 'cus_test_002',
            },
        ]

        pagos = []
        for pd in pagos_data:
            existing = db.query(Pago).filter(Pago.id_solicitud == pd['id_solicitud']).first()
            if not existing:
                existing = Pago(**pd)
                db.add(existing)
                db.flush()
                print(f"✓ Pago creado para solicitud {pd['id_solicitud']}")
            pagos.append(existing)

        db.flush()

        # ─────────────────────────────────────────
        # COMISIONES (manual, para evitar doble disparo del event listener)
        # ─────────────────────────────────────────
        for pago in pagos:
            existing = db.query(Comision).filter(Comision.id_pago == pago.id).first()
            if not existing:
                monto_com = float(pago.monto_total) * (settings.COMMISSION_PERCENTAGE / 100)
                db.add(Comision(
                    id_pago=pago.id,
                    monto=monto_com,
                    porcentaje=settings.COMMISSION_PERCENTAGE,
                    estado='Registrada',
                ))
                print(f"✓ Comisión creada para pago {pago.id}")

        db.flush()

        # ─────────────────────────────────────────
        # TOKENS DE NOTIFICACIÓN
        # ─────────────────────────────────────────
        tokens_data = [
            {'id_usuario': clientes[0].id, 'token_fcm': 'fcm_token_cliente1_android', 'plataforma': 'android', 'activo': True},
            {'id_usuario': clientes[1].id, 'token_fcm': 'fcm_token_cliente2_ios',     'plataforma': 'ios',     'activo': True},
            {'id_usuario': talleres[0].id, 'token_fcm': 'fcm_token_taller1_android',  'plataforma': 'android', 'activo': True},
            {'id_usuario': talleres[1].id, 'token_fcm': 'fcm_token_taller2_web',      'plataforma': 'web',     'activo': True},
        ]

        for td in tokens_data:
            existing = db.query(NotificacionToken).filter(
                NotificacionToken.token_fcm == td['token_fcm']
            ).first()
            if not existing:
                db.add(NotificacionToken(**td))
                print(f"✓ Token FCM creado para usuario {td['id_usuario']}")

        db.flush()

        # ─────────────────────────────────────────
        # PREFERENCIAS DE NOTIFICACIÓN
        # ─────────────────────────────────────────
        todos_usuarios = admins + talleres + clientes
        for u in todos_usuarios:
            existing = db.query(PreferenciaNotificacion).filter(
                PreferenciaNotificacion.id_usuario == u.id
            ).first()
            if not existing:
                db.add(PreferenciaNotificacion(
                    id_usuario=u.id,
                    actualizaciones_servicio=True,
                    promociones=False,
                    estado_pago=True,
                    recordatorios=True,
                ))
        print("✓ Preferencias de notificación creadas")
        db.flush()

        # ─────────────────────────────────────────
        # HISTORIAL DE NOTIFICACIONES
        # ─────────────────────────────────────────
        historial_data = [
            {
                'id_usuario': clientes[0].id, 'id_solicitud': solicitudes[0].id,
                'tipo': 'Push', 'titulo': 'Solicitud atendida',
                'contenido': 'Tu solicitud de falla de motor ha sido atendida exitosamente.',
                'estado': 'Leida',
            },
            {
                'id_usuario': clientes[0].id, 'id_solicitud': solicitudes[1].id,
                'tipo': 'Push', 'titulo': 'Técnico en camino',
                'contenido': 'El técnico Pedro Gómez está en camino para atender tu solicitud.',
                'estado': 'Enviada',
            },
            {
                'id_usuario': clientes[1].id, 'id_solicitud': solicitudes[3].id,
                'tipo': 'Push', 'titulo': 'Pago confirmado',
                'contenido': 'Tu pago de $200.00 ha sido confirmado.',
                'estado': 'Leida',
            },
            {
                'id_usuario': talleres[0].id, 'id_solicitud': solicitudes[1].id,
                'tipo': 'Push', 'titulo': 'Nueva solicitud asignada',
                'contenido': 'Se te ha asignado una nueva solicitud de problema eléctrico.',
                'estado': 'Leida',
            },
        ]

        for hd in historial_data:
            existing = db.query(HistorialNotificacion).filter(
                HistorialNotificacion.id_usuario == hd['id_usuario'],
                HistorialNotificacion.titulo == hd['titulo']
            ).first()
            if not existing:
                db.add(HistorialNotificacion(**hd))
                print(f"✓ Historial notificación: {hd['titulo']}")

        db.flush()

        # ─────────────────────────────────────────
        # BITÁCORA
        # ─────────────────────────────────────────
        bitacora_data = [
            {'id_usuario': admins[0].id,   'accion': 'LOGIN',            'ip_origen': '190.129.10.1',  'entidad_afectada': 'usuario'},
            {'id_usuario': clientes[0].id, 'accion': 'CREAR_SOLICITUD',  'ip_origen': '190.129.10.15', 'entidad_afectada': 'solicitud'},
            {'id_usuario': talleres[0].id, 'accion': 'ASIGNAR_TECNICO',  'ip_origen': '190.129.10.22', 'entidad_afectada': 'solicitud'},
            {'id_usuario': clientes[1].id, 'accion': 'REALIZAR_PAGO',    'ip_origen': '190.129.10.30', 'entidad_afectada': 'pago'},
        ]

        for bd in bitacora_data:
            db.add(Bitacora(**bd))
        print("✓ Registros de bitácora creados")

        db.flush()

        # ─────────────────────────────────────────
        # COMMIT FINAL
        # ─────────────────────────────────────────
        db.commit()
        print("\n✅ Seed completado exitosamente!")
        print("─────────────────────────────────────────")
        print("  Admins:   admin@gmail.com / Admin123!")
        print("            admin2@gmail.com / Admin123!")
        print("  Talleres: taller1@gmail.com / Taller123!")
        print("            taller2@gmail.com / Taller123!")
        print("  Clientes: cliente1@gmail.com / Cliente123!")
        print("            cliente2@gmail.com / Cliente123!")
        print("─────────────────────────────────────────")
        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error en seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
