"""
NavAgro — Señal de cambio de uso de suelo por comarca (Sprint 3, Track B)

Construye una puntuación cuantificada de intensidad de cambio de uso de
suelo por comarca, análoga en espíritu al `change_candidate_score` de
TerraYield: una señal de anomalía NO SUPERVISADA (sin etiqueta de verdad
sobre qué comarcas "realmente" cambiaron), pensada para priorizar dónde
mirar con más detalle, no como una predicción validada.

Diseño adaptado al enfoque de "tendencia gradual, no cambio binario" de
NavAgro (distinto del enfoque de TerraYield): en vez de comparar un único
par antes/después, se usa el período más largo disponible (2019->2023)
para capturar la tendencia completa, y se combinan las 2 categorías de
uso de suelo más relevantes para transición agrícola -- pérdida de
cultivo herbáceo de secano y ganancia de forestal no arbolado -- que ya
se confirmaron como el patrón dominante en el análisis descriptivo previo.

Uso:
    python3 src/analysis/land_use_change_signal.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Las 2 categorías con el patrón de cambio más fuerte y consistente,
# confirmadas en el análisis descriptivo (outputs/tendencia_*.csv).
SIGNAL_CATEGORIES = ["Cultivos herbáceos secano", "Forestal no arbolado"]

Z_THRESHOLD = 1.5  # mismo umbral por defecto usado en TerraYield


def load_trend(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def compute_change_signal(trend: pd.DataFrame) -> pd.DataFrame:
    """Para cada comarca, combina la magnitud de cambio (valor absoluto de
    pct_change) de las categorías señal en una única puntuación. Se usa
    valor absoluto porque tanto una caída fuerte de secano como una subida
    fuerte de forestal son igualmente indicativas de cambio, sin importar
    la dirección."""
    subset = trend[trend["GRUPO"].isin(SIGNAL_CATEGORIES)].copy()
    subset["abs_pct_change"] = subset["pct_change"].abs()

    signal = (
        subset.groupby("COMARCA")["abs_pct_change"]
        .sum()
        .rename("land_use_change_score")
        .reset_index()
    )
    return signal


def add_anomaly_flag(signal: pd.DataFrame) -> pd.DataFrame:
    """Marca como 'candidata a cambio significativo' cualquier comarca cuya
    puntuación esté a más de Z_THRESHOLD desviaciones estándar por encima
    de la media de las 7 comarcas -- señal no supervisada de priorización,
    no una etiqueta validada de verdad de campo."""
    signal = signal.copy()
    mean = signal["land_use_change_score"].mean()
    std = signal["land_use_change_score"].std()

    signal["z_score"] = (signal["land_use_change_score"] - mean) / std
    signal["change_candidate_flag"] = signal["z_score"] > Z_THRESHOLD
    return signal.sort_values("land_use_change_score", ascending=False)


def main() -> None:
    trend_path = Path("outputs/tendencia_2019_2023.csv")
    trend = load_trend(trend_path)

    signal = compute_change_signal(trend)
    signal = add_anomaly_flag(signal)

    output_path = Path("outputs/land_use_change_signal.csv")
    signal.to_csv(output_path, index=False)

    print("=== Señal de cambio de uso de suelo, 2019-2023 ===\n")
    print(signal.to_string(index=False))
    print(f"\nGuardado en: {output_path}")

    flagged = signal[signal["change_candidate_flag"]]
    if len(flagged) > 0:
        print(f"\n{len(flagged)} comarca(s) marcada(s) como candidata a cambio significativo:")
        for _, row in flagged.iterrows():
            print(f"  - {row['COMARCA']} (score={row['land_use_change_score']:.1f}, z={row['z_score']:.2f})")
    else:
        print("\nNinguna comarca supera el umbral de anomalía (z > 1.5).")

    print(
        "\nAVISO (misma naturaleza que TerraYield's change_candidate_score): "
        "esta es una señal NO SUPERVISADA para priorizar dónde mirar con más "
        "detalle -- no existe una etiqueta de verdad de campo (ej. inspección "
        "sobre el terreno) contra la cual validar si el cambio detectado es "
        "'real' en el sentido que un experto agrónomo confirmaría. Es un "
        "candidato a investigar, no una conclusión."
    )


if __name__ == "__main__":
    main()
