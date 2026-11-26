from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)
REAL_DATASET_PATH = BASE_DIR / "dataset_real_unificado.csv"

FEATURES = [
    "temperatura",
    "humedad",
    "viento",
    "vegetacion",
    "incendios_historicos",
]

CLASSES = ["BAJO", "MEDIO", "ALTO"]


def cargar_dataset_real():
    if not REAL_DATASET_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró {REAL_DATASET_PATH}. Ejecuta primero python preparar_datos_reales.py"
        )

    df = pd.read_csv(REAL_DATASET_PATH)

    # Índice de peligro meteorológico/histórico basado en variables reales (FWI adaptado)
    score = (
        (df["temperatura"].clip(0, 42) / 42) * 28
        + ((100 - df["humedad"].clip(0, 100)) / 100) * 28
        + (df["viento"].clip(0, 70) / 70) * 18
        + (df["vegetacion"].clip(0, 100) / 100) * 14
        + (np.minimum(df["incendios_historicos"], 50) / 50) * 12
    )

    df["riesgo"] = pd.cut(
        score,
        bins=[-np.inf, 38, 62, np.inf],
        labels=CLASSES,
    )

    return df.dropna(subset=FEATURES + ["riesgo"])


def main():
    df = cargar_dataset_real()
    print(f"Entrenando modelo con {len(df)} registros reales de EMAS + CONAF...")

    X = df[FEATURES]
    y = df["riesgo"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = make_pipeline(
        SimpleImputer(strategy="median"),
        RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print("Evaluación del modelo (Datos Reales EMAS + CONAF):")
    print(classification_report(y_test, predictions))

    output = MODEL_DIR / "modelo_riesgo.joblib"
    joblib.dump(model, output)

    print(f"Modelo actualizado guardado en: {output}")


if __name__ == "__main__":
    main()