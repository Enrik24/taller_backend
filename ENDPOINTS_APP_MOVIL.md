# 📱 ENDPOINTS PARA APP MÓVIL - Taller Backend

## 📄 Resumen de Endpoints por Caso de Uso

### 🔐 **CU01 - REGISTRAR USUARIO (Cliente/Taller)**

#### `POST /api/register`
**Descripción:** Permite a nuevos usuarios (conductores o talleres) crear una cuenta en la plataforma.

**Request Body (multipart/form-data o JSON):**
```json
{
  "nombre": "Juan Pérez",
  "email": "juan@example.com",
  "password": "password123",
  "tipo": "cliente",  // o "taller"
  "telefono": "+5491112345678",  // (opcional, solo clientes)
  "direccion_default": "Av. Siempre Viva 123",  // (opcional, solo clientes)
  "nombre_comercial": "Taller Express",  // (opcional, solo talleres)
  "direccion": "Av. Libertador 456",  // (opcional, solo talleres)
  "latitud": -34.6037,  // (opcional, solo talleres)
  "longitud": -58.3816  // (opcional, solo talleres)
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "nombre": "Juan Pérez",
  "email": "juan@example.com",
  "tipo": "cliente",
  "activo": true,
  "intentos_fallidos": 0,
  "roles": [],
  "telefono": "+5491112345678",
  "direccion_default": "Av. Siempre Viva 123",
  "vehiculos": []
}
```

**Códigos de Error:**
- `400 Bad Request`: Email ya registrado o tipo inválido
- `422 Unprocessable Entity`: Datos de validación inválidos

---

### 🔑 **CU02 - INICIAR SESIÓN**

#### `POST /api/auth/token`
**Descripción:** Permite el acceso al sistema mediante credenciales. Retorna token JWT.

**Request Body (x-www-form-urlencoded):**
```
username: juan@example.com
password: password123
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR...
  "token_type": "bearer"
}
```

**Headers Importantes:**
- `Authorization: Bearer <token>` - Debe incluirse en todas las peticiones autenticadas

**Códigos de Error:**
- `401 Unauthorized`: Credenciales inválidas

---

### 👤 **CU03 - GESTIONAR PERFIL**

#### `GET /api/perfil`
**Descripción:** Obtiene los datos del usuario logueado.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "nombre": "Juan Pérez",
  "email": "juan@example.com",
  "tipo": "cliente",
  "activo": true,
  "intentos_fallidos": 0,
  "roles": [],
  "telefono": "+5491112345678",
  "direccion_default": "Av. Siempre Viva 123",
  "vehiculos": [
    {
      "id": 1,
      "marca": "Toyota",
      "modelo": "Corolla",
      "anio": 2020,
      "placa": "ABC123"
    }
  ]
}
```

#### `PUT /api/perfil`
**Descripción:** Actualiza los datos del perfil del usuario logueado.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "nombre": "Juan Pérez Actualizado",
  "email": "juan.nuevo@example.com",
  "telefono": "+5491199887766",
  "direccion_default": "Nueva dirección 456",
  "password": "nueva_password"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "nombre": "Juan Pérez Actualizado",
  "email": "juan.nuevo@example.com",
  /* ... resto de datos */
}
```

---

### 🚗 **GESTIÓN DE VEHÍCULOS (Solo Clientes)**

#### `GET /api/perfil/vehiculos`
**Descripción:** Lista todos los vehículos del cliente.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "marca": "Toyota",
    "modelo": "Corolla",
    "anio": 2020,
    "placa": "ABC123"
  }
]
```

#### `POST /api/perfil/vehiculos`
**Descripción:** Crea un nuevo vehículo para el cliente.

**Request Body:**
```json
{
  "marca": "Honda",
  "modelo": "Civic",
  "anio": 2021,
  "placa": "XYZ789"
}
```

**Response (201 Created):**
```json
{
  "id": 2,
  "marca": "Honda",
  "modelo": "Civic",
  "anio": 2021,
  "placa": "XYZ789"
}
```

#### `PUT /api/perfil/vehiculos/{vehiculo_id}`
**Descripción:** Actualiza un vehículo del cliente.

**Request Body:**
```json
{
  "marca": "Honda",
  "modelo": "Civic",
  "anio": 2022,
  "placa": "XYZ789"
}
```

#### `DELETE /api/perfil/vehiculos/{vehiculo_id}`
**Descripción:** Elimina un vehículo del cliente.

**Response:** `204 No Content`

---

### 🔧 **GESTIÓN DE TÉCNICOS (Solo Talleres)**

#### `GET /api/perfil/tecnicos`
**Descripción:** Lista todos los técnicos del taller.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "nombre": "Carlos Mécanico",
    "especialidad": "Motor",
    "disponible": true
  }
]
```

#### `POST /api/perfil/tecnicos`
**Descripción:** Crea un nuevo técnico para el taller.

**Request Body:**
```json
{
  "nombre": "María Técnica",
  "especialidad": "Electricidad",
  "disponible": true
}
```

**Response (201 Created):**
```json
{
  "id": 2,
  "nombre": "María Técnica",
  "especialidad": "Electricidad",
  "disponible": true
}
```

#### `PUT /api/perfil/tecnicos/{tecnico_id}`
**Descripción:** Actualiza un técnico del taller.

#### `DELETE /api/perfil/tecnicos/{tecnico_id}`
**Descripción:** Elimina un técnico del taller.

---

### 🚨 **CU04 - REPORTAR EMERGENCIA**

#### `POST /api/solicitudes`
**Descripción:** Reporta una emergencia con geolocalización, fotos, videos y audio.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form Data:**
```
descripcion_texto: "Mi coche no arranca en la autopista"
id_vehiculo: 1  // (opcional)
latitud: -34.6037  // (opcional)
longitud: -58.3816  // (opcional)
tipo_problema: "mecanico"  // (opcional)
prioridad: "alta"  // (opcional)
archivos[]: [fotos o videos]  // (opcional, múltiples archivos)
```

**Response (201 Created):**
```json
{
  "id": 1,
  "descripcion_texto": "Mi coche no arranca",
  "fecha_reporte": "2026-04-23T14:30:00",
  "estado": "Pendiente",
  "latitud": -34.6037,
  "longitud": -58.3816,
  "tipo_problema": "mecanico",
  "prioridad": "alta",
  "evidencias": [
    {
      "id": 1,
      "tipo": "imagen",
      "url": "https://cloudinary.com/...",
      "fecha_subida": "2026-04-23T14:30:00"
    }
  ],
  "cliente": {
    "id_usuario": 1,
    "nombre": "Juan Pérez"
  },
  "vehiculo": null
}
```

---

### 📊 **CU05 - CONSULTAR ESTADO DE SOLICITUD**

#### `GET /api/solicitudes/mis-solicitudes`
**Descripción:** Lista todas las solicitudes del cliente con su estado.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "descripcion_texto": "Mi coche no arranca",
    "fecha_reporte": "2026-04-23T14:30:00",
    "estado": "Atendido",
    "prioridad": "alta"
  },
  {
    "id": 2,
    "descripcion_texto": "Neumático pinchado",
    "fecha_reporte": "2026-04-22T10:15:00",
    "estado": "Pendiente",
    "prioridad": "media"
  }
]
```

**Estados posibles:**
- `Pendiente`: Solicitud recibida, esperando asignación
- `En proceso`: Taller aceptó y está en camino
- `Atendido`: Servicio completado

#### `GET /api/solicitudes/{solicitud_id}`
**Descripción:** Obtiene el detalle completo de una solicitud específica.

**Response (200 OK):**
```json
{
  "id": 1,
  "descripcion_texto": "Mi coche no arranca",
  "fecha_reporte": "2026-04-23T14:30:00",
  "estado": "Pendiente",
  "evidencias": [
    {
      "tipo": "imagen",
      "url": "https://cloudinary.com/..."
    }
  ],
  "latitud": -34.6037,
  "longitud": -58.3816
}
```

---

### 🏪 **CU06 - VER TALLER ASIGNADO Y TIEMPO ESTIMADO**

#### `GET /api/solicitudes/{solicitud_id}/taller-asignado`
**Descripción:** Muestra qué taller ha aceptado la solicitud y tiempo estimado de llegada.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": 5,
  "nombre_comercial": "Taller Express",
  "calificacion": 4.5,
  "direccion": "Av. Libertador 456",
  "latitud": -34.6000,
  "longitud": -58.3800,
  "telefono": "+5491122334455",
  "tiempo_estimado_min": 25
}
```

**Response (200 OK) - Sin taller asignado:**
```json
null
```

---

### 🔔 **CU07 - GESTIONAR NOTIFICACIONES PUSH**

#### `POST /api/notificaciones/token`
**Descripción:** Registra el token FCM del dispositivo para recibir notificaciones.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/x-www-form-urlencoded
```

**Request Body:**
```
token_fcm: fcm_token_del_dispositivo
plataforma: android  // o "ios"
```

**Response (201 Created):**
```json
{
  "message": "Token registrado exitosamente"
}
```

#### `GET /api/notificaciones/configuracion`
**Descripción:** Obtiene las preferencias de notificación del usuario.

**Response (200 OK):**
```json
{
  "actualizaciones_servicio": true,
  "promociones": false,
  "estado_pago": true,
  "recordatorios": true
}
```

#### `PUT /api/notificaciones/configuracion`
**Descripción:** Actualiza las preferencias de notificación.

**Query Parameters:**
```
actualizaciones_servicio: true
promociones: false
estado_pago: true
recordatorios: true
```

**Response (200 OK):**
```json
{
  "message": "Preferencias actualizadas"
}
```

---

### 💳 **CU08 - REALIZAR PAGO**

#### `POST /api/pagos/crear-intencion`
**Descripción:** Crea un PaymentIntent de Stripe para procesar el pago.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
```
solicitud_id: 1
monto: 1500.50
```

**Response (200 OK):**
```json
{
  "client_secret": "pi_123_secret_456",
  "payment_intent_id": "pi_123",
  "monto": 1500.50,
  "moneda": "ars"
}
```

**Códigos de Error:**
- `400 Bad Request`: Solicitud no está en estado "Atendido" o ya tiene pago
- `403 Forbidden`: No tiene permiso para pagar esta solicitud
- `404 Not Found`: Solicitud no encontrada

#### `GET /api/pagos/{solicitud_id}/comprobante`
**Descripción:** Obtiene los datos del pago/comprobante de una solicitud.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "solicitud_id": 1,
  "monto_total": 1500.50,
  "monto_comision": 150.00,
  "metodo_pago": "tarjeta",
  "estado": "completado",
  "fecha_pago": "2026-04-23T15:00:00",
  "comprobante_url": "https://.../comprobante.pdf",
  "stripe_payment_intent_id": "pi_123"
}
```

---

## 🔒 **Autenticación y Seguridad**

### Token JWT
Todos los endpoints (excepto `/api/register` y `/api/auth/token`) requieren autenticación.

**Incluir en headers:**
```
Authorization: Bearer <tu_token_jwt>
```

### Renovar Token
Los tokens tienen expiración. Si recibes `401 Unauthorized`, debes pedir al usuario que inicie sesión nuevamente.

---

## 📦 **Ejemplo Completo - Flujo de Emergencia (App Móvil)**

```dart
// 1. Iniciar sesión
final loginResponse = await http.post(
  Uri.parse('$baseUrl/api/auth/token'),
  body: {'username': 'usuario@email.com', 'password': 'password'},
);
final token = jsonDecode(loginResponse.body)['access_token'];

// 2. Registrar token FCM para notificaciones
await http.post(
  Uri.parse('$baseUrl/api/notificaciones/token'),
  headers: {'Authorization': 'Bearer $token'},
  body: {'token_fcm': fcmToken, 'plataforma': 'android'},
);

// 3. Reportar emergencia con foto
var request = http.MultipartRequest(
  'POST',
  Uri.parse('$baseUrl/api/solicitudes'),
);
request.headers['Authorization'] = 'Bearer $token';
request.fields['descripcion_texto'] = 'Neumático pinchado';
request.fields['latitud'] = '-34.6037';
request.fields['longitud'] = '-58.3816';

// Adjuntar foto
var foto = await http.MultipartFile.fromPath(
  'archivos', 
  'ruta/a/foto.jpg',
);
request.files.add(foto);

var response = await request.send();

// 4. Consultar estado de la solicitud
final solicitudesResponse = await http.get(
  Uri.parse('$baseUrl/api/solicitudes/mis-solicitudes'),
  headers: {'Authorization': 'Bearer $token'},
);

// 5. Ver taller asignado
final tallerResponse = await http.get(
  Uri.parse('$baseUrl/api/solicitudes/1/taller-asignado'),
  headers: {'Authorization': 'Bearer $token'},
);
```

---

## 🎯 **Endpoints por Rol**

### Para Clientes:
- ✅ `POST /api/register` - Registrarse
- ✅ `POST /api/auth/token` - Iniciar sesión
- ✅ `GET /api/perfil` - Ver perfil
- ✅ `PUT /api/perfil` - Actualizar perfil
- ✅ `GET /api/perfil/vehiculos` - Listar vehículos
- ✅ `POST /api/perfil/vehiculos` - Crear vehículo
- ✅ `POST /api/solicitudes` - Reportar emergencia
- ✅ `GET /api/solicitudes/mis-solicitudes` - Ver mis solicitudes
- ✅ `GET /api/solicitudes/{id}/taller-asignado` - Ver taller asignado
- ✅ `POST /api/notificaciones/token` - Registrar token FCM
- ✅ `GET/PUT /api/notificaciones/configuracion` - Configurar notificaciones
- ✅ `POST /api/pagos/crear-intencion` - Crear pago
- ✅ `GET /api/pagos/{id}/comprobante` - Ver comprobante

### Para Talleres:
- ✅ `POST /api/register` - Registrarse (como taller)
- ✅ `POST /api/auth/token` - Iniciar sesión
- ✅ `GET /api/perfil` - Ver perfil
- ✅ `PUT /api/perfil` - Actualizar perfil
- ✅ `GET /api/perfil/tecnicos` - Listar técnicos
- ✅ `POST /api/perfil/tecnicos` - Crear técnico
- ✅ `GET /api/solicitudes/disponibles` - Ver solicitudes disponibles
- ✅ `POST /api/solicitudes/{id}/aceptar` - Aceptar solicitud
- ✅ `POST /api/solicitudes/{id}/rechazar` - Rechazar solicitud
- ✅ `PUT /api/solicitudes/{id}/estado` - Actualizar estado