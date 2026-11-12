# ============================================================================
# ARCHIVO: dashboard/app.py        (la VITRINA del observatorio)  · SEMANA 11
# QUÉ HACE:  Muestra en una página web, con filtros que se mueven con el ratón,
#            lo que el robot dejó guardado: precios por sector, tendencia, economía y salud del robot.
# RECIBE:    Los archivos que el robot guarda cada día en data/ y logs/ (no sale a internet).
# ENTREGA:   Una página web con un enlace público. Se actualiza sola cuando el robot guarda datos nuevos.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: los textos entre comillas, la sección «TU PROYECTO»
#            y los nombres de columnas si tus datos son distintos.
# ============================================================================
from pathlib import Path

import pandas as pd
import streamlit as st

# --- DÓNDE ESTÁN LOS DATOS (la carpeta raíz del repositorio es la carpeta de arriba de dashboard/) ---
RAIZ = Path(__file__).resolve().parent.parent
ANUNCIOS = RAIZ / "data" / "anuncios_limpios.csv"
HISTORICO = RAIZ / "data" / "historico" / "resumen_diario.csv"
MACRO = RAIZ / "data" / "macro_limpia.csv"
SALUD = RAIZ / "logs" / "salud.csv"

# --- TU PROYECTO: textos que puedes cambiar ---
TITULO = "Faro · Mercado inmobiliario de Quito"
SUBTITULO = "Observatorio automático: el robot busca, limpia y analiza los anuncios todos los días."
NOMBRE_INDICADOR = {
    "inflacion_pct": "Inflación (%)",
    "pib_crecimiento_pct": "Crecimiento del PIB, Banco Mundial (%)",
    "pib_crecimiento_fmi_pct": "Crecimiento del PIB, FMI (%)",
    "credito_privado_pib_pct": "Crédito privado (% del PIB)",
}
SEMAFORO = {"verde": "🟢 Verde", "amarillo": "🟡 Amarillo", "rojo": "🔴 Rojo"}

st.set_page_config(page_title=TITULO, page_icon="🏠", layout="wide")


# --- LEER ARCHIVOS: se guardan en memoria 10 minutos para que la página sea rápida ---
@st.cache_data(ttl=600)
def leer(ruta):
    ruta = Path(ruta)
    if not ruta.exists():
        return None
    return pd.read_csv(ruta)


anuncios = leer(ANUNCIOS)
historico = leer(HISTORICO)
macro = leer(MACRO)
salud = leer(SALUD)

st.title(TITULO)
st.caption(SUBTITULO)

if anuncios is None or anuncios.empty:
    st.error("Todavía no hay anuncios guardados. Corre el robot (pestaña Actions) y recarga esta página.")
    st.stop()

# --- FILTROS (columna izquierda): cada filtro recorta la tabla antes de calcular ---
st.sidebar.header("Filtros")
tipos = sorted(anuncios["tipo"].dropna().unique())
tipo_elegido = st.sidebar.multiselect("Tipo de vivienda", tipos, default=tipos)

pmin, pmax = int(anuncios["precio_m2"].min()), int(anuncios["precio_m2"].max())
rango = st.sidebar.slider("Precio por m² (USD)", pmin, pmax, (pmin, pmax))

dorm_max = int(min(anuncios["dormitorios"].max(), 6))
dormitorios = st.sidebar.slider("Dormitorios (mínimo)", 0, dorm_max, 0)

min_anuncios = st.sidebar.slider("Mínimo de anuncios por sector", 1, 30, 5,
                                 help="Un sector con pocos anuncios no tiene una mediana confiable.")

filtrado = anuncios[
    anuncios["tipo"].isin(tipo_elegido)
    & anuncios["precio_m2"].between(rango[0], rango[1])
    & (anuncios["dormitorios"] >= dormitorios)
]
st.sidebar.write(f"**{len(filtrado):,}** anuncios con estos filtros")

# --- TARJETAS DE NÚMEROS (KPI) ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Anuncios", f"{len(filtrado):,}")
if len(filtrado):
    c2.metric("Mediana USD por m²", f"{filtrado['precio_m2'].median():,.0f}")
else:
    c2.metric("Mediana USD por m²", "sin datos")
if historico is not None and len(historico) >= 2:
    h = historico.sort_values("fecha")
    cambio = (h["mediana_m2"].iloc[-1] / h["mediana_m2"].iloc[-2] - 1) * 100
    c3.metric("Cambio contra la corrida anterior", f"{cambio:+.2f} %")
else:
    c3.metric("Cambio contra la corrida anterior", "sin datos")
if salud is not None and not salud.empty:
    ultima = salud.sort_values("fecha_utc").iloc[-1]
    c4.metric("Salud del robot", SEMAFORO.get(str(ultima["estado"]), str(ultima["estado"])))
else:
    c4.metric("Salud del robot", "sin datos")

if filtrado.empty:
    st.warning("Con estos filtros no queda ningún anuncio. Amplía el rango en la columna izquierda.")

pestana1, pestana2, pestana3, pestana4 = st.tabs(["📍 Sectores", "📈 Tendencia", "🏦 Economía", "🩺 Salud del robot"])

# --- PESTAÑA 1: SECTORES ---
with pestana1:
    st.subheader("¿Qué sectores son más caros?")
    por_sector = (filtrado.groupby("sector")
                  .agg(anuncios=("id", "count"), mediana_m2=("precio_m2", "median"), precio_mediano=("precio_usd", "median"))
                  .round(0).reset_index())
    por_sector = por_sector[por_sector["anuncios"] >= min_anuncios].sort_values("mediana_m2", ascending=False)
    if por_sector.empty:
        st.info("Ningún sector llega al mínimo de anuncios. Baja el mínimo en la columna izquierda.")
    else:
        cuantos = st.slider("Cuántos sectores mostrar", 3, min(25, len(por_sector)), min(12, len(por_sector))) if len(por_sector) > 3 else len(por_sector)
        top = por_sector.head(cuantos)
        st.bar_chart(top.set_index("sector")["mediana_m2"], color="#002A54", horizontal=True)
        st.dataframe(
            top.rename(columns={"sector": "Sector", "anuncios": "Anuncios", "mediana_m2": "Mediana USD/m²", "precio_mediano": "Precio mediano USD"}),
            hide_index=True, width="stretch")
        st.download_button("⬇️ Descargar esta tabla (CSV)", top.to_csv(index=False).encode("utf-8"), "sectores_faro.csv", "text/csv")

# --- PESTAÑA 2: TENDENCIA ---
with pestana2:
    st.subheader("¿Está subiendo o bajando el precio por m²?")
    if historico is None or historico.empty:
        st.info("Todavía no hay histórico. Se llena con una fila por cada corrida del robot.")
    else:
        h = historico.sort_values("fecha").copy()
        h["fecha"] = pd.to_datetime(h["fecha"])
        st.line_chart(h.set_index("fecha")["mediana_m2"], color="#C8102E")
        st.caption(f"{len(h)} días de historia. Cada punto es la mediana del día; el histórico solo guarda datos reales, nunca del plan B.")
        with st.expander("Ver la tabla del histórico"):
            st.dataframe(h.sort_values("fecha", ascending=False), hide_index=True, width="stretch")

# --- PESTAÑA 3: ECONOMÍA ---
with pestana3:
    st.subheader("¿Cómo está la economía alrededor del mercado?")
    if macro is None or macro.empty:
        st.info("No hay datos económicos todavía.")
    else:
        opciones = sorted(macro["indicador"].unique())
        elegido = st.selectbox("Indicador", opciones, format_func=lambda x: NOMBRE_INDICADOR.get(x, x))
        desde = st.slider("Desde el año", int(macro["anio"].min()), int(macro["anio"].max()) - 1, 2015)
        serie = macro[(macro["indicador"] == elegido) & (macro["anio"] >= desde)].sort_values("anio")
        st.line_chart(serie.set_index("anio")["valor"], color="#002A54")
        st.caption("Fuente: " + ", ".join(sorted(serie["fuente"].unique())) + ". Los años más recientes del FMI son proyecciones.")

# --- PESTAÑA 4: SALUD DEL ROBOT ---
with pestana4:
    st.subheader("¿Está funcionando el robot?")
    if salud is None or salud.empty:
        st.info("El robot todavía no ha dejado su bitácora de salud.")
    else:
        s = salud.sort_values("fecha_utc", ascending=False).head(14).copy()
        s["estado"] = s["estado"].map(lambda x: SEMAFORO.get(str(x), str(x)))
        sin_rojo = (salud.tail(30)["estado"] != "rojo").mean() * 100
        st.metric("Corridas sin rojo (últimas 30)", f"{sin_rojo:.0f} %")
        st.dataframe(
            s[["fecha_utc", "estado", "motivo", "segundos"]].rename(
                columns={"fecha_utc": "Fecha (UTC)", "estado": "Estado", "motivo": "Qué pasó", "segundos": "Segundos"}),
            hide_index=True, width="stretch")

st.divider()
st.caption("Datos: RE/MAX Ecuador, Banco Mundial y FMI · Hecho con Streamlit · Proyecto Faro, UIDE")
