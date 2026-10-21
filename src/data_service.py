
import csv
import io
import math
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import psycopg
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, ConfigDict


DATABASE_URL = os.getenv("DATABASE_URL")

MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_CSV_ROWS = 10000

COLUMNAS_REQUERIDAS = {
    "zona",
    "temperatura",
    "humedad",
    "viento",
    "vegetacion",
    "incendios_historicos",
    "fecha_observacion",
    "fuente",
}


class Observacion(BaseModel):
    valor: float
    fuente: str = Field(min_length=1, max_length=300)
    fecha_observacion: datetime


class SolicitudDatos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zona: str = Field(min_length=1, max_length=150)
    temperatura: Observacion
    humedad: Observacion
    viento: Observacion
    vegetacion: Observacion
    incendios_historicos: Observacion


def validar_rango(nombre: str, valor: float) -> None:
    rangos = {
        "temperatura": (-30, 60),
        "humedad": (0, 100),
        "viento": (0, 300),
        "vegetacion": (0, 100),
        "incendios_historicos": (0, 100000),
    }

    if not math.isfinite(valor):
        raise ValueError(f"{nombre}: el valor debe ser finito.")

    minimo, maximo = rangos[nombre]

    if not minimo <= valor <= maximo:
        raise ValueError(
            f"{nombre}: valor fuera del rango permitido "
            f"({minimo} a {maximo})."
        )


def inicializar_base_datos():
    if not DATABASE_URL:
        raise RuntimeError(
            "Falta DATABASE_URL. Configura la conexión "
            "a PostgreSQL antes de iniciar el servicio."
        )

    with psycopg.connect(
        DATABASE_URL,
        connect_timeout=5,
    ) as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS importaciones (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                archivo TEXT NOT NULL,
                fecha_importacion TIMESTAMPTZ NOT NULL
                    DEFAULT NOW(),
                filas INTEGER NOT NULL,
                estado TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS observaciones (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                importacion_id BIGINT NOT NULL
                    REFERENCES importaciones(id),
                zona TEXT NOT NULL,
                temperatura DOUBLE PRECISION NOT NULL,
                humedad DOUBLE PRECISION NOT NULL,
                viento DOUBLE PRECISION NOT NULL,
                vegetacion DOUBLE PRECISION NOT NULL,
                incendios_historicos INTEGER NOT NULL,
                fuente TEXT NOT NULL,
                fecha_observacion TIMESTAMPTZ NOT NULL,
                fecha_registro TIMESTAMPTZ NOT NULL
                    DEFAULT NOW()
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS predicciones (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                zona TEXT NOT NULL,
                riesgo TEXT NOT NULL
                    CHECK (riesgo IN ('BAJO', 'MEDIO', 'ALTO')),
                probabilidades JSONB NOT NULL,
                modelo TEXT NOT NULL,
                fecha_prediccion TIMESTAMPTZ NOT NULL
                    DEFAULT NOW(),
                importacion_id BIGINT
                    REFERENCES importaciones(id)
            )
        """)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        inicializar_base_datos()
    except Exception as error:
        raise RuntimeError(
            "No se pudo inicializar PostgreSQL. Comprueba "
            "DATABASE_URL y que el contenedor esté activo."
        ) from error

    yield


app = FastAPI(
    title="Microservicio de Datos - Riesgo de Incendios",
    description="Validación, normalización y trazabilidad de variables.",
    version="1.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "estado": "ok",
        "servicio": "datos",
    }


@app.post("/api/v1/variables")
def preparar_variables(solicitud: SolicitudDatos):
    observaciones = {
        "temperatura": solicitud.temperatura,
        "humedad": solicitud.humedad,
        "viento": solicitud.viento,
        "vegetacion": solicitud.vegetacion,
        "incendios_historicos": solicitud.incendios_historicos,
    }

    variables = {}
    fuentes = {}

    for nombre, observacion in observaciones.items():
        try:
            validar_rango(nombre, observacion.valor)
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=str(error),
            ) from error

        if (
            observacion.fecha_observacion.tzinfo is None
            or observacion.fecha_observacion.utcoffset() is None
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{nombre}: la fecha debe incluir zona horaria."
                ),
            )

        variables[nombre] = observacion.valor
        fuentes[nombre] = {
            "fuente": observacion.fuente,
            "fecha_observacion": (
                observacion.fecha_observacion.isoformat()
            ),
        }

    return {
        "zona": solicitud.zona,
        "fecha_procesamiento": datetime.now(
            timezone.utc
        ).isoformat(),
        "variables": variables,
        "fuentes": fuentes,
        "estado": "validado",
        "advertencia": (
            "La validación de rangos no garantiza que los datos "
            "sean reales, actuales ni adecuados para la zona."
        ),
    }


@app.post("/api/v1/csv")
async def cargar_csv(archivo: UploadFile = File(...)):
    if (
        not archivo.filename
        or not archivo.filename.lower().endswith(".csv")
    ):
        raise HTTPException(
            status_code=400,
            detail="Debes subir un archivo con extensión .csv.",
        )

    contenido = await archivo.read(MAX_CSV_BYTES + 1)
    await archivo.close()

    if len(contenido) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=413,
            detail="El archivo supera el límite de 5 MB.",
        )

    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail="El CSV debe estar codificado en UTF-8.",
        ) from error

    if not texto.strip():
        raise HTTPException(
            status_code=400,
            detail="El archivo CSV está vacío.",
        )

    try:
        separador = csv.Sniffer().sniff(
            texto[:8192],
            delimiters=",;",
        ).delimiter
    except csv.Error:
        separador = ","

    lector = csv.DictReader(
        io.StringIO(texto, newline=""),
        delimiter=separador,
    )

    if not lector.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="No se encontraron encabezados en el CSV.",
        )

    lector.fieldnames = [
        nombre.strip() if nombre else ""
        for nombre in lector.fieldnames
    ]

    if len(set(lector.fieldnames)) != len(lector.fieldnames):
        raise HTTPException(
            status_code=400,
            detail="El CSV contiene encabezados duplicados.",
        )

    faltantes = COLUMNAS_REQUERIDAS - set(lector.fieldnames)

    if faltantes:
        raise HTTPException(
            status_code=400,
            detail={
                "mensaje": "Faltan columnas obligatorias.",
                "columnas_faltantes": sorted(faltantes),
            },
        )

    registros = []
    errores = []

    for numero_fila, fila in enumerate(lector, start=2):
        if numero_fila > MAX_CSV_ROWS + 1:
            raise HTTPException(
                status_code=413,
                detail=f"El CSV supera {MAX_CSV_ROWS} filas.",
            )

        if None in fila:
            errores.append({
                "fila": numero_fila,
                "error": "La fila contiene columnas adicionales.",
            })
            continue

        try:
            zona = (fila.get("zona") or "").strip()
            fuente = (fila.get("fuente") or "").strip()
            fecha_texto = (
                fila.get("fecha_observacion") or ""
            ).strip()

            if len(zona) > 150:
                raise ValueError("La zona supera 150 caracteres.")

            if not fuente or len(fuente) > 300:
                raise ValueError(
                    "La fuente es obligatoria y admite "
                    "hasta 300 caracteres."
                )

            if not fecha_texto:
                raise ValueError("La fecha es obligatoria.")

            if not zona:
                raise ValueError("La zona es obligatoria.")

            fecha = datetime.fromisoformat(
                fecha_texto.replace("Z", "+00:00")
            )

            if (
                fecha.tzinfo is None
                or fecha.utcoffset() is None
            ):
                raise ValueError(
                    "La fecha debe incluir zona horaria, "
                    "por ejemplo Z o -03:00."
                )

            temperatura = float(fila["temperatura"])
            humedad = float(fila["humedad"])
            viento = float(fila["viento"])
            vegetacion = float(fila["vegetacion"])
            historicos_numero = float(
                fila["incendios_historicos"]
            )

            if not historicos_numero.is_integer():
                raise ValueError(
                    "incendios_historicos debe ser un entero."
                )

            historicos = int(historicos_numero)

            valores = {
                "temperatura": temperatura,
                "humedad": humedad,
                "viento": viento,
                "vegetacion": vegetacion,
                "incendios_historicos": historicos,
            }

            for nombre, valor in valores.items():
                validar_rango(nombre, valor)

            registros.append({
                "zona": zona,
                "variables": valores,
                "fuente": fuente,
                "fecha_observacion": fecha,
            })

        except (ValueError, TypeError, KeyError) as error:
            errores.append({
                "fila": numero_fila,
                "error": str(error),
            })

    if errores:
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": (
                    "El archivo contiene errores. Corrige las "
                    "filas indicadas y vuelve a subirlo."
                ),
                "errores": errores[:100],
                "total_errores": len(errores),
            },
        )

    if not registros:
        raise HTTPException(
            status_code=400,
            detail="El CSV no contiene filas de datos.",
        )

    if not DATABASE_URL:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL no está configurada.",
        )

    try:
        with psycopg.connect(
            DATABASE_URL,
            connect_timeout=5,
        ) as conn:

            importacion_id = conn.execute(
                """
                INSERT INTO importaciones
                    (archivo, filas, estado)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (
                    archivo.filename,
                    len(registros),
                    "completada",
                ),
            ).fetchone()[0]

            # Psycopg 3: executemany se invoca desde un cursor.
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO observaciones (
                        importacion_id,
                        zona,
                        temperatura,
                        humedad,
                        viento,
                        vegetacion,
                        incendios_historicos,
                        fuente,
                        fecha_observacion
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            importacion_id,
                            registro["zona"],
                            registro["variables"]["temperatura"],
                            registro["variables"]["humedad"],
                            registro["variables"]["viento"],
                            registro["variables"]["vegetacion"],
                            registro["variables"]["incendios_historicos"],
                            registro["fuente"],
                            registro["fecha_observacion"],
                        )
                        for registro in registros
                    ],
                )

    except psycopg.Error as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "No se pudieron guardar los datos en PostgreSQL. "
                "Comprueba que la base de datos esté disponible."
            ),
        ) from error

    return {
        "estado": "guardado",
        "importacion_id": importacion_id,
        "archivo": archivo.filename,
        "filas_procesadas": len(registros),
        "fecha_procesamiento": datetime.now(
            timezone.utc
        ).isoformat(),
        "mensaje": (
            "Los registros se validaron y guardaron "
            "correctamente en PostgreSQL."
        ),
    }
