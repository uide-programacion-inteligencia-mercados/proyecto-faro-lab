# ============================================================================
# ARCHIVO: tests/test_respaldo.py        (pruebas del plan B vivo)
# QUÉ HACE:  Comprueba que el respaldo se renueva SOLO con datos reales aprobados, y nunca en simulacro ni con plan B.
# RECIBE:    Carpetas temporales (nunca toca el respaldo de verdad).
# ============================================================================
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
import respaldo


@pytest.fixture
def carpetas(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATOS", tmp_path / "data")
    monkeypatch.setattr(config, "RESPALDO", tmp_path / "data" / "respaldo")
    monkeypatch.setattr(config, "MODO", "auto")
    monkeypatch.setattr(config, "SIMULAR_FALLA", False)
    monkeypatch.setattr(config, "RENOVAR_RESPALDO", True)
    config.DATOS.mkdir(parents=True)
    respaldo.ORIGEN.clear()
    return config


def _crudo_remax(n):
    pd.DataFrame({"id": range(n), "precio_usd": [100000] * n, "origen": ["remax_en_vivo"] * n}).to_csv(
        config.DATOS / "remax_crudo.csv", index=False)


# PRUEBA: con datos reales aprobados, el respaldo se renueva y queda marcado como plan B.
def test_renueva_con_datos_reales(carpetas):
    _crudo_remax(config.MIN_ANUNCIOS_LIMPIOS + 5)
    respaldo.marcar("remax", "en_vivo")
    assert respaldo.renovar() == ["remax"]
    nuevo = pd.read_csv(config.RESPALDO / "respaldo_remax.csv")
    assert "respaldo" in nuevo["origen"].iloc[0]          # el análisis lo reconocerá como plan B
    assert json.loads((config.RESPALDO / "fechas.json").read_text())["remax"]


# PRUEBA: si hoy la fuente usó su plan B, el respaldo no se toca.
def test_no_renueva_si_hoy_uso_el_plan_b(carpetas):
    _crudo_remax(config.MIN_ANUNCIOS_LIMPIOS + 5)
    respaldo.marcar("remax", "respaldo")
    assert respaldo.renovar() == []
    assert not (config.RESPALDO / "respaldo_remax.csv").exists()


# PRUEBA: en simulacro o en modo prueba no se renueva nada.
@pytest.mark.parametrize("ajuste", [("SIMULAR_FALLA", True), ("MODO", "respaldo")])
def test_no_renueva_en_simulacro_ni_en_modo_prueba(carpetas, monkeypatch, ajuste):
    monkeypatch.setattr(config, ajuste[0], ajuste[1])
    _crudo_remax(config.MIN_ANUNCIOS_LIMPIOS + 5)
    respaldo.marcar("remax", "en_vivo")
    assert respaldo.renovar() == []


# PRUEBA: un dato demasiado corto no sirve como plan B.
def test_no_renueva_con_pocos_anuncios(carpetas):
    _crudo_remax(3)
    respaldo.marcar("remax", "en_vivo")
    assert respaldo.renovar() == []
