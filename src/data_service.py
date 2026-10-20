
import csv
import io
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, ConfigDict


app = FastAPI(
    title="Microservicio de Datos - Riesgo de Incendios",
    description="Validación, normalización y trazabilidad de variables.",
    version="1.0.0",
)


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

    minimo, maximo = rangos[nombre]

    if not minimo <= valor <= maximo:
        raise ValueError(
            f"{nombre}: valor fuera del rango permitido "
            f"({minimo} a {maximo})."
        )


@app.get("/health")
def health():
    return {"estado": "ok", "servicio": "datos"}


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
        validar_rango(nombre, observacion.valor)

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


@app.post("/api/v1/csv")
async def cargar_csv(archivo: UploadFile = File(...)):
    # 1. Comprobar el nombre del archivo.
    if not archivo.filename or not archivo.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Debes subir un archivo con extension .csv.",
        )

    # 2. Limitar el tamaño para evitar archivos excesivos.
    contenido = await archivo.read(MAX_CSV_BYTES + 1)
    await archivo.close()

    if len(contenido) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=413,
            detail="El archivo supera el limite de 5 MB.",
        )

    # 3. Leer CSV en UTF-8, admitiendo BOM.
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="El CSV debe estar codificado en UTF-8.",
        )

    if not texto.strip():
        raise HTTPException(
            status_code=400,
            detail="El archivo CSV esta vacio.",
        )

    # 4. Detectar separador coma o punto y coma.
    try:
        muestra = texto[:8192]
        separador = csv.Sniffer().sniff(
            muestra, delimiters=",;"
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

    # 5. Validar y normalizar cada fila.
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

            if not zona or not fuente or not fecha_texto:
                raise ValueError(
                    "Zona, fuente y fecha son obligatorias."
                )

            fecha = datetime.fromisoformat(
                fecha_texto.replace("Z", "+00:00")
            )

            if fecha.tzinfo is None:
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
                "fecha_observacion": fecha.isoformat(),
            })

        except (ValueError, TypeError, KeyError) as error:
            errores.append({
                "fila": numero_fila,
                "error": str(error),
            })

    # No aceptar parcialmente un archivo con errores.
    if errores:
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": (
                    "El archivo contiene errores. "
                    "Corrige las filas indicadas y vuelve a subirlo."
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

    return {
        "estado": "validado",
        "archivo": archivo.filename,
        "filas_procesadas": len(registros),
        "fecha_procesamiento": datetime.now(
            timezone.utc
        ).isoformat(),
        "registros": registros,
        "advertencia": (
            "Validar el formato no garantiza que la fuente "
            "sea autentica ni que los datos sean actuales."
        ),
    }
