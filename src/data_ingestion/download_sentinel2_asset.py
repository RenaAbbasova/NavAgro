"""
NavAgro — Descarga de resultados desde GEE Assets a CSV local

Complementa extract_sentinel2_comarcas.py: una vez que la tarea de
exportación aparece como COMPLETED en code.earthengine.google.com/tasks,
este script trae el resultado (FeatureCollection en Assets) a un CSV local.

Uso:
    python3 src/data_ingestion/download_sentinel2_asset.py \\
        --asset-id projects/navagro-gee/assets/sentinel2_navarra_comarcas/sentinel2_2024-01-01_2024-12-31 \\
        --output outputs/sentinel2_2024.csv
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import ee
import pandas as pd
from dotenv import load_dotenv


def init_earth_engine() -> None:
    load_dotenv()
    key_file = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    project = os.environ["GEE_PROJECT_NAME"]
    credentials = ee.ServiceAccountCredentials(email=None, key_file=key_file)
    ee.Initialize(credentials, project=project)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-id", required=True, help="ID completo del asset en GEE")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    print("Autenticando con Earth Engine...")
    init_earth_engine()

    print(f"Descargando asset: {args.asset_id}...")
    fc = ee.FeatureCollection(args.asset_id)
    features = fc.getInfo()["features"]

    rows = [f["properties"] for f in features]
    df = pd.DataFrame(rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    print(f"\n{len(df)} filas descargadas.")
    print(f"Guardado en: {args.output}")

    # Chequeo de calidad rápido, aplicando el umbral definido en el pipeline
    if "valid_pixel_count" in df.columns:
        low_quality = (df["valid_pixel_count"].fillna(0) == 0).sum()
        print(f"\nFilas con valid_pixel_count = 0 (sin datos reales, no fabricados): {low_quality}/{len(df)}")


if __name__ == "__main__":
    main()
