# ============================================================================
# ARCHIVO: tests/conftest.py        (la REGLA DEL PROBADOR)              · S07
# QUÉ HACE:  Antes de cada prueba, manda la bitácora a una carpeta temporal.
#            Así las pruebas nunca ensucian logs/ de verdad (en GitHub, las
#            pruebas corren justo antes del robot y con el mismo número de corrida).
# ============================================================================
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


@pytest.fixture(autouse=True)
def logs_temporales(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOGS", tmp_path / "logs_de_prueba")
