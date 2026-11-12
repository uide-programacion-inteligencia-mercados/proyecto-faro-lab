# ============================================================================
# ARCHIVO: limpieza.py        (la LAVANDERÍA)
# QUÉ HACE:  Deja los datos listos para medir: corrige errores comunes, quita lo que no sirve y anota cuántos descartó y por qué.
# RECIBE:    Las tablas crudas que entregaron las fuentes.
# ENTREGA:   Tablas limpias y un resumen de descartes (se muestra luego en el reporte).
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: las reglas de qué se descarta y qué se corrige. Dependen de tus datos; los límites numéricos están en config.py.
# ============================================================================
# Idea clave: cada filtro descarta filas y ANOTA cuántas, para poder explicar el resultado.
import pandas as pd

import config


def limpiar_con_descartes(df):
    """Devuelve (anuncios limpios, dict con cuántos se descartaron por cada motivo)."""
    df = df.copy()
    descartes = {"anuncios_crudos": len(df)}   # el libro de descartes empieza con el total que llegó
    # Convierte a número lo que debe serlo; si algo no se puede, queda vacío en lugar de romper.
    for c in ["precio_usd", "area_m2", "area_terreno_m2", "dormitorios", "banos"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["sector"] = df["sector"].astype(str).str.strip().str.title()

    # Ayudante: se queda con las filas que cumplen la regla y anota cuántas quitó y por qué.
    def quitar(motivo, mascara_a_conservar):
        nonlocal df
        descartes[motivo] = int((~mascara_a_conservar).sum())
        df = df[mascara_a_conservar]

    # --- Filtros de "qué es un anuncio válido" ---
    quitar("id_repetido", ~df["id"].duplicated())
    quitar("no_es_venta", df["operacion"] == "venta")          # el arriendo es un precio mensual: otra medida
    quitar("no_es_vivienda", df["tipo"].isin(config.TIPOS_VIVIENDA))
    quitar("no_esta_activo", df["estado"] == "active")          # reservado o en negociación ya no es oferta

    # --- Corrección: un precio mal escrito se arregla en vez de descartarse ---
    # Error común de digitación: 75.579 (con punto de miles) llega como 75,579 dólares.
    df = df.copy()
    arregla = (df["precio_usd"] < 1000) & (df["precio_usd"] % 1 != 0)
    df.loc[arregla, "precio_usd"] = (df.loc[arregla, "precio_usd"] * 1000).round(0)
    descartes["precio_corregido_por_punto_de_miles"] = int(arregla.sum())

    # --- Filtros de plausibilidad: lo imposible es un error de digitación ---
    quitar("sin_precio", df["precio_usd"] > 0)
    quitar("area_imposible", df["area_m2"].between(config.AREA_MIN_M2, config.AREA_MAX_M2))
    cols = ["sector", "tipo", "precio_usd", "area_m2", "dormitorios", "banos"]
    quitar("duplicado_con_otro_id", ~df.duplicated(subset=cols))   # mismo anuncio publicado dos veces

    df = df.copy()
    df["precio_m2"] = (df["precio_usd"] / df["area_m2"]).round(2)
    quitar("precio_m2_imposible", df["precio_m2"].between(config.PRECIO_M2_MIN, config.PRECIO_M2_MAX))
    df = df.copy()
    # --- Filtro estadístico: quita valores muy lejos de la mediana (método MAD, robusto a extremos) ---
    med = df["precio_m2"].median()
    mad = (df["precio_m2"] - med).abs().median()
    if mad > 0:   # fuera lo extremo: más de 3 desviaciones (errores de digitación)
        quitar("precio_m2_extremo", (df["precio_m2"] - med).abs() <= 3 * mad * 1.4826)
    else:
        descartes["precio_m2_extremo"] = 0
    descartes["anuncios_limpios"] = len(df)
    return df.reset_index(drop=True), descartes


def limpiar_anuncios(df):
    # Versión corta: solo devuelve los anuncios limpios.
    return limpiar_con_descartes(df)[0]


def limpiar_macro(df):
    # Limpia la tabla económica: valores numéricos, sin vacíos ni repetidos, ordenada.
    df = df.copy()
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["valor"]).drop_duplicates(subset=["anio", "indicador", "fuente"])
    return df.sort_values(["indicador", "anio"]).reset_index(drop=True)
