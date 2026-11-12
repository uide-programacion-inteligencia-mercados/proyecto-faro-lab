# ============================================================================
# ARCHIVO: pipeline.py        (el PLANO y el PUNTO DE PARTIDA)
# QUÉ HACE:  Define las tareas del robot, de quién depende cada una, y la función main() que las lanza con el orquestador.
# RECIBE:    Los datos que traen los archivos de fuentes/ y las reglas de config.py.
# ENTREGA:   Tablas guardadas en data/, el reporte en reports/ y el registro en logs/. Termina con éxito o con error.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: las tareas y sus dependencias (diccionario TAREAS). Aquí agregas o quitas fuentes y pasos.
# ============================================================================
# Secuencia: BUSCAR, GUARDAR, LIMPIAR, CONTROLAR, ANALIZAR, MOSTRAR.
# Cada función t_xxx es UNA tarea: recibe lo que entregó la anterior y entrega su resultado.
import sys

import config
import analisis
import limpieza
import orquestador
import reporte
from fuentes import banco_mundial, fmi, remax


def guardar(df, nombre):
    # Escribe una tabla como archivo CSV dentro de la carpeta data/.
    config.DATOS.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.DATOS / nombre, index=False)                     # GUARDAR


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
    """El portero del pipeline: si los datos no son confiables, FALLA A PROPÓSITO y nada se guarda."""
    a, lo, hi = limpiar["anuncios"], *config.MEDIANA_M2_PLAUSIBLE
    if len(a) < config.MIN_ANUNCIOS_LIMPIOS:
        raise ValueError(f"Control de calidad: solo {len(a)} anuncios limpios (mínimo {config.MIN_ANUNCIOS_LIMPIOS}).")
    mediana = a["precio_m2"].median()
    if not lo <= mediana <= hi:
        raise ValueError(f"Control de calidad: mediana de {mediana:.0f} USD/m² fuera de lo plausible ({lo}-{hi}).")
    if limpiar["macro"].empty:
        raise ValueError("Control de calidad: no llegó ningún dato macroeconómico.")
    return limpiar


# --- TAREA DE ANÁLISIS: las cifras que responden la pregunta de negocio ---
def t_analizar(control_calidad):
    return analisis.analizar(control_calidad["anuncios"], control_calidad["macro"], control_calidad["descartes"])


# --- TAREA DE REPORTE: convierte las cifras en gráfico y texto ---
def t_reportar(analizar):
    return reporte.escribir(analizar)


# EL PLANO (llamado DAG): cada tarea dice quién es y de quién depende.
# Formato:  "nombre": (función, ["tareas que deben terminar antes"])
# El orquestador ordena todo solo; tú solo describes las dependencias.
TAREAS = {
    "remax": (t_remax, []),
    "banco_mundial": (t_banco_mundial, []),
    "fmi": (t_fmi, []),
    "limpiar": (t_limpiar, ["remax", "banco_mundial", "fmi"]),
    "control_calidad": (t_control_calidad, ["limpiar"]),
    "analizar": (t_analizar, ["control_calidad"]),
    "reportar": (t_reportar, ["analizar"]),
}


def main():
    # Lanza el orquestador, guarda el registro y avisa con un código de salida:
    # 0 = todo bien (círculo verde en GitHub), 1 = hubo fallas (círculo rojo).
    print(f"Observatorio de Referencia · modo {config.MODO}")
    _, registro = orquestador.ejecutar(TAREAS)
    orquestador.guardar_registro(registro)
    fallas = [r for r in registro if r["estado"] != "ok"]
    print("RESULTADO:", "todo bien" if not fallas else f"{len(fallas)} tarea(s) con problemas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
