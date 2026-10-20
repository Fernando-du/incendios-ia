
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

FEATURES = [
    "temperatura",
    "humedad",
    "viento",
    "vegetacion",
    "incendios_historicos",
]

CLASSES = ["BAJO", "MEDIO", "ALTO"]


def create_demo_dataset(n=5000, seed=42):
    """Genera datos ficticios SOLO para probar el pipeline."""
    rng = np.random.default_rng(seed)

    data = pd.DataFrame({
        "temperatura": rng.uniform(10, 42, n),
        "humedad": rng.uniform(10, 100, n),
        "viento": rng.uniform(0, 70, n),
        "vegetacion": rng.uniform(0, 100, n),
        "incendios_historicos": rng.poisson(2, n),
    })

    # Etiquetas artificiales: no representan un modelo
    # validado con incendios reales.
    score = (
        data["temperatura"] / 42 * 25
        + (100 - data["humedad"]) / 100 * 25
        + data["viento"] / 70 * 20
        + data["vegetacion"] / 100 * 15
        + np.minimum(data["incendios_historicos"], 10) / 10 * 15
    )

    data["riesgo"] = pd.cut(
        score,
        bins=[-np.inf, 35, 60, np.inf],
        labels=CLASSES,
    )

    return data


def main():
    df = create_demo_dataset()

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

    print("Evaluación de prueba (datos sintéticos):")
    print(classification_report(y_test, predictions))

    output = MODEL_DIR / "modelo_riesgo.joblib"
    joblib.dump(model, output)

    print(f"Modelo guardado en: {output}")


if __name__ == "__main__":
    main()
