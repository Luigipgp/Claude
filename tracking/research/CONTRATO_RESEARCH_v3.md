# Lectura del research de mineras · contrato v3.0 (vigente desde 31-oct-2026)

Fuente: Drive > `04_Research_Acciones/<TICKER>/`.

> **Fuente complementaria, no única.** El research de Drive es un insumo más del análisis.
> - Se combina con IBKR (precios, cuenta, órdenes, alertas), con noticias y analistas fechados y con los datos de tu bróker.
> - Si un dato del research difiere de otra fuente, se reporta la diferencia con su fecha y fuente; no se impone ninguna.
> - Los precios de las posiciones siguen viniendo del bróker (ver la regla de gobierno de datos).

1. **Primero ESTADO_<TICKER>.json.** Se busca con `search_files` usando `title = 'ESTADO_<TICKER>.json'` (título exacto), se baja con `download_file_content` y se decodifica el base64.
2. **Resumen por ticker:** Google Doc **INDICE-Research** (`fileId 1zXOhgaOMXWEzrd26HC9yhPM5CEigLTzmLC6Xvxgoklg`), leído con `read_file_content`.
3. **Cambios desde el último reporte:** campo `delta` del ESTADO.
4. **`HIST_<TICKER>` es SOLO LECTURA.** Lo escribe únicamente el proyecto "Analisis Mineras_Junior". Desde aquí nunca se escribe en Drive.
5. **Un ESTADO con `nota_demo` no es definitivo y se ignora.**
6. **Ticker canónico = el que negocia en EE. UU.** (GALKF, SRGXF, RIOFF), no el alias.
   - Ejemplo: la posición IBK `GAL @VENTURE` se busca en el research como **GALKF**.
   - La cotización sigue saliendo del listado que se tiene en IBKR.

Este repo implementa las reglas en `research_reader.py`. Ese script solo lee archivos locales, ya descargados y decodificados. Decide si un ESTADO entra al análisis como una fuente más.
