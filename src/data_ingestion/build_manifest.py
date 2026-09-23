"""
NavAgro — Generador de manifiesto de datos (fuente, checksum, fecha)

Aplica la lección aprendida en TerraYield: cada archivo de datos crudos
debe tener un registro de manifiesto desde el primer script de ingesta,
no añadido después. Genera un manifest.jsonl con una fila por archivo,
igual que el patrón usado en TerraYield (S2-02-DE-03).

Uso:
    python3 src/data_ingestion/build_manifest.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

# Fuente y URL de descarga de cada archivo/carpeta rastreado. Debe
# mantenerse en sincronía con docs/fuentes_datos.md.
SOURCE_REGISTRY = {
    "data/comarcas_agrarias/AGRICU_Pol_ComAgrarias.shp": {
        "source_name": "comarcas_agrarias",
        "source_url": "https://idena.navarra.es/descargas/AGRICU_Pol_ComAgrarias.zip",
        "source_org": "Gobierno de Navarra — Desarrollo Rural y Medio Ambiente",
        "layer": "raw",
    },
    "data/produccion_cultivos/produccion_2015.xlsx": {
        "source_name": "produccion_cultivos_nastat",
        "source_url": "https://datosabiertos.navarra.es/es/dataset/producciones-anuales-de-los-cultivos",
        "source_org": "Nastat — Instituto de Estadística de Navarra",
        "layer": "raw",
    },
    "data/produccion_cultivos/produccion_2017.xlsx": {
        "source_name": "produccion_cultivos_nastat",
        "source_url": "https://datosabiertos.navarra.es/es/dataset/producciones-anuales-de-los-cultivos",
        "source_org": "Nastat — Instituto de Estadística de Navarra",
        "layer": "raw",
    },
    "data/produccion_cultivos/produccion_2019.xlsx": {
        "source_name": "produccion_cultivos_nastat",
        "source_url": "https://datosabiertos.navarra.es/es/dataset/producciones-anuales-de-los-cultivos",
        "source_org": "Nastat — Instituto de Estadística de Navarra",
        "layer": "raw",
    },
    "data/produccion_cultivos/produccion_2021.xlsx": {
        "source_name": "produccion_cultivos_nastat",
        "source_url": "https://datosabiertos.navarra.es/es/dataset/producciones-anuales-de-los-cultivos",
        "source_org": "Nastat — Instituto de Estadística de Navarra",
        "layer": "raw",
    },
    "data/produccion_cultivos/produccion_2023.xlsx": {
        "source_name": "produccion_cultivos_nastat",
        "source_url": "https://datosabiertos.navarra.es/es/dataset/producciones-anuales-de-los-cultivos",
        "source_org": "Nastat — Instituto de Estadística de Navarra",
        "layer": "raw",
    },
    "data/produccion_cultivos/produccion_2025.xlsx": {
        "source_name": "produccion_cultivos_nastat",
        "source_url": "https://datosabiertos.navarra.es/es/dataset/producciones-anuales-de-los-cultivos",
        "source_org": "Nastat — Instituto de Estadística de Navarra",
        "layer": "raw",
    },
    "outputs/tendencia_2019_2021.csv": {
        "source_name": "land_use_trend_derived",
        "source_url": None,
        "source_org": "NavAgro (derivado localmente)",
        "layer": "processed",
    },
    "outputs/tendencia_2019_2023.csv": {
        "source_name": "land_use_trend_derived",
        "source_url": None,
        "source_org": "NavAgro (derivado localmente)",
        "layer": "processed",
    },
    "outputs/tendencia_2021_2023.csv": {
        "source_name": "land_use_trend_derived",
        "source_url": None,
        "source_org": "NavAgro (derivado localmente)",
        "layer": "processed",
    },
    "outputs/produccion_combinada.csv": {
        "source_name": "produccion_cultivos_combinada",
        "source_url": None,
        "source_org": "NavAgro (derivado localmente)",
        "layer": "processed",
    },
}

# Archivos crudos grandes (MCA) que NO se conservan localmente (ver
# docs/fuentes_datos.md: se descargan, procesan, y borran). Se documentan
# aquí igual, con checksum=None, para dejar constancia de que existieron
# y de dónde se pueden volver a obtener, aunque no estén en disco ahora.
EPHEMERAL_SOURCES = {
    "data/mca_2019/OCUPAC_Pol_MCA_VE2019.shp": {
        "source_name": "mca_2019",
        "source_url": "https://idena.navarra.es/descargas/OCUPAC_Pol_MCA_VE2019.zip",
        "source_org": "Gobierno de Navarra — IDENA",
        "layer": "raw",
    },
    "data/mca_2021/OCUPAC_Pol_MCA_VE2021.shp": {
        "source_name": "mca_2021",
        "source_url": "https://idena.navarra.es/descargas/OCUPAC_Pol_MCA_VE2021.zip",
        "source_org": "Gobierno de Navarra — IDENA",
        "layer": "raw",
    },
    "data/mca_2023/OCUPAC_Pol_MCA_VE2023.shp": {
        "source_name": "mca_2023",
        "source_url": "https://idena.navarra.es/descargas/OCUPAC_Pol_MCA_VE2023.zip",
        "source_org": "Gobierno de Navarra — IDENA",
        "layer": "raw",
    },
}


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(repo_root: Path) -> list[dict]:
    rows = []

    for rel_path, meta in SOURCE_REGISTRY.items():
        full_path = repo_root / rel_path
        if not full_path.exists():
            print(f"AVISO: {rel_path} no existe en disco, se omite del manifiesto.")
            continue
        stat = full_path.stat()
        rows.append(
            {
                "file_path": rel_path,
                "source_name": meta["source_name"],
                "source_url": meta["source_url"],
                "source_org": meta["source_org"],
                "layer": meta["layer"],
                "sha256": sha256_of_file(full_path),
                "size_bytes": stat.st_size,
                "file_modified_utc": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
                "manifest_generated_utc": datetime.now(timezone.utc).isoformat(),
                "status": "present_on_disk",
            }
        )

    for rel_path, meta in EPHEMERAL_SOURCES.items():
        rows.append(
            {
                "file_path": rel_path,
                "source_name": meta["source_name"],
                "source_url": meta["source_url"],
                "source_org": meta["source_org"],
                "layer": meta["layer"],
                "sha256": None,
                "size_bytes": None,
                "file_modified_utc": None,
                "manifest_generated_utc": datetime.now(timezone.utc).isoformat(),
                "status": "downloaded_processed_deleted",
                "note": (
                    "Archivo crudo grande, descargado, procesado y borrado "
                    "localmente para ahorrar espacio (ver docs/fuentes_datos.md). "
                    "Checksum no disponible porque el archivo ya no está en disco "
                    "-- re-descargar con la URL de arriba para verificar contra "
                    "el original si hace falta."
                ),
            }
        )

    return rows


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    manifest_path = repo_root / "data" / "manifest.jsonl"

    rows = build_manifest(repo_root)

    with open(manifest_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    present = sum(1 for r in rows if r["status"] == "present_on_disk")
    ephemeral = sum(1 for r in rows if r["status"] == "downloaded_processed_deleted")

    print(f"Manifiesto generado: {manifest_path}")
    print(f"  {present} archivos presentes en disco, con checksum")
    print(f"  {ephemeral} archivos efímeros (descargados/procesados/borrados), sin checksum")
    print(f"  Total: {len(rows)} entradas")


if __name__ == "__main__":
    main()
