# Optimizacion de rutas para reciclaje en St. Joseph

Aplicacion web completa para distribuir camiones de reciclaje y optimizar sus rutas diarias en St. Joseph, MO. El sistema expone un backend en Python que consume la API de optimizacion de Mapbox y un frontend ligero que visualiza las rutas, genera enlaces a Google Maps y guarda el historial.

## Caracteristicas principales

- Alta de empresas y autenticacion con tokens JWT.
- Registro dinamico de camiones con direcciones de inicio y fin.
- Carga de puntos de recoleccion (hasta 9 paradas por camion, tal como exige Google Maps).
- Asignacion automatica de zonas mediante clustering geografico y calculo de rutas optimizadas con Mapbox.
- Generacion de enlaces para compartir las rutas en Google Maps.
- Historial persistente de ejecuciones con posibilidad de consulta y eliminacion.

## Estructura del proyecto

```
software/
|- backend/
|  |- app/
|  |  |- main.py               # FastAPI y puntos de montaje
|  |  |- config.py             # Configuracion via .env / pydantic-settings
|  |  |- database.py           # Conexion SQLAlchemy (SQLite por defecto)
|  |  |- models.py             # Modelos ORM: usuarios y historial
|  |  |- schemas.py            # Modelos Pydantic para requests/responses
|  |  |- security.py           # Hashing + JWT
|  |  |- services/             # Integracion Mapbox + motor de optimizacion
|  |  \- routers/              # Rutas de autenticacion y optimizacion
|  |- requirements.txt
|  |- .env.example
|  \- seed.py
\- frontend/
   |- index.html
   |- styles.css
   |- app.js
   \- config.js
```

## Requisitos previos

- Python 3.11 o superior.
- No se requiere Node: el frontend es estatico y se sirve con cualquier servidor web.
- Token de Mapbox con acceso a Optimized Trips y Geocoding.

## Configuracion del backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y establece `MAPBOX_TOKEN`, `SECRET_KEY` y demas variables segun tu entorno. Puedes definir varias URLs permitidas para CORS usando `ALLOWED_ORIGINS` separadas por comas (por ejemplo, agrega la URL de Vercel).

### Inicializar base de datos y usuario de prueba

```bash
python seed.py
```

El comando crea `backend/data/optimizer.db` y registra el usuario `demo@wm.com` con contrasena `changeme123`.

### Ejecutar servidor FastAPI

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Endpoint de salud: `GET http://localhost:8000/health`.

## Configuracion del frontend

1. Edita `frontend/config.js` y reemplaza `YOUR_MAPBOX_TOKEN` por tu token real. Ajusta `apiBaseUrl` a la URL del backend.
2. Sirve la carpeta como sitio estatico, por ejemplo:

```bash
cd frontend
python3 -m http.server 5173
```

Visita `http://localhost:5173` en tu navegador.

## Flujo de uso

1. **Registro**: crea tu empresa con el formulario de alta y luego inicia sesion.
2. **Configura el dia**: agrega camiones (nombre, direccion de salida, direccion final) y las direcciones a visitar.
3. **Optimiza**: pulsa "Optimizar rutas". El sistema geocodifica, agrupa las paradas por zonas y llama a Mapbox Optimized Trips para cada camion.
4. **Resultados**:
   - Se muestra un resumen con distancia y duracion agregadas.
   - Se despliega la asignacion por camion con enlaces a Google Maps (maximo 9 paradas por camion mas origen/destino).
   - El mapa dibuja los recorridos optimizados con Mapbox GL.
   - El historial guarda la ejecucion con fecha y enlaces para futuras consultas.

## Endpoints principales

| Metodo | Ruta                      | Descripcion                                     |
| ------ | ------------------------- | ----------------------------------------------- |
| POST   | `/api/auth/register`      | Alta de empresa (email unico)                   |
| POST   | `/api/auth/login`         | Inicio de sesion (devuelve token bearer)        |
| POST   | `/api/routes/optimize`    | Ejecuta la doble optimizacion y guarda historial |
| GET    | `/api/routes/history`     | Lista las ultimas ejecuciones del usuario       |
| DELETE | `/api/routes/history/{id}` | Elimina una ejecucion del historial             |

## Notas tecnicas

- **Doble optimizacion**: utiliza clustering k-means (NumPy) para repartir paradas entre camiones respetando el limite de 9 paradas, y luego solicita a Mapbox la ruta optimizada de cada grupo.
- **Seguridad**: contrasenas cifradas con bcrypt y autenticacion via JWT Bearer.
- **Persistencia**: SQLite por defecto; basta con cambiar `DATABASE_URL` para usar otro motor compatible.
- **Google Maps**: cada ruta genera un enlace `https://www.google.com/maps/dir` con origen, destino y hasta nueve waypoints.

## Pruebas del backend

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest
```

Los tests utilizan una base SQLite temporal y stubs para Mapbox, por lo que no consumen la cuota del token ni modifican datos reales.

## Proximos pasos sugeridos

- Incorporar gestion completa de usuarios (cambio de contrasena, recuperacion, roles).
- Agregar validaciones de geocodificacion desde la interfaz (sugerencias de direcciones).
- Ampliar reportes diarios y estadisticas por zona o camion.
- Automatizar despliegue (Docker Compose, CI/CD) segun las necesidades de la empresa.

Con este codigo tienes un punto de partida funcional para la operacion de reciclaje en St. Joseph.
