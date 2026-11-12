# ============================================================================
# ARCHIVO: orquestador.py        (el DIRECTOR DE ORQUESTA)
# QUÉ HACE:  Ejecuta cada tarea cuando sus dependencias terminaron, reintenta si una falla y omite las que dependían de una caída.
# RECIBE:    El diccionario TAREAS de pipeline.py.
# ENTREGA:   Los resultados de cada tarea y un registro (logs/ultima_corrida.json) que dice qué pasó.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: normalmente nada: es el mismo director para cualquier proyecto. Solo ajusta REINTENTOS y ESPERA_SEG en config.py.
# ============================================================================
import json
import time
from datetime import datetime, timezone

import config


def orden_de_ejecucion(tareas):
    # Decide el orden: una tarea sale cuando todas las que necesita ya salieron.
    # Si dos tareas se esperan entre sí, avisa del ciclo en vez de quedarse trabado.
    # tareas = {"nombre": (funcion, ["tareas de las que depende"])}
    listo, pendientes = [], dict(tareas)
    while pendientes:
        salen = [n for n, (_, deps) in pendientes.items() if all(d in listo for d in deps)]
        if not salen:
            raise ValueError("Hay un ciclo: dos tareas se esperan entre sí.")
        for n in sorted(salen):
            listo.append(n)
            del pendientes[n]
    return listo


def ejecutar(tareas, reintentos=None, espera=None):
    reintentos = config.REINTENTOS if reintentos is None else reintentos
    espera = config.ESPERA_SEG if espera is None else espera
    # Recorre las tareas en orden. Si falla una, la reintenta; si sigue fallando,
    # las tareas que dependían de ella se OMITEN (no se corre trabajo sobre datos malos).
    resultados, registro = {}, []
    for nombre in orden_de_ejecucion(tareas):
        funcion, deps = tareas[nombre]
        if any(registro_de(registro, d) != "ok" for d in deps):
            registro.append({"tarea": nombre, "estado": "omitida", "motivo": "falló una tarea previa"})
            print(f"-- {nombre}: omitida")
            continue
        for intento in range(1, reintentos + 2):
            try:   # si algo dentro falla, el except de abajo lo atrapa y se reintenta
                print(f"-> {nombre} (intento {intento})")
                resultados[nombre] = funcion(**{d: resultados[d] for d in deps})
                registro.append({"tarea": nombre, "estado": "ok", "intentos": intento})
                break
            except Exception as e:
                print(f"   falló: {e}")
                if intento > reintentos:
                    registro.append({"tarea": nombre, "estado": "fallo", "error": str(e), "intentos": intento})
                else:
                    time.sleep(espera)
    return resultados, registro


def registro_de(registro, nombre):
    # Busca en el registro cómo terminó una tarea ("ok", "fallo" u "omitida").
    return next((r["estado"] for r in registro if r["tarea"] == nombre), None)


def guardar_registro(registro):
    # Escribe logs/ultima_corrida.json: la hora y el estado de cada tarea. Sirve para saber qué pasó.
    config.LOGS.mkdir(parents=True, exist_ok=True)
    corrida = {"inicio_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tareas": registro}
    (config.LOGS / "ultima_corrida.json").write_text(json.dumps(corrida, ensure_ascii=False, indent=2), encoding="utf-8")
    return corrida
