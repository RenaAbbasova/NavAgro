# NavAgro — Analítica de IA para el Uso de Suelo Agrícola y Rendimiento de Cultivos en Navarra

Proyecto personal de investigación que combina imágenes satelitales (Sentinel-2), estadísticas oficiales de producción agrícola y cartografía de uso de suelo para analizar tendencias agrícolas reales en las 7 comarcas de Navarra (España).

Inspirado en la metodología de [TerraYield](https://github.com/OmdenaAI/TerraYield-2), un proyecto colaborativo de predicción de rendimiento de cultivos a escala internacional, aplicando sus lecciones de ingeniería de datos desde el diseño inicial.

## Hallazgo principal

Entre 2021 y 2023, la comarca **Nordoccidental** perdió el **78% de sus parcelas de cultivo herbáceo de secano** (1,740 → 386), con un aumento correspondiente del **58% en terreno forestal**. Pero el efecto sobre la producción real no fue uniforme:

| Cultivo | Producción 2019 → 2023 | NDVI 2019 → 2023 |
|---|---|---|
| Cebada | 2,321 t → 1,854 t (**-20%**) | 0.59 → 0.65 (**+10%**) |
| Trigo blando | 3,908 t → 4,495 t (**+15%**) | 0.59 → 0.65 (**+10%**) |

La cebada cae junto con la superficie cultivada, pero el trigo blando **crece a pesar de la pérdida de parcelas**, mientras el NDVI mejora — sugiriendo una recomposición hacia tierras más productivas, no un simple abandono agrícola.

## Qué hace este proyecto

- **Track A — Predicción de rendimiento**: modelos base para trigo blando y cebada, por comarca y año, usando estadísticas satelitales reales.
- **Track B — Tendencia de uso de suelo**: detección de cambio gradual (no binario) en el uso de suelo agrícola, comarca por comarca.

## Fuentes de datos (100% públicas y oficiales)

| Fuente | Qué aporta |
|---|---|
| [Nastat](https://nastat.navarra.es) — Instituto de Estadística de Navarra | Producción anual de cultivos, 2000-presente |
| [IDENA](https://idena.navarra.es) — Gobierno de Navarra | Mapa de Cultivos y Aprovechamientos, comarcas agrarias oficiales |
| [Sentinel-2](https://sentinel.esa.int/web/sentinel/missions/sentinel-2) vía Google Earth Engine | Bandas espectrales e índices de vegetación (NDVI, NDWI, NDBI) |

## Resultado del primer benchmark

| Modelo | MAE | R² |
|---|---|---|
| Media Histórica | 11,321 t | **0.585** |
| Regresión Lineal (solo NDVI) | 20,311 t | -0.189 |

Con solo 28 filas de entrenamiento (7 comarcas × 2 cultivos × 2 años), el NDVI por sí solo todavía no supera a la línea base más simple — resultado honesto que refleja el tamaño actual de la muestra, no una limitación del enfoque. La Media Histórica ya explica el 58.5% de la varianza, un piso sólido sobre el cual construir.

## Lecciones de ingeniería aplicadas desde el diseño

Este proyecto aplica, desde el primer commit, varias lecciones aprendidas en un proyecto anterior (TerraYield):

- **Manifiesto de datos desde el inicio** — cada archivo crudo tiene checksum SHA-256, fuente y fecha registrados (`data/manifest.jsonl`), no añadido después.
- **Nunca fabricar valores faltantes** — si Earth Engine no encuentra escenas válidas para una comarca/ventana, esa fila se omite explícitamente, nunca se rellena con un placeholder.
- **`cloud_cover_pct` siempre real** — leído del metadato de cada escena, nunca un valor fijo.
- **Índices espectrales con denominador protegido** — evitando el tipo de bug (EVI con denominador cercano a cero) que en TerraYield produjo valores erróneos de hasta -17 millones.
- **Exportación asíncrona a GEE Assets, no a Google Drive** — el Drive de una cuenta de servicio pertenece a esa cuenta, no al usuario.
- **Validación cruzada de nombres geográficos** — Nastat usa "Noroccidental"; la cartografía oficial usa "Nordoccidental". Documentado y corregido explícitamente, no descubierto por accidente.

## Estructura del repositorio

```
NavAgro/
├── configs/                      # Configuración del pipeline satelital (YAML)
├── data/
│   ├── comarcas_agrarias/        # Geometría oficial de las 7 comarcas
│   ├── produccion_cultivos/      # Exportaciones originales de Nastat
│   └── manifest.jsonl            # Manifiesto con checksums de cada archivo
├── docs/
│   └── fuentes_datos.md          # Cómo descargar cada fuente, y estrategia de almacenamiento
├── outputs/                      # Resultados procesados: tendencias, dataset integrado, benchmarks
└── src/
    ├── data_ingestion/           # Extracción de Sentinel-2, manifiesto
    └── analysis/                 # Análisis de tendencia, integración, modelos base
```

## Estado del proyecto

- [x] **Sprint 1** — Ingeniería de datos (comarcas, producción, uso de suelo, manifiesto)
- [x] **Sprint 2** — Pipeline satelital (Sentinel-2, 3 años, 7 comarcas)
- [x] **Sprint 3** — Primer benchmark de rendimiento (en progreso: mejorando features)
- [ ] **Sprint 4** — Dashboard de visualización

## Cómo reproducir

```bash
git clone https://github.com/RenaAbbasova/NavAgro.git
cd NavAgro
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # geopandas, earthengine-api, pandas, scikit-learn, pyyaml, python-dotenv, openpyxl

# Ver docs/fuentes_datos.md para descargar los datos crudos
# Configurar credentials/service_account.json y .env (ver docs/fuentes_datos.md)

python3 src/analysis/build_modeling_dataset.py
python3 src/analysis/baseline_models.py
```

## Autora

Rena Abbasova — [LinkedIn](https://www.linkedin.com/) · Proyecto personal, sin afiliación institucional.
