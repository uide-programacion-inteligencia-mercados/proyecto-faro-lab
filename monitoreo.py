# ============================================================================
# ARCHIVO: monitoreo.py        (el TABLERO DE SALUD)                 · NUEVO S07
# QUÉ HACE:  Al final de cada corrida decide un semáforo (verde, amarillo o
#            rojo), lo guarda en el historial de salud y escribe un resumen
#            que GitHub muestra en la pantalla de la corrida.
# RECIBE:    El registro de tareas del orquestador y la bitácora de la corrida.
# ENTREGA:   logs/salud.csv (una fila por corrida), logs/estado.md y el estado.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: las reglas del semáforo y
#            DIAS_MAX_SIN_DATO_REAL en config.py.
# ============================================================================
# El semáforo:
#   VERDE    = todas las tareas terminaron bien con datos de la fuente real.
#   AMARILLO = terminó, pero usó un plan B o tuvo que reintentar. Se tolera.
#   ROJO     = algo falló, o llevamos demasiados días sin dato real
#              (un amarillo que se repite días y días es un FALLO SILENCIOSO).
# Solo el ROJO detiene la corrida con error y dispara la alerta.
import os
from datetime import date, datetime, timezone

import pandas as pd

import bitacora
import config

COLUMNAS = ["fecha_utc", "corrida", "estado", "motivo", "segundos", "tareas_ok", "tareas_fallo",
            "tareas_omitidas", "uso_respaldo", "dias_sin_dato_real"]


def archivo_salud():
    return config.LOGS / "salud.csv"


def dias_sin_dato_real(hoy=None):
    """Días desde la última fecha guardada en el histórico (que solo recibe datos reales)."""
    resumen = config.HISTORICO / "resumen_diario.csv"
    if not resumen.exists():
        return None                       # proyecto nuevo: aún no hay con qué medir
    h = pd.read_csv(resumen)
    if h.empty:
        return None
    ultima = date.fromisoformat(str(h["fecha"].max()))
    return ((hoy or date.today()) - ultima).days


def decidir_estado(registro, eventos, dias_sin_real):
    """Devuelve (estado, motivo)."""
    fallos = [r["tarea"] for r in registro if r["estado"] == "fallo"]
    omitidas = [r["tarea"] for r in registro if r["estado"] == "omitida"]
    if fallos:
        return "rojo", f"falló: {', '.join(fallos)}" + (f"; omitidas: {', '.join(omitidas)}" if omitidas else "")
    if omitidas:
        return "rojo", f"omitidas: {', '.join(omitidas)}"
    if dias_sin_real is not None and dias_sin_real > config.DIAS_MAX_SIN_DATO_REAL:
        return "rojo", f"{dias_sin_real} días sin dato real (máximo {config.DIAS_MAX_SIN_DATO_REAL}): fallo silencioso"
    avisos = [e for e in eventos if e["nivel"] == "WARNING"]
    if avisos:
        return "amarillo", "; ".join(sorted({f"{e['tarea']}: {e['evento']}" for e in avisos}))[:250]
    return "verde", "todo bien con datos reales"


def registrar(registro, segundos):
    """Decide el semáforo de esta corrida y lo guarda en logs/salud.csv."""
    eventos = [e for e in bitacora.leer() if e.get("corrida") == bitacora.CORRIDA_ID]
    dias = dias_sin_dato_real()
    estado, motivo = decidir_estado(registro, eventos, dias)
    fila = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corrida": bitacora.CORRIDA_ID,
        "estado": estado,
        "motivo": motivo,
        "segundos": round(segundos, 1),
        "tareas_ok": sum(r["estado"] == "ok" for r in registro),
        "tareas_fallo": sum(r["estado"] == "fallo" for r in registro),
        "tareas_omitidas": sum(r["estado"] == "omitida" for r in registro),
        "uso_respaldo": any("respaldo" in e["evento"] for e in eventos),
        "dias_sin_dato_real": "" if dias is None else dias,
    }
    config.LOGS.mkdir(parents=True, exist_ok=True)
    salud = pd.read_csv(archivo_salud()) if archivo_salud().exists() else pd.DataFrame(columns=COLUMNAS)
    # IDEMPOTENCIA: si GitHub vuelve a correr la MISMA corrida («Re-run jobs»),
    # se reemplaza su fila en lugar de duplicarla.
    salud = salud[salud["corrida"].astype(str) != str(bitacora.CORRIDA_ID)]
    salud = pd.concat([salud, pd.DataFrame([fila])], ignore_index=True)
    salud.to_csv(archivo_salud(), index=False)
    nivel = {"verde": "INFO", "amarillo": "WARNING", "rojo": "ERROR"}[estado]
    bitacora.anotar(nivel, "monitoreo", f"semáforo {estado.upper()}: {motivo}")
    return fila


def resumen_markdown(ultimas=7):
    """Tabla de las últimas corridas + indicadores de salud de los últimos 30 registros."""
    if not archivo_salud().exists():
        return "Aún no hay corridas registradas.\n"
    s = pd.read_csv(archivo_salud())
    icono = {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}
    ult = s.tail(30)
    exito = 100 * (ult["estado"] != "rojo").mean()
    hoy = s.iloc[-1]
    filas = "\n".join(f"| {r.fecha_utc[:16].replace('T', ' ')} | {icono.get(r.estado, '')} {r.estado} | "
                      f"{r.segundos} | {str(r.motivo)[:90]} |" for r in s.tail(ultimas).iloc[::-1].itertuples())
    dias = hoy["dias_sin_dato_real"]
    return f"""## Salud del Observatorio

**Hoy:** {icono.get(hoy['estado'], '')} **{str(hoy['estado']).upper()}** · {hoy['motivo']}

| Indicador | Valor |
|---|---|
| Corridas sin rojo (últimas {len(ult)}) | {exito:.0f} % |
| Duración media | {ult['segundos'].mean():.0f} s |
| Días sin dato real | {'sin histórico aún' if pd.isna(dias) or dias == '' else int(dias)} |

### Últimas corridas
| Fecha (UTC) | Estado | Segundos | Motivo |
|---|---|---|---|
{filas}
"""


def publicar_resumen():
    """Escribe logs/estado.md y, si corre en GitHub, el resumen de la corrida."""
    texto = resumen_markdown()
    (config.LOGS / "estado.md").write_text(texto, encoding="utf-8")
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(texto)
    return texto
