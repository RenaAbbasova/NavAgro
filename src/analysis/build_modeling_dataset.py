"""
NavAgro — Integración de datos para benchmarking (Sprint 3)

Une las 3 fuentes de datos en un único dataset a nivel (comarca, año),
listo para construir modelos base de predicción de rendimiento.

Grano de salida: (comarca, year, cultivo) con producción real y estadísticas
satelitales agregadas del año completo.

Caveat importante, aplicando una lección directa de TerraYield (Sección 5,
"Feature-Grain Assumption"): las estadísticas de Sentinel-2 son a nivel de
comarca completa, promediando TODOS los usos de suelo dentro de ella (no
solo las parcelas de trigo o cebada). Son features "crop-agnostic", no
"crop-attributable" -- el mismo valor de NDVI se usa como feature tanto
para trigo como para cebada en una comarca dada. Esto se documenta
explícitamente aquí, no se descubre después.

Uso:
    python3 src/analysis/build_modeling_dataset.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

YEARS = [2019, 2021, 2023]
CROPS = ["Trigo blando", "Cebada"]

# Nastat usa "Noroccidental"; el shapefile oficial de comarcas usa
# "Nordoccidental" (con "d"). Normalizamos al nombre del shapefile, que es
# la fuente de verdad geográfica del proyecto (region_id real).
COMARCA_NAME_FIXES = {
    "Noroccidental": "Nordoccidental",
}


def normalize_comarca_names(df: pd.DataFrame, column: str = "comarca") -> pd.DataFrame:
    df = df.copy()
    df[column] = df[column].replace(COMARCA_NAME_FIXES)
    return df


def load_production(outputs_dir: Path) -> pd.DataFrame:
    """Carga la producción combinada, filtrada a los años y cultivos de
    interés, usando el tipo_riego 'Total' (agregado secano+regadío) para
    que el grano coincida con las estadísticas satelitales, que no
    distinguen tipo de riego."""
    df = pd.read_csv(outputs_dir / "produccion_combinada.csv")
    df = df[
        (df["year"].isin(YEARS))
        & (df["cultivo"].isin(CROPS))
        & (df["tipo_riego"] == "Total")
        & (df["comarca"] != "Comunidad Foral de Navarra")  # nivel comarca, no el total regional
    ]
    result = df[["comarca", "cultivo", "year", "produccion_tn"]]
    return normalize_comarca_names(result)


def load_satellite_yearly(data_dir: Path) -> pd.DataFrame:
    """Carga los 3 CSV de Sentinel-2 (uno por año) y los agrega a nivel
    (comarca, year) -- promedio de todas las ventanas de 16 días del año."""
    frames = []
    for year in YEARS:
        path = data_dir / f"sentinel2_{year}.csv"
        df = pd.read_csv(path)
        df["year"] = year
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)

    agg = combined.groupby(["comarca", "year"]).agg(
        ndvi_mean_annual=("ndvi_mean", "mean"),
        ndwi_mean_annual=("ndwi_mean", "mean"),
        ndbi_mean_annual=("ndbi_mean", "mean"),
        cloud_cover_pct_annual=("cloud_cover_pct_mean", "mean"),
        valid_pixel_count_annual=("valid_pixel_count", "sum"),
        window_count=("window_id", "count"),
    ).reset_index()

    return agg


def build_modeling_dataset(outputs_dir: Path) -> pd.DataFrame:
    production = load_production(outputs_dir)
    satellite = load_satellite_yearly(outputs_dir)

    merged = production.merge(satellite, on=["comarca", "year"], how="left")

    missing_satellite = merged["ndvi_mean_annual"].isna().sum()
    if missing_satellite > 0:
        print(
            f"AVISO: {missing_satellite} filas sin datos satelitales "
            f"correspondientes -- revisar coincidencia de nombres de comarca."
        )

    return merged


def main() -> None:
    outputs_dir = Path("outputs")

    dataset = build_modeling_dataset(outputs_dir)

    output_path = outputs_dir / "modeling_dataset_v1.csv"
    dataset.to_csv(output_path, index=False)

    print(f"Dataset de modelado construido: {len(dataset)} filas")
    print(f"Comarcas: {dataset['comarca'].nunique()}, Años: {sorted(dataset['year'].unique())}, "
          f"Cultivos: {list(dataset['cultivo'].unique())}")
    print(f"\nGuardado en: {output_path}")
    print("\nPrimeras filas:")
    print(dataset.head(10).to_string(index=False))

    print(
        "\nCAVEAT: ndvi_mean_annual/ndwi_mean_annual/"
        "ndbi_mean_annual son a nivel de comarca completa, no específicos del "
        "cultivo -- el mismo valor satelital se usa como feature tanto para "
        "Trigo blando como para Cebada en la misma comarca/año."
    )


if __name__ == "__main__":
    main()