# ============================================================================
# ARCHIVO: bitacora.py        (el CUADERNO DE BITÁCORA)            · NUEVO S07
# QUÉ HACE:  Anota cada cosa importante que hace el robot, una línea por
#            evento, en un formato que una persona y una máquina pueden leer.
# RECIBE:    Lo que cada tarea quiera contar: nivel, tarea, evento y detalles.
# ENTREGA:   logs/bitacora.jsonl (una línea JSON por evento) y un mensaje
#            en pantalla. En GitHub, los avisos y errores salen en amarillo
#            y rojo en la pantalla de la corrida.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: nada; solo decides QUÉ anotar y con
#            qué nivel. Es el mismo cuaderno para cualquier proyecto.
# ============================================================================
# Por qué no basta con print(): un print se pierde cuando la máquina de GitHub
# se apaga y no se puede filtrar. Una línea de bitácora tiene SIEMPRE los mismos
# campos (cuándo, qué corrida, qué nivel, qué tarea, qué pasó), así que mañana
# se puede preguntar: «¿cuántas veces falló RE/MAX este mes?».
#
# Los tres niveles que usamos:
#   INFO    = todo normal, para dejar constancia      (verde)
#   WARNING = funcionó, pero con un plan B o algo raro (amarillo)
#   ERROR   = falló y alguien tiene que mirar         (rojo)
import json
import os
from datetime import datetime, timezone

import config

# Cada corrida tiene un número. En GitHub es el número de la corrida (run id);
# en Colab o en tu computadora se arma con la fecha y la hora.
CORRIDA_ID = os.environ.get("GITHUB_RUN_ID") or datetime.now(timezone.utc).strftime("local-%Y%m%dT%H%M%S")
EN_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"


def archivo():
    # Se calcula cada vez (y no una sola vez al inicio) para que las pruebas
    # puedan mover la carpeta logs/ a un lugar temporal.
    return config.LOGS / "bitacora.jsonl"


def anotar(nivel, tarea, evento, **detalles):
    """Escribe una línea en la bitácora y la muestra en pantalla."""
    fila = {
        "momento_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corrida": CORRIDA_ID,
        "nivel": nivel,
        "tarea": tarea,
        "evento": evento,
        **detalles,
    }
    config.LOGS.mkdir(parents=True, exist_ok=True)
    with open(archivo(), "a", encoding="utf-8") as f:              # "a" = agregar al final, nunca borrar
        f.write(json.dumps(fila, ensure_ascii=False, default=str) + "\n")

    extra = " · " + ", ".join(f"{k}={v}" for k, v in detalles.items()) if detalles else ""
    print(f"[{nivel:<7}] {tarea:<16} {evento}{extra}")
    # En GitHub Actions, estas dos líneas especiales pintan el aviso en la pantalla de la corrida.
    if EN_GITHUB and nivel == "WARNING":
        print(f"::warning title={tarea}::{evento}")
    if EN_GITHUB and nivel == "ERROR":
        print(f"::error title={tarea}::{evento}")
    return fila


def leer():
    """Devuelve la bitácora como lista de diccionarios (vacía si aún no existe)."""
    if not archivo().exists():
        return []
    return [json.loads(l) for l in archivo().read_text(encoding="utf-8").splitlines() if l.strip()]


def recortar(max_lineas=None):
    """Deja solo las últimas líneas para que el archivo no crezca sin fin."""
    max_lineas = max_lineas or config.BITACORA_MAX_LINEAS
    if not archivo().exists():
        return
    lineas = archivo().read_text(encoding="utf-8").splitlines()
    if len(lineas) > max_lineas:
        archivo().write_text("\n".join(lineas[-max_lineas:]) + "\n", encoding="utf-8")
