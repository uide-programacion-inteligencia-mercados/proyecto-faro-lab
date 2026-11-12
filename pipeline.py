# ============================================================================
# ARCHIVO: pipeline.py        (el PLANO y el PUNTO DE PARTIDA)    · MEJORADO S08
# QUÉ HACE:  Define las tareas del robot, de quién depende cada una, y la función main() que las lanza con el orquestador.
# RECIBE:    Los datos que traen los archivos de fuentes/ y las reglas de config.py.
# ENTREGA:   Tablas guardadas en data/, el reporte en reports/ y el registro en logs/. Termina con éxito o con error.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: las tareas y sus dependencias (diccionario TAREAS). Aquí agregas o quitas fuentes y pasos.
# ============================================================================
# Secuencia: BUSCAR, GUARDAR, LIMPIAR, CONTROLAR, ANALIZAR, MOSTRAR, INFORMAR (S08).
# Cada función t_xxx es UNA tarea: recibe lo que entregó la anterior y entrega su resultado.
import sys
import time

import bitacora
import config
import monitoreo
import analisis
import limpieza
import orquestador
import reporte
import reporte_pdf
import respaldo
from fuentes import banco_mundial, fmi, remax


def guardar(df, nombre):
    # Escribe una tabla como archivo CSV dentro de la carpeta data/.
    # S07 · ESCRITURA ATÓMICA: primero escribe un borrador (.tmp) y solo al final lo
    # cambia por el archivo de verdad. Si el robot se cae a la mitad, el archivo
    # anterior queda intacto: nunca hay un CSV cortado a medias.
    config.DATOS.mkdir(parents=True, exist_ok=True)
    destino = config.DATOS / nombre
    borrador = destino.with_suffix(".tmp")
    df.to_csv(borrador, index=False)                                  # GUARDAR (borrador)
    borrador.replace(destino)                                         # reemplazo en un solo movimiento


# --- TAREAS DE BÚSQUEDA: cada una pide datos a una fuente y guarda la copia cruda ---
def t_remax():
    df = remax.traer()
    guardar(df, "remax_crudo.csv")
    return df


def t_banco_mundial():
    df = banco_mundial.traer()
    guardar(df, "banco_mundial_crudo.csv")
    return df


def t_fmi():
    df = fmi.traer()
    guardar(df, "fmi_crudo.csv")
    return df


# --- TAREA DE LIMPIEZA: recibe los tres datos crudos y entrega tablas limpias ---
def t_limpiar(remax, banco_mundial, fmi):
    import pandas as pd
    anuncios, descartes = limpieza.limpiar_con_descartes(remax)
    macro = limpieza.limpiar_macro(pd.concat([banco_mundial, fmi], ignore_index=True))
    guardar(anuncios, "anuncios_limpios.csv")
    guardar(macro, "macro_limpia.csv")
    return {"anuncios": anuncios, "macro": macro, "descartes": descartes}


def t_control_calidad(limpiar):
    """El portero del pipeline: si los datos no son confiables, FALLA A PROPÓSITO y nada se guarda.
    Usa ErrorDeDatos: el orquestador sabe que reintentar no arregla datos malos."""
    a, lo, hi = limpiar["anuncios"], *config.MEDIANA_M2_PLAUSIBLE
    if len(a) < config.MIN_ANUNCIOS_LIMPIOS:
        raise orquestador.ErrorDeDatos(f"Control de calidad: solo {len(a)} anuncios limpios (mínimo {config.MIN_ANUNCIOS_LIMPIOS}).")
    mediana = a["precio_m2"].median()
    if not lo <= mediana <= hi:
        raise orquestador.ErrorDeDatos(f"Control de calidad: mediana de {mediana:.0f} USD/m² fuera de lo plausible ({lo}-{hi}).")
    if limpiar["macro"].empty:
        raise orquestador.ErrorDeDatos("Control de calidad: no llegó ningún dato macroeconómico.")
    bitacora.anotar("INFO", "control_calidad", "datos aprobados", anuncios=len(a), mediana_m2=round(float(mediana)))
    return limpiar


# --- TAREA DEL PLAN B VIVO (S08): si los datos de hoy fueron reales y el portero los aprobó, renueva el respaldo ---
def t_renovar_respaldo(control_calidad):
    try:
        return respaldo.renovar()
    except Exception as e:      # renovar el plan B nunca debe tumbar el informe del día
        bitacora.anotar("WARNING", "renovar_respaldo", "no se pudo renovar la copia de seguridad", error=str(e)[:200])
        return []


# --- TAREA DE ANÁLISIS: las cifras que responden la pregunta de negocio ---
def t_analizar(control_calidad):
    return analisis.analizar(control_calidad["anuncios"], control_calidad["macro"], control_calidad["descartes"])


# --- TAREA DE REPORTE: convierte las cifras en gráfico y texto ---
def t_reportar(analizar):
    return reporte.escribir(analizar)


# --- TAREA DE PDF (S08): imprime el informe. Necesita las cifras Y el gráfico que dibujó reportar ---
def t_reportar_pdf(analizar, reportar):
    return reporte_pdf.generar(analizar, reportar)


# EL PLANO (llamado DAG): cada tarea dice quién es y de quién depende.
# Formato:  "nombre": (función, ["tareas que deben terminar antes"])
# El orquestador ordena todo solo; tú solo describes las dependencias.
TAREAS = {
    "remax": (t_remax, []),
    "banco_mundial": (t_banco_mundial, []),
    "fmi": (t_fmi, []),
    "limpiar": (t_limpiar, ["remax", "banco_mundial", "fmi"]),
    "control_calidad": (t_control_calidad, ["limpiar"]),
    "renovar_respaldo": (t_renovar_respaldo, ["control_calidad"]),   # S08 · plan B vivo
    "analizar": (t_analizar, ["control_calidad"]),
    "reportar": (t_reportar, ["analizar"]),
    "reportar_pdf": (t_reportar_pdf, ["analizar", "reportar"]),   # S08 · el informe en PDF
}


def t_falla_simulada():
    # SIMULACRO: se hace pasar por RE/MAX y no contesta nunca, ni siquiera con plan B.
    # Sirve para comprobar que el semáforo se pone rojo y que la alerta llega.
    raise ConnectionError("SIMULACRO: la fuente no contesta (falla provocada a propósito)")


def main():
    # Lanza el orquestador, guarda el registro, decide el semáforo y avisa con un código de salida:
    # 0 = verde o amarillo (círculo verde en GitHub), 1 = rojo (círculo rojo y alerta).
    inicio = time.time()
    tareas = dict(TAREAS)
    if config.SIMULAR_FALLA:
        tareas["remax"] = (t_falla_simulada, [])
    bitacora.anotar("INFO", "pipeline", "inicio de la corrida", modo=config.MODO, simulacro=config.SIMULAR_FALLA)
    _, registro = orquestador.ejecutar(tareas)
    orquestador.guardar_registro(registro)
    salud = monitoreo.registrar(registro, time.time() - inicio)
    monitoreo.publicar_resumen()
    bitacora.recortar()
    print("RESULTADO:", salud["estado"].upper(), "·", salud["motivo"])
    sys.exit(1 if salud["estado"] == "rojo" else 0)


if __name__ == "__main__":
    main()
