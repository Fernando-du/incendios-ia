
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# Localizar el modelo desde la raíz del proyecto.
BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "modelo_riesgo.joblib"

app = FastAPI(
    title="API de Riesgo de Incendios Forestales",
    description=(
        "Prototipo académico para clasificar el riesgo "
        "de incendios forestales."
    ),
    version="1.0.0",
)

# El modelo se carga una vez al iniciar la aplicación.
model = None


class DatosRiesgo(BaseModel):
    zona: str = Field(
        min_length=1,
        max_length=150,
        description="Nombre de la zona evaluada",
    )
    temperatura: float = Field(ge=-30, le=60)
    humedad: float = Field(ge=0, le=100)
    viento: float = Field(ge=0, le=300)
    vegetacion: float = Field(ge=0, le=100)
    incendios_historicos: int = Field(ge=0, le=100000)


@app.on_event("startup")
def cargar_modelo():
    global model

    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"No se encontró el modelo: {MODEL_PATH}. "
            "Ejecuta primero python train_model.py."
        )

    model = joblib.load(MODEL_PATH)


@app.get("/health")
def health():
    return {
        "estado": "ok",
        "modelo_cargado": model is not None,
    }


@app.post("/api/v1/riesgo")
def predecir_riesgo(datos: DatosRiesgo):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="El modelo no está disponible.",
        )

    # El orden y los nombres deben coincidir con el entrenamiento.
    entrada = [[
        datos.temperatura,
        datos.humedad,
        datos.viento,
        datos.vegetacion,
        datos.incendios_historicos,
    ]]

    try:
        riesgo = str(model.predict(entrada)[0])

        probabilidades = model.predict_proba(entrada)[0]
        clases = model.classes_

        return {
            "zona": datos.zona,
            "riesgo": riesgo,
            "probabilidades": {
                str(clase): round(float(probabilidad), 4)
                for clase, probabilidad in zip(
                    clases, probabilidades
                )
            },
            "factores_considerados": {
                "temperatura": datos.temperatura,
                "humedad": datos.humedad,
                "viento": datos.viento,
                "vegetacion": datos.vegetacion,
                "incendios_historicos": (
                    datos.incendios_historicos
                ),
            },
            "modelo": "Random Forest",
            "advertencia": (
                "Prototipo con datos sintéticos. "
                "No utilizar para decisiones reales de emergencia."
            ),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="No se pudo generar la predicción.",
        ) from error
