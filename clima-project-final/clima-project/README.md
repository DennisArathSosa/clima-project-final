# Sistema de Sensores Climaticos con Load Balancer

## Arquitectura del sistema

```
+-------------------------------------------------------------+
|                     SENSOR SIMULADO                          |
|   sensor.py -> consulta /temperatura?ciudad=tegucigalpa      |
|             -> consulta /temperatura?ciudad=san_pedro_sula   |
+----------------------+--------------------------------------+
                       | HTTP cada 30 segundos
                       v
+-------------------------------------------------------------+
|              NGINX LOAD BALANCER  :8080                      |
|            Round-Robin entre API-1, API-2, API-3             |
+------+----------------+-------------------+-----------------+
       |                |                   |
       v                v                   v
  +---------+     +---------+         +---------+
  |  API-1  |     |  API-2  |         |  API-3  |
  |  :5000  |     |  :5000  |         |  :5000  |
  +----+----+     +----+----+         +----+----+
       |                |                   |
       +----------------+-------------------+
                        | Consulta temperatura actual
                        v
            +----------------------+
            |    Open-Meteo API    |
            | api.open-meteo.com   |
            +----------------------+
                        |
                        v
         +----------------------------+
         |   PostgreSQL :5432          |
         |  tabla: temperatura_        |
         |         lecturas            |
         +----------------------------+
                        |
                        v
         +----------------------------+
         |   Jupyter Notebook :8888   |
         |  analisis_clima.ipynb      |
         |  -> Graficos de temp.      |
         |  -> Resumen min/max/avg    |
         |  -> Distribucion balanceo  |
         +----------------------------+
```

## Requisitos previos

- Docker Desktop instalado y corriendo
- Docker Compose v2+
- Conexion a internet (para Open-Meteo)

## Como levantar el sistema

```bash
# 1. Entrar a la carpeta del proyecto
cd clima-project

# 2. Construir y levantar todo
docker compose up --build -d

# 3. Verificar que todos los contenedores esten corriendo
docker compose ps
```

Deben aparecer 7 contenedores con status "running" o "healthy":
- clima_db
- clima_api1
- clima_api2
- clima_api3
- clima_nginx
- clima_sensor
- clima_jupyter

## Como acceder a cada parte del sistema

### API via Nginx Load Balancer

Abrir en el navegador o usar curl:

```
http://localhost:8080/temperatura?ciudad=tegucigalpa
http://localhost:8080/temperatura?ciudad=san_pedro_sula
http://localhost:8080/historial
http://localhost:8080/instancias
http://localhost:8080/resumen
```

### Jupyter Notebook

Abrir directamente en el navegador con esta URL:

```
http://localhost:8888/lab/tree/work/analisis_clima.ipynb
```

Una vez abierto el notebook:
1. Agregar una celda al inicio con el siguiente codigo e instalar dependencias:

```python
import subprocess
subprocess.run(["pip", "install", "psycopg2-binary", "pandas", "matplotlib", "seaborn"],
               capture_output=True)
print("Instalacion completa")
```

2. Ejecutar esa celda primero (Shift+Enter)
3. Luego ejecutar el resto: Run -> Run All Cells

El notebook genera 3 graficos:
- grafico_temperatura_dia.png — temperatura por hora por ciudad
- grafico_resumen_ciudades.png — minima, maxima y promedio por ciudad
- grafico_balanceo_carga.png — peticiones atendidas por cada instancia

## Verificar el balanceo de carga

```
http://localhost:8080/instancias
```

Muestra cuantas peticiones atendio cada instancia (API-1, API-2, API-3).

Tambien se puede verificar desde la terminal haciendo varias peticiones seguidas:

```bash
for i in 1 2 3 4 5 6; do
  curl -s http://localhost:8080/health
  echo ""
done
```

Se observara que las respuestas rotan entre API-1, API-2 y API-3.

## Apagar el sistema

```bash
docker compose down
```

## Estructura del proyecto

```
clima-project/
|-- docker-compose.yml
|-- README.md
|-- db-init/
|   `-- init.sql              <- Crea la tabla y vista en PostgreSQL
|-- api/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- app.py                <- Flask API (3 instancias del mismo codigo)
|-- nginx/
|   |-- Dockerfile
|   `-- nginx.conf            <- Round-robin entre api1, api2, api3
|-- sensor/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- sensor.py             <- Simula sensores enviando peticiones cada 30s
`-- notebook/
    `-- analisis_clima.ipynb  <- Analisis y graficos en Python
```

## Tabla en base de datos

```sql
temperatura_lecturas (
    id            SERIAL PRIMARY KEY,
    ciudad        VARCHAR(100),      -- "Tegucigalpa" / "San Pedro Sula"
    temperatura   DECIMAL(5,2),      -- ej: 28.50
    unidad        VARCHAR(10),       -- "C"
    latitud       DECIMAL(9,6),
    longitud      DECIMAL(9,6),
    instancia_api VARCHAR(20),       -- "API-1" / "API-2" / "API-3"
    fecha_hora    TIMESTAMP          -- momento de la lectura
)
```

## Endpoints disponibles

| Endpoint | Descripcion |
|---|---|
| GET /temperatura?ciudad=tegucigalpa | Temperatura actual de Tegucigalpa |
| GET /temperatura?ciudad=san_pedro_sula | Temperatura actual de San Pedro Sula |
| GET /historial?ciudad=tegucigalpa&limit=20 | Ultimas N lecturas de una ciudad |
| GET /resumen | Minima, maxima y promedio por ciudad |
| GET /instancias | Peticiones atendidas por cada API |
| GET /health | Estado de la instancia que responde |

## Conclusion tecnica

Se uso un Load Balancer (Nginx) para distribuir las peticiones entre tres instancias de API,
simulando un entorno de produccion donde la carga se reparte para evitar que un solo servidor
se sature. Cada instancia es identica en codigo pero se identifica con un ID distinto (API-1,
API-2, API-3) para poder rastrear cuantas peticiones atendio cada una.

La persistencia en base de datos (PostgreSQL) permite conservar el historico de temperaturas
y analizarlo despues con Jupyter Notebook, lo cual conecta directamente con el concepto de
Big Data: capturar datos continuamente, almacenarlos y procesarlos para extraer informacion util.

El simulador de sensores reemplaza sensores fisicos reales, enviando peticiones periodicas
como lo haria un dispositivo IoT en un entorno real de monitoreo climatico.
