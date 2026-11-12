# ============================================================================
# ARCHIVO: respaldo.py        (el que renueva el plan B)
# QUÉ HACE:  Cuando el robot trabajó con datos REALES y el control de calidad los aprobó,
#            guarda una copia fresca en data/respaldo/ para que el plan B no envejezca.
# RECIBE:    Nada: las fuentes le avisan si su dato vino en vivo; los archivos crudos están en data/.
# ENTREGA:   Los archivos de data/respaldo/ renovados y data/respaldo/fechas.json con la fecha de cada uno.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: la lista FUENTES y el apagador RENOVAR_RESPALDO de config.py.
# ============================================================================
import json
from datetime import date

import pandas as pd

import bitacora
import config

# Cada fuente avisa aquí si su último dato vino "en_vivo" o del "respaldo".
ORIGEN = {}

# fuente: (archivo crudo que guardó la tarea de búsqueda, archivo de respaldo)
FUENTES = {
    "remax": ("remax_crudo.csv", "respaldo_remax.csv"),
    "banco_mundial": ("banco_mundial_crudo.csv", "respaldo_banco_mundial.csv"),
    "fmi": ("fmi_crudo.csv", "respaldo_fmi.csv"),
}


def marcar(fuente, origen):
    # Las fuentes llaman a esto al terminar: origen = "en_vivo" o "respaldo".
    ORIGEN[fuente] = origen


def _guardar_atomico(df, destino):
    # Mismo cuidado que en pipeline.guardar: primero borrador, después reemplazo en un solo movimiento.
    destino.parent.mkdir(parents=True, exist_ok=True)
    borrador = destino.with_suffix(".tmp")
    df.to_csv(borrador, index=False)
    borrador.replace(destino)


def renovar():
    """Renueva el plan B de cada fuente cuyo dato de hoy fue real. Devuelve la lista de fuentes renovadas."""
    if not config.RENOVAR_RESPALDO or config.MODO == "respaldo" or config.SIMULAR_FALLA:
        return []
    renovadas = []
    for fuente, (crudo, copia) in FUENTES.items():
        if ORIGEN.get(fuente) != "en_vivo":
            continue                                   # hoy esta fuente usó su plan B: no se toca
        archivo = config.DATOS / crudo
        if not archivo.exists():
            continue
        df = pd.read_csv(archivo)
        minimo = config.MIN_ANUNCIOS_LIMPIOS if fuente == "remax" else 1
        if len(df) < minimo:
            continue                                   # muy corto: no vale como plan B
        if "origen" in df.columns:
            df["origen"] = "respaldo_remax_renovado"   # la palabra «respaldo» le avisa al análisis que es plan B
        _guardar_atomico(df, config.RESPALDO / copia)
        renovadas.append(fuente)
    if renovadas:
        fechas_archivo = config.RESPALDO / "fechas.json"
        fechas = json.loads(fechas_archivo.read_text()) if fechas_archivo.exists() else {}
        for f in renovadas:
            fechas[f] = date.today().isoformat()
        fechas_archivo.write_text(json.dumps(fechas, indent=2, ensure_ascii=False))
        # Ojo: este texto NO lleva la palabra «respaldo» a propósito: el monitoreo la usa para detectar el plan B.
        bitacora.anotar("INFO", "renovar_respaldo", "copia de seguridad actualizada con datos reales", fuentes=",".join(renovadas))
    return renovadas
