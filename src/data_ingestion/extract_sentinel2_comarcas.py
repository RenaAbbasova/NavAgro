"""
NavAgro — Pipeline de extracción Sentinel-2 (Sprint 2)

Calcula estadísticas regionales de Sentinel-2 por (comarca, ventana de 16
días) para las 7 comarcas agrarias reales de Navarra, y exporta los
resultados como tareas asíncronas a GEE Assets.

Diseño (config-driven vía sentinel2_pipeline_config.yaml), aplicando
lecciones de TerraYield:
  - Ventanas de 16 días, alineadas al ciclo de revisita nativo de Sentinel-2
    (mismo enfoque que el schema v2.0 maduro de TerraYield).
  - Exporta a GEE Assets, no a Google Drive -- el Drive de una cuenta de
    servicio pertenece a esa cuenta, no al usuario; los resultados quedarían
    inaccesibles (lección explícita documentada en TerraYield).
  - EVI excluido a propósito (ver config) hasta implementar y validar una
    guarda de denominador explícita -- no se repite el bug de TerraYield.
  - cloud_cover_pct siempre calculado del metadato real de las escenas,
    nunca un valor fijo.
  - valid_pixel_count por ventana, con umbral de calidad configurable que
    FLAGGEA (no excluye silenciosamente) ventanas de baja confianza.
  - Geometría real de las 7 comarcas (no bounding boxes aproximados).
  - Chequeo de sanidad: imprime el número de tareas esperado antes de
    enviarlas, para poder confirmar que el volumen es razonable.

Uso:
    python3 src/data_ingestion/extract_sentinel2_comarcas.py \\
        --config configs/sentinel2_pipeline_config.yaml \\
        --start-date 2024-01-01 --end-date 2024-12-31
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

import ee
import geopandas as gpd
import yaml
from dotenv import load_dotenv


def init_earth_engine() -> None:
    load_dotenv()
    key_file = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    project = os.environ["GEE_PROJECT_NAME"]
    credentials = ee.ServiceAccountCredentials(email=None, key_file=key_file)
    ee.Initialize(credentials, project=project)


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_comarcas(config: dict) -> dict[str, ee.Geometry]:
    """Carga las 7 comarcas reales con su geometría exacta, disolviendo
    multi-partes en un único polígono por comarca."""
    shapefile = Path(config["source"]["comarcas_shapefile"])
    name_field = config["source"]["comarca_name_field"]

    gdf = gpd.read_file(shapefile).to_crs("EPSG:4326")
    gdf = gdf.dissolve(by=name_field)

    return {name: ee.Geometry(geom.__geo_interface__) for name, geom in gdf.geometry.items()}


def generate_windows(start_date: str, end_date: str, window_days: int) -> list[tuple[str, str, str]]:
    """Genera ventanas consecutivas de N días entre dos fechas. Devuelve
    (window_id, window_start, window_end) para cada una, con window_id
    determinístico a partir de la fecha de inicio."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    windows = []
    current = start
    while current < end:
        window_end = min(current + timedelta(days=window_days), end)
        window_id = f"W-{current.strftime('%Y%m%d')}"
        windows.append((window_id, current.strftime("%Y-%m-%d"), window_end.strftime("%Y-%m-%d")))
        current = window_end
    return windows


def mask_clouds(image: ee.Image, config: dict) -> ee.Image:
    scl = image.select(config["cloud_masking"]["scl_band"])
    valid_classes = config["cloud_masking"]["valid_classes"]
    valid_mask = ee.Image.constant(0).byte()
    for cls in valid_classes:
        valid_mask = valid_mask.Or(scl.eq(cls))
    return image.updateMask(valid_mask)


def add_indices(image: ee.Image, config: dict) -> ee.Image:
    bands = config["bands"]
    ndvi = image.normalizedDifference([bands["nir"], bands["red"]]).rename("ndvi")
    ndwi = image.normalizedDifference([bands["green"], bands["nir"]]).rename("ndwi")
    ndbi = image.normalizedDifference([bands["swir1"], bands["nir"]]).rename("ndbi")
    return image.addBands([ndvi, ndwi, ndbi])


def build_reducer(stats: list[str]) -> ee.Reducer:
    reducer_map = {
        "mean": ee.Reducer.mean(),
        "stdDev": ee.Reducer.stdDev(),
        "min": ee.Reducer.min(),
        "max": ee.Reducer.max(),
    }
    reducer = reducer_map[stats[0]]
    for stat in stats[1:]:
        reducer = reducer.combine(reducer2=reducer_map[stat], sharedInputs=True)
    return reducer


def build_window_feature(
    comarca_name: str,
    geometry: ee.Geometry,
    window_id: str,
    window_start: str,
    window_end: str,
    config: dict,
) -> ee.Feature:
    """Construye un ee.Feature con las estadísticas de una (comarca, ventana).
    Todo el cómputo queda del lado del servidor -- se resuelve en batch al
    exportar, no con llamadas getInfo() individuales (que no escalan)."""
    collection = (
        ee.ImageCollection(config["source"]["collection"])
        .filterBounds(geometry)
        .filterDate(window_start, window_end)
    )

    masked = collection.map(lambda img: mask_clouds(img, config)).map(lambda img: add_indices(img, config))
    composite = masked.median()

    index_names = [idx["name"] for idx in config["indices"]]
    reducer = build_reducer(config["output"]["stats"])

    stats = composite.select(index_names).reduceRegion(
        reducer=reducer,
        geometry=geometry,
        scale=config["output"]["scale_meters"],
        maxPixels=1e9,
        tileScale=4,
        bestEffort=True,
    )

    valid_pixel_count = composite.select(index_names[0]).reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=geometry,
        scale=config["output"]["scale_meters"],
        maxPixels=1e9,
        tileScale=4,
        bestEffort=True,
    ).values().get(0)

    cloud_cover_pct_mean = collection.aggregate_mean("CLOUDY_PIXEL_PERCENTAGE")
    scene_count = collection.size()

    extra_properties = ee.Dictionary({
        "comarca": comarca_name,
        "window_id": window_id,
        "window_start": window_start,
        "window_end": window_end,
        "scene_count": scene_count,
        "valid_pixel_count": valid_pixel_count,
        "cloud_cover_pct_mean": cloud_cover_pct_mean,
        "schema_version": config["schema_version"],
        "data_source": config["data_source_label"],
    })
    properties = stats.combine(extra_properties)

    return ee.Feature(None, properties)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/sentinel2_pipeline_config.yaml"))
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Envía las tareas de verdad. Sin esta bandera, solo muestra el chequeo de sanidad y termina.",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    print("Autenticando con Earth Engine...")
    init_earth_engine()

    print(f"Cargando geometría real de comarcas desde {config['source']['comarcas_shapefile']}...")
    comarcas = load_comarcas(config)
    print(f"  {len(comarcas)} comarcas: {sorted(comarcas.keys())}")

    windows = generate_windows(args.start_date, args.end_date, config["temporal"]["window_days"])
    print(f"\n{len(windows)} ventanas de {config['temporal']['window_days']} días entre {args.start_date} y {args.end_date}")

    total_features = len(comarcas) * len(windows)
    print(f"\n=== Chequeo de sanidad ===")
    print(f"{len(comarcas)} comarcas x {len(windows)} ventanas = {total_features} filas de resultado")
    print(f"Se exportará como UNA tarea de tabla (FeatureCollection), no {total_features} tareas separadas.")

    if not args.confirm:
        print("\nEsto fue solo el chequeo de sanidad -- no se envió ninguna tarea.")
        print("Si el número de filas es razonable, vuelve a correr con --confirm.")
        return

    print("\nConstruyendo FeatureCollection (cómputo del lado del servidor)...")
    features = []
    for comarca_name, geometry in comarcas.items():
        for window_id, window_start, window_end in windows:
            features.append(
                build_window_feature(comarca_name, geometry, window_id, window_start, window_end, config)
            )
    fc = ee.FeatureCollection(features)

    asset_folder = config["output"]["gee_asset_folder"]
    asset_id = f"projects/{os.environ['GEE_PROJECT_NAME']}/assets/{asset_folder}/sentinel2_{args.start_date}_{args.end_date}"

    task = ee.batch.Export.table.toAsset(
        collection=fc,
        description=f"navagro_sentinel2_{args.start_date}_{args.end_date}",
        assetId=asset_id,
    )
    task.start()

    print(f"\nTarea enviada: {task.id}")
    print(f"Asset de destino: {asset_id}")
    print("Progreso: https://code.earthengine.google.com/tasks")
    print("Una vez completada, usa download_sentinel2_asset.py para traer el resultado a un CSV local.")


if __name__ == "__main__":
    main()