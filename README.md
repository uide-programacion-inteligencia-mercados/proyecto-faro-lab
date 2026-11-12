# Observatorio de Referencia (Faro inmobiliario de Quito) · versión Semana 8

![Estado del robot](https://github.com/uide-programacion-inteligencia-mercados/proyecto-faro-docente/actions/workflows/orquestador_diario.yml/badge.svg)

> **Materia:** Programación Aplicada a la Inteligencia de Mercados (02A-TAM557-8) · UIDE Business School.
> Mercado inmobiliario y hábitat de Quito.

El modelo completo del docente. Muestra cómo se ve un observatorio cuando todas las piezas del curso ya trabajan juntas. Los grupos construyen el suyo semana a semana mirando este.

**Pregunta de negocio:** ¿cuánto cuesta el metro cuadrado en cada sector de Quito, cambió desde la última vez que miramos, y qué está pasando en la economía del país que pueda explicarlo?

## Las dos fuentes

| Fuente | Qué trae | Archivo que la lee |
|---|---|---|
| RE/MAX Ecuador (vitrina de anuncios) | Precio, área, dormitorios y sector de cada anuncio | `fuentes/remax.py` |
| Banco Mundial y FMI (ventanilla de datos) | Inflación, crecimiento del PIB y crédito al sector privado | `fuentes/banco_mundial.py`, `fuentes/fmi.py` |

Cada fuente tiene su plan B en `data/respaldo/`. Si la fuente real no contesta, el robot usa el respaldo y lo dice en pantalla.

**Sobre RE/MAX:** el sitio web de RE/MAX saca sus anuncios de una API pública (`api-ec.redremax.com`), y `fuentes/remax.py` lee esa misma API. Hay unos 6.300 anuncios en el país y unos 2.360 en Quito. Se descargan 64 páginas de 100, con una pausa de un segundo entre ellas, y se queda solo lo que termina en «Quito, Pichincha» (así no entra Puerto Quito). El `robots.txt` del sitio solo bloquea un rastreador de SEO y las URL con `?associate`; los términos de uso del sitio todavía hay que leerlos antes de publicar el proyecto.

**Sobre el respaldo de RE/MAX:** `respaldo_remax.csv` es una muestra **real** de 170 anuncios de Quito tomada el 8 de octubre de 2026 (columna `origen` = `respaldo_remax_real`), con sus errores originales: arriendos y terrenos mezclados con ventas, un departamento de venta a 250 dólares, precios con punto de miles (75.579) y un local con 154.569 m². Es el material de práctica de los grupos para limpiar datos.

**Plan B vivo (S08):** cuando una fuente contesta en vivo y el control de calidad aprueba los datos, la tarea `renovar_respaldo` guarda una copia fresca en `data/respaldo/` (columna `origen` = `respaldo_remax_renovado`) y anota la fecha en `fechas.json`. No renueva si hoy la fuente usó su plan B, si es un simulacro, si se corre en modo prueba o si el dato es demasiado corto. Se apaga con `RENOVAR_RESPALDO = False` en `config.py`.

**Regla de oro del respaldo:** si una corrida usa el respaldo, el reporte lo dice y **no se guarda en el histórico**. Así nunca se mezclan datos viejos con la serie real.

**Pendiente:** confirmar que la API contesta desde los servidores de GitHub (se prueba una vez con **Run workflow**). Si no contestara, el robot usa el respaldo y lo avisa en el reporte.

## Semana 8 · «Reporte PDF»: el observatorio escribe su propio informe

Además de las cinco defensas de la semana 7, el robot imprime cada día un informe de dos páginas: `reports/ultimo.pdf` (y `reports/reporte_FECHA.pdf`).

| Pieza | Qué hace | Dónde está |
|---|---|---|
| El molde | Una página web con huecos (`{{ hueco }}`, `{% for %}`, `{% if %}`) que Jinja2 rellena | `plantillas/reporte.html.j2` |
| El impresor | Arma los valores, rellena el molde y lo convierte en PDF con WeasyPrint | `reporte_pdf.py` |
| El portero del PDF | Rechaza un PDF vacío, que no sea PDF o con demasiadas páginas (`ErrorDeDatos`) | `reporte_pdf.validar_pdf` |
| La tarea nueva | `reportar_pdf` espera a `analizar` y a `reportar` (el gráfico) | `pipeline.py` · diccionario `TAREAS` |

**Qué lleva el informe:** titular en una frase, cuatro tarjetas (anuncios, precio mediano por m², cambio contra la corrida anterior y semáforo del robot), gráfico por sector, tabla de los 12 sectores con más anuncios, entorno económico, calidad de los datos y las últimas corridas del robot. Si la corrida usó datos de respaldo, el informe lo dice arriba y no se guarda en el histórico.

**Escritura atómica:** el PDF se escribe primero como borrador (`.tmp`) y se cambia por el definitivo solo si está completo.

**Pruebas:** 31 (21 de las semanas 6 y 7, y 10 del informe en `tests/test_reporte_pdf.py`).

**En Colab:** `!pip install -q -r requirements.txt` ya instala Jinja2 y WeasyPrint.

## El recorrido del dato

```
BUSCAR      remax, banco_mundial, fmi        (se ejecutan sin esperarse entre sí)
GUARDAR     data/*_crudo.csv
LIMPIAR     limpiar                          (espera a las tres anteriores)
CONTROLAR   control_calidad                  (si los datos no son confiables, FALLA A PROPÓSITO)
ANALIZAR    analizar                         (mediana por sector, cambio contra ayer, alerta)
MOSTRAR     reportar                         (gráfico y reporte en texto)
INFORMAR    reportar_pdf                     (S08: el informe en PDF, con semáforo de salud)
AUTOMATIZAR .github/workflows/orquestador_diario.yml
```

`orquestador.py` es el director: ejecuta cada tarea cuando sus dependencias terminaron, reintenta si una falla y omite las que dependían de la que falló. Deja el resultado en `logs/ultima_corrida.json`.

## Semana 7 · «Avisa si falla»: las cinco defensas

| Defensa | Qué hace | Dónde está |
|---|---|---|
| 1. Reintentar con espera creciente | 3 s, luego 6 s. No reintenta si el problema son los datos (`ErrorDeDatos`) | `orquestador.py` |
| 2. Idempotencia | Correr dos veces da el mismo resultado: una fila por día en el histórico, una por corrida en la salud, escritura atómica de los CSV | `analisis.py`, `monitoreo.py`, `pipeline.py` |
| 3. Control de calidad (el fusible) | Si los datos no son confiables, se detiene sin reintentar | `pipeline.py` · `t_control_calidad` |
| 4. Bitácora estructurada | Una línea JSON por evento con nivel INFO / WARNING / ERROR | `bitacora.py` → `logs/bitacora.jsonl` |
| 5. Alertas y monitoreo | Semáforo verde / amarillo / rojo, historial de salud, resumen en la corrida y un Issue automático cuando falla | `monitoreo.py` → `logs/salud.csv`, `logs/estado.md` · workflow |

**El semáforo.** Verde: todo con datos reales. Amarillo: funcionó con plan B o reintentos. Rojo: algo falló, o pasaron más de 3 días sin dato real (un fallo silencioso). Solo el rojo pone la corrida en rojo y abre la alerta.

**El simulacro.** Pestaña **Actions** → **Orquestador diario del Observatorio** → **Run workflow** → marcar **simular_falla** → **Run workflow**. La corrida debe salir en rojo y aparecer una alerta en la pestaña **Issues**. La siguiente corrida normal la cierra sola.

## El trabajador digital

`.github/workflows/orquestador_diario.yml` corre todos los días a las **11:00 UTC (06:00 en Quito)**. También se puede lanzar a mano: pestaña **Actions**, el flujo **Orquestador diario del Observatorio**, botón **Run workflow**.

Cada corrida: prueba el código, ejecuta el pipeline, guarda el reporte como archivo descargable y sube al repositorio los datos nuevos.

## Cómo correrlo sin instalar nada (Google Colab)

En un cuaderno de Colab, una celda con:

```
!git clone https://github.com/uide-programacion-inteligencia-mercados/proyecto-faro-docente
%cd proyecto-faro-docente
!pip install -q -r requirements.txt
!python pipeline.py
```

Para probar sin salir a internet: `!FARO_MODO=respaldo python pipeline.py`.

## Qué hay en cada archivo

| Archivo | Para qué sirve |
|---|---|
| `config.py` | Lo que se puede cambiar: umbral de alerta, indicadores, años |
| `fuentes/` | Un lector por fuente |
| `limpieza.py` | Se queda con ventas de vivienda activas, corrige el punto de miles, quita repetidos y datos imposibles o extremos, y anota cuántos descartó por cada motivo |
| `analisis.py` | Mediana por sector, cambio contra la corrida anterior y alerta |
| `reporte.py` | Gráfico y reporte en texto |
| `reporte_pdf.py` | (S08) El informe en PDF: Jinja2 + WeasyPrint |
| `plantillas/reporte.html.j2` | (S08) El molde del informe |
| `orquestador.py` | Orden de las tareas, reintentos y registro |
| `pipeline.py` | Define las tareas y de quién depende cada una |
| `bitacora.py` | (S07) La bitácora: una línea por evento |
| `monitoreo.py` | (S07) El semáforo y el historial de salud |
| `tests/` | 36 pruebas: 12 de la semana 6, 9 de resiliencia (S07), 10 del informe PDF (S08) y 5 del plan B vivo (S08) |
| `respaldo.py` | El plan B vivo: tras una corrida con datos reales aprobados, renueva `data/respaldo/` y anota la fecha en `data/respaldo/fechas.json` |
