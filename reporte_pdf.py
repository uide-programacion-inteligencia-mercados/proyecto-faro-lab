# ============================================================================
# ARCHIVO: reporte_pdf.py        (el IMPRESOR)                      · NUEVO S08
# QUÉ HACE:  Toma las cifras del análisis, las mete en el molde
#            plantillas/reporte.html.j2 (Jinja2) y lo convierte en un PDF
#            con WeasyPrint. Es el paso INFORMAR del recorrido del dato.
# RECIBE:    El diccionario de cifras de analisis.py y el gráfico que dibujó reporte.py.
# ENTREGA:   reports/reporte_FECHA.pdf y reports/ultimo.pdf (la copia con nombre fijo).
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: las frases de contexto() y el molde .j2.
# ============================================================================
# Receta en tres pasos:  1) ARMAR el diccionario de valores  ->  2) RELLENAR el molde (HTML)  ->  3) IMPRIMIR a PDF.
# Cada paso es una función pequeña para poder probarla por separado.
import base64
from datetime import date
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

import bitacora
import config
import monitoreo
import orquestador

PLANTILLAS = config.RAIZ / "plantillas"
COLOR = {"verde": "verde", "amarillo": "amarillo", "rojo": "rojo"}


def _fmt(par, sufijo="%"):
    # Convierte (año, valor) en texto legible; si no hay dato, lo dice en vez de romper.
    return "sin dato" if par is None else f"{par[1]:.1f}{sufijo} ({par[0]})"


def _imagen_en_texto(png):
    # Mete la imagen DENTRO del HTML (como texto base64): así el PDF no depende de rutas de archivos.
    datos = base64.b64encode(Path(png).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{datos}"


def _corridas_recientes(n=5):
    # Lee las últimas corridas de logs/salud.csv (las de ANTES de esta; la de hoy se anota al final).
    archivo = monitoreo.archivo_salud()
    if not archivo.exists():
        return []
    s = pd.read_csv(archivo).tail(n).iloc[::-1]
    return [{"fecha": str(r.fecha_utc)[:16].replace("T", " "), "estado": r.estado, "color": COLOR.get(r.estado, "gris"),
             "segundos": r.segundos, "motivo": str(r.motivo)[:80]} for r in s.itertuples()]


def _frase_hilo(r):
    # La lectura en una frase: conecta el precio con la economía (el hilo conductor del observatorio).
    if r["es_respaldo"]:
        return "Corrida con datos de respaldo: no hay lectura de mercado confiable hoy."
    if r["cambio_pct"] is None:
        base = "Es la primera lectura guardada: todavía no hay con qué comparar el precio por m²."
    else:
        base = f"El precio mediano por m² cambió {r['cambio_pct']:+.2f} % frente a la corrida anterior"
        if r["inflacion"] is not None:
            base += f", mientras la inflación anual del país fue {r['inflacion'][1]:.1f} % ({r['inflacion'][0]})"
        base += "."
    if r["credito"] is not None:
        base += (f" Contexto: en {r['credito'][0]}, los préstamos de bancos y otras entidades financieras a empresas y familias "
                 f"equivalían a {r['credito'][1]:.1f} % de todo lo que produce el país en un año (dato anual del Banco Mundial).")
    return base


def contexto(resumen, png, ultimo_estado=None):
    """PASO 1 · Arma el diccionario con TODOS los valores que el molde necesita."""
    top = resumen["por_sector"].nlargest(config.PDF_TOP_SECTORES, "anuncios")
    d = resumen["descartes"]
    calidad = []
    if d:
        calidad.append(f"Anuncios recibidos: {d['anuncios_crudos']}; quedaron {d['anuncios_limpios']} tras la limpieza.")
        calidad += [f"Descartados por {k.replace('_', ' ')}: {v}" for k, v in d.items()
                    if k not in ("anuncios_crudos", "anuncios_limpios", "precio_corregido_por_punto_de_miles") and v]
        calidad.append(f"Precios corregidos por punto de miles: {d.get('precio_corregido_por_punto_de_miles', 0)}")
    corridas = _corridas_recientes()
    estado = corridas[0]["estado"] if corridas else "sin datos"
    motivo = corridas[0]["motivo"] if corridas else "primera corrida"
    return {
        "titulo": f"Mercado inmobiliario de {config.CIUDAD}",
        "fecha": date.today().isoformat(),
        "ciudad": config.CIUDAD,
        "pie": f"Observatorio de Referencia · corrida {bitacora.CORRIDA_ID}",
        "es_respaldo": resumen["es_respaldo"],
        "alerta": resumen["alerta"],
        "umbral": config.UMBRAL_ALERTA_PCT,
        "n_anuncios": f"{resumen['n_anuncios']:,}",
        "mediana_m2": f"{resumen['mediana_m2']:,.0f}",
        "cambio_texto": "primera lectura" if resumen["cambio_pct"] is None else f"{resumen['cambio_pct']:+.2f} %",
        "salud_estado": estado.upper() if estado != "sin datos" else "SIN DATOS",
        "salud_color": COLOR.get(estado, "gris"),
        "salud_motivo": motivo,
        "frase_hilo": _frase_hilo(resumen),
        "grafico_uri": _imagen_en_texto(png),
        "sectores": [{"sector": r.sector, "anuncios": int(r.anuncios), "mediana_m2": f"{int(r.mediana_m2):,}",
                      "precio_mediano": f"{int(r.precio_mediano):,}"} for r in top.itertuples()],
        "entorno": [{"nombre": "Inflación anual (Banco Mundial, dato anual)", "valor": _fmt(resumen["inflacion"])},
                    {"nombre": "Crecimiento del PIB (Banco Mundial)", "valor": _fmt(resumen["pib_bm"])},
                    {"nombre": "Crecimiento del PIB (FMI)", "valor": _fmt(resumen["pib_fmi"])},
                    {"nombre": "Crédito privado (% del PIB, dato anual)", "valor": _fmt(resumen["credito"])}],
        "calidad": calidad,
        "corridas": corridas,
        "origen": resumen["origen"],
    }


def renderizar_html(ctx):
    """PASO 2 · Rellena el molde con los valores. autoescape evita que un texto raro rompa el HTML."""
    entorno = Environment(loader=FileSystemLoader(str(PLANTILLAS)), autoescape=select_autoescape(["html", "j2"]))
    return entorno.get_template("reporte.html.j2").render(**ctx)


def imprimir_pdf(html, destino):
    """PASO 3 · Convierte el HTML en PDF. Devuelve cuántas páginas salieron."""
    try:
        from weasyprint import HTML
    except ImportError as e:                     # falta la herramienta: no es un problema de datos
        raise RuntimeError("Falta WeasyPrint: agrega 'weasyprint' a requirements.txt") from e
    documento = HTML(string=html, base_url=str(config.RAIZ)).render()
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    borrador = destino.with_suffix(".tmp")        # escritura atómica, igual que los CSV (S07)
    documento.write_pdf(str(borrador))
    borrador.replace(destino)
    return len(documento.pages)


def validar_pdf(destino, paginas):
    """El portero del PDF: un PDF vacío o roto NO debe publicarse como si estuviera bien."""
    p = Path(destino)
    if not p.exists() or p.stat().st_size < config.PDF_MIN_BYTES:
        raise orquestador.ErrorDeDatos(f"El PDF no se generó bien (menos de {config.PDF_MIN_BYTES} bytes).")
    if p.read_bytes()[:5] != b"%PDF-":
        raise orquestador.ErrorDeDatos("El archivo generado no es un PDF válido.")
    if paginas < 1 or paginas > config.PDF_MAX_PAGINAS:
        raise orquestador.ErrorDeDatos(f"El PDF tiene {paginas} páginas (esperado: 1 a {config.PDF_MAX_PAGINAS}).")


def generar(resumen, png):
    """Hace los tres pasos, valida y guarda reports/reporte_FECHA.pdf y reports/ultimo.pdf."""
    config.REPORTES.mkdir(parents=True, exist_ok=True)
    destino = config.REPORTES / f"reporte_{date.today().isoformat()}.pdf"
    html = renderizar_html(contexto(resumen, png))
    paginas = imprimir_pdf(html, destino)
    validar_pdf(destino, paginas)
    (config.REPORTES / "ultimo.pdf").write_bytes(destino.read_bytes())
    bitacora.anotar("INFO", "reporte_pdf", "PDF generado", archivo=destino.name, paginas=paginas,
                    kb=round(destino.stat().st_size / 1024))
    return destino
