# Observatorio de Referencia · Mercado inmobiliario y hábitat de Quito

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

**Regla de oro del respaldo:** si una corrida usa el respaldo, el reporte lo dice y **no se guarda en el histórico**. Así nunca se mezclan datos viejos con la serie real.

**Pendiente:** confirmar que la API contesta desde los servidores de GitHub (se prueba una vez con **Run workflow**). Si no contestara, el robot usa el respaldo y lo avisa en el reporte.

## El recorrido del dato

```
BUSCAR      remax, banco_mundial, fmi        (se ejecutan sin esperarse entre sí)
GUARDAR     data/*_crudo.csv
LIMPIAR     limpiar                          (espera a las tres anteriores)
CONTROLAR   control_calidad                  (si los datos no son confiables, FALLA A PROPÓSITO)
ANALIZAR    analizar                         (mediana por sector, cambio contra ayer, alerta)
MOSTRAR     reportar                         (gráfico y reporte en texto)
AUTOMATIZAR .github/workflows/orquestador_diario.yml
```

`orquestador.py` es el director: ejecuta cada tarea cuando sus dependencias terminaron, reintenta si una falla y omite las que dependían de la que falló. Deja el resultado en `logs/ultima_corrida.json`.

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
| `reporte.py` | Gráfico y reporte |
| `orquestador.py` | Orden de las tareas, reintentos y registro |
| `pipeline.py` | Define las tareas y de quién depende cada una |
| `tests/` | Seis pruebas que comprueban que todo funciona |
