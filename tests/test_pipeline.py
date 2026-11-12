# ============================================================================
# ARCHIVO: tests/test_pipeline.py        (el PROBADOR)
# QUÉ HACE:  Comprueba que cada pieza hace lo que debe ANTES de que el robot
#            toque tus datos. Cada función test_... es una pregunta con respuesta
#            clara: si algo se rompe, el test falla y el robot se detiene.
# RECIBE:    Datos de respaldo (nunca sale a internet).
# ENTREGA:   Verde si todo pasa; rojo si algo falla (y el despertador se detiene).
# ESTO PUEDES CAMBIARLO EN TU PROYECTO: agrega un test por cada regla importante
#            que tenga tu proyecto (un umbral, un filtro, una fuente).
# ============================================================================
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest
import pandas as pd

import config
config.MODO = "respaldo"
import limpieza, orquestador, pipeline


# PRUEBA: una tarea espera a las que necesita.
def test_orden_respeta_dependencias():
    t = {"c": (None, ["a", "b"]), "a": (None, []), "b": (None, ["a"])}
    assert orquestador.orden_de_ejecucion(t) == ["a", "b", "c"]


# PRUEBA: dos tareas que se esperan entre sí se detectan como error.
def test_ciclo_se_detecta():
    with pytest.raises(ValueError):
        orquestador.orden_de_ejecucion({"a": (None, ["b"]), "b": (None, ["a"])})


# PRUEBA: una tarea que cae una vez se reintenta; si cae siempre, las que dependen de ella se omiten.
def test_reintento_y_omision():
    intentos = {"n": 0}

    def inestable():
        intentos["n"] += 1
        if intentos["n"] < 2:
            raise RuntimeError("cae una vez")
        return 1

    def siempre_falla():
        raise RuntimeError("no")

    t = {"a": (inestable, []), "b": (siempre_falla, []), "c": (lambda b: 1, ["b"])}
    _, reg = orquestador.ejecutar(t, reintentos=2, espera=0)
    estados = {r["tarea"]: r["estado"] for r in reg}
    assert estados == {"a": "ok", "b": "fallo", "c": "omitida"}


# PRUEBA: la lavandería quita arriendos, no viviendas y precios imposibles.
def test_limpieza_descarta_lo_que_no_sirve():
    crudo = pd.read_csv(config.RESPALDO / "respaldo_remax.csv")
    limpio, d = limpieza.limpiar_con_descartes(crudo)
    assert d["anuncios_crudos"] == 170
    assert d["no_es_venta"] > 0 and d["no_es_vivienda"] > 0     # arriendos, terrenos y oficinas fuera
    assert d["anuncios_limpios"] == len(limpio)
    assert limpio["id"].is_unique
    assert limpio["tipo"].isin(config.TIPOS_VIVIENDA).all()
    assert limpio["precio_m2"].between(config.PRECIO_M2_MIN, config.PRECIO_M2_MAX).all()


# PRUEBA: 75.579 mal escrito se corrige a 75579 dólares.
def test_limpieza_corrige_el_punto_de_miles():
    # 75.579 llega como 75.579 dólares: en realidad son 75 579
    crudo = pd.DataFrame([{"id": i, "sector": "X", "tipo": "departamento", "operacion": "venta", "estado": "active",
                           "precio_usd": p, "area_m2": 80, "area_terreno_m2": 0, "dormitorios": 3, "banos": 2}
                          for i, p in enumerate([75.579, 80000, 90000, 85000], 1)])
    limpio, d = limpieza.limpiar_con_descartes(crudo)
    assert d["precio_corregido_por_punto_de_miles"] == 1
    assert 75579 in limpio["precio_usd"].values


# PRUEBA: Puerto Quito no cuenta como Quito.
def test_quito_no_incluye_puerto_quito():
    from fuentes import remax
    assert remax.es_de_quito({"geoLabel": "La Floresta, Quito, Pichincha"})
    assert not remax.es_de_quito({"geoLabel": "Puerto Quito, Pichincha"})
    assert not remax.es_de_quito({"geoLabel": "Tarqui, Guayaquil, Guayas"})


# PRUEBA: un anuncio de la API se convierte en una fila de nuestra tabla.
def test_normalizar_un_anuncio_de_la_api():
    from fuentes import remax
    api = {"id": 7, "title": "Depa", "operation": {"value": "sale"}, "type": {"value": "departamento"},
           "currency": {"value": "USD"}, "price": 120000, "dimensionTotalBuilt": 90, "dimensionLand": 0,
           "bedrooms": 3, "bathrooms": 2, "geoLabel": "Cumbayá, Quito, Pichincha", "listingStatus": {"value": "active"}}
    f = remax.normalizar(api)
    assert (f["operacion"], f["tipo"], f["sector"], f["precio_usd"], f["area_m2"], f["estado"]) == \
           ("venta", "departamento", "Cumbayá", 120000, 90, "active")


# PRUEBA: el portero detiene el pipeline si hay muy pocos anuncios.
def test_control_de_calidad_frena_con_pocos_datos():
    limpio = {"anuncios": pd.DataFrame({"precio_m2": [800.0] * 5}), "macro": pd.DataFrame({"x": [1]}), "descartes": {}}
    with pytest.raises(ValueError, match="Control de calidad"):
        pipeline.t_control_calidad(limpio)


# PRUEBA: el pipeline completo corre de principio a fin con datos de respaldo.
def test_pipeline_completo_con_respaldo(tmp_path, monkeypatch):
    for nombre in ("DATOS", "HISTORICO", "REPORTES", "LOGS"):
        monkeypatch.setattr(config, nombre, tmp_path / nombre.lower())
    import analisis
    monkeypatch.setattr(analisis, "ARCHIVO_RESUMEN", config.HISTORICO / "resumen_diario.csv")
    _, reg = orquestador.ejecutar(pipeline.TAREAS, reintentos=0, espera=0)
    assert all(r["estado"] == "ok" for r in reg), reg
    assert (config.REPORTES / "ultimo.md").exists()
    assert (config.DATOS / "anuncios_limpios.csv").exists()
    # los datos de respaldo NO se guardan en el histórico
    assert not (config.HISTORICO / "resumen_diario.csv").exists()


# PRUEBA: una corrida con datos reales sí se guarda en el histórico.
def test_corrida_real_si_se_guarda_en_el_historico(tmp_path, monkeypatch):
    import analisis
    monkeypatch.setattr(config, "HISTORICO", tmp_path)
    monkeypatch.setattr(analisis, "ARCHIVO_RESUMEN", tmp_path / "resumen_diario.csv")
    anuncios = pd.DataFrame({"id": [1, 2], "sector": ["A", "A"], "precio_m2": [800.0, 820.0], "precio_usd": [1, 1],
                             "origen": ["remax_en_vivo"] * 2})
    macro = pd.DataFrame(columns=["indicador", "anio", "valor"])
    analisis.analizar(anuncios, macro)
    assert (tmp_path / "resumen_diario.csv").exists()


# PRUEBA: la alerta suena cuando el precio cambia más que el umbral.
def test_alerta_cuando_el_precio_cambia_mas_que_el_umbral(tmp_path, monkeypatch):
    import analisis
    archivo = tmp_path / "resumen_diario.csv"
    pd.DataFrame([{"fecha": "2026-01-01", "anuncios": 30, "mediana_m2": 1000.0}]).to_csv(archivo, index=False)
    monkeypatch.setattr(analisis, "ARCHIVO_RESUMEN", archivo)
    monkeypatch.setattr(config, "HISTORICO", tmp_path)
    assert analisis.cambio_contra_anterior(1100.0) == 10.0       # +10 % supera el umbral de 5 %
    assert abs(analisis.cambio_contra_anterior(1020.0)) < config.UMBRAL_ALERTA_PCT


# PRUEBA: el reporte se genera bien con datos reales.
def test_reporte_de_corrida_real_no_falla(tmp_path, monkeypatch):
    # Este camino (origen distinto al respaldo) no lo recorría ninguna prueba y falló en GitHub.
    import analisis, reporte
    monkeypatch.setattr(config, "HISTORICO", tmp_path / "h")
    monkeypatch.setattr(config, "REPORTES", tmp_path / "r")
    monkeypatch.setattr(analisis, "ARCHIVO_RESUMEN", tmp_path / "h" / "resumen_diario.csv")
    crudo = pd.read_csv(config.RESPALDO / "respaldo_remax.csv")
    crudo["origen"] = "remax_en_vivo"
    limpio, d = limpieza.limpiar_con_descartes(crudo)
    macro = pd.DataFrame([{"indicador": "inflacion_pct", "anio": 2024, "valor": 1.5, "fuente": "bm"}])
    res = analisis.analizar(limpio, macro, d)
    assert res["es_respaldo"] is False
    reporte.escribir(res)
    assert (tmp_path / "r" / "ultimo.md").exists()
    assert (tmp_path / "h" / "resumen_diario.csv").exists()
