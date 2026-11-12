# ============================================================================
# ARCHIVO: orquestador.py        (el DIRECTOR DE ORQUESTA)        · MEJORADO S07
# QUÉ HACE:  Ejecuta cada tarea cuando sus dependencias terminaron, reintenta
#            si una falla (esperando cada vez más), omite las que dependían de
#            una caída y anota todo en la bitácora.
# RECIBE:    El diccionario TAREAS de pipeline.py.
# ENTREGA:   Los resultados de cada tarea y un registro (logs/ultima_corrida.json).
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: normalmente nada. Ajusta REINTENTOS y
#            ESPERA_SEG en config.py.
# ============================================================================
# Novedades de la semana 7:
#   1. ESPERA CRECIENTE: 3 s, luego 6 s, luego 12 s. Si la fuente está saturada,
#      insistir de inmediato empeora las cosas; dar aire le permite recuperarse.
#   2. NO REINTENTAR LO QUE NO SE ARREGLA SOLO: si el problema son los DATOS
#      (ErrorDeDatos), repetir no sirve: se detiene a la primera.
#   3. BITÁCORA: cada intento, cada falla y cada omisión queda anotada.
import json
import time
from datetime import datetime, timezone

import bitacora
import config


class ErrorDeDatos(ValueError):
    """Un problema con los DATOS (no con la red): reintentar no lo arregla."""


def orden_de_ejecucion(tareas):
    # Decide el orden: una tarea sale cuando todas las que necesita ya salieron.
    # Si dos tareas se esperan entre sí, avisa del ciclo en vez de quedarse trabado.
    listo, pendientes = [], dict(tareas)
    while pendientes:
        salen = [n for n, (_, deps) in pendientes.items() if all(d in listo for d in deps)]
        if not salen:
            raise ValueError("Hay un ciclo: dos tareas se esperan entre sí.")
        for n in sorted(salen):
            listo.append(n)
            del pendientes[n]
    return listo


def espera_para(intento, espera_inicial):
    # Espera creciente (en inglés, «exponential backoff»): se duplica en cada intento.
    # intento 1 -> espera_inicial, intento 2 -> el doble, intento 3 -> el cuádruple...
    return espera_inicial * 2 ** (intento - 1)


def ejecutar(tareas, reintentos=None, espera=None):
    reintentos = config.REINTENTOS if reintentos is None else reintentos
    espera = config.ESPERA_SEG if espera is None else espera
    resultados, registro = {}, []
    for nombre in orden_de_ejecucion(tareas):
        funcion, deps = tareas[nombre]
        caidas = [d for d in deps if registro_de(registro, d) != "ok"]
        if caidas:
            registro.append({"tarea": nombre, "estado": "omitida", "motivo": f"falló {', '.join(caidas)}"})
            bitacora.anotar("WARNING", nombre, "omitida: depende de una tarea que falló", depende_de=caidas)
            continue
        inicio = time.time()
        for intento in range(1, reintentos + 2):
            try:
                resultados[nombre] = funcion(**{d: resultados[d] for d in deps})
                seg = round(time.time() - inicio, 1)
                registro.append({"tarea": nombre, "estado": "ok", "intentos": intento, "segundos": seg})
                bitacora.anotar("INFO", nombre, "terminó bien", intentos=intento, segundos=seg)
                break
            except ErrorDeDatos as e:
                # Los datos están mal: reintentar daría el mismo resultado. Se detiene ya.
                registro.append({"tarea": nombre, "estado": "fallo", "error": str(e), "intentos": intento,
                                 "tipo": "datos"})
                bitacora.anotar("ERROR", nombre, str(e), tipo="datos", intentos=intento)
                break
            except Exception as e:
                if intento > reintentos:
                    registro.append({"tarea": nombre, "estado": "fallo", "error": str(e), "intentos": intento,
                                     "tipo": "fuente"})
                    bitacora.anotar("ERROR", nombre, f"falló después de {intento} intentos: {e}", tipo="fuente")
                else:
                    pausa = espera_para(intento, espera)
                    bitacora.anotar("WARNING", nombre, f"intento {intento} falló; espero {pausa} s y reintento",
                                    error=str(e)[:200])
                    time.sleep(pausa)
    return resultados, registro


def registro_de(registro, nombre):
    # Busca en el registro cómo terminó una tarea ("ok", "fallo" u "omitida").
    return next((r["estado"] for r in registro if r["tarea"] == nombre), None)


def guardar_registro(registro):
    # Escribe logs/ultima_corrida.json: la foto de la ÚLTIMA corrida (se reemplaza cada vez).
    config.LOGS.mkdir(parents=True, exist_ok=True)
    corrida = {"corrida": bitacora.CORRIDA_ID,
               "inicio_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "tareas": registro}
    (config.LOGS / "ultima_corrida.json").write_text(json.dumps(corrida, ensure_ascii=False, indent=2), encoding="utf-8")
    return corrida
