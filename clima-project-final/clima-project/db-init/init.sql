-- Tabla principal de lecturas de temperatura
CREATE TABLE IF NOT EXISTS temperatura_lecturas (
    id SERIAL PRIMARY KEY,
    ciudad VARCHAR(100) NOT NULL,
    temperatura DECIMAL(5,2) NOT NULL,
    unidad VARCHAR(10) DEFAULT '°C',
    latitud DECIMAL(9,6) NOT NULL,
    longitud DECIMAL(9,6) NOT NULL,
    instancia_api VARCHAR(20) NOT NULL,
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_ciudad ON temperatura_lecturas(ciudad);
CREATE INDEX IF NOT EXISTS idx_fecha ON temperatura_lecturas(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_instancia ON temperatura_lecturas(instancia_api);

-- Vista útil para el análisis
CREATE OR REPLACE VIEW resumen_temperatura AS
SELECT
    ciudad,
    DATE(fecha_hora) AS fecha,
    ROUND(MIN(temperatura)::numeric, 2) AS temp_minima,
    ROUND(MAX(temperatura)::numeric, 2) AS temp_maxima,
    ROUND(AVG(temperatura)::numeric, 2) AS temp_promedio,
    COUNT(*) AS total_lecturas
FROM temperatura_lecturas
GROUP BY ciudad, DATE(fecha_hora)
ORDER BY fecha DESC, ciudad;
