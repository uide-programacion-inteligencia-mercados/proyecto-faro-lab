# ============================================================================
# ARCHIVO: fuentes/remax.py        (un BUSCADOR (fuente 1))
# QUÉ HACE:  Pide los anuncios inmobiliarios a la API pública de RE/MAX y los ordena en una tabla con columnas fijas.
# RECIBE:    Nada. Usa la dirección y los límites de config.py.
# ENTREGA:   Una tabla de anuncios de Quito. Si la fuente falla, entrega la copia de respaldo.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: la dirección de la fuente, qué se filtra (por ciudad) y las columnas. Es el archivo que más cambia entre proyectos.
# ============================================================================
import time
from datetime import date

import pandas as pd
import requests

import config

# Las columnas que SIEMPRE entrega, para que el resto del código no se confunda.
COLUMNAS = ["id", "titulo", "sector", "tipo", "operacion", "precio_usd", "area_m2",
            "area_terreno_m2", "dormitorios", "banos", "estado", "fecha_captura", "origen"]


def _valor(d, clave):
    # Algunos datos vienen como {"value": ...}; esta función saca el valor en ambos casos.
    v = d.get(clave)
    return v.get("value") if isinstance(v, dict) else v


def es_de_quito(anuncio):
    # "Puerto Quito" y otros cantones NO son Quito: por eso se compara el final de la ubicación.
    return (anuncio.get("geoLabel") or "").strip().lower().endswith(", " + config.UBICACION.lower())


def normalizar(a):
    """Convierte un anuncio de la API en una fila de nuestra tabla."""
    tipo = _valor(a, "type")
    sector = (a.get("geoLabel") or "").split(",")[0].strip()
    return {
        "id": a.get("id"),
        "titulo": a.get("title") or f"{tipo} en {sector}",
        "sector": sector,
        "tipo": tipo,
        "operacion": {"sale": "venta", "rent": "arriendo"}.get(_valor(a, "operation"), _valor(a, "operation")),
        "precio_usd": a.get("price") if _valor(a, "currency") == "USD" else None,
        "area_m2": a.get("dimensionTotalBuilt"),
        "area_terreno_m2": a.get("dimensionLand"),
        "dormitorios": a.get("bedrooms"),
        "banos": a.get("bathrooms"),
        "estado": _valor(a, "listingStatus"),
    }


# --- Lee la fuente real, página por página (con una pausa de cortesía) ---
def traer_en_vivo():
    filas, vistas = [], 0
    for pagina in range(config.REMAX_MAX_PAGINAS):
        r = requests.get(config.REMAX_API, timeout=40, headers={"User-Agent": "observatorio-curso-UIDE"}, params={
            "page": pagina, "pageSize": config.REMAX_TAMANO_PAGINA,
            "sort": "-createdAt", "in": "operationId:1,2"})
        r.raise_for_status()
        pagina_datos = r.json()["data"]["data"]
        if not pagina_datos:
            break
        vistas += len(pagina_datos)
        filas += [normalizar(a) for a in pagina_datos if es_de_quito(a)]
        time.sleep(config.REMAX_PAUSA_SEG)
    if not filas:
        raise RuntimeError(f"RE/MAX respondió ({vistas} anuncios en el país), pero ninguno es de {config.UBICACION}.")
    df = pd.DataFrame(filas)
    df["fecha_captura"] = date.today().isoformat()
    df["origen"] = "remax_en_vivo"
    print(f"   RE/MAX: {vistas} anuncios en el país, {len(df)} en Quito")
    return df.reindex(columns=COLUMNAS)


# --- Plan B: lee la copia guardada en data/respaldo/ ---
def traer_respaldo():
    df = pd.read_csv(config.RESPALDO / "respaldo_remax.csv")
    df["fecha_captura"] = date.today().isoformat()
    return df.reindex(columns=COLUMNAS)


# --- La función que usa el pipeline: intenta la fuente real; si falla, el respaldo ---
def traer():
    if config.MODO != "respaldo":
        try:
            return traer_en_vivo()
        except Exception as e:
            print(f"   aviso RE/MAX: {e}. Uso el respaldo.")
    return traer_respaldo()
