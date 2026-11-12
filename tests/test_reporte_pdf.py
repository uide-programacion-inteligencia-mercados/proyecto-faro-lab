# ============================================================================
# ARCHIVO: tests/test_reporte_pdf.py        (el PROBADOR DEL INFORME)        · NUEVO S08
# QUÉ HACE:  Comprueba que el informe PDF se arma bien ANTES de que el robot lo
#            publique: que el molde se rellene, que el PDF exista y sea válido,
#            que no se rompa con textos raros ni con datos que faltan.
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: agrega una prueba por cada bloque nuevo
#            que pongas en tu informe.
# ============================================================================
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
import pytest

import config
config.MODO = "respaldo"
import analisis, orquestador, pipeline, reporte, reporte_pdf


@pytest.fixture
def carpetas(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATOS", tmp_path / "data")
    monkeypatch.setattr(config, "HISTORICO", tmp_path / "data" / "historico")
    monkeypatch.setattr(config, "REPORTES", tmp_path / "reports")
    monkeypatch.setattr(analisis, "ARCHIVO_RESUMEN", tmp_path / "data" / "historico" / "resumen_diario.csv")
    return tmp_path


def _resumen(**cambios):
    """Cifras de ejemplo, como las que entrega analisis.analizar()."""
    por_sector = pd.DataFrame({"sector": ["La Carolina", "Cumbayá", "Ñuñoa <b>"], "anuncios": [40, 30, 12],
                               "mediana_m2": [1800.0, 2100.0, 900.0], "precio_mediano": [150000.0, 260000.0, 70000.0]})
    r = {"descartes": {"anuncios_crudos": 120, "anuncios_limpios": 82, "arriendo": 30, "precio_corregido_por_punto_de_miles": 4},
         "es_respaldo": False, "n_anuncios": 82, "mediana_m2": 1650.5, "cambio_pct": 1.2, "alerta": False,
         "por_sector": por_sector, "inflacion": (2024, 2.4), "pib_bm": (2024, -2.0), "pib_fmi": (2024, -1.9),
         "credito": (2024, 31.5), "origen": "remax_api"}
    r.update(cambios)
    return r


@pytest.fixture
def png(carpetas):
    config.REPORTES.mkdir(parents=True, exist_ok=True)
    destino = config.REPORTES / "grafico.png"
    reporte.grafico(_resumen(), destino)
    return destino


# PRUEBA: el molde se rellena con las cifras y con los acentos intactos.
def test_html_trae_las_cifras(png):
    html = reporte_pdf.renderizar_html(reporte_pdf.contexto(_resumen(), png))
    assert "1,650" in html and "La Carolina" in html and "Cumbayá" in html
    assert "Mercado inmobiliario de Quito" in html


# PRUEBA: un texto con <etiquetas> no rompe el HTML (autoescape).
def test_texto_raro_no_rompe_el_html(png):
    html = reporte_pdf.renderizar_html(reporte_pdf.contexto(_resumen(), png))
    assert "Ñuñoa <b>" not in html and "Ñuñoa &lt;b&gt;" in html


# PRUEBA: si falta un dato económico, el informe dice «sin dato» y no se cae.
def test_dato_faltante_dice_sin_dato(png):
    html = reporte_pdf.renderizar_html(reporte_pdf.contexto(_resumen(inflacion=None, credito=None), png))
    assert html.count("sin dato") >= 2


# PRUEBA: primera corrida (sin comparación) y corrida de respaldo muestran su aviso.
def test_avisos_de_primera_corrida_y_respaldo(png):
    ctx = reporte_pdf.contexto(_resumen(cambio_pct=None, es_respaldo=True), png)
    html = reporte_pdf.renderizar_html(ctx)
    assert "primera lectura" in html and "Datos de respaldo" in html


# PRUEBA: la alerta aparece solo si el cambio supera el umbral.
def test_alerta_visible_solo_si_corresponde(png):
    sin = reporte_pdf.renderizar_html(reporte_pdf.contexto(_resumen(), png))
    con = reporte_pdf.renderizar_html(reporte_pdf.contexto(_resumen(cambio_pct=7.5, alerta=True), png))
    assert "ALERTA" not in sin and "ALERTA" in con


# PRUEBA: el PDF se genera, empieza con %PDF y tiene de 1 a 4 páginas.
def test_pdf_se_genera_y_es_valido(carpetas, png):
    destino = reporte_pdf.generar(_resumen(), png)
    datos = destino.read_bytes()
    assert datos[:5] == b"%PDF-" and len(datos) >= config.PDF_MIN_BYTES
    assert (config.REPORTES / "ultimo.pdf").read_bytes() == datos
    assert destino.name == f"reporte_{date.today().isoformat()}.pdf"
    assert not list(config.REPORTES.glob("*.tmp"))        # escritura atómica: no quedan borradores


# PRUEBA: IDEMPOTENCIA. Generar dos veces el mismo día deja un solo PDF con ese nombre.
def test_generar_dos_veces_no_duplica(carpetas, png):
    reporte_pdf.generar(_resumen(), png)
    reporte_pdf.generar(_resumen(), png)
    assert len(list(config.REPORTES.glob("reporte_*.pdf"))) == 1


# PRUEBA: el portero rechaza un PDF vacío, uno falso o uno con demasiadas páginas.
def test_validar_rechaza_pdf_malo(tmp_path):
    vacio = tmp_path / "a.pdf"; vacio.write_bytes(b"")
    falso = tmp_path / "b.pdf"; falso.write_bytes(b"x" * 9000)
    bueno = tmp_path / "c.pdf"; bueno.write_bytes(b"%PDF-1.7" + b"x" * 9000)
    for malo in (vacio, falso):
        with pytest.raises(orquestador.ErrorDeDatos):
            reporte_pdf.validar_pdf(malo, 1)
    with pytest.raises(orquestador.ErrorDeDatos):
        reporte_pdf.validar_pdf(bueno, config.PDF_MAX_PAGINAS + 1)
    reporte_pdf.validar_pdf(bueno, 2)


# PRUEBA: el PDF incluye el semáforo de las corridas anteriores si existe logs/salud.csv.
def test_pdf_muestra_la_salud_anterior(carpetas, png):
    config.LOGS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"fecha_utc": "2026-10-20T11:00:00+00:00", "corrida": "1", "estado": "verde", "motivo": "todo bien con datos reales",
                   "segundos": 12.0}]).to_csv(config.LOGS / "salud.csv", index=False)
    html = reporte_pdf.renderizar_html(reporte_pdf.contexto(_resumen(), png))
    assert "VERDE" in html and "2026-10-20 11:00" in html


# PRUEBA: el pipeline completo (con respaldos) produce el PDF y la tarea queda en el plano.
def test_pipeline_produce_el_pdf(carpetas, monkeypatch):
    monkeypatch.setattr(config, "LOGS", carpetas / "logs")
    monkeypatch.setattr(config, "SIMULAR_FALLA", False)
    assert "reportar_pdf" in pipeline.TAREAS and pipeline.TAREAS["reportar_pdf"][1] == ["analizar", "reportar"]
    with pytest.raises(SystemExit) as fin:
        pipeline.main()
    assert fin.value.code == 0
    assert (config.REPORTES / "ultimo.pdf").read_bytes()[:5] == b"%PDF-"
