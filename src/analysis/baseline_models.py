"""
NavAgro — Modelos base de rendimiento (Sprint 3, v2)

Extiende el benchmark original con un tercer modelo: Regresión Lineal
Múltiple usando NDVI + NDWI + NDBI juntas, en vez de solo NDVI.

AVISO HONESTO adicional: con 28 filas de entrenamiento y ahora 3 features
en vez de 1, el riesgo de sobreajuste es todavía mayor que en la versión
anterior. Se incluye de todas formas para completar la comparación
metodológica planeada -- el resultado (mejor o peor que el modelo de 1
feature) es informativo en cualquier caso.

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
    group_means = train.groupby(["comarca", "cultivo"])["produccion_tn"].mean()
    predictions = test.apply(
        lambda row: group_means.get((row["comarca"], row["cultivo"]), train["produccion_tn"].mean()),
        axis=1,
    )
    return predictions.values


def linear_regression_model(
    train: pd.DataFrame, test: pd.DataFrame, features: list[str]
) -> np.ndarray:
    model = LinearRegression()
    model.fit(train[features], train["produccion_tn"])
    return model.predict(test[features])


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
        "son un primer benchmark de referencia, no una validación robusta. "
        "El modelo multi-feature tiene aún más riesgo de sobreajuste que el "
        "de una sola variable."
    )

    y_true = test["produccion_tn"].values
    results = []

    pred_historical = baseline_historical_mean(train, test)
    results.append(evaluate(y_true, pred_historical, "Historical Mean"))

    pred_linear_ndvi = linear_regression_model(train, test, ["ndvi_mean_annual"])
    results.append(evaluate(y_true, pred_linear_ndvi, "Linear Regression (NDVI)"))

    multi_features = ["ndvi_mean_annual", "ndwi_mean_annual", "ndbi_mean_annual"]
    pred_linear_multi = linear_regression_model(train, test, multi_features)
    results.append(evaluate(y_true, pred_linear_multi, "Linear Regression (NDVI+NDWI+NDBI)"))

    results_df = pd.DataFrame(results)
    print("\n=== Resultados ===")
    print(results_df.to_string(index=False))

    output_path = Path("outputs/baseline_model_results.csv")
    results_df.to_csv(output_path, index=False)

    predictions_df = test[["comarca", "cultivo", "year", "produccion_tn"]].copy()
    predictions_df["pred_historical_mean"] = pred_historical
    predictions_df["pred_linear_ndvi"] = pred_linear_ndvi
    predictions_df["pred_linear_multi"] = pred_linear_multi
    predictions_path = Path("outputs/baseline_model_predictions.csv")
    predictions_df.to_csv(predictions_path, index=False)

    print(f"\nResultados guardados en: {output_path}")
    print(f"Predicciones detalladas guardadas en: {predictions_path}")

    best_model = results_df.loc[results_df["R2"].idxmax(), "model"]
    print(
        f"\n=== Interpretación ===\n"
        f"Mejor modelo por R²: {best_model}. "
        f"Si sigue siendo Historical Mean, ninguna combinación de features "
        f"satelitales probada hasta ahora supera a la línea base más simple "
        f"con este tamaño de muestra -- resultado honesto, no un fallo del "
        f"enfoque. Más años de datos (ver docs/fuentes_datos.md) son el "
        f"siguiente paso lógico antes de esperar que las features satelitales "
        f"aporten señal medible."
    )


if __name__ == "__main__":
    main()
