"""
NavAgro — Comparación de tendencia de uso de suelo por comarca (S3-like benchmark)

Compara el Mapa de Cultivos y Aprovechamientos (MCA) entre dos años,
uniendo espacialmente cada parcela a su comarca agraria correspondiente,
para detectar tendencias de cambio de uso de suelo a nivel de comarca.

Uso:
    python3 src/analysis/land_use_trend.py --year-start 2021 --year-end 2023
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd


def load_mca(year: int, data_dir: Path) -> gpd.GeoDataFrame:
    """Carga el shapefile del Mapa de Cultivos y Aprovechamientos de un año dado."""
    path = data_dir / f"mca_{year}" / f"OCUPAC_Pol_MCA_VE{year}.shp"
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró {path}. Descárgalo primero (ver docs/fuentes_datos.md)."
        )
    gdf = gpd.read_file(path)
    gdf["year"] = year
    return gdf


def load_comarcas(data_dir: Path) -> gpd.GeoDataFrame:
    """Carga el shapefile de las 7 comarcas agrarias."""
    path = data_dir / "comarcas_agrarias" / "AGRICU_Pol_ComAgrarias.shp"
    if not path.exists():
        raise FileNotFoundError(f"No se encontró {path}.")
    return gpd.read_file(path)[["IDCOMARCA", "COMARCA", "geometry"]]


def join_parcela_comarca(mca: gpd.GeoDataFrame, comarcas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Une espacialmente cada parcela del MCA a su comarca, usando el centroide
    de la parcela (más rápido que un join por intersección completa, y suficiente
    para asignar una única comarca por parcela)."""
    mca_centroids = mca.copy()
    mca_centroids["geometry"] = mca.geometry.centroid
    joined = gpd.sjoin(mca_centroids, comarcas, how="left", predicate="within")
    return joined


def compute_trend_by_comarca(
    gdf_start: gpd.GeoDataFrame, gdf_end: gpd.GeoDataFrame, group_col: str = "GRUPO"
) -> pd.DataFrame:
    """Calcula el cambio en número de parcelas por (comarca, categoría de uso)
    entre dos años."""
    counts_start = (
        gdf_start.groupby(["COMARCA", group_col]).size().rename("count_start")
    )
    counts_end = gdf_end.groupby(["COMARCA", group_col]).size().rename("count_end")

    trend = pd.concat([counts_start, counts_end], axis=1).fillna(0)
    trend["change"] = trend["count_end"] - trend["count_start"]
    trend["pct_change"] = (
        trend["change"] / trend["count_start"].replace(0, pd.NA) * 100
    )
    return trend.reset_index().sort_values("change")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year-start", type=int, required=True)
    parser.add_argument("--year-end", type=int, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    comarcas = load_comarcas(args.data_dir)

    print(f"Cargando MCA {args.year_start}...")
    mca_start = load_mca(args.year_start, args.data_dir)
    print(f"Cargando MCA {args.year_end}...")
    mca_end = load_mca(args.year_end, args.data_dir)

    print("Uniendo parcelas a comarcas (año inicio)...")
    joined_start = join_parcela_comarca(mca_start, comarcas)
    print("Uniendo parcelas a comarcas (año fin)...")
    joined_end = join_parcela_comarca(mca_end, comarcas)

    trend = compute_trend_by_comarca(joined_start, joined_end)

    print(f"\n=== Tendencia de uso de suelo por comarca: {args.year_start} -> {args.year_end} ===\n")
    print(trend.to_string(index=False))

    if args.output:
        trend.to_csv(args.output, index=False)
        print(f"\nGuardado en: {args.output}")


if __name__ == "__main__":
    main()