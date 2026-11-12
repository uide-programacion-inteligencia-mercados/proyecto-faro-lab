# ============================================================================
# ARCHIVO: config.py        (el TABLERO DE CONTROL)
# QUÉ HACE:  Reúne en un solo lugar todos los valores que se pueden ajustar: carpetas, ciudad, umbrales, indicadores.
# RECIBE:    Nada (los demás archivos lo leen).
# ENTREGA:   Valores con nombre, por ejemplo UMBRAL_ALERTA_PCT. Los demás archivos hacen import config.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: casi todo: ciudad, indicadores, umbrales y límites. Es el archivo que más cambia entre proyectos.
# ============================================================================
import os
from pathlib import Path

# --- CARPETAS: dónde se guarda cada cosa (rutas relativas a este archivo) ---
RAIZ = Path(__file__).parent
DATOS = RAIZ / "data"
RESPALDO = DATOS / "respaldo"
HISTORICO = DATOS / "historico"
REPORTES = RAIZ / "reports"
LOGS = RAIZ / "logs"

# --- MODO DE TRABAJO ---
# "auto" = intenta la fuente real y, si falla, usa el respaldo.
# "respaldo" = no sale a internet (sirve para probar).
MODO = os.environ.get("FARO_MODO", "auto")

# --- QUÉ SE ESTUDIA ---
PAIS = "ECU"            # código del país para Banco Mundial y FMI
CIUDAD = "Quito"

# --- ALERTA ---
# El cambio (en %) del precio por m2 que hace sonar la alerta.
UMBRAL_ALERTA_PCT = 5.0

# --- FUENTE 1: RE/MAX (cómo se pide y qué cuenta como "Quito") ---
# La página de RE/MAX saca sus anuncios de esta API pública (la misma que usa su sitio web).
REMAX_API = "https://api-ec.redremax.com/remaxweb-ec/api/listings/findAllWithEntrepreneurships"
REMAX_TAMANO_PAGINA = 100
REMAX_MAX_PAGINAS = 80          # tope de seguridad: hoy son unas 64 páginas en todo el país
REMAX_PAUSA_SEG = 1             # cortesía con el sitio entre una página y otra
UBICACION = "Quito, Pichincha"  # el anuncio cuenta si su ubicación termina así

# --- REGLAS DE LIMPIEZA: qué se considera un anuncio válido ---
TIPOS_VIVIENDA = ["casa", "departamento", "penthouse"]   # terrenos, oficinas y locales no se comparan con vivienda
AREA_MIN_M2, AREA_MAX_M2 = 15, 3000
PRECIO_M2_MIN, PRECIO_M2_MAX = 100, 10000   # fuera de este rango (USD por m²) es error de digitación
MIN_ANUNCIOS_SECTOR = 3                      # un sector con menos anuncios no tiene mediana confiable

# --- CONTROL DE CALIDAD: el portero (control_calidad en pipeline.py) usa estos límites ---
# Control de calidad: si no se cumple, el pipeline se detiene a propósito.
MIN_ANUNCIOS_LIMPIOS = 30
MEDIANA_M2_PLAUSIBLE = (300, 6000)   # USD por m² razonable para vivienda en Quito

# --- FUENTES 2a y 2b: indicadores económicos (códigos oficiales) ---
BM_INDICADORES = {
    "inflacion_pct": "FP.CPI.TOTL.ZG",
    "pib_crecimiento_pct": "NY.GDP.MKTP.KD.ZG",
    "credito_privado_pib_pct": "FS.AST.PRVT.GD.ZS",
}
BM_DESDE, BM_HASTA = 2015, 2025
FMI_INDICADOR = "NGDP_RPCH"   # crecimiento real del PIB

# --- REINTENTOS: cuántas veces repite una tarea que falla y cuántos segundos espera ---
REINTENTOS = 2
ESPERA_SEG = 3
