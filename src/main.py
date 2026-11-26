import json
import os
from pathlib import Path

import joblib
import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "modelo_riesgo.joblib"
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(
    title="API de Riesgo de Incendios Forestales",
    description="Servicio de inferencia IA entrenado con datos reales EMAS / CONAF.",
    version="1.2.0",
)

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

        probs_dict = {
            str(clase): round(float(probabilidad), 4)
            for clase, probabilidad in zip(clases, probabilidades)
        }

        # Persistir predicción en PostgreSQL
        if DATABASE_URL:
            with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
                conn.execute(
                    """
                    INSERT INTO predicciones (zona, riesgo, probabilidades, modelo)
                    VALUES (%s, %s, %s::jsonb, %s)
                    """,
                    (
                        datos.zona,
                        riesgo,
                        json.dumps(probs_dict),
                        "Random Forest (EMAS/CONAF)",
                    ),
                )

        return {
            "zona": datos.zona,
            "riesgo": riesgo,
            "probabilidades": probs_dict,
            "factores_considerados": {
                "temperatura": datos.temperatura,
                "humedad": datos.humedad,
                "viento": datos.viento,
                "vegetacion": datos.vegetacion,
                "incendios_historicos": datos.incendios_historicos,
            },
            "modelo": "Random Forest (Datos Reales EMAS/CONAF)",
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo generar la predicción: {error}",
        ) from error