# ============================================================================
# ARCHIVO: reporte.py        (el REPORTERO)
# QUÉ HACE:  Convierte las cifras en algo que se puede leer: un gráfico de barras y un reporte en texto (Markdown).
# RECIBE:    El diccionario de cifras que entregó la calculadora.
# ENTREGA:   reports/ultimo.md, reports/reporte_FECHA.md y reports/precio_m2_FECHA.png.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: los textos, el gráfico y los colores. Cambia la pregunta que el reporte responde.
# ============================================================================
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

# Colores de la marca del curso.
AZUL, MAGENTA, ORO, GRIS = "#002C71", "#910048", "#EAAA00", "#E7E6E6"


def _fmt(par, sufijo="%"):
    # Convierte (año, valor) en texto legible, por ejemplo "3.7% (2024)".
    return "sin dato" if par is None else f"{par[1]:.1f}{sufijo} ({par[0]})"


def grafico(resumen, destino):
    # Dibuja barras horizontales con el precio por m² de los sectores con más anuncios.
    t = resumen["por_sector"].nlargest(15, "anuncios").sort_values("mediana_m2")   # los 15 sectores con más anuncios
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(t["sector"], t["mediana_m2"], color=AZUL)
    ax.barh(t["sector"].iloc[-1:], t["mediana_m2"].iloc[-1:], color=MAGENTA)
    ax.set_xlabel("Precio mediano por m² (USD)")
    ax.set_title(f"{config.CIUDAD}: precio por m² en los 15 sectores con más anuncios")
    ax.grid(axis="x", color=GRIS)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    fig.savefig(destino, dpi=140)
    plt.close(fig)


def escribir(resumen):
    # Arma el gráfico y el texto del reporte, y los guarda en la carpeta reports/.
    config.REPORTES.mkdir(parents=True, exist_ok=True)
    hoy = date.today().isoformat()
    png = config.REPORTES / f"precio_m2_{hoy}.png"
    grafico(resumen, png)
    cambio = "primera corrida: aún no hay con qué comparar" if resumen["cambio_pct"] is None else f"{resumen['cambio_pct']:+.2f} % contra la corrida anterior"
    aviso = "ALERTA: el cambio supera el umbral." if resumen["alerta"] else "Sin alerta."
    t = resumen["por_sector"].nlargest(20, "anuncios")
    d = resumen["descartes"]
    calidad = ""
    if d:
        calidad = (f"- Anuncios recibidos: {d['anuncios_crudos']}; quedaron {d['anuncios_limpios']} tras la limpieza.\n"
                   + "\n".join(f"- Descartados por {k.replace('_', ' ')}: {v}" for k, v in d.items()
                                if k not in ("anuncios_crudos", "anuncios_limpios", "precio_corregido_por_punto_de_miles") and v)
                   + f"\n- Precios corregidos por punto de miles: {d['precio_corregido_por_punto_de_miles']}\n")
    nota_respaldo = "\n> Esta corrida usó datos de respaldo: no se guardó en el histórico ni se calculó alerta.\n" if resumen["es_respaldo"] else ""
    filas = "\n".join(f"| {r.sector} | {int(r.anuncios)} | {int(r.mediana_m2):,} | {int(r.precio_mediano):,} |" for r in t.itertuples())
    texto = f"""# Observatorio de Referencia · Mercado inmobiliario de {config.CIUDAD}
Reporte del {hoy}

## Lo más importante
- Anuncios analizados: **{resumen['n_anuncios']}**
- Precio mediano por m²: **USD {resumen['mediana_m2']:,.0f}** ({cambio})
- {aviso} (umbral: {config.UMBRAL_ALERTA_PCT} %)

{nota_respaldo}
## Calidad de los datos
{calidad}
## Por sector (los 20 con más anuncios)
| Sector | Anuncios | Mediana USD/m² | Precio mediano USD |
|---|---|---|---|
{filas}

![Precio por m²]({png.name})

## El entorno económico del Ecuador
- Inflación anual (Banco Mundial): {_fmt(resumen['inflacion'])}
- Crecimiento del PIB (Banco Mundial): {_fmt(resumen['pib_bm'])}
- Crecimiento del PIB (FMI): {_fmt(resumen['pib_fmi'])}
- Crédito al sector privado (% del PIB, Banco Mundial): {_fmt(resumen['credito'])}

## De dónde salen los datos
- Anuncios: {resumen['origen']}
- Macroeconomía: Banco Mundial y FMI
"""
    (config.REPORTES / f"reporte_{hoy}.md").write_text(texto, encoding="utf-8")
    (config.REPORTES / "ultimo.md").write_text(texto.replace(png.name, f"precio_m2_{hoy}.png"), encoding="utf-8")
    return png
