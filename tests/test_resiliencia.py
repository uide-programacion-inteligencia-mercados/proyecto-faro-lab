# ============================================================================
# ARCHIVO: tests/test_resiliencia.py        (el PROBADOR de la semana 7)
# QUÉ HACE:  Comprueba las cinco defensas nuevas: espera creciente, no reintentar
#            datos malos, bitácora, semáforo de salud e idempotencia.
# RECIBE:    Datos inventados en carpetas temporales (nunca toca tus datos).
# ENTREGA:   Verde si las defensas funcionan.
# ============================================================================
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
import pytest

import config
config.MODO = "respaldo"
import bitacora, monitoreo, orquestador, pipeline


@pytest.fixture
def carpetas(tmp_path, monkeypatch):
    # Todo lo que escriben estas pruebas va a una carpeta temporal.
    for nombre in ("DATOS", "HISTORICO", "REPORTES", "LOGS"):
        monkeypatch.setattr(config, nombre, tmp_path / nombre.lower())
    import analisis
    monkeypatch.setattr(analisis, "ARCHIVO_RESUMEN", config.HISTORICO / "resumen_diario.csv")
    return tmp_path


# PRUEBA: la espera se duplica en cada intento (3, 6, 12...).
def test_espera_creciente():
    assert [orquestador.espera_para(i, 3) for i in (1, 2, 3)] == [3, 6, 12]


# PRUEBA: el orquestador espera más cada vez que reintenta.
def test_reintentos_esperan_cada_vez_mas(carpetas, monkeypatch):
    esperas = []
    monkeypatch.setattr(orquestador.time, "sleep", lambda s: esperas.append(s))
    def nunca():
        raise ConnectionError("no contesta")
    orquestador.ejecutar({"a": (nunca, [])}, reintentos=3, espera=2)
    assert esperas == [2, 4, 8]


# PRUEBA: un error de DATOS no se reintenta (repetir no lo arregla).
def test_error_de_datos_no_se_reintenta(carpetas, monkeypatch):
    llamadas = {"n": 0}
    monkeypatch.setattr(orquestador.time, "sleep", lambda s: None)
    def datos_malos():
        llamadas["n"] += 1
        raise orquestador.ErrorDeDatos("tabla vacía")
    _, reg = orquestador.ejecutar({"a": (datos_malos, [])}, reintentos=3, espera=1)
    assert llamadas["n"] == 1 and reg[0]["tipo"] == "datos"


# PRUEBA: cada línea de la bitácora es JSON con los mismos campos.
def test_bitacora_es_estructurada(carpetas):
    bitacora.anotar("INFO", "prueba", "hola", filas=3)
    bitacora.anotar("ERROR", "prueba", "chao")
    lineas = (config.LOGS / "bitacora.jsonl").read_text(encoding="utf-8").splitlines()
    filas = [json.loads(l) for l in lineas]
    assert [f["nivel"] for f in filas] == ["INFO", "ERROR"]
    assert all({"momento_utc", "corrida", "nivel", "tarea", "evento"} <= f.keys() for f in filas)
    assert filas[0]["filas"] == 3


# PRUEBA: el semáforo: verde, amarillo con plan B, rojo si algo falla o si hay demasiados días sin dato real.
def test_semaforo():
    ok = [{"tarea": "a", "estado": "ok"}]
    aviso = [{"nivel": "WARNING", "tarea": "remax", "evento": "usé el respaldo"}]
    assert monitoreo.decidir_estado(ok, [], 0)[0] == "verde"
    assert monitoreo.decidir_estado(ok, aviso, 1)[0] == "amarillo"
    assert monitoreo.decidir_estado([{"tarea": "a", "estado": "fallo"}], [], 0)[0] == "rojo"
    estado, motivo = monitoreo.decidir_estado(ok, aviso, config.DIAS_MAX_SIN_DATO_REAL + 1)
    assert estado == "rojo" and "silencioso" in motivo


# PRUEBA: IDEMPOTENCIA. Registrar dos veces la MISMA corrida deja una sola fila.
def test_salud_no_duplica_la_misma_corrida(carpetas):
    reg = [{"tarea": "a", "estado": "ok"}]
    monitoreo.registrar(reg, 1.0)
    monitoreo.registrar(reg, 2.0)
    salud = pd.read_csv(config.LOGS / "salud.csv")
    assert len(salud) == 1 and salud.iloc[0]["segundos"] == 2.0


# PRUEBA: la escritura atómica no deja borradores .tmp.
def test_guardar_no_deja_borradores(carpetas):
    pipeline.guardar(pd.DataFrame({"x": [1, 2]}), "prueba.csv")
    assert (config.DATOS / "prueba.csv").exists()
    assert not list(config.DATOS.glob("*.tmp"))


# PRUEBA: el simulacro pone el semáforo en ROJO y no toca el histórico.
def test_simulacro_termina_en_rojo(carpetas, monkeypatch):
    monkeypatch.setattr(config, "SIMULAR_FALLA", True)
    monkeypatch.setattr(orquestador.time, "sleep", lambda s: None)
    with pytest.raises(SystemExit) as fin:
        pipeline.main()
    assert fin.value.code == 1
    salud = pd.read_csv(config.LOGS / "salud.csv")
    assert salud.iloc[-1]["estado"] == "rojo"
    assert not (config.HISTORICO / "resumen_diario.csv").exists()
    assert (config.LOGS / "estado.md").exists()


# PRUEBA: una corrida normal con respaldo termina en AMARILLO (funciona, pero no es dato real).
def test_corrida_con_respaldo_es_amarilla(carpetas, monkeypatch):
    monkeypatch.setattr(config, "SIMULAR_FALLA", False)
    with pytest.raises(SystemExit) as fin:
        pipeline.main()
    assert fin.value.code == 0
    assert pd.read_csv(config.LOGS / "salud.csv").iloc[-1]["estado"] == "amarillo"
