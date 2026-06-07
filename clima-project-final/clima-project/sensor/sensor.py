"""
Simulador de Sensores Climáticos
─────────────────────────────────
Simula dos sensores físicos que consultan la temperatura
de Tegucigalpa y San Pedro Sula cada N segundos.
Las peticiones pasan por el Nginx Load Balancer.
"""

import os
import time
import requests
from datetime import datetime

API_URL      = os.environ.get("API_URL", "http://nginx/temperatura")
INTERVAL     = int(os.environ.get("INTERVAL_SECONDS", 30))
CIUDADES     = ["tegucigalpa", "san_pedro_sula"]

print("=" * 55)
print("  SIMULADOR DE SENSORES CLIMÁTICOS  ")
print(f"  URL API  : {API_URL}")
print(f"  Intervalo: {INTERVAL} segundos")
print(f"  Ciudades : {CIUDADES}")
print("=" * 55)

# Espera inicial para que Nginx y las APIs estén listas
print("[sensor] Esperando 15 s para que el sistema arranque...")
time.sleep(15)

ciclo = 0
while True:
    ciclo += 1
    print(f"\n[sensor] ── Ciclo #{ciclo} ─ {datetime.now().strftime('%H:%M:%S')} ──")

    for ciudad in CIUDADES:
        try:
            resp = requests.get(API_URL, params={"ciudad": ciudad}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                print(
                    f"  ✔ {data['ciudad']:20s} | "
                    f"{data['temperatura']:5.1f} {data['unidad']} | "
                    f"Respondió: {data['instancia_api']}"
                )
            else:
                print(f"  ✗ {ciudad}: HTTP {resp.status_code} – {resp.text[:80]}")
        except Exception as e:
            print(f"  ✗ {ciudad}: ERROR – {e}")

        # Pequeña pausa entre ciudades para no saturar
        time.sleep(2)

    print(f"[sensor] Durmiendo {INTERVAL} segundos...")
    time.sleep(INTERVAL)
