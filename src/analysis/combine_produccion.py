"""
NavAgro — Combinar producción anual de cultivos (Nastat) por comarca/año

Lee los archivos produccion_AAAA.xlsx exportados desde el portal Nastat
(PxWeb), y los combina en un único dataset limpio en formato largo:
(comarca, cultivo, tipo_riego, year, produccion_tn).

Modo inspección (para ver la estructura cruda antes de parsear):
    python3 src/analysis/combine_produccion.py --inspect data/produccion_cultivos/produccion_2015.xlsx

Modo combinar (una vez confirmada la estructura):
    python3 src/analysis/combine_produccion.py --combine --data-dir data/produccion_cultivos --output outputs/produccion_combinada.csv
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


CROPS_OF_INTEREST = {"Trigo blando", "Cebada"}


def inspect_file(path: Path) -> None:
    """Muestra las primeras filas crudas del archivo, sin asumir estructura,
    para confirmar en qué fila están los encabezados reales antes de parsear."""
    raw = pd.read_excel(path, header=None)
    print(f"Archivo: {path}")
    print(f"Dimensiones: {raw.shape[0]} filas x {raw.shape[1]} columnas\n")
    print("Primeras 20 filas (todas las columnas):")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(raw.head(20))


def _to_float(value) -> float | None:
    """Convierte un valor con formato español (coma decimal) a float.
    Devuelve None si no es convertible (celdas vacías, texto, etc.)."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s.lower() in {"nan", ""}:
        return None
    s = s.replace(".", "").replace(",", ".")  # 1.234,56 -> 1234.56
    try:
        return float(s)
    except ValueError:
        return None


def parse_produccion_file(path: Path, year: int) -> pd.DataFrame:
    """Parsea un archivo produccion_AAAA.xlsx a formato largo.

    Estructura esperada (típica de exportación PxWeb):
      Fila 0: 'Comarca', <nombre comarca 1>, <nombre comarca 2>, ...
      Fila 1: 'Tipo de dato', 'Producción', 'Producción', ...
      Fila 2: 'Cultivo', 'tipo_agricultura', 'Medida_valor', ...
      Filas de datos: <cultivo o vacío>, <Total/Secano/Regadío>, <valores...>
      Al final: fila 'Total' y notas de 'Filtros aplicados' (se descartan).
    """
    raw = pd.read_excel(path, header=None)

    header_row_idx = raw[raw.iloc[:, 0] == "Comarca"].index
    if len(header_row_idx) == 0:
        raise ValueError(
            f"No se encontró la fila de encabezado 'Comarca' en {path}. "
            f"Corre --inspect para revisar la estructura real."
        )
    header_row = header_row_idx[0]

    comarca_names = raw.iloc[header_row, 2:].tolist()
    data_start = header_row + 3  # salta las 3 filas de encabezado

    records = []
    current_crop = None
    for i in range(data_start, len(raw)):
        row = raw.iloc[i]
        first_cell = row.iloc[0]
        second_cell = row.iloc[1]

        if pd.notna(first_cell) and str(first_cell).strip() == "Total":
            break  # fila resumen final, ya no hay más datos de cultivos
        if pd.notna(first_cell) and str(first_cell).strip() == "":
            continue

        if pd.notna(first_cell):
            current_crop = str(first_cell).strip()

        if pd.isna(second_cell):
            continue
        tipo_riego = str(second_cell).strip()

        if current_crop not in CROPS_OF_INTEREST:
            continue

        for col_idx, comarca in enumerate(comarca_names, start=2):
            if pd.isna(comarca):
                continue
            value = _to_float(row.iloc[col_idx])
            if value is None:
                continue
            records.append(
                {
                    "comarca": str(comarca).strip(),
                    "cultivo": current_crop,
                    "tipo_riego": tipo_riego,
                    "year": year,
                    "produccion_tn": value,
                }
            )

    return pd.DataFrame.from_records(records)


def extract_year_from_filename(path: Path) -> int:
    match = re.search(r"(\d{4})", path.stem)
    if not match:
        raise ValueError(f"No se pudo extraer el año del nombre de archivo: {path}")
    return int(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", type=Path, help="Ruta a un .xlsx para inspeccionar su estructura cruda")
    parser.add_argument("--combine", action="store_true", help="Combinar todos los archivos del directorio")
    parser.add_argument("--data-dir", type=Path, default=Path("data/produccion_cultivos"))
    parser.add_argument("--output", type=Path, default=Path("outputs/produccion_combinada.csv"))
    args = parser.parse_args()

    if args.inspect:
        inspect_file(args.inspect)
        return

    if args.combine:
        files = sorted(args.data_dir.glob("produccion_*.xlsx"))
        if not files:
            raise FileNotFoundError(f"No se encontraron archivos produccion_*.xlsx en {args.data_dir}")

        all_dfs = []
        for f in files:
            year = extract_year_from_filename(f)
            print(f"Procesando {f.name} (año {year})...")
            df = parse_produccion_file(f, year)
            print(f"  -> {len(df)} filas extraídas")
            all_dfs.append(df)

        combined = pd.concat(all_dfs, ignore_index=True)
        combined = combined.sort_values(["comarca", "cultivo", "tipo_riego", "year"])

        args.output.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(args.output, index=False)
        print(f"\nTotal combinado: {len(combined)} filas")
        print(f"Guardado en: {args.output}")
        print("\nResumen por año:")
        print(combined.groupby("year").size())
        return

    parser.print_help()


if __name__ == "__main__":
    main()
