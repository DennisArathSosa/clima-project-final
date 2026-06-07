import os
import requests
import psycopg2
from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

INSTANCE_ID = os.environ.get("INSTANCE_ID", "API-UNKNOWN")

# Ciudades soportadas con sus coordenadas
CIUDADES = {
    "tegucigalpa": {"lat": 14.0818, "lon": -87.2068, "nombre": "Tegucigalpa"},
    "san_pedro_sula": {"lat": 15.5026, "lon": -88.0253, "nombre": "San Pedro Sula"},
}

def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", 5432),
        dbname=os.environ.get("DB_NAME", "clima_db"),
        user=os.environ.get("DB_USER", "clima_user"),
        password=os.environ.get("DB_PASS", "clima_pass"),
    )

def consultar_open_meteo(lat, lon):
    """Consulta temperatura actual desde Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "timezone": "America/Tegucigalpa",
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    temperatura = data["current"]["temperature_2m"]
    return temperatura

def guardar_lectura(ciudad_nombre, temperatura, lat, lon):
    """Guarda la lectura en la base de datos."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO temperatura_lecturas
            (ciudad, temperatura, unidad, latitud, longitud, instancia_api, fecha_hora)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (ciudad_nombre, temperatura, "°C", lat, lon, INSTANCE_ID, datetime.now()),
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return new_id

# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@app.route("/temperatura", methods=["GET"])
def get_temperatura():
    """Obtiene temperatura de una ciudad (por defecto Tegucigalpa)."""
    ciudad_key = request.args.get("ciudad", "tegucigalpa").lower().replace(" ", "_")

    if ciudad_key not in CIUDADES:
        return jsonify({
            "error": f"Ciudad '{ciudad_key}' no soportada. Usa: {list(CIUDADES.keys())}"
        }), 400

    info = CIUDADES[ciudad_key]
    try:
        temperatura = consultar_open_meteo(info["lat"], info["lon"])
        record_id = guardar_lectura(info["nombre"], temperatura, info["lat"], info["lon"])

        return jsonify({
            "ciudad": info["nombre"],
            "temperatura": temperatura,
            "unidad": "°C",
            "latitud": info["lat"],
            "longitud": info["lon"],
            "instancia_api": INSTANCE_ID,
            "timestamp": datetime.now().isoformat(),
            "id_registro": record_id,
        })
    except Exception as e:
        return jsonify({"error": str(e), "instancia_api": INSTANCE_ID}), 500


@app.route("/historial", methods=["GET"])
def get_historial():
    """Devuelve el historial de temperaturas por ciudad."""
    ciudad = request.args.get("ciudad", None)
    limit = int(request.args.get("limit", 50))

    conn = get_db_connection()
    cur = conn.cursor()

    if ciudad:
        cur.execute(
            """
            SELECT id, ciudad, temperatura, unidad, latitud, longitud,
                   instancia_api, fecha_hora
            FROM temperatura_lecturas
            WHERE LOWER(ciudad) = LOWER(%s)
            ORDER BY fecha_hora DESC
            LIMIT %s
            """,
            (ciudad, limit),
        )
    else:
        cur.execute(
            """
            SELECT id, ciudad, temperatura, unidad, latitud, longitud,
                   instancia_api, fecha_hora
            FROM temperatura_lecturas
            ORDER BY fecha_hora DESC
            LIMIT %s
            """,
            (limit,),
        )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    cols = ["id", "ciudad", "temperatura", "unidad", "latitud", "longitud",
            "instancia_api", "fecha_hora"]
    return jsonify([dict(zip(cols, r)) for r in
                    [{**dict(zip(cols, row)), "fecha_hora": row[7].isoformat()} for row in rows]])


@app.route("/resumen", methods=["GET"])
def get_resumen():
    """Devuelve resumen (min, max, promedio) por ciudad."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM resumen_temperatura")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    cols = ["ciudad", "fecha", "temp_minima", "temp_maxima", "temp_promedio", "total_lecturas"]
    return jsonify([{**dict(zip(cols, r)), "fecha": r[1].isoformat()} for r in rows])


@app.route("/instancias", methods=["GET"])
def get_instancias():
    """Muestra cuántas peticiones atendió cada instancia."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT instancia_api, COUNT(*) AS peticiones
        FROM temperatura_lecturas
        GROUP BY instancia_api
        ORDER BY instancia_api
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"instancia": r[0], "peticiones": r[1]} for r in rows])


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "instancia": INSTANCE_ID})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
