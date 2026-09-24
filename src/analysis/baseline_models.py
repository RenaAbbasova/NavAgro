"""
NavAgro — Modelos base de rendimiento (Sprint 3)

Primeros 2 escalones de la "escalera de modelos base": Media Histórica
(línea base mínima) y Regresión Lineal (línea base interpretable usando
NDVI). Mismo patrón conceptual usado en TerraYield para benchmarks de
rendimiento.

División de datos: leave-most-recent-year-out (entrena con 2019+2021,
evalúa contra 2023) -- no un split aleatorio de filas. Con solo 3 años,
un split aleatorio filtraría información del futuro al pasado (la misma
comarca aparecería en train y test simultáneamente para años distintos,
violando independencia temporal) -- lección aplicada de TerraYield sobre
repeated observations no siendo independientes.

AVISO HONESTO: el dataset tiene 42 filas totales (28 para entrenar, 14
para evaluar). Es un tamaño muy pequeño para conclusiones robustas --
estos resultados son un primer benchmark de referencia, no una validación
estadística sólida. Se necesitarán más años de datos (ver Sección 7 de la
propuesta original) antes de tomar estos modelos como predictivos.

Uso:
    python3 src/analysis/baseline_models.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

TEST_YEAR = 2023
TRAIN_YEARS = [2019, 2021]


def load_dataset(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def split_train_test(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df["year"].isin(TRAIN_YEARS)].copy()
    test = df[df["year"] == TEST_YEAR].copy()
    return train, test


def baseline_historical_mean(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Predice la producción de 2023 como el promedio histórico de esa
    misma (comarca, cultivo) en los años de entrenamiento -- la línea
    base más simple posible, sin usar ninguna feature satelital."""
    group_means = train.groupby(["comarca", "cultivo"])["produccion_tn"].mean()
    predictions = test.apply(
        lambda row: group_means.get((row["comarca"], row["cultivo"]), train["produccion_tn"].mean()),
        axis=1,
    )
    return predictions.values


def baseline_linear_regression(
    train: pd.DataFrame, test: pd.DataFrame, feature: str = "ndvi_mean_annual"
) -> np.ndarray:
    """Regresión lineal simple: produccion_tn ~ ndvi_mean_annual.
    Una sola feature a propósito, dado el tamaño pequeño del dataset --
    más features con solo 28 filas de entrenamiento arriesgaría sobreajuste
    sin aportar señal real."""
    model = LinearRegression()
    model.fit(train[[feature]], train["produccion_tn"])
    return model.predict(test[[feature]])


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, model_name: str) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return {"model": model_name, "MAE": mae, "RMSE": rmse, "R2": r2}


def main() -> None:
    dataset_path = Path("outputs/modeling_dataset_v1.csv")
    df = load_dataset(dataset_path)

    train, test = split_train_test(df)
    print(f"Entrenamiento: {len(train)} filas (años {TRAIN_YEARS})")
    print(f"Evaluación: {len(test)} filas (año {TEST_YEAR})")
    print(
        "\nAVISO: dataset muy pequeño (28 train / 14 test) -- estos resultados "
        "son un primer benchmark de referencia, no una validación robusta."
    )

    y_true = test["produccion_tn"].values

    results = []

    pred_historical = baseline_historical_mean(train, test)
    results.append(evaluate(y_true, pred_historical, "Historical Mean"))

    pred_linear = baseline_linear_regression(train, test)
    results.append(evaluate(y_true, pred_linear, "Linear Regression (NDVI)"))

    results_df = pd.DataFrame(results)
    print("\n=== Resultados ===")
    print(results_df.to_string(index=False))

    output_path = Path("outputs/baseline_model_results.csv")
    results_df.to_csv(output_path, index=False)

    predictions_df = test[["comarca", "cultivo", "year", "produccion_tn"]].copy()
    predictions_df["pred_historical_mean"] = pred_historical
    predictions_df["pred_linear_regression"] = pred_linear
    predictions_path = Path("outputs/baseline_model_predictions.csv")
    predictions_df.to_csv(predictions_path, index=False)

    print(f"\nResultados guardados en: {output_path}")
    print(f"Predicciones detalladas guardadas en: {predictions_path}")

    print(
        "\n=== Interpretación ===\n"
        "Si Linear Regression (NDVI) tiene MAE/RMSE menor que Historical Mean, "
        "el NDVI aporta señal predictiva real más allá de simplemente repetir "
        "el promedio histórico. Si no, el NDVI todavía no supera a la línea "
        "base más simple con este tamaño de muestra -- resultado honesto, "
        "no un fallo del enfoque, dado que 28 filas es muy poco para entrenar."
    )


if __name__ == "__main__":
    main()
