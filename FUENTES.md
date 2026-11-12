# Fuentes del Observatorio de Referencia

| Dato | Fuente | Dirección | Respaldo |
|---|---|---|---|
| Anuncios de venta y arriendo | RE/MAX Ecuador | API pública de https://www.remax.com.ec (api-ec.redremax.com) | `data/respaldo/respaldo_remax.csv` (170 anuncios reales de Quito, 8 oct 2026) |
| Inflación anual (%) | Banco Mundial, FP.CPI.TOTL.ZG | https://api.worldbank.org/v2/country/ECU/indicator/FP.CPI.TOTL.ZG | `respaldo_banco_mundial.csv`, 2015–2025 |
| Crecimiento del PIB (%) | Banco Mundial, NY.GDP.MKTP.KD.ZG | https://api.worldbank.org/v2/country/ECU/indicator/NY.GDP.MKTP.KD.ZG | `respaldo_banco_mundial.csv`, 2018–2025 |
| Crédito privado (% del PIB) | Banco Mundial, FS.AST.PRVT.GD.ZS | https://api.worldbank.org/v2/country/ECU/indicator/FS.AST.PRVT.GD.ZS | `respaldo_banco_mundial.csv`, 2018–2025 |
| Crecimiento del PIB (%) | FMI, DataMapper NGDP_RPCH | https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH/ECU | `respaldo_fmi.csv`, 2018–2026 (2026 es proyección) |

Los respaldos del Banco Mundial y del FMI se consultaron el 8 de octubre de 2026.
